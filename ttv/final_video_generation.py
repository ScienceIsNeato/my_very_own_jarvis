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

def concatenate_video_segments(video_segments, output_path):
    try:
        concat_list_path = "/tmp/concat_list.txt"
        with open(concat_list_path, "w") as f:
            for segment in video_segments:
                f.write(f"file '{segment}'\n")
        Logger.print_info(f"Concatenating video segments: {video_segments}")
        ffmpeg_cmd = [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_list_path,
            "-pix_fmt", "yuv420p", "-c:v", "libx264", "-crf", "23", "-preset", "medium",
            "-c:a", "aac", "-b:a", "192k", output_path
        ]
        result = run_ffmpeg_command(ffmpeg_cmd)
        if result:
            Logger.print_info(f"Main video created at {output_path}")
    except Exception as e:
        Logger.print_error(f"Error concatenating video segments: {e}")

    return output_path

def assemble_final_video(video_segments, music_path=None, song_with_lyrics_path=None, movie_poster_path=None, output_path=None, config=None):
    """
    Assembles the final video from given segments, adds background music, and generates closing credits.

    Args:
        video_segments (list): List of paths to video segments.
        music_path (str, optional): Path to the background music file. If None, no background music is added.
        song_with_lyrics_path (str, optional): Path to the song with lyrics file for closing credits. If None, no closing credits are added.
        movie_poster_path (str, optional): Path to the movie poster image for closing credits. Required if song_with_lyrics_path is provided.
        output_path (str, optional): Path to save the final output video. Defaults to "/tmp/final_output.mp4".
        config (TTVConfig, optional): Configuration object containing caption style and other settings.

    Returns:
        str: Path to the most recent successfully generated video.
    """
    if not output_path:
        temp_dir = get_tempdir()
        output_path = os.path.join(temp_dir, "ttv", "final_output.mp4")
    
    main_video_path = None
    main_video_with_background_music_path = None
    final_output_path = None

    try:
        temp_dir = get_tempdir()
        main_video_path = os.path.join(temp_dir, "ttv", "final_video.mp4")
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

        if movie_poster_path and song_with_lyrics_path:
            Logger.print_info("Generating closing credits...")
            closing_credits = generate_closing_credits(movie_poster_path, song_with_lyrics_path, output_path, config)
            if closing_credits:
                # now all we have to do is stitch together the main content and the credits
                fully_assembled_movie_path = append_video_segments([main_video_with_background_music_path, closing_credits], output_path)
                final_output_path = fully_assembled_movie_path
            else:
                Logger.print_error("Failed to generate closing credits, using main video without credits")
                final_output_path = main_video_with_background_music_path
        else:
            Logger.print_info("Skipping closing credits (disabled in config)")
            final_output_path = main_video_with_background_music_path

        subprocess.run(["ffplay", "-autoexit", final_output_path], check=True)
        return final_output_path

    except (OSError, subprocess.SubprocessError) as e:
        Logger.print_error(f"Error creating final video with music: {e}")
        return final_output_path if final_output_path else main_video_path if main_video_path else "/tmp/final_video.mp4"

def generate_closing_credits(movie_poster_path, song_with_lyrics_path, output_path, config=None):
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

    # Create captions for the song lyrics - let Whisper transcribe without a prompt
    captions = create_word_level_captions(song_with_lyrics_path, "")
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
            size_ratio=1.5  # Scale up to 48px
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

def play_video_if_error(video_segments, main_video_path=None, main_video_with_background_music_path=None, final_output_path=None):
    try:
        if final_output_path:
            Logger.print_info(f"Playing final video with closing credits: {final_output_path}")
            subprocess.run(["ffplay", "-autoexit", final_output_path], check=True)
        elif main_video_with_background_music_path:
            Logger.print_info(f"Playing final video with background music: {main_video_with_background_music_path}")
            subprocess.run(["ffplay", "-autoexit", main_video_with_background_music_path], check=True)
        elif main_video_path:
            Logger.print_info(f"Playing final video: {main_video_path}")
            subprocess.run(["ffplay", "-autoexit", main_video_path], check=True)
    except (OSError, subprocess.SubprocessError) as e:
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
        # Assuming the dictionary has a key 'path' that holds the music file path
        music_path = music_path.get('path')
        if music_path is None:
            Logger.print_error("Music path is missing in the dictionary")
            return None

    background_music_volume = 0.3  # Adjust this value to change the relative volume of the background music

    main_video_with_background_music_path = "/tmp/GANGLIA/ttv/main_video_with_background_music.mp4"
    try:
        if music_path:
            ffmpeg_cmd = [
                "ffmpeg", "-y", "-i", final_video_path, "-i", music_path, "-filter_complex",
                f"[0:a]volume=1.0[v];[1:a]volume={background_music_volume}[m];[v][m]amix=inputs=2:duration=first:dropout_transition=2",
                "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", main_video_with_background_music_path
            ]
            result = run_ffmpeg_command(ffmpeg_cmd)
            if result is not None:
                Logger.print_info(f"Final video with background music created at {main_video_with_background_music_path}")
            else:
                Logger.print_error("Failed to add background music. Playing final video without background music.")
                main_video_with_background_music_path = final_video_path
        else:
            Logger.print_error("Background music generation failed. Playing final video without background music.")
            main_video_with_background_music_path = final_video_path
    except (OSError, subprocess.SubprocessError) as e:
        Logger.print_error(f"Error adding background music: {e}")
        main_video_with_background_music_path = final_video_path
    return main_video_with_background_music_path
