import os
import pytest
import subprocess
import sys
import termios
import tty
import json
import select
from music_lib import MusicGenerator
from ttv.config_loader import load_input

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
    if not os.getenv('PLAYBACK_MEDIA_IN_TESTS'):
        return
        
    try:
        if os.uname().sysname == 'Darwin':  # macOS
            process = subprocess.Popen(['afplay', audio_path])
        else:  # Linux/Others - requires vlc
            process = subprocess.Popen(['vlc', '--play-and-exit', audio_path])
        
        # Check process status and spacebar in small intervals
        while process.poll() is None:
            try:
                # Set stdin to non-blocking mode
                fd = sys.stdin.fileno()
                old_settings = termios.tcgetattr(fd)
                tty.setraw(sys.stdin.fileno())
                # Only wait for 0.1 seconds for input
                rlist, _, _ = select.select([sys.stdin], [], [], 0.1)
                if rlist:
                    ch = sys.stdin.read(1)
                    if ch == ' ':
                        process.terminate()
                        break
            except Exception:
                pass
            finally:
                try:
                    termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
                except Exception:
                    pass
    except Exception:
        pass

@pytest.mark.costly
def test_suno_backend():
    """Test music generation using the Suno backend."""
    config = load_input("tests/integration/test_data/minimal_ttv_config.json")
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
