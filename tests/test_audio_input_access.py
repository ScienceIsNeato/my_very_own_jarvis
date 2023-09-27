import argparse
import speech_recognition as sr
import wave
import pyaudio
import subprocess
import pytest

@pytest.fixture
def listen_dur_secs():
    return 5

@pytest.fixture
def device_index():
    return 0

@pytest.mark.skip
def test_audio_input(listen_dur_secs, device_index):
    print("Testing audio input access...")
    print("Using SpeechRecognition version: ", sr.__version__)
    print("Using PyAudio version: ", pyaudio.__version__)
    print("Note - This test will fail if you don't talk into the microphone! Testing audio input access...")

    recognizer = sr.Recognizer()

    with sr.Microphone(device_index=device_index) as source:
        print("Microphone detected.")
        device_info = pyaudio.PyAudio().get_device_info_by_index(device_index)
        channels = device_info.get("maxInputChannels", 5)
        sample_width = pyaudio.PyAudio().get_sample_size(source.format)
        frame_rate = source.SAMPLE_RATE
        print("Device index:", device_index)
        print("Format:", source.format)
        print("Sample rate:", source.SAMPLE_RATE)
        print("Will listen for", listen_dur_secs, "seconds...")
        print("Channels:", channels)
        print("Go!")

        audio = recognizer.listen(source, timeout=listen_dur_secs)
        print("Finished listening.")

        try:
            text = recognizer.recognize_google(audio)
            print("You said: ", text)
        except sr.UnknownValueError:
            print("Google Speech Recognition could not understand the audio.")
        except sr.RequestError as e:
            print(f"Could not request results from Google Speech Recognition service; {e}")

        with wave.open("recorded_audio.wav", "wb") as file:
            file.setnchannels(channels)
            file.setsampwidth(sample_width)
            file.setframerate(frame_rate)
            file.writeframes(audio.get_wav_data())
        print("Audio saved to recorded_audio.wav")

        # Convert the WAV file to an MP3 file
        subprocess.run(['ffmpeg', '-y', '-i', 'recorded_audio.wav', 'recorded_audio.mp3'])

        print("Playing recorded audio...")
        # Play the recorded audio using ffplay
        subprocess.call(['ffplay', '-nodisp', '-autoexit', 'recorded_audio.mp3'])

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--listen_dur_secs', type=int, default=5,
                        help='Number of seconds to listen.')
    parser.add_argument('--device_index', type=int, default=0,
                        help='Index of the input device to use.')
    args = parser.parse_args()
    test_audio_input(args.listen_dur_secs, args.device_index)
