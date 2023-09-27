import os
import shutil
import json
import requests
import subprocess
import logging
from typing import Dict, Any

# This is a quick script that allows batch processing of text inputs to coqui (used to generate time killing samples)

# Set up basic logging
logging.basicConfig(level=logging.INFO)

class Config:
    def __init__(self, api_url: str, bearer_token: str, voice_id: str):
        self.api_url = api_url
        self.bearer_token = bearer_token
        self.voice_id = voice_id

def read_config() -> Config:
    logging.info("Reading configuration...")
    with open("coqui_config.json", 'r') as file:
        data = json.load(file)
        return Config(data["api_url"], data["bearer_token"], data["voice_id"])

def prepare_payload(voice_id: str, text: str) -> Dict[str, Any]:
    logging.info(f"Preparing payload for text: {text}...")
    return {
        "name": "my test sample",
        "voice_id": voice_id,
        "text": text,
    }

def prepare_request(api_url: str, bearer_token: str, payload: Dict[str, Any]) -> requests.Request:
    logging.info("Preparing API request...")
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {bearer_token}",
        "Accept": "application/json"
    }
    return requests.Request("POST", api_url, headers=headers, json=payload)

def call_api(req: requests.Request) -> Dict[str, Any]:
    logging.info("Calling Coqui API...")
    session = requests.Session()
    resp = session.send(req.prepare())
    resp.raise_for_status()
    return resp.json()

def parse_response(body: Dict[str, Any]) -> str:
    logging.info("Parsing API response...")
    audio_url = body.get("audio_url")
    if not audio_url:
        raise Exception("No audio url found in the response")
    return audio_url

def play_audio(audio_url: str) -> None:
    logging.info(f"Playing audio from URL: {audio_url}")
    subprocess.run(["ffplay", "-nodisp", "-autoexit", audio_url], check=True)

def save_audio_to_file(audio_url: str, text: str) -> None:
    logging.info(f"Saving audio for text: {text} to file...")
    file_name = "_".join(text.split()[:5]) + ".wav"  # Taking first 5 words as filename
    file_path = os.path.join("coqui_outputs", file_name)
    
    response = requests.get(audio_url, stream=True)
    with open(file_path, 'wb') as out_file:
        shutil.copyfileobj(response.raw, out_file)
    del response

def main() -> None:
    logging.info("Starting main process...")
    config = read_config()

    # Ensure the coqui_outputs folder exists
    if not os.path.exists("coqui_outputs"):
        os.makedirs("coqui_outputs")

    # Read from coqui_inputs.txt
    with open("coqui_inputs.txt", 'r') as f:
        lines = f.readlines()

    for line in lines:
        text = line.strip()

        payload = prepare_payload(config.voice_id, text)
        req = prepare_request(config.api_url, config.bearer_token, payload)
        body = call_api(req)
        audio_url = parse_response(body)

        # Play the received audio
        play_audio(audio_url)

        save_audio_to_file(audio_url, text)

if __name__ == "__main__":
    main()
