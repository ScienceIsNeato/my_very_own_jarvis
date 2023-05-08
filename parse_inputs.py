import argparse
from tts import TextToSpeech, GoogleTTS, NaturalReadersTTS
from dictation import Dictation, StaticGoogleDictation, LiveAssemblyAIDictation

def parse_tts_interface(tts_interface: str) -> TextToSpeech:
    if tts_interface.lower() == "natural_reader":
        return NaturalReadersTTS()
    elif tts_interface.lower() == "google":
        return GoogleTTS()
    else:
        raise ValueError(
            "Invalid TTS interface provided. Available options: 'google', 'natural_reader'"
        )

def parse_dictation_type(dictation_type: str) -> Dictation:
    if dictation_type.lower() == "static_google":
        return StaticGoogleDictation()
    elif dictation_type.lower() == "live_assemblyai":
        return LiveAssemblyAIDictation()
    else:
        raise ValueError(
            "Invalid dictation type provided. Available options: 'static_google', 'live_assemblyai'"
        )

def parse_args(args=None):
    parser = argparse.ArgumentParser(description="GANGLIA - AI Assistant")
    parser.add_argument("--listen-dur-secs", type=int, default=5, help="Duration in seconds to listen for user input")
    parser.add_argument("--device-index", type=int, default=0, help="Index of the input device to use.")
    parser.add_argument("--pre-prompt", type=str, default=None, help="Any context you want for the session (should take form of a prompt)")
    parser.add_argument("--tts-interface", type=str, default="google", help="Text-to-speech interface to use. Available options: 'google', 'natural_reader'")
    parser.add_argument("--static-response", action="store_true", help="Provide responses without conversation history (default: False)")
    parser.add_argument("--suppress-session-logging", action="store_true", help="Disable session logging (default: False)")
    parser.add_argument("--enable-turn-indicators", action="store_true", help="Enable turn indicators (default: False)")
    parser.add_argument("--dictation-type", type=str, default="static_google", choices=["static_google", "live_assemblyai"], help="Dictation type to use. Available options: 'static_google', 'live_assemblyai'")

    return parser.parse_args(args)