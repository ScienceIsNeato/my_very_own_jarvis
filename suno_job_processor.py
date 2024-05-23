from datetime import datetime
import os
import time
import requests
from logger import Logger

class SunoJobProcessor:
    def __init__(self):
        self.api_key = os.getenv('SUNO_API_KEY')
        if not self.api_key:
            raise EnvironmentError("Environment variable 'SUNO_API_KEY' is not set.")
        
        self.base_url = "https://api.suno.com"  # Replace with the actual base URL
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def wait_for_completion(self, job_id, with_lyrics):
        complete = False
        audio_url = None
        expected_duration = 30 if with_lyrics else 120
        start_time = datetime.now()

        log_file_path = "/tmp/GANGLIA/analytics.log"

        # Ensure the directory exists
        os.makedirs(os.path.dirname(log_file_path), exist_ok=True)

        while not complete:
            time_elapsed = (datetime.now() - start_time).total_seconds()
            expected_time_remaining = int(expected_duration - time_elapsed)
            time.sleep(5)  # Check every 5 seconds
            music_type = "song_with_lyrics" if with_lyrics else "instrumental"
            Logger.print_info(f"Music generation for {music_type} in progress... Expected time remaining: {expected_time_remaining} seconds")
            status_response = self.query_music_status(job_id)
            if status_response.get("status") == "complete":
                complete = True
                audio_url = status_response.get("audio_url")
                # Log the completion time to /tmp/GANGLIA/analytics.log
                completion_time = (datetime.now() - start_time).total_seconds()
                with open(log_file_path, "a") as log_file:
                    log_file.write(f"Completion time for {music_type} (job_id: {job_id}): {completion_time} seconds\n")
            elif status_response.get("status") == "error":
                Logger.print_error("Audio generation failed")
                return {"error": "audio_generation_failed", "message": "Audio generation failed."}

        return audio_url

    def query_music_status(self, song_id):
        endpoint = f"{self.base_url}/gateway/query?ids={song_id}"
        try:
            response = requests.get(endpoint, headers=self.headers)
            if response.status_code == 200:
                return response.json()[0]  # Assuming the response is a list
            else:
                Logger.print_error(f"Error in status response: {response.text}")
                return {"error": response.status_code, "message": response.text}
        except Exception as e:
            Logger.print_error(f"Exception during request to {endpoint}: {e}")
            return {"error": "exception", "message": str(e)}

    def download_audio(self, audio_url, output_path):
        Logger.print_debug(f"Downloading audio from {audio_url} to {output_path}")
        try:
            response = requests.get(audio_url, stream=True)
            Logger.print_debug(f"Request to download audio completed with status code {response.status_code}")

            if response.status_code == 200:
                with open(output_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                Logger.print_debug(f"Download completed successfully")
                return True
            else:
                Logger.print_error(f"Error downloading audio: {response.text}")
                return False
        except Exception as e:
            Logger.print_error(f"Exception during download: {e}")
            return False
