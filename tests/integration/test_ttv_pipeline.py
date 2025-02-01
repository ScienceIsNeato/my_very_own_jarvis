"""Integration tests for the TTV pipeline.

This module contains tests that verify the end-to-end functionality of the
text-to-video pipeline, including video generation, audio synchronization,
and output validation.
"""

# Standard library imports
import logging
import subprocess
import sys

# Third-party imports
import pytest

# Local imports
from ttv.ttv import pipeline
from tests.integration.test_helpers import (
    validate_segment_count,
    validate_audio_video_durations,
    validate_final_video_path,
    validate_total_duration,
    validate_closing_credits_duration
)
from utils import get_tempdir

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

@pytest.mark.costly
def test_generated_pipeline_execution():
    """Test execution of TTV pipeline with generated content (music, images).
    
    This test verifies the pipeline works with:
    1. DALL-E generated images
    2. Suno-generated background music and closing credits
    3. Dynamic captions in an urban contemporary style
    """
    print("\n=== Starting Generated Pipeline Integration Test ===")
    
    # Run the TTV command and capture output
    config_path = "tests/integration/test_data/generated_pipeline_config.json"
    command = f"PYTHONUNBUFFERED=1 python ganglia.py --text-to-video --ttv-config {config_path}"
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
    with open(get_tempdir() + "/test_output_generated.log", "w") as f:
        f.write(output)

    # Validate all segments are present
    validate_segment_count(output, config_path)

    # Validate segment durations and get total duration
    total_video_duration = validate_audio_video_durations(output, config_path)

    # Add closing credits duration to total video duration
    closing_credits_duration = validate_closing_credits_duration(output, config_path)
    total_video_duration += closing_credits_duration

    # Validate final video
    final_video_path = validate_final_video_path(output, config_path)
    validate_total_duration(final_video_path, total_video_duration)

    # Clean up
    # os.remove(final_video_path)  # Commented out to preserve files for debugging
    print("\n=== Test Complete ===\n")

def test_ttv_pipeline_with_config(tmp_path):
    """Test the TTV pipeline with a configuration file."""
    config_path = tmp_path / "test_config.json"
    with open(config_path, "w", encoding='utf-8') as f:
        f.write('{"story": ["test story"]}')

    ttv_pipeline = pipeline(config_path)
    output = ttv_pipeline.run()

    validate_segment_count(output, config_path)
    total_duration = validate_audio_video_durations(output, config_path)
    final_video_path = validate_final_video_path(output, config_path)
    validate_total_duration(final_video_path, total_duration)
    validate_closing_credits_duration(output, config_path)
