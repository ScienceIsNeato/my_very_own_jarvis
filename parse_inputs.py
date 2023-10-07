import argparse
import json
from tts import TextToSpeech, GoogleTTS, NaturalReadersTTS, CoquiTTS
from dictation import Dictation, StaticGoogleDictation, LiveGoogleDictation, LiveAssemblyAIDictation
import sys
from logger import Logger

def load_coqui_config():
    """
    Load configuration from coqui_config.json.
    Returns a tuple containing (api_url, bearer_token, voice_id) or
    exits the program in case of errors.
    """
    try:
        # Load configuration from coqui_config.json
        with open('coqui_config.json', 'r') as config_file:
            coqui_config = json.load(config_file)

        if "api_url" not in coqui_config or "bearer_token" not in coqui_config or "voice_id" not in coqui_config:
            raise ValueError("Missing one or more required keys in coqui_config.json")

        Logger.print_info("Successfully loaded coqui config")
        return coqui_config["api_url"], coqui_config["bearer_token"], coqui_config["voice_id"]

    except FileNotFoundError:
        Logger.print_error("Error: coqui_config.json file not found in the current directory.", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError:
        Logger.print_error("Error: coqui_config.json file contains invalid JSON.", file=sys.stderr)
        sys.exit(1)
    except ValueError as ve:
        Logger.print_error(f"Error: {ve}", file=sys.stderr)
        sys.exit(1)


def parse_tts_interface(tts_interface: str) -> TextToSpeech:
    if tts_interface.lower() == "natural_reader":
        return NaturalReadersTTS()
    elif tts_interface.lower() == "google":
        return GoogleTTS()
    elif tts_interface.lower() == "coqui":
        try:
            api_url, bearer_token, voice_id = load_coqui_config()
            Logger.print_debug("api_url: ", api_url)
            return CoquiTTS(api_url, bearer_token, voice_id)
        except Exception as e:
            Logger.print_error(f"Error initializing CoquiTTS: {str(e)}", file=sys.stderr)
            raise ValueError("Unable to load coqui config.")
    else:
        raise ValueError(
            "Invalid TTS interface provided. Available options: 'google', 'natural_reader', 'coqui'"
        )

def parse_dictation_type(dictation_type: str) -> Dictation:
    if dictation_type.lower() == "static_google":
        return StaticGoogleDictation()
    elif dictation_type.lower() == "live_google":
        return LiveGoogleDictation()
    elif dictation_type.lower() == "live_assemblyai":
        return LiveAssemblyAIDictation()
    else:
        raise ValueError(
            "Invalid dictation type provided. Available options: 'static_google', 'live_assemblyai'"
        )

def parse_args(args=None):
    parser = argparse.ArgumentParser(description="GANGLIA - AI Assistant")
    parser.add_argument("--device-index", type=int, default=0, help="Index of the input device to use.")
    parser.add_argument("--tts-interface", type=str, default="google", help="Text-to-speech interface to use. Available options: 'google', 'natural_reader'")
    parser.add_argument("--suppress-session-logging", action="store_true", help="Disable session logging (default: False)")
    parser.add_argument("--enable-turn-indicators", action="store_true", help="Enable turn indicators (default: False)")
    parser.add_argument("--dictation-type", type=str, default="static_google", choices=["static_google", "live_google", "live_assemblyai"], help="Dictation type to use. Available options: 'static_google', 'live_google', 'live_assemblyai'")

    return parser.parse_args(args)