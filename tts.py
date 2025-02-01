"""Text-to-Speech module for GANGLIA.

This module provides text-to-speech functionality using various backends.
Currently supports Google Cloud Text-to-Speech with features including:
- Text chunking for long inputs
- Audio playback with skip functionality
- Error handling and retries
- Local file handling
"""

# Standard library imports
import os
import re
import select
import subprocess
import sys
import threading
from abc import ABC, abstractmethod
from datetime import datetime
from urllib.parse import urlparse

# Third-party imports
from google.cloud import texttospeech_v1 as tts

# Local imports
from logger import Logger
from utils import get_tempdir, exponential_backoff

class TextToSpeech(ABC):
    """Abstract base class for text-to-speech functionality.
    
    This class defines the interface for text-to-speech implementations
    and provides common utility methods for audio handling and playback.
    """

    @abstractmethod
    def convert_text_to_speech(self, text: str, voice_id: str = None, 
                             thread_id: str = None):
        """Convert text to speech using the specified voice.
        
        Args:
            text: The text to convert to speech
            voice_id: The ID of the voice to use (default: "en-US-Casual-K")
            thread_id: Optional thread ID for logging purposes
            
        Returns:
            tuple: (success: bool, file_path: str) where file_path is the path
                  to the generated audio file if successful, None otherwise
        """
        pass

    def is_local_filepath(self, file_path: str) -> bool:
        """Check if a file path is a local file path.
        
        Args:
            file_path: The file path to check
            
        Returns:
            bool: True if the path is a local file path, False otherwise
        """
        try:
            result = urlparse(file_path)
            return all([result.scheme, result.netloc])
        except ValueError:
            return False

    @classmethod
    def split_text(cls, text: str, max_length: int = 250):
        """Split text into chunks of maximum length while preserving sentences.
        
        Args:
            text: The text to split
            max_length: Maximum length of each chunk (default: 250)
            
        Returns:
            list: List of text chunks
        """
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
        """Play speech response and handle user interaction.
        
        Args:
            file_path: Path to the audio file to play
            raw_response: The text response to display
        """
        if file_path.endswith('.txt'):
            file_path = self.concatenate_audio_from_text(file_path)

        # Only play audio if explicitly enabled
        if os.getenv('PLAYBACK_MEDIA_IN_TESTS', 'false').lower() == 'true':
            # Prepare the play command and determine the audio duration
            play_command, audio_duration = self.prepare_playback(file_path)

            Logger.print_demon_output(
                f"\nGANGLIA says... (Audio Duration: {audio_duration:.1f} seconds)"
            )
            Logger.print_demon_output(raw_response)

            # Start playback in a non-blocking manner
            playback_process = subprocess.Popen(
                play_command, 
                stdout=subprocess.DEVNULL, 
                stderr=subprocess.DEVNULL, 
                stdin=subprocess.DEVNULL
            )

            # Start the Enter key listener in a separate thread
            stop_thread = threading.Thread(
                target=self.monitor_enter_keypress, 
                args=(playback_process,)
            )
            # Ensure the thread exits when the main program exits
            stop_thread.daemon = True
            stop_thread.start()

            # Wait for playback process to finish
            playback_process.wait()

            # Ensure Enter key thread finishes
            stop_thread.join(timeout=1)  # Attempt to join, but timeout if it hangs

    def monitor_enter_keypress(self, playback_process):
        """Monitor for Enter key press to stop playback.
        
        Args:
            playback_process: The subprocess running the audio playback
        """
        Logger.print_debug("Press Enter to stop playback...")

        while playback_process.poll() is None:  # While playback is running
            # Use select to check if input is available (non-blocking check)
            if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
                key_press = sys.stdin.read(1)  # Read single character
                if key_press == '\n':  # Check for Enter key
                    Logger.print_debug("Enter key detected. Terminating playback...")
                    playback_process.terminate()
                    break

    def concatenate_audio_from_text(self, text_file_path):
        """Concatenate multiple audio files listed in a text file.
        
        Args:
            text_file_path: Path to the text file containing audio file paths
            
        Returns:
            str: Path to the concatenated audio file
        """
        output_file = "combined_audio.mp3"
        concat_command = [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0", 
            "-i", text_file_path, output_file
        ]
        subprocess.run(
            concat_command, 
            stdout=subprocess.DEVNULL, 
            stderr=subprocess.DEVNULL, 
            stdin=subprocess.DEVNULL, 
            check=True
        )
        return output_file

    def prepare_playback(self, file_path):
        """Prepare audio playback command and get duration.
        
        Args:
            file_path: Path to the audio file
            
        Returns:
            tuple: (play_command: list, audio_duration: float)
        """
        if file_path.endswith('.mp4'):
            play_command = ["ffplay", "-nodisp", "-autoexit", file_path]
        else:
            play_command = [
                "ffplay", "-nodisp", "-af", "volume=5", "-autoexit", file_path
            ]
        audio_duration = self.get_audio_duration(file_path)
        return play_command, audio_duration

    def get_audio_duration(self, file_path):
        """Get the duration of an audio file.
        
        Args:
            file_path: Path to the audio file
            
        Returns:
            float: Duration of the audio in seconds
        """
        duration_command = [
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", file_path
        ]
        duration_output = subprocess.run(
            duration_command, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE, 
            check=True
        ).stdout.decode('utf-8')
        return float(duration_output.strip())





