from abc import ABC, abstractmethod
import re
from gtts import gTTS
from datetime import datetime
import subprocess
import os
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor
import subprocess
from urllib.parse import urlparse
import requests
from datetime import datetime
from logger import Logger
from concurrent.futures import ThreadPoolExecutor, as_completed
import concurrent.futures
import time
from logger import Logger

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

    def split_text(cls, text: str, max_length: int = 250):
        sentences = [match.group() for match in re.finditer(r'[^.!?]*[.!?]', text)]
        chunks = []

        for sentence in sentences:
            while len(sentence) > max_length:
                chunk = sentence[:max_length]
                chunks.append(chunk.strip())
                sentence = sentence[max_length:]
            chunks.append(sentence.strip())

        return chunks


    def fetch_audio(self, chunk, payload, headers, index):
        try:
            start_time = datetime.now()  # Record start time
            response = requests.post(self.api_url, json=payload, headers=headers, timeout=30)
            end_time = datetime.now()  # Record end time
            audio_url = response.json().get("audio_url")
            
            if not audio_url:
                Logger.print_debug(f"No audio url found in the response for chunk {index}: {chunk}")
                return None, index

            file_path = os.path.abspath(f"/tmp/chatgpt_response_{datetime.now().strftime('%Y%m%d-%H%M%S')}_{index}.mp3")
            audio_response = requests.get(audio_url, timeout=30)
            with open(file_path, 'wb') as audio_file:
                audio_file.write(audio_response.content)
            return file_path, index, start_time, end_time
        except Exception as e:
            Logger.print_error(f"Error fetching audio for chunk {index}: {e}")
            return None, index, None, None

    def play_speech_response(self, file_path, raw_response):
        try:
            if file_path.endswith('.txt'): # Concatenate and play if it's a text file containing paths
                output_file = "combined_audio.mp3"
                concat_command = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", file_path, output_file]
                with open(os.devnull, "wb") as devnull:
                    subprocess.run(concat_command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL, check=True)
                file_path = output_file

            if file_path.endswith('.mp4'): # Handle video files differently if needed
                # Define commands for playing video
                play_command = ["ffplay", "-nodisp", "-autoexit", file_path]
            else: # Assume audio file
                duration_command = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", file_path]
                duration_output = subprocess.run(duration_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout.decode('utf-8')
                play_command = ["ffplay", "-nodisp", "-af", "volume=5", "-autoexit", file_path]

            Logger.print_demon_output(f"\nA Demonic Voice Echos (Audio Duration: {float(duration_output.strip()):.1f} seconds. Playing... ")
            Logger.print_demon_output(raw_response)
            # TODO - save the audio to disk here. Also see if we can save the input audio to disk as well?

            with open(os.devnull, "wb") as devnull:
                subprocess.run(play_command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL) # Wait for completion
        except Exception as e:
            Logger.print_error(f"Error playing the speech response: {e}")

class GoogleTTS(TextToSpeech):
    def convert_text_to_speech(self, text: str):
        try:
            tts = gTTS(text=text, lang="en-uk",)
            file_path = f"/tmp/chatgpt_response_{datetime.now().strftime('%Y%m%d-%H%M%S')}.mp3"
            tts.save(file_path)
            return 0, file_path
        except Exception as e:
            Logger.print_error(f"Error converting text to speech: {e}")
            return 1, None

class NaturalReadersTTS(TextToSpeech):
    def convert_text_to_speech(self, text: str):
        # TODO: Implement NaturalReadersTTS conversion
        pass

class CoquiTTS(TextToSpeech):
    def __init__(self, api_url, bearer_token, voice_id):
        Logger.print_info("Initializing CoquiTTS...")

        self.api_url = api_url
        self.bearer_token = bearer_token
        self.voice_id = voice_id

    def convert_text_to_speech(self, text: str):
        try:
            Logger.print_info("\nConverting text to speech...")
            start_time = time.time()
            
            chunks = self.split_text(text)
            if not chunks:
                Logger.print_debug("Tried to split text into phrase chunks, but no chunks were found. Returning original text.")
                chunks = [text]

            files = [None] * len(chunks)
            payloads_headers = []

            for index, chunk in enumerate(chunks):
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

                payloads_headers.append((chunk, payload, headers, index))
            
            Logger.print_debug(f"Splitting oriignal text into {len(chunks)} phrases and converting to speech in parallel...")

            spinner = "|/-\\"
            spinner_idx = 0

            with ThreadPoolExecutor() as executor:
                futures = [executor.submit(self.fetch_audio, chunk, payload, headers, index) for chunk, payload, headers, index in payloads_headers]

                for future in as_completed(futures):
                    Logger.print_debug(f"\rWaiting for responses... {spinner[spinner_idx % len(spinner)]}", end='', flush=True)
                    spinner_idx += 1

                    file_path, idx, _, _ = future.result()
                    if file_path:
                        files[idx] = file_path

            Logger.print_info(f"\nText-to-speech conversion completed in {time.time() - start_time:.5f} seconds.")

            files = [file for file in files if file]

            list_file_path = "/tmp/concat_list.txt"
            with open(list_file_path, 'w') as list_file:
                list_file.write('\n'.join(f"file '{file}'" for file in files))

            return 0, list_file_path

        except Exception as e:
            Logger.print_error(f"Error converting text to speech: {e}")
            return 1, None
