import os
import pytest
import subprocess
import sys
import termios
import tty
import select
from music_lib import MusicGenerator
from ttv.config_loader import load_input

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

@pytest.mark.third_party
def test_meta_backend():
    """Test the Meta MusicGen backend for instrumental music generation."""
    config = load_input("tests/integration/test_data/minimal_ttv_config.json")
    config.music_backend = "meta"  # Override to use Meta backend
    generator = MusicGenerator(config=config)
    
    def verify_duration(prompt: str, target_duration: int):
        print(f"\nGenerating instrumental music with prompt: {prompt}")
        audio_path = generator.generate_instrumental(
            prompt,
            duration_seconds=target_duration
        )
        
        # Verify the output
        assert audio_path is not None, "Audio path should not be None"
        assert os.path.exists(audio_path), f"Audio file should exist at {audio_path}"
        assert audio_path.endswith('.wav'), "Audio file should be WAV format"
        
        # Check actual duration with ffprobe
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", audio_path],
            stdout=subprocess.PIPE,
            check=True,
            text=True
        )
        actual_duration = float(result.stdout.strip())
        # Allow 10% tolerance for duration
        assert abs(actual_duration - target_duration) <= 0.1 * target_duration, \
            f"Generated audio duration ({actual_duration:.1f}s) should be within 10% of target ({target_duration}s)"
        
        print(f"Expected duration: {target_duration}s matches Actual duration: {actual_duration:.1f}s")
        
        if os.getenv('PLAYBACK_MEDIA_IN_TESTS'):
            print(f"\nPlaying generated audio from {audio_path}")
            print("Press SPACE to skip audio playback...")
            play_audio(audio_path)
    
    # Test short duration (7 seconds)
    verify_duration("A short peaceful piano melody. High quality recording.", 7)

@pytest.mark.third_party
@pytest.mark.costly
def test_meta_backend_longer_durations():
    """Test the Meta MusicGen backend with a 25 second duration (maximum single generation length)."""
    config = load_input("tests/integration/test_data/minimal_ttv_config.json")
    config.music_backend = "meta"  # Override to use Meta backend
    generator = MusicGenerator(config=config)
    
    def verify_duration(prompt: str, target_duration: int):
        print(f"\nGenerating instrumental music with prompt: {prompt}")
        audio_path = generator.generate_instrumental(
            prompt,
            duration_seconds=target_duration
        )
        
        # Verify the output
        assert audio_path is not None, "Audio path should not be None"
        assert os.path.exists(audio_path), f"Audio file should exist at {audio_path}"
        assert audio_path.endswith('.wav'), "Audio file should be WAV format"
        
        # Check actual duration with ffprobe
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", audio_path],
            stdout=subprocess.PIPE,
            check=True,
            text=True
        )
        actual_duration = float(result.stdout.strip())
        # Allow 10% tolerance for duration
        assert abs(actual_duration - target_duration) <= 0.1 * target_duration, \
            f"Generated audio duration ({actual_duration:.1f}s) should be within 10% of target ({target_duration}s)"
        
        print(f"Expected duration: {target_duration}s matches Actual duration: {actual_duration:.1f}s")
        
        if os.getenv('PLAYBACK_MEDIA_IN_TESTS'):
            print(f"\nPlaying generated audio from {audio_path}")
            print("Press SPACE to skip audio playback...")
            play_audio(audio_path)
    
    # Test maximum single generation duration (25 seconds)
    verify_duration("An evolving ambient soundscape with gentle pads and subtle rhythms.", 25)

@pytest.mark.third_party
@pytest.mark.costly
def test_meta_backend_looping():
    """Test the Meta MusicGen backend with a 3 minute duration that requires looping."""
    config = load_input("tests/integration/test_data/minimal_ttv_config.json")
    config.music_backend = "meta"  # Override to use Meta backend
    generator = MusicGenerator(config=config)
    
    def verify_duration(prompt: str, target_duration: int):
        print(f"\nGenerating instrumental music with prompt: {prompt}")
        audio_path = generator.generate_instrumental(
            prompt,
            duration_seconds=target_duration
        )
        
        # Verify the output
        assert audio_path is not None, "Audio path should not be None"
        assert os.path.exists(audio_path), f"Audio file should exist at {audio_path}"
        assert audio_path.endswith('.wav'), "Audio file should be WAV format"
        
        # Check actual duration with ffprobe
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", audio_path],
            stdout=subprocess.PIPE,
            check=True,
            text=True
        )
        actual_duration = float(result.stdout.strip())
        # Allow 10% tolerance for duration
        assert abs(actual_duration - target_duration) <= 0.1 * target_duration, \
            f"Generated audio duration ({actual_duration:.1f}s) should be within 10% of target ({target_duration}s)"
        
        print(f"Expected duration: {target_duration}s matches Actual duration: {actual_duration:.1f}s")
        
        if os.getenv('PLAYBACK_MEDIA_IN_TESTS'):
            print(f"\nPlaying generated audio from {audio_path}")
            print("Press SPACE to skip audio playback...")
            play_audio(audio_path)
    
    # Test long duration that requires looping (3 minutes)
    verify_duration(
        "A progressive electronic journey with evolving textures, subtle rhythms, and atmospheric pads that build and transform over time.",
        180  # 3 minutes in seconds
    ) 