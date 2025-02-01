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

import os
import time
import pytest
import logging
import subprocess
import json
import sys
import re
from logger import Logger
from tests.integration.test_helpers import (
    validate_audio_video_durations,
    validate_final_video_path,
    validate_total_duration,
    get_audio_duration,
    get_video_duration,
    LOG_FFPROBE_COMMAND,
    LOG_VIDEO_SEGMENT_CREATE,
    LOG_FINAL_VIDEO_CREATED,
    validate_closing_credits_duration,
    wait_for_completion,
    validate_segment_count
)
from utils import get_tempdir
from ttv.log_messages import (
    LOG_BACKGROUND_MUSIC_SUCCESS,
    LOG_BACKGROUND_MUSIC_FAILURE
)

logger = logging.getLogger(__name__)

def parse_test_logs(log_file):
    """Parse test run logs and extract results."""
    results = []
    with open(log_file, 'r', encoding='utf-8') as f:
        # Basic log parsing logic
        for line in f:
            if 'TEST RESULT:' in line:
                results.append(line.strip())
    return results

# Path to the hardcoded config file
HARD_CODED_CONFIG_PATH = "tests/integration/test_data/minimal_ttv_config.json"
# Path to the test config file
SIMULATED_PIPELINE_CONFIG = "tests/integration/test_data/simulated_pipeline_config.json"

def validate_background_music(output: str) -> None:
    """Validate background music was added successfully.
    
    Args:
        output: The captured output from the pipeline execution
    """
    # Check for successful background music addition
    assert LOG_BACKGROUND_MUSIC_SUCCESS in output, "Background music should be added successfully"
    assert LOG_BACKGROUND_MUSIC_FAILURE not in output, "Background music should not fail to be added"

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
    command = f"PYTHONUNBUFFERED=1 python ganglia.py --text-to-video --ttv-config {SIMULATED_PIPELINE_CONFIG}"
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

    # Validate all segments are present
    validate_segment_count(output, SIMULATED_PIPELINE_CONFIG)

    # Validate segment durations
    total_video_duration = validate_audio_video_durations(output, SIMULATED_PIPELINE_CONFIG)

    # Validate background music was added successfully
    validate_background_music(output)

    # Add closing credits duration to total video duration
    closing_credits_duration = validate_closing_credits_duration(output, SIMULATED_PIPELINE_CONFIG)
    total_video_duration += closing_credits_duration

    # Validate final video
    final_video_path = validate_final_video_path(output, SIMULATED_PIPELINE_CONFIG)
    validate_total_duration(final_video_path, total_video_duration)

    # Clean up
    # os.remove(final_video_path)  # Commented out to preserve files for debugging
    print("\n=== Test Complete ===\n") 