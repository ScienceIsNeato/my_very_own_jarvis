import requests
import os
import time
import logging

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

    def generate_music(self, gpt_description_prompt, make_instrumental=True, model="chirp-v3-0", duration=10, prompt=""):
        endpoint = f"{self.base_url}/gateway/generate/gpt_desc"
        data = {
            "gpt_description_prompt": gpt_description_prompt,
            "make_instrumental": make_instrumental,
            "mv": model,
            "prompt": prompt,
            "duration": duration  # Ensure duration is passed correctly
        }

        logging.debug(f"Sending request to {endpoint} with data: {data}")
        response = requests.post(endpoint, headers=self.headers, json=data)
        if response.status_code == 200:
            logging.debug(f"Response received: {response.json()}")
            return response.json()
        else:
            logging.error(f"Error in response: {response.text}")
            return {"error": response.status_code, "message": response.text}

    def query_music_status(self, song_id):
        endpoint = f"{self.base_url}/gateway/feed/{song_id}"
        logging.debug(f"Querying status for song ID: {song_id}")
        response = requests.get(endpoint, headers=self.headers)
        if response.status_code == 200:
            logging.debug(f"Status response: {response.json()}")
            return response.json()
        else:
            logging.error(f"Error in status response: {response.text}")
            return {"error": response.status_code, "message": response.text}

    def download_audio(self, audio_url, output_path):
        logging.debug(f"Downloading audio from {audio_url} to {output_path}")
        response = requests.get(audio_url, stream=True)
        if response.status_code == 200:
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            logging.debug(f"Download completed successfully")
            return True
        else:
            logging.error(f"Error downloading audio: {response.text}")
            return False
