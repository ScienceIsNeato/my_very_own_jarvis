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

# Third-party imports
import pytest

# Local application imports
from utils import get_tempdir
from ttv.log_messages import LOG_TTV_DIR_CREATED
from tests.integration.test_helpers import (
    validate_segment_count,
    validate_audio_video_durations,
    validate_final_video_path,
    validate_total_duration,
    validate_closing_credits_duration,
    validate_background_music,
    validate_gcs_upload,
)

logger = logging.getLogger(__name__)

# Path to the test config files
GENERATED_PIPELINE_CONFIG = "tests/integration/test_data/generated_pipeline_config.json"

@pytest.mark.costly
def test_generated_pipeline_execution():
    """Test execution of TTV pipeline with generated content (music, images).
    
    This test verifies:
    1. DALL-E generated images
    2. Audio generation and synchronization
    3. Background music integration
    4. Closing credits generation and assembly
    5. Final video compilation and validation
    6. GCS upload validation
    """
    # Skip if GCS credentials are not configured
    bucket_name = os.getenv('GCP_BUCKET_NAME')
    project_name = os.getenv('GCP_PROJECT_NAME')
    if not (bucket_name and project_name):
        pytest.skip("GCS credentials not configured")

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
    with open(get_tempdir() + "/test_output.log", "w", encoding="utf-8") as f:
        f.write(output)

    # Get the output directory from the output by getting everything after the : following `Created TTV directory` from the output
    output_dir = output.split(LOG_TTV_DIR_CREATED)[1].split("\n")[0]
    print(f"Detected output directory: {output_dir}")

    # Validate all segments are present
    validate_segment_count(output, GENERATED_PIPELINE_CONFIG)

    # Validate segment durations
    total_video_duration = validate_audio_video_durations(GENERATED_PIPELINE_CONFIG, output_dir)

    # Validate background music was added successfully
    validate_background_music(output)

    # Add closing credits duration to total video duration
    closing_credits_duration = validate_closing_credits_duration(output, GENERATED_PIPELINE_CONFIG)
    total_video_duration += closing_credits_duration

    # Validate final video
    final_video_path = validate_final_video_path(output_dir)
    validate_total_duration(final_video_path, total_video_duration)

    # Validate GCS upload
    validate_gcs_upload(bucket_name, project_name)

    # Clean up
    # os.remove(final_video_path)  # Commented out to preserve files for debugging
    # uploaded_file.delete()  # Commented out to preserve GCS files for debugging
    print("\n=== Test Complete ===\n")
