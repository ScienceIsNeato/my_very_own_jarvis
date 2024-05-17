import os
import sys
import time
import logging
import subprocess
from datetime import datetime
import re

# Ensure the project root is in the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from music_lib import MusicGenerator

def sanitize_filename(name):
    return re.sub(r'\W+', '_', name.lower())

def test_generate_music(log_level=logging.INFO):
    logging.basicConfig(level=log_level, format='%(asctime)s - %(levelname)s - %(message)s')
    
    # Ensure the environment variable is set
    if 'SUNO_API_KEY' not in os.environ:
        raise EnvironmentError("Environment variable 'SUNO_API_KEY' is not set.")
    
    music_gen = MusicGenerator()
    gpt_description_prompt = "background music for a Ken Burns documentary"
    duration = 10  # Duration in seconds for testing purposes

    response = music_gen.generate_music(gpt_description_prompt, duration=duration)
    logging.info("Generate Music Response: %s", response)

    if 'error' in response:
        logging.error(f"Error: {response['message']}")
        return
    
    song_id = response['data'][0]['song_id']
    logging.info(f"Generated Song ID: {song_id}")

    # Polling the status until the song is ready
    status = "queued"
    last_status = status
    start_time = time.time()
    status_change_time = start_time
    stuck_timeout = 10 * 60  # 10 minutes

    while status in ["queued", "processing", "streaming"]:
        time.sleep(5)
        status_response = music_gen.query_music_status(song_id)
        status = status_response['data']['status']
        
        current_time = time.time()
        elapsed_time = current_time - start_time
        status_elapsed_time = current_time - status_change_time
        
        logging.info(f"Current status: {status} (Elapsed time: {elapsed_time // 60:.0f}m {elapsed_time % 60:.0f}s)")

        if status != last_status:
            last_status = status
            status_change_time = current_time
        elif status_elapsed_time > stuck_timeout:
            logging.error("Music generation appears to be stuck.")
            return

    if status == "complete":
        audio_url = status_response['data']['audio_url']
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        description_sanitized = sanitize_filename(gpt_description_prompt)
        output_path = f"/tmp/GANGLIA/music/{description_sanitized}_{timestamp}.mp3"
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        if music_gen.download_audio(audio_url, output_path):
            logging.info(f"Audio downloaded to {output_path}")
            # Playing the audio file using ffplay
            subprocess.run(["ffplay", "-nodisp", "-autoexit", output_path])
        else:
            logging.error("Failed to download audio.")
    else:
        logging.error("Music generation failed or was not completed.")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate and test music creation.")
    parser.add_argument('--log-level', default='INFO', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                        help='Set the logging level')

    args = parser.parse_args()
    log_level = getattr(logging, args.log_level.upper(), logging.INFO)
    test_generate_music(log_level)
