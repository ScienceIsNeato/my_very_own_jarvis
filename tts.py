from abc import ABC, abstractmethod
import json
from gtts import gTTS
from pydub import AudioSegment
from pydub.playback import play
from datetime import datetime

import requests

import subprocess
from urllib.parse import urlparse

class TextToSpeech(ABC):
    @abstractmethod
    def convert_text_to_speech(self, text: str):
        pass

    def is_local_filepath(self, file_path: str) -> bool:
        try:
            result = urlparse(file_path)
            return all([result.scheme, result.netloc])
        except ValueError:
            return False

    def play_speech_response(self, error_code, file_path):
        if error_code != 0:
            print("Error: Cannot play the speech response due to previous error.")
            return

        try:
            if self.is_local_filepath(file_path):
                audio = AudioSegment.from_mp3(file_path)
                play(audio)
            else:
                subprocess.run(
                    ["ffplay", "-nodisp", "-af", "volume=5", "-autoexit", file_path], 
                    check=True, 
                    stdout=subprocess.DEVNULL, 
                    stderr=subprocess.DEVNULL)
        except Exception as e:
            print(f"Error playing the speech response: {e}")

class GoogleTTS(TextToSpeech):
    def convert_text_to_speech(self, text: str):
        try:
            tts = gTTS(text=text, lang="en-uk",)
            file_path = f"/tmp/chatgpt_response_{datetime.now().strftime('%Y%m%d-%H%M%S')}.mp3"
            tts.save(file_path)
            return 0, file_path
        except Exception as e:
            print(f"Error converting text to speech: {e}")
            return 1, None

class NaturalReadersTTS(TextToSpeech):
    def convert_text_to_speech(self, text: str):
        # TODO: Implement NaturalReadersTTS conversion
        pass

class CoquiTTS(TextToSpeech):
    def __init__(self, api_url, bearer_token, voice_id):
        self.api_url = api_url
        self.bearer_token = bearer_token
        self.voice_id = voice_id

    def convert_text_to_speech(self, text: str):
        try:
            payload = {
                "name": "my test sample",
                "voice_id": self.voice_id,
                "text": text
            }

            headers = {
                "Content-Type": "application/json",
                "Authorization": "Bearer " + self.bearer_token,
                "Accept": "application/json"
            }

            response = requests.post(self.api_url, data=json.dumps(payload), headers=headers)
            audio_url = response.json()["audio_url"]
            
            if not audio_url:
                print("No audio url found in the response")
                return 1, None
            
            file_path = f"/tmp/chatgpt_response_{datetime.now().strftime('%Y%m%d-%H%M%S')}.mp3"
            audio_response = requests.get(audio_url)
            with open(file_path, 'wb') as audio_file:
                audio_file.write(audio_response.content)
            
            return 0, file_path
        except Exception as e:
            print(f"Error converting text to speech: {e}")
            return 1, None