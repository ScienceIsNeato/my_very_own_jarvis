import os
import tempfile
import sys

import pytest
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
from utils import get_tempdir
from PIL import Image, ImageFont
from tts import GoogleTTS
from ttv.audio_alignment import create_word_level_captions
from ttv.video_generation import run_ffmpeg_command
from ttv.captions import (
    CaptionEntry, create_dynamic_captions, create_srt_captions,
    create_static_captions, Word, create_caption_windows,
    split_into_words, calculate_word_positions
)
from logger import Logger
import numpy as np
import soundfile as sf

def get_default_font():
    """Get the default font path for testing."""
    # Try common system font locations
    font_paths = [
        "/System/Library/Fonts/Supplemental/Arial.ttf",  # macOS
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",  # Linux
        "C:\\Windows\\Fonts\\arial.ttf"  # Windows
    ]
    for path in font_paths:
        if os.path.exists(path):
            return path
    return None

def create_test_video(duration=5, size=(1920, 1080), color=(0, 0, 255)):
    """Create a simple colored background video for testing with a silent audio track"""
    # Create a colored image using PIL
    image = Image.new('RGB', size, color)
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as img_file:
        image.save(img_file.name)
        
        # First create video with silent audio
        video_path = img_file.name.replace('.png', '.mp4')
        
        # Create video with silent audio track
        ffmpeg_cmd = [
            "ffmpeg", "-y", "-loop", "1", "-i", img_file.name,
            "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
            "-c:v", "libx264", "-t", str(duration),
            "-c:a", "aac", "-b:a", "192k",
            "-pix_fmt", "yuv420p", video_path
        ]
        result = run_ffmpeg_command(ffmpeg_cmd)
        if result is None:
            Logger.print_error("Failed to create test video")
            return None
        
        # Clean up temporary files
        os.unlink(img_file.name)
        return video_path

def play_test_video(video_path):
    """Play the test video using ffplay."""
    if os.getenv('PLAYBACK_MEDIA_IN_TESTS', 'false').lower() == 'true':
        play_cmd = ["ffplay", "-autoexit", video_path]
        run_ffmpeg_command(play_cmd)


def test_default_static_captions():
    """Test that static captions work with default settings."""
    # Create test video
    input_video_path = create_test_video(duration=2)
    assert input_video_path is not None, "Failed to create test video"
    
    # Create test captions
    captions = [CaptionEntry("Testing default static captions", 0.0, 2.0)]
    
    # Create output path
    output_path = os.path.join(get_tempdir(), "output_default_static_test.mp4")
    
    try:
        # Test the function with default settings
        result = create_static_captions(
            input_video=input_video_path,
            captions=captions,
            output_path=output_path
        )
        
        # Verify results
        assert result is not None, "Failed to create video with default static captions"
        assert os.path.exists(output_path), f"Output file not created: {output_path}"
        assert os.path.getsize(output_path) > 0, "Output file is empty"
        
        # Play the video (skipped in automated testing)
        play_test_video(output_path)
        
    finally:
        # Clean up
        if os.path.exists(input_video_path):
            os.unlink(input_video_path)
        if os.path.exists(output_path):
            os.unlink(output_path)


def test_static_captions():
    """Test static caption generation"""
    # Create test video
    input_video_path = create_test_video(duration=1)
    assert input_video_path is not None, "Failed to create test video"
    
    # Create test captions
    captions = [
        CaptionEntry("Hello World", 0.0, 0.5),
        CaptionEntry("Testing Captions", 0.5, 1.0)
    ]
    
    # Create output path
    output_path = os.path.join(get_tempdir(), "output_static_test.mp4")
    
    try:
        # Test the function
        result = create_static_captions(
            input_video=input_video_path,
            captions=captions,
            output_path=output_path
        )
        
        # Verify results
        assert result is not None, "Failed to create video with static captions"
        assert os.path.exists(output_path), f"Output file not created: {output_path}"
        assert os.path.getsize(output_path) > 0, "Output file is empty"
        
        # Play the video (skipped in automated testing)
        play_test_video(output_path)
        
    finally:
        # Clean up
        if os.path.exists(input_video_path):
            os.unlink(input_video_path)
        if os.path.exists(output_path):
            os.unlink(output_path)


def test_caption_text_completeness():
    """Test that all words from the original caption appear in the dynamic captions"""
    original_text = "This is a test caption with multiple words that should all appear in the output"
    # Split into words and verify all words are present
    words = original_text.split()
    # Use standard 720p dimensions for testing
    width, height = 1280, 720
    margin = 40
    max_window_height_ratio = 0.3
    # Calculate safe dimensions
    safe_width = width - (2 * margin)
    safe_height = int(height * max_window_height_ratio)
    windows = create_caption_windows(
        words=[Word(text=w, start_time=0, end_time=1) for w in words],
        min_font_size=32,
        max_font_size=48,
        safe_width=safe_width,
        safe_height=safe_height
    )
    # Collect all words from all windows
    processed_words = []
    for window in windows:
        processed_words.extend(word.text for word in window.words)
    assert set(words) == set(processed_words), "Not all words from original caption are present in processed output"


