import subprocess
from logger import Logger
from music_lib import generate_music_concurrently
from ttv.music_generation import add_background_music_to_video
from .ffmpeg_wrapper import run_ffmpeg_command
from .video_generation import append_video_segments, create_still_video_with_fade
from .image_generation import generate_movie_poster
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
            Logger.print_info(f"Final video created at {output_path}")
            subprocess.run(["ffplay", "-autoexit", output_path])
    except Exception as e:
        Logger.print_error(f"Error concatenating video segments: {e}")

def create_final_video_with_music(video_segments, style, context, full_story_text, tts, skip_generation, output_path):
    final_video_path = None
    final_video_with_music_path = None
    final_output_path = None
    try:
        Logger.print_info("Generating movie poster...")
        movie_poster_path = generate_movie_poster(context, style, full_story_text)
        Logger.print_info(f"Movie poster saved to {movie_poster_path}")

        Logger.print_info("Generating music concurrently...")
        music_path, song_with_lyrics_path = generate_music_concurrently(full_story_text)

        if not music_path or not song_with_lyrics_path:
            raise Exception("Music generation failed")

        Logger.print_info("Concatenating video segments...")
        final_video_path = concatenate_video_segments(video_segments, "/tmp/final_video.mp4")
        Logger.print_info("Adding background music to final video...")
        final_video_with_music_path = add_background_music_to_video(final_video_path, music_path)
        Logger.print_info("Generating closing credits...")
        final_output_path = generate_closing_credits(final_video_with_music_path, song_with_lyrics_path, movie_poster_path, full_story_text, output_path)
        
        subprocess.run(["ffplay", "-autoexit", final_output_path])
    except Exception as e:
        Logger.print_error(f"Error creating final video with music: {e}")
        play_video_if_error(video_segments, final_video_path, final_video_with_music_path, final_output_path)

def generate_closing_credits(final_video_with_music_path, song_with_lyrics_path, movie_poster_path, full_story_text, output_path):
    closing_credits_video_path = "/tmp/closing_credits_video.mp4"
    song_duration = get_audio_duration(song_with_lyrics_path)
    create_still_video_with_fade(movie_poster_path, song_with_lyrics_path, closing_credits_video_path, duration=song_duration)
    Logger.print_info(f"Generated closing credits video at {closing_credits_video_path}")

    final_output_path = output_path if output_path else "/tmp/final_video_with_closing_credits.mp4"
    append_video_segments([final_video_with_music_path, closing_credits_video_path], final_output_path)
    return final_output_path

def play_video_if_error(video_segments, final_video_path=None, final_video_with_music_path=None, final_output_path=None):
    try:
        if final_output_path:
            Logger.print_info(f"Playing final video with closing credits: {final_output_path}")
            subprocess.run(["ffplay", "-autoexit", final_output_path])
        elif final_video_with_music_path:
            Logger.print_info(f"Playing final video with background music: {final_video_with_music_path}")
            subprocess.run(["ffplay", "-autoexit", final_video_with_music_path])
        elif final_video_path:
            Logger.print_info(f"Playing final video: {final_video_path}")
            subprocess.run(["ffplay", "-autoexit", final_video_path])
    except Exception as e:
        Logger.print_error(f"Error playing video: {e}")
