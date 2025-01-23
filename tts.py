from abc import ABC, abstractmethod
import re
import select
import sys
import threading
import os
from google.cloud import texttospeech_v1 as tts
import subprocess
from urllib.parse import urlparse
from datetime import datetime
from logger import Logger
from utils import get_tempdir

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

    @classmethod
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



    def play_speech_response(self, file_path, raw_response):
        if file_path.endswith('.txt'):
            file_path = self.concatenate_audio_from_text(file_path)

        # Prepare the play command and determine the audio duration
        play_command, audio_duration = self.prepare_playback(file_path)

        Logger.print_demon_output(f"\nGANGLIA says... (Audio Duration: {audio_duration:.1f} seconds)")
        Logger.print_demon_output(raw_response)

        # Start playback in a non-blocking manner
        playback_process = subprocess.Popen(play_command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL)

        # Start the Enter key listener in a separate thread
        stop_thread = threading.Thread(target=self.monitor_enter_keypress, args=(playback_process,))
        stop_thread.daemon = True  # Ensure the thread exits when the main program exits
        stop_thread.start()

        # Wait for playback process to finish
        playback_process.wait()  # This will wait for natural completion

        # Ensure Enter key thread finishes
        stop_thread.join(timeout=1)  # Attempt to join, but timeout if it hangs

    def monitor_enter_keypress(self, playback_process):
        """Non-blocking Enter key listener."""
        Logger.print_debug("Press Enter to stop playback...")

        while playback_process.poll() is None:  # While playback is running
            # Use select to check if input is available (non-blocking check)
            if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
                key_press = sys.stdin.read(1)  # Read single character
                if key_press == '\n':  # Check for Enter key
                    Logger.print_debug("Enter key detected. Terminating playback...")
                    playback_process.terminate()  # Terminate the playback if Enter is pressed
                    break

    def concatenate_audio_from_text(self, text_file_path):
        output_file = "combined_audio.mp3"
        concat_command = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", text_file_path, output_file]
        subprocess.run(concat_command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL, check=True)
        return output_file

    def prepare_playback(self, file_path):
        if file_path.endswith('.mp4'):
            play_command = ["ffplay", "-nodisp", "-autoexit", file_path]
        else:
            play_command = ["ffplay", "-nodisp", "-af", "volume=5", "-autoexit", file_path]
        audio_duration = self.get_audio_duration(file_path)
        return play_command, audio_duration

    def get_audio_duration(self, file_path):
        duration_command = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", file_path]
        duration_output = subprocess.run(duration_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True).stdout.decode('utf-8')
        return float(duration_output.strip())





class GoogleTTS(TextToSpeech):
    def __init__(self):
        super().__init__()
        Logger.print_info("Initializing GoogleTTS...")

    def convert_text_to_speech(self, text: str, voice_id="en-US-Casual-K"):
        try:
            # Initialize the Text-to-Speech client
            client = tts.TextToSpeechClient()

            # Set up the text input and voice settings
            synthesis_input = tts.SynthesisInput(text=text)
            voice = tts.VoiceSelectionParams(
                language_code="en-US",
                name=voice_id,)

            # Set the audio configuration
            audio_config = tts.AudioConfig(
                audio_encoding=tts.AudioEncoding.MP3)

            Logger.print_debug("Converting text to speech...")

            # Perform the text-to-speech request
            response = client.synthesize_speech(
                input=synthesis_input,
                voice=voice,
                audio_config=audio_config)

            # Create temp directory if it doesn't exist
            temp_dir = get_tempdir()
            os.makedirs(os.path.join(temp_dir, "tts"), exist_ok=True)

            # Sanitize the text for use in filename
            # Take first 3 words and replace problematic characters
            words = text.split()[:3]
            sanitized_words = []
            for word in words:
                # Replace slashes, parentheses, and other problematic characters
                sanitized = re.sub(r'[^\w\s-]', '_', word)
                sanitized_words.append(sanitized)
            snippet = '_'.join(sanitized_words)

            # Save the audio to a file
            file_path = os.path.join(temp_dir, "tts", f"chatgpt_response_{snippet}_{datetime.now().strftime('%Y%m%d-%H%M%S')}.mp3")
            with open(file_path, "wb") as out:
                out.write(response.audio_content)

            return True, file_path
        except Exception as e:
            Logger.print_error(f"Error converting text to speech: {e}")
            return False, None