def test_font_size_scaling():
    """Test that font sizes are properly scaled based on video dimensions"""
    # Create test video with specific dimensions
    video_size = (1280, 720)  # 720p test video
    input_video_path = create_test_video(size=video_size)
    assert input_video_path is not None, "Failed to create test video"
    
    # Create output path
    output_path = os.path.join(get_tempdir(), "output_font_test.mp4")
    
    try:
        # Test with various caption lengths
        test_cases = [
            "Short caption",  # Should use larger font
            "This is a much longer caption that should use a smaller font size to fit properly",
            "🎉 Testing with emojis and special characters !@#$%"
        ]
        captions = [CaptionEntry(text, idx * 2.0, (idx + 1) * 2.0) for idx, text in enumerate(test_cases)]
        
        # Add dynamic captions
        result_path = create_dynamic_captions(
            input_video=input_video_path,
            captions=captions,
            output_path=output_path,
            min_font_size=24,  # Smaller min to test scaling
            max_font_size=48  # Larger max to test scaling
        )
        
        # Verify results
        assert result_path is not None, "Failed to create video with font size testing"
        assert os.path.exists(output_path), f"Output file not created: {output_path}"
        assert os.path.getsize(output_path) > 0, "Output file is empty"
        
        # Play the video (skipped in automated testing)
        play_test_video(output_path)
        
    finally:
        # Clean up
        if os.path.exists(input_video_path):
            os.unlink(input_video_path)
        if os.path.exists(output_path):
            os.unlink(output_path)


def test_caption_positioning():
    """Test that captions stay within the safe viewing area"""
    # Create test video with specific dimensions
    video_size = (1920, 1080)
    input_video_path = create_test_video(size=video_size)
    assert input_video_path is not None, "Failed to create test video"
    
    # Create output path
    output_path = os.path.join(get_tempdir(), "output_position_test.mp4")
    
    try:
        # Test with long captions that might overflow
        test_cases = [
            # Long single line to test horizontal overflow
            "This is a very long caption that should not extend beyond the right margin of the video frame",
            # Multiple short lines to test vertical spacing
            "Line one\nLine two\nLine three",
            # Long words that might cause overflow
            "Supercalifragilisticexpialidocious Pneumonoultramicroscopicsilicovolcanoconiosis",
            # Emojis and special characters
            "🌟 Testing with emojis 🎬 and special characters !@#$% to ensure proper spacing"
        ]
        captions = [
            CaptionEntry(text, idx * 2.0, (idx + 1) * 2.0)
            for idx, text in enumerate(test_cases)
        ]
        
        # Add dynamic captions with specific margin
        result_path = create_dynamic_captions(
            input_video=input_video_path,
            captions=captions,
            output_path=output_path,
            min_font_size=32,  # Ensure readable text
            max_font_size=48  # Scale up to 48px
        )
        
        # Verify results
        assert result_path is not None, "Failed to create video with position testing"
        assert os.path.exists(output_path), f"Output file not created: {output_path}"
        assert os.path.getsize(output_path) > 0, "Output file is empty"
        
        # Play the video (skipped in automated testing)
        play_test_video(output_path)
        
    finally:
        # Clean up
        if os.path.exists(input_video_path):
            os.unlink(input_video_path)
        if os.path.exists(output_path):
            os.unlink(output_path)


def test_create_srt_captions():
    """Test SRT caption file generation"""
    captions = [
        CaptionEntry("First caption", 0.0, 2.5),
        CaptionEntry("Second caption", 2.5, 5.0)
    ]
    output_path = os.path.join(get_tempdir(), "test_captions.srt")
    result_path = create_srt_captions(captions, output_path)
    assert result_path is not None, "Failed to create SRT file"
    assert os.path.exists(output_path), f"SRT file not created: {output_path}"
    with open(output_path, 'r') as f:
        content = f.read()
        assert "First caption" in content, "First caption not found in SRT"
        assert "Second caption" in content, "Second caption not found in SRT"
        assert "00:00:00,000" in content, "Start time not formatted correctly"
        assert "00:00:02,500" in content, "End time not formatted correctly"


