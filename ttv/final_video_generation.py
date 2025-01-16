import os
import subprocess
from logger import Logger
from .ffmpeg_wrapper import run_ffmpeg_command
from . import parallel_encoding
from utils import get_tempdir

def concatenate_video_segments(video_segments, output_path):
    try:
        temp_dir = os.path.join(os.path.dirname(output_path), "temp_encoded")
        os.makedirs(temp_dir, exist_ok=True)

        # Encode segments in parallel
        Logger.print_info(f"Encoding {len(video_segments)} segments in parallel...")
        
        encoded_segments = parallel_encoding.encode_segments_in_parallel(
            segments=video_segments,
            output_dir=temp_dir
        )
        
        if not encoded_segments:
            Logger.print_error("Failed to encode video segments")
            return None
            
        # Concatenate encoded segments
        Logger.print_info("Concatenating encoded segments...")
        result = parallel_encoding.concatenate_encoded_segments(encoded_segments, output_path)
        
        if result:
            Logger.print_info(f"Main video created at {output_path}")
            return output_path
        else:
            Logger.print_error("Failed to concatenate encoded segments")
            return None

    except Exception as e:
        Logger.print_error(f"Error concatenating video segments: {e}")
        return None

def assemble_final_video(video_segments, music_path=None, song_with_lyrics_path=None, movie_poster_path=None, output_path=None):
    """
    Assembles the final video from given segments, adds background music, and generates closing credits.

    Args:
        video_segments (list): List of paths to video segments.
        music_path (str, optional): Path to the background music file. If None, no background music is added.
        song_with_lyrics_path (str, optional): Path to the song with lyrics file for closing credits. If None, no closing credits are added.
        movie_poster_path (str, optional): Path to the movie poster image for closing credits. Required if song_with_lyrics_path is provided.
        output_path (str, optional): Path to save the final output video. Defaults to "/tmp/final_output.mp4".

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
            closing_credits = generate_closing_credits(movie_poster_path, song_with_lyrics_path, output_path)
            if closing_credits:
                # now all we have to do is stitch together the main content and the credits
                fully_assembled_movie_path = parallel_encoding.append_video_segments([main_video_with_background_music_path, closing_credits], output_path)
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

def generate_closing_credits(movie_poster_path, song_with_lyrics_path, output_path):
    """
    Generates a closing credits video from a still image and an audio file.
    Uses parallel encoding for better performance.

    Args:
        movie_poster_path (str): Path to the still image to be used.
        song_with_lyrics_path (str): Path to the audio file to be used.
        output_path (str): Path to save the generated closing credits video.

    Returns:
        str: Path to the generated closing credits video.
    """
    temp_dir = get_tempdir()
    initial_credits_video_path = os.path.join(temp_dir, "ttv", "initial_credits_video.mp4")
    closing_credits_video_path = os.path.join(temp_dir, "ttv", "closing_credits_video.mp4")
    
    # Ensure the directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # Create a video from the still image and audio with fade-in effect
    ffmpeg_cmd = [
        "ffmpeg", "-y", "-loop", "1", "-i", movie_poster_path, "-i", song_with_lyrics_path,
        "-c:v", "libx264", "-tune", "stillimage", "-c:a", "aac", "-b:a", "192k", "-pix_fmt", "yuv420p",
        "-vf", "fade=in:st=3:d=2", "-shortest", initial_credits_video_path
    ]

    Logger.print_info(f"Creating initial closing credits video from {movie_poster_path} and {song_with_lyrics_path}")
    result = run_ffmpeg_command(ffmpeg_cmd)
    if not result:
        Logger.print_error("Failed to generate initial closing credits video")
        return None

    # Create captions for the song lyrics - let Whisper transcribe without a prompt
    from .audio_alignment import create_word_level_captions
    from .captions import create_dynamic_captions, CaptionEntry

    captions = create_word_level_captions(song_with_lyrics_path, "")
    if not captions:
        Logger.print_error("Failed to generate word-level captions for closing credits")
        return initial_credits_video_path

    # Split captions into segments of roughly equal duration
    segment_duration = 5.0  # 5 seconds per segment
    segments = []
    current_segment = []
    current_duration = 0.0
    segment_start_time = 0.0

    for caption in captions:
        caption_duration = caption.end_time - caption.start_time
        if current_duration + caption_duration > segment_duration and current_segment:
            # Create segment with adjusted timings
            segments.append((segment_start_time, current_segment))
            current_segment = []
            segment_start_time += current_duration
            current_duration = 0.0

        # Adjust timing relative to segment start
        adjusted_caption = CaptionEntry(
            caption.text,
            caption.start_time - segment_start_time,
            caption.end_time - segment_start_time
        )
        current_segment.append(adjusted_caption)
        current_duration += caption_duration

    # Add final segment
    if current_segment:
        segments.append((segment_start_time, current_segment))

    # Process each segment in parallel
    segment_paths = []
    for i, (start_time, _) in enumerate(segments):
        segment_path = os.path.join(temp_dir, "ttv", f"credits_segment_{i}.mp4")
        
        # Extract segment from initial video
        extract_cmd = [
            "ffmpeg", "-y",
            "-i", initial_credits_video_path,
            "-ss", str(start_time),
            "-t", str(segment_duration),
            "-c", "copy",
            segment_path
        ]
        if not run_ffmpeg_command(extract_cmd):
            Logger.print_error(f"Failed to extract segment {i}")
            continue

        segment_paths.append(segment_path)

    # Encode segments in parallel
    encoded_dir = os.path.join(temp_dir, "ttv", "encoded_credits")
    os.makedirs(encoded_dir, exist_ok=True)
    
    encoded_segments = parallel_encoding.encode_segments_in_parallel(
        segments=segment_paths,
        output_dir=encoded_dir
    )

    if not encoded_segments:
        Logger.print_error("Failed to encode credit segments")
        return initial_credits_video_path

    # Concatenate encoded segments
    result = parallel_encoding.concatenate_encoded_segments(encoded_segments, closing_credits_video_path)
    
    if result:
        Logger.print_info(f"Generated closing credits video with captions at {closing_credits_video_path}")
        return closing_credits_video_path
    else:
        Logger.print_error("Failed to concatenate credit segments")
        return initial_credits_video_path



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
            # Check if the video has audio
            ffprobe_cmd = f"ffprobe -v error -select_streams a -show_entries stream=codec_type -of csv=p=0 {final_video_path}"
            has_audio = bool(os.popen(ffprobe_cmd).read().strip())

            if has_audio:
                # Mix video audio with background music
                ffmpeg_cmd = [
                    "ffmpeg", "-y", "-i", final_video_path, "-i", music_path, "-filter_complex",
                    f"[0:a]volume=1.0[v];[1:a]volume={background_music_volume}[m];[v][m]amix=inputs=2:duration=first:dropout_transition=2",
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", main_video_with_background_music_path
                ]
            else:
                # Just use background music as audio track
                ffmpeg_cmd = [
                    "ffmpeg", "-y", "-i", final_video_path, "-i", music_path, "-c:v", "copy",
                    "-c:a", "aac", "-b:a", "192k", "-map", "0:v:0", "-map", "1:a:0",
                    main_video_with_background_music_path
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
