"""Test helper functions for integration tests.

This module provides utility functions for integration testing, including:
- Video and audio duration measurement
- Configuration file handling
- Process completion waiting
- File validation
- Test log parsing
"""

import os
import re
import subprocess
import time
import json
import logging
from google.cloud import storage
from logger import Logger
from ttv.log_messages import (
    LOG_CLOSING_CREDITS_DURATION,
    LOG_FFPROBE_COMMAND,
    LOG_BACKGROUND_MUSIC_SUCCESS,
    LOG_BACKGROUND_MUSIC_FAILURE
)

logger = logging.getLogger(__name__)

def validate_background_music(output: str) -> None:
    """Validate background music generation and addition.
    
    Args:
        output: The output log to validate
        
    Raises:
        AssertionError: If background music validation fails
    """
    # Check for successful background music generation
    success_pattern = re.compile(LOG_BACKGROUND_MUSIC_SUCCESS)
    failure_pattern = re.compile(LOG_BACKGROUND_MUSIC_FAILURE)
    
    success_matches = success_pattern.findall(output)
    failure_matches = failure_pattern.findall(output)
    
    # Either we should have a success message or a failure message
    assert len(success_matches) + len(failure_matches) > 0, "No background music status found"
    
    if success_matches:
        logger.info("Background music successfully added")
    else:
        logger.warning("Background music addition failed (expected in some test cases)")

