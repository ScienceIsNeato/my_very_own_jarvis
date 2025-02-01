import os
import time
import requests
from datetime import datetime
from logger import Logger
from suno_request_handler import SunoRequestHandler
from utils import get_tempdir

class SunoJobProcessor:
    def wait_for_completion(self, job_id, with_lyrics):
        complete = False
        audio_url = None
        expected_duration = 30 if with_lyrics else 120
        start_time = datetime.now()

        log_file_path = get_tempdir() + "/analytics.log" # TODO: not sure what this file is for

        # Ensure the directory exists
        os.makedirs(os.path.dirname(log_file_path), exist_ok=True)

        Logger.print_debug(f"Entering wait_for_completion method...")

        while not complete:
            time_elapsed = (datetime.now() - start_time).total_seconds()
            expected_time_remaining = int(expected_duration - time_elapsed)
            time.sleep(5)  # Check every 5 seconds
            music_type = "song_with_lyrics" if with_lyrics else "instrumental"
            Logger.print_info(f"Music generation for {music_type} in progress... Expected time remaining: {expected_time_remaining} seconds")
            status_response = self.query_music_status(job_id)
            Logger.print_debug(f"Status response: {status_response}")

            if status_response.get("status") == "complete":
                complete = True
                audio_url = status_response.get("audio_url")
                # Log the completion time to get_tempdir()/analytics.log
                completion_time = (datetime.now() - start_time).total_seconds()
                with open(log_file_path, "a") as log_file:
                    log_file.write(f"Completion time for {music_type} (job_id: {job_id}): {completion_time} seconds\n")
            elif status_response.get("status") == "error":
                Logger.print_error("Audio generation failed")
                return {"error": "audio_generation_failed", "message": "Audio generation failed."}

        return audio_url

    def query_music_status(self, song_id):
        data = {"ids": song_id}
        endpoint = f"{self.base_url}/gateway/query"
        Logger.print_debug(f"Querying music status for song ID: {song_id}")
        
        retries = 3
        wait_time = 5

        Logger.print_debug("TESTY about to send from query_music")
        return SunoRequestHandler().send_request(endpoint, data, retries=retries, wait_time=wait_time)
