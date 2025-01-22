import os
import time
import pytest
import logging
import subprocess
import json
import sys
import re

logger = logging.getLogger(__name__)

def wait_for_completion(timeout=300):
    """Wait for test run to complete with timeout."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        # Check for completion
        if os.path.exists("test_complete.flag"):
            return True
        time.sleep(5)
    return False

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

def validate_audio_video_durations(output):
    """Validate that each audio file matches the corresponding video segment duration."""
    print("\n=== Validating Audio/Video Segment Durations ===")
    total_video_duration = 0.0
    discrepancies = []
    for line in output.splitlines():
        if line.startswith("Creating video segment: output_path"):
            audio_match = re.search(r'audio_path=(.+\.mp3)', line)
            video_match = re.search(r'output_path=(.+\.mp4)', line)
            if audio_match and video_match:
                audio_file = audio_match.group(1)
                video_file = video_match.group(1)

                # Get durations
                audio_duration = get_audio_duration(audio_file)
                video_duration = get_video_duration(video_file)

                # Validate durations
                if abs(audio_duration - video_duration) >= 0.1:
                    discrepancies.append((audio_file, video_file, audio_duration, video_duration))
                else:
                    print(f"✓ Duration match: {os.path.basename(audio_file)} ({audio_duration:.2f}s) vs {os.path.basename(video_file)} ({video_duration:.2f}s)")

                # Accumulate total video duration
                total_video_duration += video_duration

    # Print discrepancies if any
    if discrepancies:
        print("\n!!! Duration Mismatches Found !!!")
        print("-" * 80)
        print("|{:^20}|{:^20}|{:^15}|{:^15}|".format(
            "Audio File", "Video File", "Audio Duration", "Video Duration"))
        print("-" * 80)
        for audio_file, video_file, audio_duration, video_duration in discrepancies:
            print("|{:^20}|{:^20}|{:^15.2f}|{:^15.2f}|".format(
                os.path.basename(audio_file),
                os.path.basename(video_file),
                audio_duration,
                video_duration
            ))
        print("-" * 80)

    # Fail test if discrepancies exist
    assert not discrepancies, "Audio and video durations do not match for some segments."

    print(f"\n✓ Total segment duration: {total_video_duration:.2f}s")
    print("✓ All segment durations validated successfully")
    return total_video_duration


def extract_final_video_path(output):
    """Extract the final video path from the logs."""
    match = re.search(r'Final video with closing credits created: output_path=(.+\.mp4)', output)
    if match:
        return match.group(1)
    else:
        raise AssertionError("Final video path not found in logs.")


def validate_final_video_path(output):
    """Validate that the final video path is found in the logs."""
    print("\n=== Validating Final Video Path ===")
    final_video_path = extract_final_video_path(output)
    assert os.path.exists(final_video_path), f"Expected output video not found at {final_video_path}"
    print(f"✓ Final video found at: {os.path.basename(final_video_path)}")
    return final_video_path


def validate_total_duration(output, total_video_duration):
    """Validate that the total video duration matches the expected duration."""
    print("\n=== Validating Total Video Duration ===")
    final_video_path = extract_final_video_path(output)
    
    # Get actual duration of final video
    final_duration = get_video_duration(final_video_path)
    
    assert abs(final_duration - total_video_duration) < 1.0, f"Final video duration ({final_duration}s) does not match expected duration ({total_video_duration}s)."
    print(f"✓ Final duration ({final_duration:.2f}s) matches expected duration ({total_video_duration:.2f}s)")


def test_minimal_ttv_execution_direct():
    """Test direct execution of TTV command and verify output."""
    print("\n=== Starting TTV Integration Test ===")
    
    # Run the TTV command and capture output
    command = f"PYTHONUNBUFFERED=1 python ganglia.py --text-to-video --ttv-config {HARD_CODED_CONFIG_PATH}"
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
    with open("/tmp/GANGLIA/test_output.log", "w") as f:
        f.write(output)

    # Calculate closing credits duration
    closing_credits_path = 'tests/integration/test_data/sample_closing_credits.mp3'
    closing_credits_duration = get_audio_duration(closing_credits_path)
    print(f"\n✓ Closing credits duration: {closing_credits_duration:.2f}s")

    # Add closing credits duration to total video duration
    total_video_duration = validate_audio_video_durations(output) + closing_credits_duration

    # Perform validations
    final_video_path = validate_final_video_path(output)
    validate_total_duration(output, total_video_duration)

    # Clean up
    os.remove(final_video_path)
    print("\n=== Test Complete ===\n")


def get_audio_duration(audio_file):
    """Get the duration of an audio file using ffprobe."""
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries",
             "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", audio_file],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True)
        return float(result.stdout)
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to get audio duration for {audio_file}: {e.stderr}")
        return 0.0

def get_video_duration(video_file):
    """Get the duration of a video file using ffprobe."""
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries",
             "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", video_file],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True)
        return float(result.stdout)
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to get video duration for {video_file}: {e.stderr}")
        return 0.0


if __name__ == "__main__":
    # Directly run the test function
    try:
        test_minimal_ttv_execution_direct()
    except AssertionError as e:
        print(f"Test failed: {e}")
    else:
        print("Test passed successfully.")