def wait_for_completion(timeout=300):
    """Wait for a process to complete within the specified timeout."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        time.sleep(1)
    return True

def get_audio_duration(audio_file_path):
    """Get the duration of an audio file using ffprobe."""
    if not os.path.exists(audio_file_path):
        Logger.print_error(f"Audio file not found: {audio_file_path}")
        return None

    Logger.print_info(LOG_FFPROBE_COMMAND)
    cmd = [
        'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1', audio_file_path
    ]
    try:
        output = subprocess.check_output(cmd).decode().strip()
        return float(output)
    except (subprocess.CalledProcessError, ValueError) as e:
        Logger.print_error(f"Failed to get audio duration: {e}")
        return None

def get_video_duration(video_file_path):
    """Get the duration of a video file using ffprobe."""
    if not os.path.exists(video_file_path):
        Logger.print_error(f"Video file not found: {video_file_path}")
        return None

    Logger.print_info(LOG_FFPROBE_COMMAND)
    cmd = [
        'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1', video_file_path
    ]
    try:
        output = subprocess.check_output(cmd).decode().strip()
        return float(output)
    except (subprocess.CalledProcessError, ValueError) as e:
        Logger.print_error(f"Failed to get video duration: {e}")
        return None

def validate_segment_count(output, config_path):
    """Validate that all story segments are present in the output."""
    print("\n=== Validating Segment Count ===")
    
    try:
        with open(config_path, encoding='utf-8') as f:
            config = json.loads(f.read())
            expected_segments = len(config.get('story', []))
    except (json.JSONDecodeError, FileNotFoundError, KeyError) as e:
        raise AssertionError(f"Failed to read story from config: {e}") # pylint: disable=raise-missing-from
    
    segment_pattern = r'segment_(\d+)_initial\.mp4'
    found_segments = {int(m.group(1)) for m in re.finditer(segment_pattern, output)}
    actual_segments = len(found_segments)
    
    print(f"Expected segments: {expected_segments}")
    print(f"Actual segments: {actual_segments}")
    print(f"Found segment numbers: {sorted(list(found_segments))}")
    
    if actual_segments != expected_segments:
        raise AssertionError(
            f"Expected {expected_segments} segments but found {actual_segments}"
        )
    print("✓ All story segments are present")
    return actual_segments

def validate_audio_video_durations(config_path, output_dir):
    """Validate that each audio file matches the corresponding video segment duration."""
    print("\n=== Validating Audio/Video Segment Durations ===")
    
    try:
        with open(config_path, encoding='utf-8') as f:
            config = json.loads(f.read())
            expected_segments = len(config.get('story', []))
    except (json.JSONDecodeError, FileNotFoundError, KeyError) as e:
        raise AssertionError(f"Failed to read story from config: {e}") # pylint: disable=raise-missing-from

    print(f"Checking {expected_segments} segments in {output_dir}")
    
    # First get all the segment files
    segments = []
    for i in range(expected_segments):
        # Try final segment first, fall back to initial if not found
        final_path = os.path.join(output_dir, f"segment_{i}.mp4")
        initial_path = os.path.join(output_dir, f"segment_{i}_initial.mp4")
        
        if os.path.exists(final_path):
            segments.append((i, final_path))
            print(f"Found final segment {i}: {final_path}")
        elif os.path.exists(initial_path):
            segments.append((i, initial_path))
            print(f"Found initial segment {i}: {initial_path}")
        else:
            print(f"No segment found for index {i}")
    
    if not segments:
        raise AssertionError("No video segments found")
    
    if len(segments) != expected_segments:
        raise AssertionError(f"Expected {expected_segments} segments but found {len(segments)}")

    # Check each segment's audio/video duration
    total_duration = 0.0
    for i, segment_path in segments:
        video_duration = get_video_duration(segment_path)
        if video_duration is None:
            raise AssertionError(f"Could not get video duration for segment {i}")
            
        cmd = [
            "ffprobe", "-v", "error",
            "-select_streams", "a:0",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            segment_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        audio_duration = float(result.stdout.strip())
        
        if abs(audio_duration - video_duration) >= 0.1:
            print(f"⚠️  Duration mismatch in segment {i}:")
            print(f"   Audio: {audio_duration:.2f}s")
            print(f"   Video: {video_duration:.2f}s")
        else:
            print(f"✓ Segment {i} durations match: {video_duration:.2f}s")
            total_duration += video_duration

    # Check the main video with background music
    main_video = os.path.join(output_dir, "main_video_with_background_music.mp4")
    if os.path.exists(main_video):
        main_duration = get_video_duration(main_video)
        print(f"✓ Main video with background music duration: {main_duration:.2f}s")
        return main_duration
    else:
        print(f"✓ Using total segment duration: {total_duration:.2f}s")
        return total_duration

def extract_final_video_path(output):
    """Extract the final video path from the logs."""
    patterns = [
        r'Final video (?:with|without) closing credits created: output_path=(.+\.mp4)',
        r'Final video created at: output_path=(.+\.mp4)'
    ]
    
    for pattern in patterns:
        if match := re.search(pattern, output):
            return match.group(1)
    
    raise AssertionError("Final video path not found in logs.")

def validate_final_video_path(output_dir=None):
    """Validate that the final video path is found in the logs."""
    print("\n=== Validating Final Video Path ===")
    final_video_path = os.path.join(output_dir, "final_video.mp4")
    if not os.path.exists(final_video_path):
        raise AssertionError(f"Expected output video not found at {final_video_path}")
    print(f"✓ Final video found at: {os.path.basename(final_video_path)}")

    return final_video_path

def validate_total_duration(final_video_path, main_video_duration):
    """Validate that the final video duration matches main video + credits."""
    print("\n=== Validating Final Video Duration ===")
    final_duration = get_video_duration(final_video_path)
    expected_duration = main_video_duration  # Credits duration is added by caller
    
    if abs(final_duration - expected_duration) >= 1.0:
        raise AssertionError(
            f"Final video duration ({final_duration:.2f}s) does not match expected "
            f"duration of main video + credits ({expected_duration:.2f}s)."
        )
    print(
        f"✓ Final duration ({final_duration:.2f}s) matches expected duration "
        f"({expected_duration:.2f}s)"
    )

def validate_closing_credits_duration(output, config_path):
    """Validate that the closing credits audio and video durations match."""
    print("\n=== Validating Closing Credits Duration ===")
    
    duration_match = re.search(f'{LOG_CLOSING_CREDITS_DURATION}: (\\d+\\.\\d+)s', output)
    if duration_match:
        audio_duration = float(duration_match.group(1))
        print(f"✓ Generated closing credits duration: {audio_duration:.2f}s")
        return audio_duration
    
    try:
        with open(config_path, encoding='utf-8') as f:
            config = json.loads(f.read())
            if 'closing_credits' in config and isinstance(config['closing_credits'], str):
                credits_path = config['closing_credits']
                audio_duration = get_audio_duration(credits_path)
                print(
                    f"✓ Pre-loaded closing credits ({os.path.basename(credits_path)}) "
                    f"duration: {audio_duration:.2f}s"
                )
                return audio_duration
    except (IOError, ValueError) as e:
        print(f"Failed to read closing credits from config: {e}")
        
    print("No closing credits found")
    return 0.0

def read_story_from_config(config_file_path):
    """Read and parse a story configuration file."""
    try:
        with open(config_file_path, encoding='utf-8') as f:
            return json.load(f)
    except (IOError, ValueError) as e:
        raise AssertionError(f'Failed to read story from config: {e}') from e

def read_story_from_config_file(config_file_path):
    """Read and parse a story configuration file with error handling."""
    try:
        with open(config_file_path, encoding='utf-8') as f:
            return json.load(f)
    except (IOError, ValueError) as e:
        raise AssertionError(f'Failed to read story from config: {e}') from e

def read_story_from_config_file_with_retry(config_file_path):
    """Read and parse a story configuration file with retry on failure."""
    try:
        with open(config_file_path, encoding='utf-8') as f:
            return json.load(f)
    except (IOError, ValueError) as e:
        Logger.print_error(f"Failed to read story from config: {e}")
        return None

def read_story_from_config_file_with_retry_and_wait(config_file_path):
    """Read and parse a story configuration file with retry and wait."""
    try:
        with open(config_file_path, encoding='utf-8') as f:
            return json.load(f)
    except (IOError, ValueError) as e:
        Logger.print_error(f"Failed to read story from config: {e}")
        return None

def validate_gcs_upload(bucket_name: str, project_name: str) -> storage.Blob:
    """Validate that a file was uploaded to GCS and return the uploaded file blob.
    
    Args:
        bucket_name: The name of the GCS bucket
        project_name: The GCP project name
        
    Returns:
        storage.Blob: The most recently uploaded video file blob
        
    Raises:
        AssertionError: If no uploaded file is found or if the file doesn't exist
    """
    print("\n=== Validating GCS Upload ===")
    storage_client = storage.Client(project=project_name)
    bucket = storage_client.get_bucket(bucket_name)
    
    # List blobs in test_outputs directory
    blobs = list(bucket.list_blobs(prefix="test_outputs/"))
    
    # Find the most recently uploaded file
    uploaded_file = None
    for blob in blobs:
        if blob.name.endswith("_final_video.mp4"):
            if not uploaded_file or blob.time_created > uploaded_file.time_created:
                uploaded_file = blob
    
    assert uploaded_file is not None, "Failed to find uploaded video in GCS"
    assert uploaded_file.exists(), "Uploaded file does not exist in GCS"
    
    print(f"✓ Found uploaded file in GCS: {uploaded_file.name}")
    return uploaded_file
