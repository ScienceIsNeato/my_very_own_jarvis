import pyaudio
import keyboard  # Import keyboard to detect space bar press
from google.cloud import speech_v1p1beta1 as speech
from logger import Logger
from threading import Timer
import time
import socket
from session_logger import SessionEvent

from .dictation import Dictation

class LiveGoogleDictation(Dictation):
    SILENCE_THRESHOLD = 2.5  # seconds
    COUNTER = 0
    MAX_RETRIES = 5  # Number of retry attempts in case of a broken pipe
    RETRY_DELAY = 2  # Seconds to wait before retrying

    def __init__(self):
        try:
            self.session_logger = None
            self.listening = True
            self.client = speech.SpeechClient()
            self.audio_stream = pyaudio.PyAudio().open(
                format=pyaudio.paInt16,
                channels=1,
                rate=16000,
                input=True,
                frames_per_buffer=1024
            )
        except Exception as e:
            Logger.print_error(f"Error initializing LiveGoogleDictation: {e}")
            raise

    def get_config(self):
        return speech.StreamingRecognitionConfig(
            config=speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
                sample_rate_hertz=16000,
                language_code="en-US",
                enable_automatic_punctuation=True,
                use_enhanced=True
            ),
            interim_results=True,
        )

    def generate_audio_chunks(self):
        """Generator that yields audio chunks from the audio stream."""
        while self.listening:
            yield self.audio_stream.read(1024, exception_on_overflow=False)

    def done_speaking(self):
        """Mark the dictation as complete."""
        self.listening = False

    def transcribe_stream(self, stream, interruptable=False):
        """Main transcription loop."""
        done_speaking_timer = None
        self.state = 'START'
        finalized_transcript = ''

        responses = self.stream_with_retries(stream)

        for response in responses:
            if not response.results:
                continue
            result = response.results[0]
            if not result.alternatives:
                continue

            current_input = result.alternatives[0].transcript.strip()

            # Check for space bar press if interruptable is True
            if interruptable and keyboard.is_pressed('space'):
                Logger.print_info("Spacebar pressed! Stopping dictation.")
                self.done_speaking()
                break  # Exit the transcription loop

            if done_speaking_timer is not None:
                done_speaking_timer.cancel()

            is_final = result.is_final

            if self.state == 'START':
                Logger.print_user_input(f'\033[K{current_input}\r', end='', flush=True)
                self.state = 'LISTENING'

            elif is_final:
                finalized_transcript += f"{current_input} "
                Logger.print_user_input(f'\033[K{current_input}', flush=True)
                self.state = 'START'
                done_speaking_timer = Timer(self.SILENCE_THRESHOLD, self.done_speaking)
                done_speaking_timer.start()

            elif self.state == 'LISTENING':
                Logger.print_user_input(f'\033[K{current_input}', end='\r', flush=True)

        return finalized_transcript

    def stream_with_retries(self, stream):
        """
        Handles the `streaming_recognize` call with retry logic in case of BrokenPipeError or other network-related issues.
        Logs the BrokenPipeError as a conversation event.
        """
        retries = 0
        while retries < self.MAX_RETRIES:
            try:
                requests = (speech.StreamingRecognizeRequest(audio_content=chunk) for chunk in stream)
                responses = self.client.streaming_recognize(self.get_config(), requests)
                return responses  # Exit loop on success
            except (BrokenPipeError, socket.error) as e:
                Logger.print_error(f"503 BrokenPipeError encountered: {e}. Retrying in {self.RETRY_DELAY} seconds...")

                # Log BrokenPipeError as a conversation event
                if self.session_logger:
                    self.session_logger.log_session_interaction(
                        SessionEvent(
                            user_input="SYSTEM ERROR",
                            response_output=f"503 BrokenPipeError encountered: {e}. Retrying... (Attempt {retries + 1})"
                        )
                    )

                retries += 1
                time.sleep(self.RETRY_DELAY)
            except Exception as e:
                Logger.print_error(f"Unexpected error during streaming: {e}")

                # Log any other exceptions as conversation events
                self.session_logger.log_session_interaction(
                    SessionEvent(
                        user_input="SYSTEM ERROR",
                        response_output=f"Unexpected error occurred: {e}"
                    )
                )
                break

        # If max retries exceeded, log failure and return empty iterator
        Logger.print_error("Max retries exceeded. Failed to establish streaming connection.")
        self.session_logger.log_session_interaction(
            SessionEvent(
                user_input="SYSTEM ERROR",
                response_output="Max retries exceeded. Failed to establish streaming connection."
            )
        )
        return iter([])  # Return an empty iterator to gracefully end the transcription

    def getDictatedInput(self, device_index, interruptable=False):
        """
        Start the transcription process, re-using the stream_with_retries method.
        """
        self.listening = True
        transcript = self.transcribe_stream(self.generate_audio_chunks(), interruptable)
        return transcript
