"""Smoke tests for the Text-to-Video (TTV) pipeline.

This module contains smoke tests that verify the end-to-end functionality for ttv
of the TTV pipeline, including:
- Audio/video generation and synchronization
- Background music integration
- Closing credits generation
- Final video assembly and validation

Each test case validates:
1. Audio/video duration matches for each segment
2. Final video path and existence
3. Total video duration including credits
4. Proper cleanup of temporary files
"""

import logging
import subprocess
import sys
from tests.integration.test_helpers import (
    validate_audio_video_durations,
    validate_final_video_path,
    validate_total_duration,
    validate_closing_credits_duration,
    validate_segment_count,
    validate_background_music
)
from utils import get_tempdir
from ttv.log_messages import LOG_TTV_DIR_CREATED

logger = logging.getLogger(__name__)

# Path to the test config files
SIMULATED_PIPELINE_CONFIG = "tests/integration/test_data/simulated_pipeline_config.json"


def test_simulated_pipeline_execution():
    """Test the full TTV pipeline with simulated responses for music and image generation.
    
    This test verifies:
    1. Image generation/loading from preloaded directory
    2. Audio generation and synchronization
    3. Background music integration
    4. Closing credits generation and assembly
    5. Final video compilation and validation
    """
    print("\n=== Starting TTV Pipeline Integration Test ===")

    # Run the TTV command and capture output
    command = (
        f"PYTHONUNBUFFERED=1 python ganglia.py --text-to-video "
        f"--ttv-config {SIMULATED_PIPELINE_CONFIG}"
    )
    output = ""  # Initialize output here
    process = subprocess.Popen(
        command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
    )
    for line in iter(process.stdout.readline, b''):
        decoded_line = line.decode('utf-8')
        print(decoded_line, end='')  # Print to console
        sys.stdout.flush()  # Ensure immediate output
        output += decoded_line
    process.stdout.close()
    process.wait()

    # Save output to a file for debugging
    with open(get_tempdir() + "/test_output.log", "w", encoding='utf-8') as f:
        f.write(output)

    # Get the output directory from the output
    output_dir = output.split(LOG_TTV_DIR_CREATED)[1].split("\n")[0]
    print(f"Detected output directory: {output_dir}")

    # Validate all segments are present
    validate_segment_count(output, SIMULATED_PIPELINE_CONFIG)

    # Validate segment durations
    total_video_duration = validate_audio_video_durations(
        output, SIMULATED_PIPELINE_CONFIG, output_dir
    )

    # Validate background music was added successfully
    validate_background_music(output)

    # Add closing credits duration to total video duration
    closing_credits_duration = validate_closing_credits_duration(
        output, SIMULATED_PIPELINE_CONFIG, output_dir
    )
    total_video_duration += closing_credits_duration

    # Validate final video
    final_video_path = validate_final_video_path(
        SIMULATED_PIPELINE_CONFIG, output_dir
    )
    validate_total_duration(final_video_path, total_video_duration)

    # Clean up
    # os.remove(final_video_path)  # Commented out to preserve files for debugging
    print("\n=== Test Complete ===\n")
