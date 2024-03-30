import argparse
import json
from tts import TextToSpeech, GoogleTTS, NaturalReadersTTS, CoquiTTS
from dictation import Dictation, StaticGoogleDictation, LiveGoogleDictation
import sys
from logger import Logger

def parse_tts_interface(tts_interface: str) -> TextToSpeech:
    if tts_interface.lower() == "google":
        return GoogleTTS()
    else:
        raise ValueError(
            "Invalid TTS interface provided. Available options: 'google'"
        )

def parse_dictation_type(dictation_type: str) -> Dictation:
    if dictation_type.lower() == "static_google":
        return StaticGoogleDictation()
    elif dictation_type.lower() == "live_google":
        return LiveGoogleDictation()
    else:
        raise ValueError(
            "Invalid dictation type provided. Available options: 'static_google', 'live_assemblyai'"
        )

def parse_args(args=None):
    parser = argparse.ArgumentParser(description="GANGLIA - AI Assistant")
    parser.add_argument("--device-index", type=int, default=0, help="Index of the input device to use.")
    parser.add_argument("--tts-interface", type=str, default="google", help="Text-to-speech interface to use. Available options: 'google'")
    parser.add_argument("--suppress-session-logging", action="store_true", help="Disable session logging (default: False)")
    parser.add_argument("--enable-turn-indicators", action="store_true", help="Enable turn indicators (default: False)")
    parser.add_argument("--dictation-type", type=str, default="static_google", choices=["static_google", "live_google", "live_assemblyai"], help="Dictation type to use. Available options: 'static_google', 'live_google', 'live_assemblyai'")
    parser.add_argument("--store-logs", action="store_true", help="Enable storing logs in the cloud (default: False)")
    parser.add_argument('--text-to-video', action='store_true', help='Generate video from text input.')
    parser.add_argument('--ttv-config', type=str, help='Path to the JSON input file for video generation.')
    parser.add_argument('--skip-image-generation', type=str, help='Use previously generated images when generating text-to-video')

    parsed_args = parser.parse_args(args)

    # Check if --text-to-video is used, then --json-input must also be provided
    if parsed_args.text_to_video and not parsed_args.ttv_config:
        parser.error("--json-input is required when --text-to-video is specified.")

    return parsed_args