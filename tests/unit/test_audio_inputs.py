import pytest
import speech_recognition as sr
from pydub import AudioSegment
from pydub.playback import play
import threading
from gtts import gTTS
import io

def play_phrase(phrase="Testing microphone, please listen.", repetitions=3, duration=3000):
    tts = gTTS(text=phrase, lang="en")
    with io.BytesIO() as f:
        tts.write_to_fp(f)
        f.seek(0)
        phrase_audio = AudioSegment.from_file(f, format="mp3")
        repeated_phrase = phrase_audio * repetitions
        play(repeated_phrase[:duration])

def getDictatedInput(device_index):
    recognizer = sr.Recognizer()

    try:
        with sr.Microphone(device_index=device_index) as source:
            recognizer.adjust_for_ambient_noise(source, duration=1)
            audio = recognizer.listen(source)
            text = recognizer.recognize_google(audio)
            return True, text
    except Exception as e:
        print(f"Error using device index {device_index}: {e}")
        return False, None


@pytest.mark.skip # This is a helper test to see which microphones are available
def test_microphones():
    recognizer = sr.Recognizer()
    available_mics = sr.Microphone.list_microphone_names()

    results = []

    for index, mic_name in enumerate(available_mics):
        print(f"Testing microphone {index}: {mic_name}")

        # Play the phrase in a separate thread for each input
        phrase_thread = threading.Thread(target=play_phrase, args=("Testing microphone, please listen.", 3))
        phrase_thread.start()

        is_available, text = getDictatedInput(device_index=index)
        status = "Available" if is_available else "N/A"
        results.append((index, mic_name, status))

        # Wait for the phrase to finish playing
        phrase_thread.join()

    print("\nResults:")
    print("Index | Microphone Name | Status")
    for result in results:
        print(f"{result[0]} | {result[1]} | {result[2]}")


if __name__ == "__main__":
    test_microphones()
