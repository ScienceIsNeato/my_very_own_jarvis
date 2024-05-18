from datetime import datetime
import time
import requests
import os
import logging
from logger import Logger

class MusicGenerator:
    def __init__(self):
        self.api_key = os.getenv('SUNO_API_KEY')
        if not self.api_key:
            raise EnvironmentError("Environment variable 'SUNO_API_KEY' is not set.")
        
        self.base_url = "https://api.sunoaiapi.com/api/v1"
        self.headers = {
            "api-key": self.api_key,
            "Content-Type": "application/json"
        }

    def generate_music(self, prompt, model="chirp-v3-0", duration=10, with_lyrics=False, max_length=4096):
        """
        Generates audio based on the given prompt, with options for instrumental or with lyrics.

        Args:
            prompt (str): The prompt for generating the audio.
            model (str): The model to be used for generation. Defaults to "chirp-v3-0".
            duration (int): The duration of the generated audio in seconds. Defaults to 10.
            with_lyrics (bool): Whether to generate audio with lyrics. Defaults to False.
            max_length (int): The maximum length of the prompt. Defaults to 4096.

        Returns:
            str: Path to the generated audio file, or an error message.
        """
        Logger.print_debug(f"Generating audio with prompt: {prompt}")

        if len(prompt) > max_length:
            original_length = len(prompt)
            prompt = prompt[:max_length]
            Logger.print_info(f"Truncated prompt from {original_length} to {max_length} characters")

        endpoint = f"{self.base_url}/gateway/generate/gpt_desc" if not with_lyrics else f"{self.base_url}/gateway/generate/music"
        data = {
            "gpt_description_prompt": prompt if not with_lyrics else None,
            "prompt": prompt if with_lyrics else None,
            "make_instrumental": not with_lyrics,
            "mv": model,
            "duration": duration,
        }

        if with_lyrics:
            data["title"] = "Generated Song"
            data["tags"] = "general"

        # Remove keys with None values to prevent validation errors
        data = {k: v for k, v in data.items() if v is not None}

        Logger.print_debug(f"Sending request to {endpoint} with data: {data}")
        try:
            response = requests.post(endpoint, headers=self.headers, json=data)
            Logger.print_debug(f"Request to {endpoint} completed with status code {response.status_code}")

            if response.status_code == 200:
                Logger.print_debug(f"Response received: {response.json()}")
                job_data = response.json().get("data", [])[0]  # Accessing the first item in the list
                job_id = job_data.get("song_id")
                if not job_id:
                    Logger.print_info("No job ID found in response.")
                    return

                Logger.print_info("Waiting for audio generation to complete...")
                complete = False
                audio_url = None
                expected_duration = 30 if with_lyrics else 120
                start_time = datetime.now()
                while not complete:
                    time_elapsed = (datetime.now() - start_time).total_seconds()
                    expected_time_remaining = int(expected_duration - time_elapsed)
                    time.sleep(5)  # Check every 5 seconds
                    music_type = "song_with_lyrics" if with_lyrics else "instrumental"
                    Logger.print_info(f"Music generation for {music_type} in progress... Expected time remaining: {expected_time_remaining} seconds ".format(time_remaining=expected_duration))
                    status_response = self.query_music_status(job_id)
                    if status_response.get("status") == "complete":
                        complete = True
                        audio_url = status_response.get("audio_url")
                    elif status_response.get("status") == "error":
                        Logger.print_error("Audio generation failed")
                        return

                filename = f"generated_{'song_with_lyrics' if with_lyrics else 'instrumental'}_{int(time.time())}.mp3"
                local_path = os.path.join("/tmp/GANGLIA/ttv", filename)

                if self.download_audio(audio_url, local_path):
                    return local_path
                else:
                    Logger.print_error(f"Failed to download audio from {audio_url}")
                    return {"error": "download_failed", "message": "Failed to download generated audio"}
            else:
                Logger.print_error(f"Error in response: {response.text}")
                return {"error": response.status_code, "message": response.text}
        except Exception as e:
            Logger.print_error(f"Exception during request to {endpoint}: {e}")
            return {"error": "exception", "message": str(e)}

    # Helper Functions (Assumed to be implemented elsewhere in your codebase)
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
