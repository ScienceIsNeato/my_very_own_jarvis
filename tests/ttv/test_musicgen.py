import os
import pytest
import subprocess
import sys
import termios
import tty
import json
from music_lib import MusicGenerator
from ttv.config_loader import load_input

"""
Test for Meta's MusicGen model using Hugging Face Transformers.
This test verifies:
1. Music generation with text prompts
2. Audio output generation and saving
3. Model configuration and parameter settings

Requirements:
- transformers
- torch
- soundfile
- numpy
- tqdm
"""

class MockQueryDispatcher:
    """Mock query dispatcher for testing."""
    def sendQuery(self, query):
        return json.dumps({
            "style": "folk",
            "lyrics": "\n".join([
                "Life is beautiful, every day brings something new",
                "The sun is shining, and the sky is so blue",
                "Birds are singing their sweet melodies",
                "Nature's symphony, carried by the breeze"
            ])
        })

def is_space_pressed():
    """Check if spacebar is pressed without blocking."""
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(sys.stdin.fileno())
        ch = sys.stdin.read(1)
        return ch == ' '
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

def play_audio(audio_path):
    """Play audio file and allow skipping with spacebar."""
    try:
        if os.uname().sysname == 'Darwin':  # macOS
            process = subprocess.Popen(['afplay', audio_path])
        else:  # Linux/Others - requires vlc
            process = subprocess.Popen(['vlc', '--play-and-exit', audio_path])
        
        while process.poll() is None:
            if is_space_pressed():
                process.terminate()
                break
            
    except Exception as e:
        print(f"Failed to play audio: {str(e)}")

def test_suno_backend():
    """Test music generation using the Suno backend."""
    config = load_input("tests/ttv/test_data/prompt_based_config.json")
    config.music_backend = "suno"  # Ensure we're using Suno backend
    generator = MusicGenerator(config=config)
    
    # Test music with lyrics first (since it was failing)
    print("\nGenerating music with lyrics...")
    story_text = """
    Life is beautiful, every day brings something new
    The sun is shining, and the sky is so blue
    Birds are singing their sweet melodies
    Nature's symphony, carried by the breeze
    """
    audio_path = generator.generate_with_lyrics(
        "A gentle folk song with acoustic guitar",
        story_text,
        duration_seconds=30,
        query_dispatcher=MockQueryDispatcher()
    )
    assert audio_path is not None
    assert os.path.exists(audio_path)
    assert audio_path.endswith('.mp3')
    
    print(f"\nPlaying generated audio from {audio_path}")
    print("Press SPACE to skip audio playback...")
    play_audio(audio_path)
    
    # Test instrumental generation (30 seconds max)
    print("\nGenerating instrumental music with prompt: A short peaceful piano melody. High quality recording.")
    audio_path = generator.generate_instrumental(
        "A short peaceful piano melody. High quality recording.",
        duration_seconds=30
    )
    assert audio_path is not None
    assert os.path.exists(audio_path)
    assert audio_path.endswith('.mp3')
    
    print(f"\nPlaying generated audio from {audio_path}")
    print("Press SPACE to skip audio playback...")
    play_audio(audio_path)

def test_meta_backend():
    """Test the Meta MusicGen backend for instrumental music generation."""
    config = load_input("tests/ttv/test_data/prompt_based_config.json")
    config.music_backend = "meta"  # Override to use Meta backend
    generator = MusicGenerator(config=config)
    
    # Test instrumental music generation
    print("\nGenerating instrumental music with prompt: A short peaceful piano melody. High quality recording.")
    audio_path = generator.generate_instrumental(
        "A short peaceful piano melody. High quality recording.",
        max_new_tokens=256  # ~8 seconds of audio
    )
    
    # Verify the output
    assert audio_path is not None, "Audio path should not be None"
    assert os.path.exists(audio_path), f"Audio file should exist at {audio_path}"
    assert audio_path.endswith('.wav'), "Audio file should be WAV format"
    
    print(f"\nPlaying generated audio from {audio_path}")
    print("Press SPACE to skip audio playback...")
    play_audio(audio_path) 