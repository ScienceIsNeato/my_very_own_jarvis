import os
import time
import json
import requests
import re
from datetime import datetime
from lyrics_lib import LyricsGenerator
from logger import Logger

class MusicGenerator:
    def __init__(self):
        self.api_base_url = 'https://api.sunoaiapi.com/api/v1'
        self.api_key = os.getenv('SUNO_API_KEY')
        if not self.api_key:
            raise EnvironmentError("Environment variable 'SUNO_API_KEY' is not set.")
        self.headers = {
            'api-key': self.api_key,
            'Content-Type': 'application/json'
        }

    def generate_music(self, prompt, model="chirp-v3-5", duration=10, with_lyrics=False, story_text=None, retries=5, wait_time=60, query_dispatcher=None):
        Logger.print_debug(f"Generating audio with prompt: {prompt}")

        if with_lyrics and story_text:
            song_id = self.start_lyrical_song_job(prompt, model, story_text, query_dispatcher)
        elif with_lyrics and not story_text:
            Logger.print_error("Error: Story text is required when generating audio with lyrics.")
            return None
        else:
            song_id = self.start_instrumental_song_job(prompt, model)

        if not song_id:
            Logger.print_error("Failed to start music generation job.")
            return None

        # Poll the job status until complete
        audio_url = self.poll_job_status(song_id)
        if not audio_url:
            Logger.print_error("Failed to retrieve audio URL.")
            return None

        # Download the audio file and save it locally
        audio_path = self.download_audio(audio_url, prompt)
        if not audio_path:
            Logger.print_error("Failed to download audio.")
            return None

        return audio_path  # Return the local path to the audio file

    def start_instrumental_song_job(self, prompt, model):
        # Use API3 to generate music based on prompt only (instrumental)
        endpoint = f"{self.api_base_url}/gateway/generate/gpt_desc"

        data = {
            "gpt_description_prompt": prompt,
            "make_instrumental": True,
            "mv": model
        }

        Logger.print_info(f"Sending request to {endpoint} with data: {data} and headers: {self.headers}")
        response = requests.post(endpoint, headers=self.headers, json=data)
        Logger.print_info(f"Request completed with status code {response.status_code}")
        # Logger.print_info(f"Response text: {response.text}") # Uncomment this for debugging issues with errors

        if response.status_code != 200:
            Logger.print_error(f"Failed to start instrumental music job: {response.text}")
            return None

        response_data = response.json()
        if response_data.get('code') != 0:
            Logger.print_error(f"API error: {response_data.get('msg')}")
            return None

        # Extract the song_id
        if "data" in response_data and isinstance(response_data["data"], list):
            job_data = response_data["data"]
            if job_data and "song_id" in job_data[0]:
                song_id = job_data[0]["song_id"]
                Logger.print_info(f"Received song_id: {song_id}")
                return song_id
            else:
                Logger.print_error("song_id not found in response data")
                return None
        else:
            Logger.print_error("Invalid response format")
            return None

    def start_lyrical_song_job(self, prompt, model, story_text, query_dispatcher):
        # Use API1 to generate music with lyrics
        # Generate lyrics using LyricsGenerator
        lyrics_generator = LyricsGenerator()
        lyrics_json = lyrics_generator.generate_song_lyrics(story_text, query_dispatcher)
        lyrics_data = json.loads(lyrics_json)
        style = lyrics_data.get('style', 'pop') # TODO: make the style configurable
        lyrics = lyrics_data.get('lyrics', '')
        full_prompt = f"{style} song with lyrics:\n{lyrics}"
        Logger.print_info(f"Generated lyrics: {lyrics}")

        endpoint = f"{self.api_base_url}/gateway/generate/music"

        data = {
            "title": "Generated Song",
            "tags": "general",
            "prompt": full_prompt,
            "mv": model
        }

        Logger.print_info(f"Sending request to {endpoint} with data: {data} and headers: {self.headers}")
        response = requests.post(endpoint, headers=self.headers, json=data)
        Logger.print_info(f"Request completed with status code {response.status_code}")
        # Logger.print_info(f"Response text: {response.text}") # Uncomment this for debugging issues with errors

        if response.status_code != 200:
            Logger.print_error(f"Failed to start lyrical music job: {response.text}")
            return None

        response_data = response.json()
        if response_data.get('code') != 0:
            Logger.print_error(f"API error: {response_data.get('msg')}")
            return None

        # Extract the song_id
        if "data" in response_data and isinstance(response_data["data"], list):
            job_data = response_data["data"]
            if job_data and "song_id" in job_data[0]:
                song_id = job_data[0]["song_id"]
                Logger.print_info(f"Received song_id: {song_id}")
                return song_id
            else:
                Logger.print_error("song_id not found in response data")
                return None
        else:
            Logger.print_error("Invalid response format")
            return None

    def poll_job_status(self, song_id, max_retries=60, retry_interval=15):
        endpoint = f"{self.api_base_url}/gateway/query?ids={song_id}"

        start_time = time.time()

        for attempt in range(max_retries):
            Logger.print_info(f"Checking status of song_id {song_id} (Attempt {attempt + 1}/{max_retries})")
            response = requests.get(endpoint, headers=self.headers)
            Logger.print_info(f"Status response status code: {response.status_code}")
            # Logger.print_info(f"Status response text: {response.text}") # Uncomment this for debugging issues with errors

            if response.status_code != 200:
                Logger.print_error(f"Failed to get status for song_id {song_id}: {response.text}")
                return None

            try:
                response_data = response.json()
            except json.JSONDecodeError:
                Logger.print_error(f"Failed to parse response as JSON: {response.text}")
                return None

            if not isinstance(response_data, list):
                Logger.print_error(f"Unexpected response format: {response_data}")
                return None

            song_data = None
            for item in response_data:
                if item.get('id') == song_id:
                    song_data = item
                    break

            if not song_data:
                Logger.print_error(f"Song data for song_id {song_id} not found in response")
                return None

            status = song_data.get('status')
            Logger.print_info(f"Song {song_id} status: {status}")

            if status == 'complete':
                audio_url = song_data.get('audio_url')
                if audio_url:
                    Logger.print_info(f"Song {song_id} completed. Audio URL: {audio_url}")
                    return audio_url
                else:
                    Logger.print_error("audio_url not found in completed job response")
                    return None
            elif status == 'error':
                # Check for error details
                meta_data = song_data.get('meta_data', {})
                error_type = meta_data.get('error_type')
                error_message = meta_data.get('error_message')
                Logger.print_error(f"Song {song_id} generation failed. Error Type: {error_type}, Message: {error_message}")
                return None
            else:
                # Status could be 'submitted', 'queued', 'streaming'
                time_elapsed = time.time() - start_time
                Logger.print_info(f"Song {song_id} is still processing. Time elapsed: {time_elapsed:.1f}. Waiting for {retry_interval} seconds before retrying.")
                time.sleep(retry_interval)
        else:
            Logger.print_error(f"Song {song_id} did not complete within the expected time.")
            return None

    def download_audio(self, audio_url, description):
        # Existing implementation remains the same
        Logger.print_info(f"Downloading audio from URL: {audio_url}")
        response = requests.get(audio_url)
        if response.status_code != 200:
            Logger.print_error(f"Failed to download audio file: {response.status_code}")
            return None

        # Create a sanitized filename
        sanitized_description = re.sub(r'\W+', '_', description.lower())[:50]
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        audio_directory = "/tmp/GANGLIA/music"
        os.makedirs(audio_directory, exist_ok=True)
        audio_path = os.path.join(audio_directory, f"{sanitized_description}_{timestamp}.mp3")

        # Save the audio file
        with open(audio_path, 'wb') as f:
            f.write(response.content)
        Logger.print_info(f"Audio downloaded to {audio_path}")
        return audio_path
