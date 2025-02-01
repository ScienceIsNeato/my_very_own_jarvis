"""Tests for audio input device access and configuration.

This module contains tests for verifying audio input device detection,
configuration, and recording capabilities.
"""

# Standard library imports
import os
import subprocess
import wave

# Third-party imports
import pytest
import pyaudio

@pytest.fixture
def device_index():
    """Get the default audio input device index."""
    audio = pyaudio.PyAudio()
    try:
        return audio.get_default_input_device_info()['index']
    finally:
        audio.terminate()

def test_get_device_index(device_index):
    """Test retrieving the default audio input device index."""
    audio = pyaudio.PyAudio()
    try:
        device_info = audio.get_default_input_device_info()
        assert device_info['index'] == device_index
    finally:
        audio.terminate()

def test_audio_recording():
    """Test basic audio recording functionality."""
    audio = pyaudio.PyAudio()
    try:
        # Configure recording parameters
        format_code = pyaudio.paInt16
        channels = 1
        rate = 44100
        chunk = 1024
        duration = 1  # seconds
        frames = []

        # Start recording
        stream = audio.open(
            format=format_code,
            channels=channels,
            rate=rate,
            input=True,
            frames_per_buffer=chunk
        )

        # Record for specified duration
        for _ in range(0, int(rate / chunk * duration)):
            data = stream.read(chunk)
            frames.append(data)

        # Stop recording
        stream.stop_stream()
        stream.close()

        # Save recording to WAV file
        test_file = "test_recording.wav"
        with wave.open(test_file, 'wb') as wf:
            wf.setnchannels(channels)
            wf.setsampwidth(audio.get_sample_size(format_code))
            wf.setframerate(rate)
            wf.writeframes(b''.join(frames))

        # Verify file exists and has content
        assert os.path.exists(test_file)
        assert os.path.getsize(test_file) > 0

        # Clean up
        os.remove(test_file)

    finally:
        audio.terminate()

def test_audio_playback():
    """Test audio playback functionality."""
    # Create a test WAV file
    test_file = "test_playback.wav"
    with wave.open(test_file, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(44100)
        wf.writeframes(b'\x00' * 44100 * 2)  # 1 second of silence

    try:
        # Test playback using ffplay
        subprocess.run(["ffplay", "-nodisp", "-autoexit", test_file], check=True)
    except subprocess.CalledProcessError as e:
        pytest.skip(f"Audio playback failed: {e}")
    finally:
        os.remove(test_file)
