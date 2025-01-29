import os
import subprocess
from logger import Logger
from .ffmpeg_wrapper import run_ffmpeg_command
from .video_generation import append_video_segments, create_still_video_with_fade
from .audio_generation import get_audio_duration
from logger import Logger
import subprocess
from utils import get_tempdir
from typing import Optional, List
from .audio_alignment import create_word_level_captions
from .captions import create_dynamic_captions, create_static_captions, CaptionEntry
from .log_messages import LOG_CLOSING_CREDITS_DURATION
import json
from datetime import datetime

def _get_timestamped_filename(base_name: str) -> str:
    """Generate a timestamped filename."""
    timestamp = datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
    return f"{base_name}_{timestamp}.mp4"

def concatenate_video_segments(video_segments, output_path):
    try:
        # First, ensure all segments have consistent audio streams
        reencoded_segments = []
        for segment in video_segments:
            reencoded_segment = segment.replace(".mp4", "_reencoded.mp4")
            ffmpeg_cmd = [
                "ffmpeg", "-y", "-i", segment,
                "-c:v", "copy",  # Copy video stream
                "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",  # Consistent audio parameters
                reencoded_segment
            ]
            Logger.print_info(f"Re-encoding video segment: {segment} to {reencoded_segment}")
            result = run_ffmpeg_command(ffmpeg_cmd)
            if result:
                Logger.print_info(f"Re-encoded video segment created: reencoded_segment={reencoded_segment}")
                reencoded_segments.append(reencoded_segment)
            else:
                Logger.print_error(f"Error re-encoding video segment: {segment}")
                return None

        # Create concat list with re-encoded segments
        concat_list_path = os.path.join(get_tempdir(), "ttv", "concat_list.txt")
        with open(concat_list_path, "w") as f:
            for segment in reencoded_segments:
                f.write(f"file '{segment}'\n")

        Logger.print_info(f"Concatenating video segments: {reencoded_segments}")
        ffmpeg_cmd = [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_list_path,
            "-c:v", "copy",  # Copy video stream
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",  # Consistent audio parameters
            output_path
        ]
        result = run_ffmpeg_command(ffmpeg_cmd)
        if result:
            Logger.print_info(f"Main video created: output_path={output_path}")
            return output_path
        else:
            Logger.print_error("Failed to concatenate video segments")
            return None
    except Exception as e:
        Logger.print_error(f"Error concatenating video segments: {e}")
        return None

def assemble_final_video(video_segments, music_path=None, song_with_lyrics_path=None, movie_poster_path=None, output_path=None, config=None, closing_credits_lyrics=None):
    """
    Assembles the final video from given segments, adds background music, and generates closing credits.

    Args:
        video_segments (list): List of paths to video segments.
        music_path (str, optional): Path to the background music file. If None, no background music is added.
        song_with_lyrics_path (str, optional): Path to the song with lyrics file for closing credits. If None, no closing credits are added.
        movie_poster_path (str, optional): Path to the movie poster image for closing credits. Required if song_with_lyrics_path is provided.
        output_path (str, optional): Path to save the final output video.
        config (TTVConfig, optional): Configuration object containing caption style and other settings.
        closing_credits_lyrics (str, optional): The lyrics to use for word alignment in closing credits.

    Returns:
        str: Path to the most recent successfully generated video.
    """
    main_video_path = None
    main_video_with_background_music_path = None
    final_output_path = None

    try:
        temp_dir = get_tempdir()
        if not output_path:
            output_path = os.path.join(temp_dir, "ttv", _get_timestamped_filename("final_output"))

        main_video_path = os.path.join(temp_dir, "ttv", _get_timestamped_filename("main_video"))
        Logger.print_info("Concatenating video segments...")
        main_video_path = concatenate_video_segments(video_segments, main_video_path)
        final_output_path = main_video_path  # Update the final output path after this step

        if music_path:
            Logger.print_info("Adding background music to main video...")
            main_video_with_background_music_path = add_background_music_to_video(main_video_path, music_path)
            final_output_path = main_video_with_background_music_path  # Update the final output path after this step
        else:
            Logger.print_info("Skipping background music (disabled in config)")
            main_video_with_background_music_path = main_video_path

        if song_with_lyrics_path:
            Logger.print_info("Generating closing credits...")
            if movie_poster_path:
                closing_credits = generate_closing_credits(movie_poster_path, song_with_lyrics_path, output_path, config, closing_credits_lyrics)
                if closing_credits:
                    # now all we have to do is stitch together the main content and the credits
                    fully_assembled_movie_path = append_video_segments([main_video_with_background_music_path, closing_credits], output_path)
                    final_output_path = fully_assembled_movie_path
                    Logger.print_info(f"Final video with closing credits created: output_path={final_output_path}")
                else:
                    Logger.print_warning("Failed to generate closing credits, using main video without credits")
                    final_output_path = main_video_with_background_music_path
                    Logger.print_info(f"Final video without closing credits created: output_path={final_output_path}")
            else:
                Logger.print_warning("No movie poster available for closing credits, using main video without credits")
                final_output_path = main_video_with_background_music_path
                Logger.print_info(f"Final video without closing credits created: output_path={final_output_path}")
        else:
            Logger.print_info("Skipping closing credits (disabled in config)")
            final_output_path = main_video_with_background_music_path
            Logger.print_info(f"Final video without closing credits created: output_path={final_output_path}")

        play_video(final_output_path)
        return final_output_path

    except (OSError, subprocess.SubprocessError) as e:
        Logger.print_error(f"Error creating final video with music: {e}")
        if final_output_path:
            Logger.print_info(f"Final video created at: output_path={final_output_path}")
            return final_output_path
        elif main_video_path:
            Logger.print_info(f"Final video created at: output_path={main_video_path}")
            return main_video_path
        else:
            fallback_path = os.path.join(get_tempdir(), "ttv", _get_timestamped_filename("fallback_video"))
            Logger.print_info(f"Final video created at: output_path={fallback_path}")
            return fallback_path

