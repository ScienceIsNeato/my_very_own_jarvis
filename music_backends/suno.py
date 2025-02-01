import os
import time
import json
import requests
import re
from datetime import datetime
from lyrics_lib import LyricsGenerator
from logger import Logger
from music_backends.base import MusicBackend
from utils import get_tempdir
class SunoMusicBackend(MusicBackend):
    """Suno API implementation for music generation."""
    
    def __init__(self):
        self.api_base_url = 'https://api.sunoaiapi.com/api/v1'
        self.api_key = os.getenv('SUNO_API_KEY')
        if not self.api_key:
            raise EnvironmentError("Environment variable 'SUNO_API_KEY' is not set.")
        self.headers = {
            'api-key': self.api_key,
            'Content-Type': 'application/json'
        }
        self.audio_directory = get_tempdir() + "/music"
        os.makedirs(self.audio_directory, exist_ok=True)
    
    def start_generation(self, prompt: str, with_lyrics: bool = False, **kwargs) -> str:
        """Start the generation process via API."""
        model = kwargs.get('model', 'chirp-v3-5')
        duration = kwargs.get('duration', 30)  # Default to 30 seconds if not specified
        
        if with_lyrics and 'story_text' in kwargs:
            return self._start_lyrical_song_job(prompt, model, kwargs['story_text'], kwargs.get('query_dispatcher'))
        else:
            return self._start_instrumental_song_job(prompt, duration, model)
    
    def check_progress(self, job_id: str) -> tuple[str, float]:
        """Check the progress of a generation job via API."""
        endpoint = f"{self.api_base_url}/gateway/query?ids={job_id}"
        
        try:
            response = requests.get(endpoint, headers=self.headers)
            if response.status_code != 200:
                return f"Error: HTTP {response.status_code}", 0
            
            response_data = response.json()
            if not isinstance(response_data, list):
                return "Error: Invalid response format", 0
            
            song_data = next((item for item in response_data if item.get('id') == job_id), None)
            if not song_data:
                return "Error: Song data not found", 0
            
            status = song_data.get('status', '')
            meta_data = song_data.get('meta_data', {})
            
            # Determine if this is background music or closing credits based on the prompt
            prompt = meta_data.get('prompt', '')
            is_closing_credits = 'with lyrics' in prompt.lower() if prompt else False
            file_type = "closing_credits.mp3" if is_closing_credits else "background_music.mp3"
            
            if status == 'complete':
                return "Complete", 100
            elif status == 'error':
                error_type = meta_data.get('error_type', 'Unknown error')
                error_message = meta_data.get('error_message', '')
                return f"Error: {error_type} - {error_message}", 0
            else:
                # Estimate progress based on typical generation time
                elapsed = time.time() - self._get_start_time(job_id)
                estimated_progress = min(95, (elapsed / 180) * 100)  # 3 minutes typical time
                return f"{status} ({file_type})", estimated_progress
                
        except Exception as e:
            return f"Error: {str(e)}", 0
    
    def get_result(self, job_id: str) -> str:
        """Get the result of a completed generation job."""
        endpoint = f"{self.api_base_url}/gateway/query?ids={job_id}"
        
        try:
            response = requests.get(endpoint, headers=self.headers)
            if response.status_code != 200:
                return None
            
            response_data = response.json()
            if not isinstance(response_data, list):
                return None
            
            song_data = next((item for item in response_data if item.get('id') == job_id), None)
            if not song_data or song_data.get('status') != 'complete':
                return None
            
            audio_url = song_data.get('audio_url')
            if not audio_url:
                return None
            
            return self._download_audio(audio_url, job_id)
            
        except Exception as e:
            Logger.print_error(f"Failed to get result: {str(e)}")
            return None
    
    def _start_instrumental_song_job(self, prompt: str, duration: int, model: str) -> str:
        """Start a job for instrumental music generation."""
        endpoint = f"{self.api_base_url}/gateway/generate/gpt_desc"

        # Modify prompt to specify duration in a more natural way
        commercial_prompt = f"Create a {prompt} that is exactly {duration} seconds long"

        data = {
            "gpt_description_prompt": commercial_prompt,
            "make_instrumental": True,
            "mv": model,
        }

        logging_headers = self.headers.copy()
        api_key = self.headers['api-key']
        masked_key = f"{api_key[:2]}{'*' * (len(api_key)-4)}{api_key[-2:]}"
        logging_headers['api-key'] = masked_key
        Logger.print_info(f"Sending request to {endpoint} with data: {data} and headers: {logging_headers}")
        response = requests.post(endpoint, headers=self.headers, json=data)
        Logger.print_info(f"Request completed with status code {response.status_code}")
        
        if response.status_code != 200:
            try:
                error_detail = response.json()
                Logger.print_error(f"Failed to start instrumental music job. Status: {response.status_code}, Response: {error_detail}")
                if 'detail' in error_detail:
                    Logger.print_error(f"Error detail: {error_detail['detail']}")
                if 'message' in error_detail:
                    Logger.print_error(f"Error message: {error_detail['message']}")
            except json.JSONDecodeError:
                Logger.print_error(f"Failed to start instrumental music job. Status: {response.status_code}, Raw response: {response.text}")
            return None
        
        response_data = response.json()
        if response_data.get('code') != 0:
            return None
        
        if "data" in response_data and isinstance(response_data["data"], list):
            job_data = response_data["data"]
            if job_data and "song_id" in job_data[0]:
                song_id = job_data[0]["song_id"]
                self._save_start_time(song_id)
                return song_id
        
        return None
    
    def _start_lyrical_song_job(self, prompt, model, story_text, query_dispatcher):
        """Start a job for music generation with lyrics."""
        try:
            lyrics_generator = LyricsGenerator()
            lyrics_json = lyrics_generator.generate_song_lyrics(story_text, query_dispatcher)
            lyrics_data = json.loads(lyrics_json)
            
            style = lyrics_data.get('style', 'pop')
            lyrics = lyrics_data.get('lyrics', '')
            # Combine the config prompt with the generated style
            full_prompt = f"A 30-second {style} song with lyrics that match this theme: {prompt}\nLyrics:\n{lyrics}"
            
            endpoint = f"{self.api_base_url}/gateway/generate/music"
            data = {
                "title": "Generated Song",
                "tags": "general",
                "prompt": full_prompt,
                "mv": model
            }

            logging_headers = self.headers.copy()
            api_key = self.headers['api-key']
            masked_key = f"{api_key[:2]}{'*' * (len(api_key)-4)}{api_key[-2:]}"
            logging_headers['api-key'] = masked_key
            Logger.print_info(f"Sending request to {endpoint} with data: {data} and headers: {logging_headers}")
                
            response = requests.post(endpoint, headers=self.headers, json=data)
            if response.status_code != 200:
                return None
            
            response_data = response.json()
            if response_data.get('code') != 0:
                return None
            
            if "data" in response_data and isinstance(response_data["data"], list):
                job_data = response_data["data"]
                if job_data and "song_id" in job_data[0]:
                    song_id = job_data[0]["song_id"]
                    self._save_start_time(song_id)
                    return song_id
            
            return None
            
        except Exception as e:
            Logger.print_error(f"Failed to start lyrical job: {str(e)}")
            return None
    
    def _download_audio(self, audio_url, job_id):
        """Download the generated audio file."""
        try:
            response = requests.get(audio_url)
            if response.status_code != 200:
                return None
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            audio_path = os.path.join(self.audio_directory, f"suno_{job_id}_{timestamp}.mp3")
            
            with open(audio_path, 'wb') as f:
                f.write(response.content)
            
            return audio_path
            
        except Exception as e:
            Logger.print_error(f"Failed to download audio: {str(e)}")
            return None
    
    def _save_start_time(self, job_id):
        """Save the start time of a job for progress estimation."""
        path = os.path.join(self.audio_directory, f"{job_id}_start_time")
        with open(path, 'w') as f:
            f.write(str(time.time()))
    
    def _get_start_time(self, job_id):
        """Get the start time of a job for progress estimation."""
        try:
            path = os.path.join(self.audio_directory, f"{job_id}_start_time")
            with open(path, 'r') as f:
                return float(f.read().strip())
        except:
            return time.time()
    
    # Keep these methods for backward compatibility
    def generate_instrumental(self, prompt: str, **kwargs) -> str:
        job_id = self.start_generation(prompt, with_lyrics=False, **kwargs)
        if not job_id:
            return None
            
        while True:
            status, progress = self.check_progress(job_id)
            if progress >= 100:
                return self.get_result(job_id)
            time.sleep(5)
    
    def generate_with_lyrics(self, prompt: str, story_text: str, **kwargs) -> str:
        kwargs['story_text'] = story_text
        job_id = self.start_generation(prompt, with_lyrics=True, **kwargs)
        if not job_id:
            return None
            
        while True:
            status, progress = self.check_progress(job_id)
            if progress >= 100:
                return self.get_result(job_id)
            time.sleep(5) 