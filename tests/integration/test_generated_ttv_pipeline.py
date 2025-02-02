"""Integration tests for the TTV pipeline.

This module contains tests that verify the end-to-end functionality of the
text-to-video pipeline, including video generation, audio synchronization,
and output validation.
"""

# Standard library imports
import logging
import subprocess
import sys
import os
import pathlib

# Third-party imports
import pytest

# Local imports
from ttv.ttv import text_to_video
from tests.integration.test_helpers import (
    validate_segment_count,
    validate_audio_video_durations,
    validate_final_video_path,
    validate_total_duration,
    validate_closing_credits_duration,
    validate_background_music,
    parse_test_logs
)
from utils import get_tempdir, get_timestamped_ttv_dir

logger = logging.getLogger(__name__)

# Path to the test config files
GENERATED_PIPELINE_CONFIG = "tests/integration/test_data/generated_pipeline_config.json"

def test_generated_ttv_pipeline_with_config(tmp_path):
    """Test the TTV pipeline with a configuration file."""
    # Create test audio files
    test_audio_dir = tmp_path / "test_audio"
    test_audio_dir.mkdir(parents=True)
    
    # Create a simple audio file for testing
    background_music_path = test_audio_dir / "background_music.mp3"
    closing_credits_path = test_audio_dir / "closing_credits.mp3"
    
    # Create dummy audio files using ffmpeg
    for audio_path in [background_music_path, closing_credits_path]:
        subprocess.run([
            "ffmpeg", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
            "-t", "5", "-q:a", "9", "-acodec", "libmp3lame", str(audio_path)
        ], check=True, capture_output=True)

    # Create a test config file
    config_path = tmp_path / "test_config.json"
    with open(config_path, "w") as f:
        f.write(f"""
        {{
            "style": "test style",
            "story": ["Test story line 1", "Test story line 2"],
            "title": "Test Title",
            "caption_style": "static",
            "background_music": {{
                "file": "{str(background_music_path)}",
                "prompt": null
            }},
            "closing_credits": {{
                "file": "{str(closing_credits_path)}",
                "prompt": null
            }}
        }}
        """)

    # Run the pipeline
    result = text_to_video(str(config_path))

    # Verify the result
    assert result is not None, "Pipeline execution failed"

@pytest.mark.costly
def test_generated_pipeline_execution():
    """Test execution of TTV pipeline with generated content (music, images).
    
    This test verifies:
    1. DALL-E generated images
    2. Audio generation and synchronization
    3. Background music integration
    4. Closing credits generation and assembly
    5. Final video compilation and validation
    """
    print("\n=== Starting Generated Pipeline Integration Test ===")

    # Run the TTV command and capture output
    command = f"PYTHONUNBUFFERED=1 python ganglia.py --text-to-video --ttv-config {GENERATED_PIPELINE_CONFIG}"
    output = ""  # Initialize output here
    process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    for line in iter(process.stdout.readline, b''):
        decoded_line = line.decode('utf-8')
        print(decoded_line, end='')  # Print to console
        sys.stdout.flush()  # Ensure immediate output
        output += decoded_line
    process.stdout.close()
    process.wait()



    # Save output to a file for debugging
    with open(get_tempdir() + "/test_output.log", "w") as f:
        f.write(output)

    # Get the output directory from the output by getting everything after the : following `Created TTV directory` from the output
    output_dir = output.split("Created TTV directory: ")[1].split("\n")[0]
    print(f"Detected output directory: {output_dir}")

    # Validate all segments are present
    validate_segment_count(output, GENERATED_PIPELINE_CONFIG)

    # Validate segment durations
    total_video_duration = validate_audio_video_durations(output, GENERATED_PIPELINE_CONFIG, output_dir)

    # Validate background music was added successfully
    validate_background_music(output)

    # Add closing credits duration to total video duration
    closing_credits_duration = validate_closing_credits_duration(output, GENERATED_PIPELINE_CONFIG, output_dir)
    total_video_duration += closing_credits_duration

    # Validate final video
    final_video_path = validate_final_video_path(GENERATED_PIPELINE_CONFIG, output_dir)
    validate_total_duration(final_video_path, total_video_duration)

    # Clean up
    # os.remove(final_video_path)  # Commented out to preserve files for debugging
    print("\n=== Test Complete ===\n")