def test_audio_aligned_captions():
    """Test creation of a video with audio-aligned captions"""
    # Create test video
    video_size = (1920, 1080)
    duration = 5
    input_video_path = create_test_video(size=video_size, duration=duration)
    assert input_video_path is not None, "Failed to create test video"

    # Test text for captions
    test_text = "This is a test video with synchronized audio and captions. The captions should match the spoken words exactly."

    # Generate audio using Google TTS
    tts = GoogleTTS()
    success, audio_path = tts.convert_text_to_speech(test_text)
    assert success and audio_path is not None, "Failed to generate test audio"

    try:
        # Verify the audio file exists and has content
        assert os.path.exists(audio_path), "Audio file not created"
        assert os.path.getsize(audio_path) > 0, "Audio file is empty"

        # Get word-level captions from audio
        captions = create_word_level_captions(audio_path, test_text)
        assert len(captions) > 0, "No captions generated"

        # Create output path for the final video
        output_path = os.path.join(get_tempdir(), "output_with_audio_captions.mp4")

        # Add dynamic captions
        result_path = create_dynamic_captions(
            input_video=input_video_path,
            captions=captions,
            output_path=output_path,
            min_font_size=32,
            max_font_size=48  # Scale up to 48px
        )
        assert result_path is not None, "Failed to create video with captions"

        # Add audio to the video with improved FFmpeg command
        final_output = os.path.join(get_tempdir(), "final_output_with_audio.mp4")
        ffmpeg_cmd = [
            "ffmpeg", "-y",
            "-i", output_path,     # Video with captions
            "-i", audio_path,      # Audio file
            "-map", "0:v:0",       # Map video from first input
            "-map", "1:a:0",       # Map audio from second input
            "-c:v", "copy",        # Copy video stream without re-encoding
            "-c:a", "aac",         # Encode audio as AAC
            "-b:a", "192k",        # Set audio bitrate
            "-shortest",           # Match duration to shortest stream
            final_output
        ]
        result = run_ffmpeg_command(ffmpeg_cmd)
        assert result is not None, "Failed to add audio to video"
        assert os.path.exists(final_output), "Final output file not created"
        assert os.path.getsize(final_output) > 0, "Final output file is empty"

        # Verify audio stream exists in output
        probe_cmd = [
            "ffprobe", "-v", "error",
            "-select_streams", "a:0",
            "-show_entries", "stream=codec_name",
            "-of", "default=noprint_wrappers=1:nokey=1",
            final_output
        ]
        probe_result = run_ffmpeg_command(probe_cmd)
        assert probe_result is not None and probe_result.stdout, "No audio stream found in output video"

        # Play the video (skipped in automated testing)
        play_test_video(final_output)

    finally:
        # Cleanup
        if os.path.exists(input_video_path):
            os.remove(input_video_path)
        if os.path.exists(audio_path):
            os.remove(audio_path)


def test_text_wrapping_direction():
    """Test that when text wraps to a new line, it goes downward rather than upward"""
    # Set up dimensions
    video_width = 1920
    margin = 40
    roi_width = video_width - (2 * margin)  # Full ROI width
    min_font_size = 32  # Use minimum font size to be conservative

    # Create a very long text that will definitely wrap
    test_text = "This is a test caption that should wrap to multiple lines. " * 3  # Repeat 3 times to ensure wrapping
    captions = [CaptionEntry(test_text, 0.0, 2.0)]

    # Process caption into words
    words = split_into_words(captions[0])

    # Create caption windows
    video_height = 1080  # Standard HD height
    margin = 40
    safe_width = 1920 - (2 * margin)  # Standard HD width minus margins
    safe_height = int(video_height * 0.3)  # 30% of video height

    windows = create_caption_windows(
        words=words,
        min_font_size=32,
        max_font_size=48,
        safe_width=safe_width,
        safe_height=safe_height
    )

    assert len(windows) > 0, "No caption windows created"
    window = windows[0]  # We only created one caption
    
    # Get positions for all words
    positions = calculate_word_positions(window, video_height, margin, roi_width)
    
    # Group positions by line number
    line_positions = {}
    for word, (_, y_pos) in zip(window.words, positions):
        if word.line_number not in line_positions:
            line_positions[word.line_number] = []
        line_positions[word.line_number].append(y_pos)
    
    # Verify that each line's y-position is below the previous line
    line_numbers = sorted(line_positions.keys())
    assert len(line_numbers) > 1, "Text did not wrap into multiple lines"
    for i in range(1, len(line_numbers)):
        prev_line = line_numbers[i-1]
        curr_line = line_numbers[i]
        assert min(line_positions[curr_line]) > max(line_positions[prev_line]), \
            f"Line {curr_line} is not below line {prev_line}"

if __name__ == "__main__":
    output_dir = os.path.join(get_tempdir(), "caption_test_outputs")
    os.makedirs(output_dir, exist_ok=True)
    Logger.print_info("Running caption tests and saving outputs...")
    test_default_static_captions()
    test_static_captions()
    test_caption_text_completeness()
    test_font_size_scaling()
    test_caption_positioning()
    test_create_srt_captions()
    test_audio_aligned_captions()
    test_text_wrapping_direction()
