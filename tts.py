from abc import ABC, abstractmethod
from gtts import gTTS
from pydub import AudioSegment
from pydub.playback import play
from datetime import datetime
import subprocess
import os

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

    def split_text(self, text: str, max_length: int = 250):
        words = text.split()
        chunks = []
        current_chunk = ""
        for word in words:
            if len(current_chunk) + len(word) + 1 > max_length:
                chunks.append(current_chunk)
                current_chunk = ""
            current_chunk += (" " if current_chunk else "") + word
        if current_chunk:
            chunks.append(current_chunk)
        return chunks

    def convert_text_to_speech(self, text: str):
        try:
            chunks = self.split_text(text)
            files = []
            for chunk in chunks:
                payload = {
                    "name": "GANGLIA",
                    "voice_id": self.voice_id,
                    "text": chunk
                }

                headers = {
                    "Content-Type": "application/json",
                    "Authorization": "Bearer " + self.bearer_token,
                    "Accept": "application/json"
                }

                response = requests.post(self.api_url, json=payload, headers=headers)
                audio_url = response.json().get("audio_url")

                if not audio_url:
                    print(f"No audio url found in the response for chunk: {chunk}")
                    continue

                file_path = os.path.abspath(f"/tmp/chatgpt_response_{datetime.now().strftime('%Y%m%d-%H%M%S')}.mp3")
                audio_response = requests.get(audio_url)
                with open(file_path, 'wb') as audio_file:
                    audio_file.write(audio_response.content)
                files.append(file_path)

            # Write the list of files to a temporary file
            list_file_path = "/tmp/concat_list.txt"
            with open(list_file_path, 'w') as list_file:
                list_file.write('\n'.join(f"file '{file}'" for file in files))

            print(f"Written file list to {list_file_path}")  # Logging

            # Use FFmpeg to concatenate the files together
            output_file = "combined_audio.mp3"
            command = f"ffmpeg -y -f concat -safe 0 -i {list_file_path} {output_file}"
            subprocess.run(command, shell=True)

            return 0, output_file
        except Exception as e:
            print(f"Error converting text to speech: {e}")
            return 1, None
