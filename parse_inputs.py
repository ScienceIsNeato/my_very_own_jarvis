import argparse
from tts import TextToSpeech, GoogleTTS, NaturalReadersTTS

def parse_tts_interface(tts_interface: str) -> TextToSpeech:
    if tts_interface.lower() == "natural_reader":
        return NaturalReadersTTS()
    elif tts_interface.lower() == "google":
        return GoogleTTS()
    else:
        raise ValueError(
            "Invalid TTS interface provided. Available options: 'google', 'natural_reader'"
        )

def parse_args():
    parser = argparse.ArgumentParser(description="Jarvis - AI Assistant")
    parser.add_argument("-l", "--listen_dur_secs", type=int, default=5, help="Duration in seconds to listen for user input")
    parser.add_argument("-d", "--device_index", type=int, default=0, help="Index of the input device to use.")
    parser.add_argument("-p", "--pre_prompt", type=str, default=None, help="Any context you want for the session (should take form of a prompt)")
    parser.add_argument(
        "-t",
        "--tts_interface",
        type=str,
        default="google",
        help="Text-to-speech interface to use. Available options: 'google', 'natural_reader'",
    )
    return parser.parse_args()