def generate_closing_credits(movie_poster_path, song_with_lyrics_path, output_path, config=None, lyrics=None):
    """Generate closing credits video with dynamic captions for song lyrics."""
    # Create initial video with poster and music
    temp_dir = get_tempdir()
    initial_credits_video_path = os.path.join(temp_dir, "initial_credits.mp4")
    closing_credits_video_path = os.path.join(temp_dir, "closing_credits.mp4")

    # Get video duration from audio file
    ffprobe_cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        song_with_lyrics_path
    ]
    result = run_ffmpeg_command(ffprobe_cmd)
    if not result:
        Logger.print_error("Failed to get audio duration")
        return None
    duration = float(result.stdout.decode('utf-8').strip())
    Logger.print_info(f"{LOG_CLOSING_CREDITS_DURATION}: {duration}s")

    # Create video from poster image with duration matching audio
    ffmpeg_cmd = [
        "ffmpeg", "-y",
        "-loop", "1",
        "-i", movie_poster_path,
        "-i", song_with_lyrics_path,
        "-c:v", "libx264",
        "-tune", "stillimage",
        "-c:a", "aac",
        "-b:a", "192k",
        "-pix_fmt", "yuv420p",
        "-shortest",
        initial_credits_video_path
    ]

    result = run_ffmpeg_command(ffmpeg_cmd)
    if not result:
        Logger.print_error("Failed to generate initial closing credits video")
        return None

    # Get caption style from config
    caption_style = getattr(config, 'caption_style', 'static') if config else 'static'

    # Create captions for the song lyrics - use provided lyrics if available
    captions = create_word_level_captions(song_with_lyrics_path, lyrics if lyrics else "")
    if not captions:
        Logger.print_error("Failed to create captions for closing credits")
        return initial_credits_video_path

    if caption_style == "dynamic":
        # Add dynamic captions to the video
        captioned_path = create_dynamic_captions(
            input_video=initial_credits_video_path,
            captions=captions,
            output_path=closing_credits_video_path,
            min_font_size=32,
            max_font_size=48
        )
    else:
        # Combine all captions into one for static display
        combined_text = " ".join(c.text for c in captions)
        static_captions = [CaptionEntry(combined_text, 0.0, duration)]
        
        # Add static captions to the video
        captioned_path = create_static_captions(
            input_video=initial_credits_video_path,
            captions=static_captions,
            output_path=closing_credits_video_path,
            font_size=40
        )

    if captioned_path:
        Logger.print_info(f"Generated closing credits video with captions at {closing_credits_video_path}")
        return closing_credits_video_path
    else:
        Logger.print_error("Failed to add captions to closing credits video")
        return initial_credits_video_path

def play_video(video_path):
    """Play a video file if playback is enabled."""
    if os.getenv('PLAYBACK_MEDIA_IN_TESTS', 'false').lower() == 'true':
        try:
            subprocess.run(["ffplay", "-autoexit", video_path], check=True)
        except subprocess.CalledProcessError as e:
            Logger.print_error(f"Error playing video: {e}")

def add_background_music_to_video(final_video_path, music_path):
    if final_video_path is None:
        Logger.print_error("Final video path is None")
        return None
    if music_path is None:
        Logger.print_error("Music path is None")
        return None

    # Ensure music_path is a string, not a dictionary
    if isinstance(music_path, dict):
        music_path = music_path.get('path')
        if music_path is None:
            Logger.print_error("Music path is missing in the dictionary")
            return None

    background_music_volume = 0.3  # Adjust this value to change the relative volume of the background music
    main_video_with_background_music_path = "/tmp/GANGLIA/ttv/main_video_with_background_music.mp4"
    
    try:
        # Mix the audio streams with consistent parameters
        ffmpeg_cmd = [
            "ffmpeg", "-y", 
            "-i", final_video_path, 
            "-i", music_path,
            "-filter_complex",
            f"[0:a]aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo[v];"
            f"[1:a]aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo,volume={background_music_volume}[m];"
            "[v][m]amix=inputs=2:duration=first:dropout_transition=2",
            "-c:v", "copy",  # Copy video stream
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",  # Consistent audio parameters
            main_video_with_background_music_path
        ]
        result = run_ffmpeg_command(ffmpeg_cmd)
        if result:
            Logger.print_info(f"Final video with background music created at {main_video_with_background_music_path}")
            return main_video_with_background_music_path
        else:
            Logger.print_error("Failed to add background music")
            return final_video_path

    except Exception as e:
        Logger.print_error(f"Error adding background music: {e}")
        return final_video_path
