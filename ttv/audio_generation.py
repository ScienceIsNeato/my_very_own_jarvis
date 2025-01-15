import subprocess
import uuid
from logger import Logger

def generate_audio(tts, sentence):
    try:
        success, file_path = tts.convert_text_to_speech(sentence)
        if success:
            Logger.print_info(f"Audio generation successful for: '{sentence}'. Saved to {file_path}")
            return file_path
        else:
            Logger.print_error(f"Audio generation failed for: '{sentence}'")
            return None
    except (OSError, subprocess.SubprocessError, ValueError) as e:
        Logger.print_error(f"Audio generation failed for: '{sentence}'. Error: {e}")
        return None

def get_audio_duration(audio_file):
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries",
         "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", audio_file],
        stdout=subprocess.PIPE,
        check=True)
    return float(result.stdout)
