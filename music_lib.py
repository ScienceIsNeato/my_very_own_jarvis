import requests
import os
import time
import logging
import concurrent.futures

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

    def generate_instrumental_music(self, gpt_description_prompt, model="chirp-v3-0", duration=10):
        endpoint = f"{self.base_url}/gateway/generate/gpt_desc"
        data = {
            "gpt_description_prompt": gpt_description_prompt,
            "make_instrumental": True,
            "mv": model,
            "duration": duration
        }

        logging.debug(f"Sending request to {endpoint} with data: {data}")
        try:
            response = requests.post(endpoint, headers=self.headers, json=data)
            logging.debug(f"Request to {endpoint} completed with status code {response.status_code}")

            if response.status_code == 200:
                logging.debug(f"Response received: {response.json()}")
                return response.json()
            else:
                logging.error(f"Error in response: {response.text}")
                return {"error": response.status_code, "message": response.text}
        except Exception as e:
            logging.error(f"Exception during request to {endpoint}: {e}")
            return {"error": "exception", "message": str(e)}

    def generate_song_with_lyrics(self, gpt_description_prompt, model="chirp-v3-0", duration=10):
        endpoint = f"{self.base_url}/gateway/generate/gpt_desc"
        data = {
            "gpt_description_prompt": gpt_description_prompt,
            "make_instrumental": False,
            "mv": model,
            "duration": duration
        }

        logging.debug(f"Sending request to {endpoint} with data: {data}")
        try:
            response = requests.post(endpoint, headers=self.headers, json=data)
            logging.debug(f"Request to {endpoint} completed with status code {response.status_code}")

            if response.status_code == 200:
                logging.debug(f"Response received: {response.json()}")
                return response.json()
            else:
                logging.error(f"Error in response: {response.text}")
                return {"error": response.status_code, "message": response.text}
        except Exception as e:
            logging.error(f"Exception during request to {endpoint}: {e}")
            return {"error": "exception", "message": str(e)}

    def query_music_status(self, song_id):
        endpoint = f"{self.base_url}/gateway/feed/{song_id}"
        logging.debug(f"Querying status for song ID: {song_id}")
        try:
            response = requests.get(endpoint, headers=self.headers)
            logging.debug(f"Request to {endpoint} completed with status code {response.status_code}")

            if response.status_code == 200:
                logging.debug(f"Status response: {response.json()}")
                return response.json()
            else:
                logging.error(f"Error in status response: {response.text}")
                return {"error": response.status_code, "message": response.text}
        except Exception as e:
            logging.error(f"Exception during request to {endpoint}: {e}")
            return {"error": "exception", "message": str(e)}

    def download_audio(self, audio_url, output_path):
        logging.debug(f"Downloading audio from {audio_url} to {output_path}")
        try:
            response = requests.get(audio_url, stream=True)
            logging.debug(f"Request to download audio completed with status code {response.status_code}")

            if response.status_code == 200:
                with open(output_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                logging.debug(f"Download completed successfully")
                return True
            else:
                logging.error(f"Error downloading audio: {response.text}")
                return False
        except Exception as e:
            logging.error(f"Exception during download: {e}")
            return False

def generate_music_concurrently(full_story_text):
    try:
        music_gen = MusicGenerator()
        with concurrent.futures.ThreadPoolExecutor() as executor:
            logging.info("Submitting music generation tasks...")
            background_music_future = executor.submit(music_gen.generate_instrumental_music, "background music for the final video", "chirp-v3-0", 180)
            song_with_lyrics_future = executor.submit(music_gen.generate_song_with_lyrics, f"Write a song about this story: {full_story_text}", "chirp-v3-0", 180)

            music_path = background_music_future.result()
            logging.info(f"Background music generated: {music_path}")

            song_with_lyrics_path = song_with_lyrics_future.result()
            logging.info(f"Song with lyrics generated: {song_with_lyrics_path}")

        return music_path, song_with_lyrics_path
    except Exception as e:
        logging.error(f"Error generating music concurrently: {e}")
        return None, None
