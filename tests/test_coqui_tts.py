import json
import requests
import time
import subprocess
import sys
from typing import Dict, Any

class Config:
    def __init__(self, api_url: str, bearer_token: str, voice_id: str):
        self.api_url = api_url
        self.bearer_token = bearer_token
        self.voice_id = voice_id

def read_config() -> Config:
    with open("coqui_config.json", 'r') as file:
        data = json.load(file)
        return Config(data["api_url"], data["bearer_token"], data["voice_id"])

def prepare_payload(voice_id: str, text: str) -> Dict[str, Any]:
    return {
        "name": "my test sample",
        "voice_id": voice_id,
        "text": text,
    }

def prepare_request(api_url: str, bearer_token: str, payload: Dict[str, Any]) -> requests.Request:
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {bearer_token}",
        "Accept": "application/json"
    }
    return requests.Request("POST", api_url, headers=headers, json=payload)

def call_api(req: requests.Request) -> Dict[str, Any]:
    session = requests.Session()
    resp = session.send(req.prepare())
    resp.raise_for_status()
    return resp.json()

def parse_response(body: Dict[str, Any]) -> str:
    audio_url = body.get("audio_url")
    if not audio_url:
        raise Exception("No audio url found in the response")
    return audio_url

def play_audio(audio_url: str) -> None:
    subprocess.run(["ffplay", "-nodisp", "-autoexit", audio_url], check=True)

def main(text: str) -> None:
    timings = {}
    config = read_config()

    start = time.time()
    timings["Start"] = start

    payload = prepare_payload(config.voice_id, text)
    timings["Payload Prepared"] = time.time()

    req = prepare_request(config.api_url, config.bearer_token, payload)
    timings["Request Prepared"] = time.time()

    body = call_api(req)
    timings["API Called"] = time.time()

    audio_url = parse_response(body)
    timings["Response Parsed"] = time.time()

    play_audio(audio_url)
    timings["Audio Played"] = time.time()

    for event, timestamp in timings.items():
        print(f"{event}: {timestamp - start}s")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("You must provide exactly one argument: the text to speechify")
    main(sys.argv[1])
