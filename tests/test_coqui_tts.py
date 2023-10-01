import json
import time
import sys
import os

from typing import Dict, Any

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tts import CoquiTTS

class Config:
    def __init__(self, api_url: str, bearer_token: str, voice_id: str):
        self.api_url = api_url
        self.bearer_token = bearer_token
        self.voice_id = voice_id

def read_config() -> Config:
    with open("coqui_config.json", 'r') as file:
        data = json.load(file)
        return Config(data["api_url"], data["bearer_token"], data["voice_id"])

def main() -> None:
    timings = {}
    text = "If you are hearing playback, then this is working, my fiend."
    config = read_config()

    start = time.time()

    tts = CoquiTTS(config.api_url, config.bearer_token, config.voice_id)
    timings["TTS Initialized"] = time.time()

    error_code, filepath = tts.convert_text_to_speech(text)

    if error_code != 0:
        raise Exception(f"Error converting text to speech: {error_code}")

    tts.play_speech_response(filepath, text)
    timings["Audio Played"] = time.time()

    for event, timestamp in timings.items():
        print(f"{event}: {timestamp - start}s")

if __name__ == "__main__":
    main()
