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
