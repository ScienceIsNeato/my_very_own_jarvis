import os
import subprocess
import time
from music_lib import MusicGenerator
from datetime import datetime
from logger import Logger
from .ffmpeg_wrapper import run_ffmpeg_command

def add_background_music(video_path, music_path, output_path, video_volume=1.0, music_volume=0.3):
    Logger.print_info("Adding background music to final video.")
    ffmpeg_cmd = [
        "ffmpeg", "-y", "-i", video_path, "-i", music_path, "-filter_complex",
        f"[0:a]volume={video_volume}[v];[1:a]volume={music_volume}[m];[v][m]amix=inputs=2:duration=first:dropout_transition=2",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", output_path
    ]
    result = run_ffmpeg_command(ffmpeg_cmd)
    if result:
        Logger.print_info(f"Final video with background music created at {output_path}")


def generate_song_with_lyrics(story):
    try:
        music_gen = MusicGenerator()
        description_prompt = f"Write a song about this story: {story}"
        response = music_gen.generate_music(description_prompt, make_instrumental=False, duration=180)
        if 'error' in response:
            Logger.print_error(f"Music generation error: {response['message']}")
            return None
        song_id = response['data'][0]['song_id']
        status = "queued"
        start_time = time.time()
        while status in ["queued", "processing", "streaming"]:
            elapsed_time = time.time() - start_time
            estimated_time_left = max(60 - elapsed_time, 0)  # Assuming 60 seconds typical duration
            Logger.print_info(f"Current music generation status: {status} - Estimated time left: {estimated_time_left:.2f} seconds")
            time.sleep(5)
            status_response = music_gen.query_music_status(song_id)
            status = status_response['data']['status']
        if status == "complete":
            audio_url = status_response['data']['audio_url']
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = f"/tmp/GANGLIA/ttv/song_with_lyrics_{timestamp}.mp3"
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            if music_gen.download_audio(audio_url, output_path):
                Logger.print_info(f"Song with lyrics downloaded to {output_path}")
                return output_path
            else:
                Logger.print_error("Failed to download song with lyrics.")
                return None
        else:
            Logger.print_error("Music generation failed or was not completed.")
            return None
    except Exception as e:
        Logger.print_error(f"Error generating song with lyrics: {e}")
        return None

def add_background_music_to_video(final_video_path, music_path):
    final_video_with_music_path = "/tmp/GANGLIA/ttv/final_video_with_music.mp4"
    try:
        if music_path:
            ffmpeg_cmd = [
                "ffmpeg", "-y", "-i", final_video_path, "-i", music_path, "-filter_complex",
                f"[0:a]volume=1.0[v];[1:a]volume=0.3[m];[v][m]amix=inputs=2:duration=first:dropout_transition=2",
                "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", final_video_with_music_path
            ]
            Logger.print_info(f"Running ffmpeg command: {' '.join(ffmpeg_cmd)}")
            result = subprocess.run(ffmpeg_cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            Logger.print_info(f"ffmpeg output: {result.stdout.decode('utf-8')}")
            Logger.print_info(f"Final video with background music created at {final_video_with_music_path}")
        else:
            Logger.print_error("Background music generation failed. Playing final video without background music.")
            final_video_with_music_path = final_video_path
    except Exception as e:
        Logger.print_error(f"Error adding background music: {e}")
        final_video_with_music_path = final_video_path
    return final_video_with_music_path