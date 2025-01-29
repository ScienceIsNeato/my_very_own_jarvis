import argparse
import speech_recognition as sr
import wave
import pyaudio
import subprocess
import pytest
import os

@pytest.fixture
def device_index():
    return 1  # USB Advanced Audio Device with 2 input channels

@pytest.mark.unit
@pytest.mark.skip # This test only needs to be run if you are experiencing microphone issues
def test_audio_input(device_index):
    print("Testing audio input access...")
    print("Using PyAudio version: ", pyaudio.__version__)

    # Initialize PyAudio
    audio = pyaudio.PyAudio()
    
    # List available devices
    print("\nAvailable audio devices:")
    for i in range(audio.get_device_count()):
        dev_info = audio.get_device_info_by_index(i)
        print(f"{i}: {dev_info['name']} (in: {dev_info['maxInputChannels']}, out: {dev_info['maxOutputChannels']})")
    
    try:
        # Get device info
        device_info = audio.get_device_info_by_index(device_index)
        channels = max(1, int(device_info["maxInputChannels"]))
        rate = int(device_info["defaultSampleRate"])
        
        print(f"\nUsing device {device_index}: {device_info['name']}")
        print(f"Channels: {channels}")
        print(f"Sample rate: {rate}")
        
        # Open stream
        stream = audio.open(
            format=pyaudio.paInt16,
            channels=channels,
            rate=rate,
            input=True,
            input_device_index=device_index,
            frames_per_buffer=1024
        )
        
        print("\nRecording for 3 seconds...")
        frames = []
        for _ in range(0, int(rate / 1024 * 3)):
            data = stream.read(1024)
            frames.append(data)
        print("Finished recording")
        
        # Stop and close the stream
        stream.stop_stream()
        stream.close()
        
        # Save the recorded data as a WAV file
        with wave.open("recorded_audio.wav", "wb") as file:
            # pylint: disable=no-member
            file.setnchannels(channels)
            file.setsampwidth(audio.get_sample_size(pyaudio.paInt16))
            file.setframerate(rate)
            file.writeframes(b''.join(frames))
        print("Audio saved to recorded_audio.wav")
        
        # Convert to MP3
        subprocess.run(['ffmpeg', '-y', '-i', 'recorded_audio.wav', 'recorded_audio.mp3'], check=True)
        
        print("Playing recorded audio...")
        test_play_audio()
        
    finally:
        audio.terminate()

def test_play_audio():
    # Only play audio if explicitly enabled
    if os.getenv('PLAYBACK_MEDIA_IN_TESTS', 'false').lower() == 'true':
        subprocess.call(['ffplay', '-nodisp', '-autoexit', 'recorded_audio.mp3'])

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--device-index', type=int, default=1,
                      help='Index of the input device to use.')
    args = parser.parse_args()
    test_audio_input(args.device_index)
