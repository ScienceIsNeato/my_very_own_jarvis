from abc import ABC, abstractmethod
from gtts import gTTS
from pydub import AudioSegment
from pydub.playback import play
from datetime import datetime

class TextToSpeech(ABC):
    @abstractmethod
    def convert_text_to_speech(self, text: str):
        pass

    def play_speech_response(self, error_code, file_path):
        if error_code != 0:
            print("Error: Cannot play the speech response due to previous error.")
            return

        try:
            audio = AudioSegment.from_mp3(file_path)
            play(audio)
        except Exception as e:
            print(f"Error playing the speech response: {e}")

class GoogleTTS(TextToSpeech):
    def convert_text_to_speech(self, text: str):
        try:
            tts = gTTS(text=text, lang="en-uk",)
            file_path = f"/tmp/chatgpt_response_{datetime.now().strftime('%Y%m%d-%H%M%S')}.mp3"
            tts.save(file_path)
            return 0, file_path
        except Exception as e:
            print(f"Error converting text to speech: {e}")
            return 1, None

class NaturalReadersTTS(TextToSpeech):
    def convert_text_to_speech(self, text: str):
        # TODO: Implement NaturalReadersTTS conversion
        pass
