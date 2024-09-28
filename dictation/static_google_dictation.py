import pyaudio
import speech_recognition as sr
from logger import Logger
from .dictation import Dictation
from google.cloud import speech_v1p1beta1 as speech
from threading import Timer

class StaticGoogleDictation(Dictation):
    def getDictatedInput(self, device_index, interruptable=False):
        Logger.print_debug("Testing audio input access...")
        recognizer = sr.Recognizer()

        with sr.Microphone(device_index=device_index) as source:
            Logger.print_info("Microphone detected.")
            Logger.print_info("Calibrating microphone...")
            recognizer.adjust_for_ambient_noise(source, duration=1)
            Logger.print_info("Go!")
            audio = recognizer.listen(source, phrase_time_limit=50000)
            Logger.print_info("Finished listening.")

            try:
                text = recognizer.recognize_google(audio)
                Logger.print_user_input("You: ", text)
                return text
            except sr.UnknownValueError:
                Logger.print_error("Google Speech Recognition could not understand the audio.")
            except sr.RequestError as e:
                Logger.print_error(f"Could not request results from Google Speech Recognition service; {e}")

    def done_speaking(self, current_line):
        pass


class LiveGoogleDictation(Dictation):
    SILENCE_THRESHOLD = 2.5  # seconds
    COUNTER = 0

    def __init__(self):
        try:
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
        while self.listening:
            yield self.audio_stream.read(1024, exception_on_overflow=False)

    def done_speaking(self):
        self.listening = False

    def transcribe_stream(self, stream, interruptable=False):
        done_speaking_timer = None
        self.state = 'START'
        finalized_transcript = ''

        requests = (speech.StreamingRecognizeRequest(audio_content=chunk) for chunk in stream)
        responses = self.client.streaming_recognize(self.get_config(), requests)

        for response in responses:
            if not response.results:
                continue
            result = response.results[0]
            if not result.alternatives:
                continue

            current_input = result.alternatives[0].transcript.strip()

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

    def getDictatedInput(self, device_index, interruptable=False):
        self.listening = True
        transcript = self.transcribe_stream(self.generate_audio_chunks(), interruptable)
        return transcript