class GoogleTTS(TextToSpeech):
    """Google Cloud Text-to-Speech implementation.
    
    This class implements text-to-speech functionality using the Google Cloud
    Text-to-Speech API, with support for various voices and audio configurations.
    """

    # Class-level lock for gRPC client creation
    _client_lock = threading.Lock()

    def __init__(self):
        """Initialize the Google TTS client."""
        super().__init__()
        Logger.print_info("Initializing GoogleTTS...")
        # Create a single shared client instance with thread safety
        with self._client_lock:
            self._client = tts.TextToSpeechClient()

    def _convert_text_to_speech_impl(self, text: str, voice_id="en-US-Casual-K", 
                                   thread_id: str = None):
        """Internal implementation of text-to-speech conversion.
        
        Args:
            text: The text to convert to speech
            voice_id: The ID of the voice to use (default: "en-US-Casual-K")
            thread_id: Optional thread ID for logging purposes
            
        Returns:
            tuple: (success: bool, file_path: str) where file_path is the path
                  to the generated audio file if successful
        """
        # Set up the text input and voice settings
        synthesis_input = tts.SynthesisInput(text=text)
        voice = tts.VoiceSelectionParams(
            language_code="en-US",
            name=voice_id,
        )

        # Set the audio configuration
        audio_config = tts.AudioConfig(
            audio_encoding=tts.AudioEncoding.MP3
        )

        thread_prefix = f"{thread_id} " if thread_id else ""
        Logger.print_debug(f"{thread_prefix}Converting text to speech...")

        # Use the shared client instance
        response = self._client.synthesize_speech(
            input=synthesis_input,
            voice=voice,
            audio_config=audio_config
        )

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
        timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
        file_path = os.path.join(
            temp_dir, "tts", 
            f"chatgpt_response_{snippet}_{timestamp}.mp3"
        )
        with open(file_path, "wb") as out:
            out.write(response.audio_content)

        return True, file_path

    def convert_text_to_speech(self, text: str, voice_id="en-US-Casual-K", 
                             thread_id: str = None):
        """Convert text to speech using the specified voice with retry logic.
        
        Args:
            text: The text to convert to speech
            voice_id: The ID of the voice to use (default: "en-US-Casual-K")
            thread_id: Optional thread ID for logging purposes
            
        Returns:
            tuple: (success: bool, file_path: str) where file_path is the path
                  to the generated audio file if successful, None otherwise
        """
        thread_prefix = f"{thread_id} " if thread_id else ""
        
        try:
            return exponential_backoff(
                lambda: self._convert_text_to_speech_impl(text, voice_id, thread_id),
                max_retries=5,
                initial_delay=1.0,
                thread_id=thread_id
            )
        except (tts.TextToSpeechError, IOError) as e:
            Logger.print_error(
                f"{thread_prefix}Error converting text to speech: {e}"
            )
            return False, None

