import os
import time
import requests
from logger import Logger

class SunoRequestHandler:
    def __init__(self, base_url, headers):
        self.base_url = base_url
        self.headers = headers
        self.api_key = os.getenv('SUNO_API_KEY')
        self.base_url = os.getenv('SUNO_BASE_URL')
        if not self.api_key:
            raise EnvironmentError("Environment variable 'SUNO_API_KEY' is not set.")
        if not self.base_url:
            raise EnvironmentError("Environment variable 'SUNO_BASE_URL' is not set.")
        
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def build_request_data(self, prompt, model, duration, with_lyrics):
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

        endpoint = f"{self.base_url}/gateway/generate/music"
        data = {k: v for k, v in data.items() if v is not None}

        return endpoint, data

    def send_request(self, endpoint, data, retries, wait_time):
        attempt = 0
        while attempt < retries:
            try:
                Logger.print_debug(f"Sending request to {endpoint} with data: {data} and headers: {self.headers}")
                response = requests.post(endpoint, headers=self.headers, json=data)
                Logger.print_debug(f"Request to {endpoint} completed with status code {response.status_code}")

                if response.status_code == 200:
                    return response.json()
                else:
                    Logger.print_error(f"Error in response: {response.text}")
                    if response.status_code == 429:
                        Logger.print_warning(f"Rate limit exceeded. Retrying in {wait_time} seconds... (Attempt {attempt + 1} of {retries})")
                        time.sleep(wait_time)
                        attempt += 1
                    else:
                        return {"error": response.status_code, "message": response.text}
            except Exception as e:
                Logger.print_error(f"Exception during request to {endpoint}: {e}")
                if 'Rate limit exceeded' in str(e):
                    Logger.print_warning(f"Rate limit exceeded. Retrying in {wait_time} seconds... (Attempt {attempt + 1} of {retries})")
                    time.sleep(wait_time)
                    attempt += 1
                else:
                    return {"error": "exception", "message": str(e)}
            print("Retrying... (Attempt {attempt + 1} of {retries})")

        Logger.print_error(f"Failed to generate audio after {retries} attempts due to rate limiting.")
        return {"error": "rate_limit_exceeded", "message": "Failed to generate audio after multiple attempts due to rate limiting."}
