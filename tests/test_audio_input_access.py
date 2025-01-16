import argparse
import speech_recognition as sr
import pyaudio
import subprocess
import pytest
import os

def find_input_device():
    """Find the first available input device."""
    p = pyaudio.PyAudio()
    for i in range(p.get_device_count()):
        device_info = p.get_device_info_by_index(i)
        if device_info.get("maxInputChannels", 0) > 0:
            return i
    return None

@pytest.fixture
def device_index():
    device = find_input_device()
    if device is None:
        pytest.skip("No input devices found")
    return device

@pytest.fixture
def temp_files():
    yield
    # Cleanup after test
    for file in ["recorded_audio.wav", "recorded_audio.mp3"]:
        if os.path.exists(file):
            os.remove(file)

def test_audio_input(device_index, temp_files):
    """Test audio input access and recording capabilities."""
    recognizer = sr.Recognizer()
    
    with sr.Microphone(device_index=device_index) as source:
        # Verify device info
        device_info = pyaudio.PyAudio().get_device_info_by_index(device_index)
        channels = device_info.get("maxInputChannels", 0)
        sample_width = pyaudio.PyAudio().get_sample_size(source.format)
        frame_rate = source.SAMPLE_RATE
        
        assert channels > 0, "No input channels available"
        assert sample_width > 0, "Invalid sample width"
        assert frame_rate > 0, "Invalid frame rate"
        
        print(f"\nUsing input device {device_index}: {device_info.get('name', 'Unknown')}")
        print("Recording 3 seconds of audio...")
        audio = recognizer.listen(source, timeout=3)
        assert audio is not None, "Failed to record audio"
        
        # Save WAV
        wav_data = audio.get_wav_data()
        with open("recorded_audio.wav", "wb") as f:
            f.write(wav_data)
        assert os.path.exists("recorded_audio.wav"), "WAV file not created"
        assert os.path.getsize("recorded_audio.wav") > 0, "WAV file is empty"
        
        # Convert to MP3
        subprocess.run(['ffmpeg', '-y', '-i', 'recorded_audio.wav', 'recorded_audio.mp3'], 
                      check=True, capture_output=True)
        assert os.path.exists("recorded_audio.mp3"), "MP3 file not created"
        assert os.path.getsize("recorded_audio.mp3") > 0, "MP3 file is empty"

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--device_index', type=int, default=None,
                      help='Index of the input device to use.')
    args = parser.parse_args()
    if args.device_index is not None:
        device_index = args.device_index
    pytest.main([__file__, "-v"])
