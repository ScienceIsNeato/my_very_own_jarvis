"""Tests for the Suno MusicGen backend integration.

This module contains tests that verify the functionality of the Suno MusicGen
backend, including music generation with lyrics and instrumental music generation.
The tests include audio playback capabilities with skip functionality.
"""

# Standard library imports
import json
import os
import select
import subprocess
import sys
import termios
import tty

# Third-party imports
import pytest

# Local imports
from music_lib import MusicGenerator
from ttv.config_loader import load_input

class MockQueryDispatcher:
    """Mock query dispatcher for testing music generation with lyrics."""
    def send_query(self, query):  # pylint: disable=unused-argument
        """Return a mock response with folk style and test lyrics.
        
        Args:
            query: The query string (unused in mock)
            
        Returns:
            str: JSON string containing mock style and lyrics
        """
        return json.dumps({
            "style": "folk",
            "lyrics": "\n".join([
                "Life is beautiful, every day brings something new",
                "The sun is shining, and the sky is so blue",
                "Birds are singing their sweet melodies",
                "Nature's symphony, carried by the breeze"
            ])
        })

def play_audio(audio_path):
    """Play audio file and allow skipping with spacebar.
    
    Args:
        audio_path: Path to the audio file to play
    """
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
            except (termios.error, tty.error) as e:
                print(f"Terminal interaction error: {e}")
            finally:
                try:
                    termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
                except (termios.error, tty.error) as e:
                    print(f"Failed to restore terminal settings: {e}")
    except (subprocess.SubprocessError, OSError) as e:
        print(f"Audio playback error: {e}")

@pytest.mark.costly
def test_suno_backend():
    """Test music generation using the Suno backend.
    
    This test verifies both lyrical and instrumental music generation.
    It includes audio playback with skip functionality if enabled.
    """
    config = load_input("tests/integration/test_data/minimal_ttv_config.json")
    config.music_backend = "suno"  # Ensure we're using Suno backend
    generator = MusicGenerator(config=config)

    # Test music with lyrics first (since it was failing)
    print("\nGenerating music with lyrics...")
    story_text = (
        "Life is beautiful, every day brings something new\n"
        "The sun is shining, and the sky is so blue\n"
        "Birds are singing their sweet melodies\n"
        "Nature's symphony, carried by the breeze"
    )
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
    print("\nGenerating instrumental music with prompt: A short peaceful piano melody.")
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
