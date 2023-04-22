import speech_recognition as sr
from abc import ABC, abstractmethod


class Dictation(ABC):
    @abstractmethod
    def getDictatedInput(self, listen_dur_secs, device_index):
        pass


class StaticGoogleDictation(Dictation):
    def getDictatedInput(self, listen_dur_secs, device_index):
        print("Testing audio input access...")
        recognizer = sr.Recognizer()

        with sr.Microphone(device_index=device_index) as source:
            print("Microphone detected.")
            print("Will listen for", listen_dur_secs, "seconds...")
            print("Calibrating microphone...")

            recognizer.adjust_for_ambient_noise(source, duration=1)

            print("Go!")

            audio = recognizer.listen(source, timeout=listen_dur_secs, phrase_time_limit=50000)
            print("Finished listening.")

            try:
                text = recognizer.recognize_google(audio)
                print("You said: ", text)
                return text
            except sr.UnknownValueError:
                print("Google Speech Recognition could not understand the audio.")
            except sr.RequestError as e:
                print(f"Could not request results from Google Speech Recognition service; {e}")


class LiveAssemblyAIDictation(Dictation):
    def getDictatedInput(self, listen_dur_secs, device_index):
        # Stubbed method, implement the actual functionality here
        pass
