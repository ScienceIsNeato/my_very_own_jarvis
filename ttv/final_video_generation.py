import os
import subprocess
from logger import Logger
from .ffmpeg_wrapper import run_ffmpeg_command
from .video_generation import append_video_segments, create_still_video_with_fade
from .audio_generation import get_audio_duration
from logger import Logger
import subprocess

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

def assemble_final_video(video_segments, music_path=None, song_with_lyrics_path=None, movie_poster_path=None, output_path="/tmp/final_output.mp4"):
    """
    Assembles the final video from given segments, adds background music, and generates closing credits.

    Args:
        video_segments (list): List of paths to video segments.
        music_path (str, optional): Path to the background music file. Defaults to None.
        song_with_lyrics_path (str, optional): Path to the song with lyrics file for closing credits. Defaults to None.
        movie_poster_path (str, optional): Path to the movie poster image for closing credits. Defaults to None.
        output_path (str, optional): Path to save the final output video. Defaults to "/tmp/final_output.mp4".

    Returns:
        str: Path to the most recent successfully generated video.
    """
    main_video_path = None
    main_video_with_background_music_path = None
    final_output_path = None

    try:
        Logger.print_info("Concatenating video segments...")
        main_video_path = concatenate_video_segments(video_segments, "/tmp/GANGLIA/final_video.mp4")
        final_output_path = main_video_path  # Update the final output path after this step

        if music_path:
            Logger.print_info("Adding background music to main video...")
            main_video_with_background_music_path = add_background_music_to_video(main_video_path, music_path)
            final_output_path = main_video_with_background_music_path  # Update the final output path after this step
        else:
            main_video_with_background_music_path = main_video_path

        if movie_poster_path and song_with_lyrics_path:
            Logger.print_info("Generating closing credits...")
            closing_credits = generate_closing_credits(movie_poster_path, song_with_lyrics_path, output_path)
            # now all we have to do is stitch together the main content and the credits
            fully_assembled_movie_path = append_video_segments([main_video_with_background_music_path, closing_credits], output_path)
            final_output_path = fully_assembled_movie_path
        else:
            final_output_path = main_video_with_background_music_path

        subprocess.run(["ffplay", "-autoexit", final_output_path])
        return final_output_path

    except Exception as e:
        Logger.print_error(f"Error creating final video with music: {e}")
        return final_output_path if final_output_path else main_video_path if main_video_path else "/tmp/final_video.mp4"

def generate_closing_credits(movie_poster_path, song_with_lyrics_path, output_path):
    """
    Generates a closing credits video from a still image and an audio file.

    Args:
        movie_poster_path (str): Path to the still image to be used.
        song_with_lyrics_path (str): Path to the audio file to be used.
        output_path (str): Path to save the generated closing credits video.

    Returns:
        str: Path to the generated closing credits video.
    """
    closing_credits_video_path = "/tmp/GANGLIA/ttv/closing_credits_video.mp4"
    
    # Ensure the directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # Create a video from the still image and audio
    ffmpeg_cmd = [
        "ffmpeg", "-y", "-loop", "1", "-i", movie_poster_path, "-i", song_with_lyrics_path,
        "-c:v", "libx264", "-tune", "stillimage", "-c:a", "aac", "-b:a", "192k", "-pix_fmt", "yuv420p",
        "-shortest", closing_credits_video_path
    ]

    Logger.print_info(f"Creating closing credits video from {movie_poster_path} and {song_with_lyrics_path}")
    result = run_ffmpeg_command(ffmpeg_cmd)
    if result:
        Logger.print_info(f"Generated closing credits video at {closing_credits_video_path}")
        return closing_credits_video_path
    else:
        Logger.print_error("Failed to generate closing credits video")
        return None

def play_video_if_error(video_segments, main_video_path=None, main_video_with_background_music_path=None, final_output_path=None):
    try:
        if final_output_path:
            Logger.print_info(f"Playing final video with closing credits: {final_output_path}")
            subprocess.run(["ffplay", "-autoexit", final_output_path])
        elif main_video_with_background_music_path:
            Logger.print_info(f"Playing final video with background music: {main_video_with_background_music_path}")
            subprocess.run(["ffplay", "-autoexit", main_video_with_background_music_path])
        elif main_video_path:
            Logger.print_info(f"Playing final video: {main_video_path}")
            subprocess.run(["ffplay", "-autoexit", main_video_path])
    except Exception as e:
        Logger.print_error(f"Error playing video: {e}")

def add_background_music_to_video(final_video_path, music_path):
    if final_video_path is None:
        Logger.print_error("Final video path is None")
        return None
    if music_path is None:
        Logger.print_error("Music path is None")
        return None
    main_video_with_background_music_path = "/tmp/GANGLIA/ttv/main_video_with_background_music.mp4"
    try:
        if music_path:
            ffmpeg_cmd = [
                "ffmpeg", "-y", "-i", final_video_path, "-i", music_path, "-filter_complex",
                "[0:a]volume=1.0[v];[1:a]volume=0.3[m];[v][m]amix=inputs=2:duration=first:dropout_transition=2",
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
    except Exception as e:
        Logger.print_error(f"Error adding background music: {e}")
        main_video_with_background_music_path = final_video_path
    return main_video_with_background_music_path