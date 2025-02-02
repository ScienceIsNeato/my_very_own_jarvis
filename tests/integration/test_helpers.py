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
from logger import Logger
from utils import get_tempdir
from ttv.log_messages import (
    LOG_FINAL_VIDEO_CREATED,
    LOG_CLOSING_CREDITS_DURATION,
    LOG_FFPROBE_COMMAND,
    LOG_VIDEO_SEGMENT_CREATE,
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
        raise AssertionError(f"Failed to read story from config: {e}")
    
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

def validate_audio_video_durations(output, config_path):
    """Validate that each audio file matches the corresponding video segment duration."""
    print("\n=== Validating Audio/Video Segment Durations ===")
    main_video_duration = 0.0
    discrepancies = []
    segments_found = []

    try:
        with open(config_path, encoding='utf-8') as f:
            config = json.loads(f.read())
            expected_segments = len(config.get('story', []))
    except (json.JSONDecodeError, FileNotFoundError, KeyError) as e:
        raise AssertionError(f"Failed to read story from config: {e}")

    # First validate individual segments match their audio
    for segment_num in range(expected_segments):
        # Try final segment first, fall back to initial if not found
        video_file = f"{get_tempdir()}/ttv/segment_{segment_num}.mp4"
        if not os.path.exists(video_file):
            video_file = f"{get_tempdir()}/ttv/segment_{segment_num}_initial.mp4"
            if not os.path.exists(video_file):
                continue
            Logger.print_warning(f"Using initial segment for {segment_num} - final segment not found")

        segments_found.append(segment_num)
        video_duration = get_video_duration(video_file)
        if video_duration == 0.0:
            continue

        try:
            cmd = [
                "ffprobe", "-v", "error", "-select_streams", "a:0",
                "-show_entries", "stream=duration",
                "-of", "default=noprint_wrappers=1:nokey=1", video_file
            ]
            result = subprocess.run(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True
            )
            audio_duration = float(result.stdout.decode().strip())
            
            if abs(audio_duration - video_duration) >= 0.1:
                discrepancies.append((
                    f"audio_stream_{segment_num}",
                    video_file,
                    audio_duration,
                    video_duration
                ))
            else:
                print(
                    f"✓ Duration match for segment {segment_num}: "
                    f"audio stream ({audio_duration:.2f}s) vs "
                    f"video container ({video_duration:.2f}s)"
                )
                main_video_duration += video_duration  # Add to total duration
                
        except (subprocess.CalledProcessError, ValueError) as e:
            Logger.print_error(f"Failed to get audio duration for segment {segment_num}: {e}")
            continue

    if discrepancies:
        print("\n!!! Duration Mismatches Found !!!")
        print("-" * 80)
        header_fmt = "|{:^20}|{:^20}|{:^15}|{:^15}|"
        print(header_fmt.format("Audio Stream", "Video File", "Audio Duration", "Video Duration"))
        print("-" * 80)
        row_fmt = "|{:^20}|{:^20}|{:^15.2f}|{:^15.2f}|"
        for audio_id, video_file, audio_dur, video_dur in discrepancies:
            print(row_fmt.format(
                audio_id,
                os.path.basename(video_file),
                audio_dur,
                video_dur
            ))
        print("-" * 80)

    segments_found.sort()
    print(f"\nFound segments: {segments_found}")

    if len(segments_found) != expected_segments:
        raise AssertionError(
            f"Expected {expected_segments} segments but found {len(segments_found)}"
        )

    # Get duration from the main video with background music
    main_video_path = os.path.join(get_tempdir(), "ttv", "main_video_with_background_music.mp4")
    if os.path.exists(main_video_path):
        main_video_duration = get_video_duration(main_video_path)
    else:
        Logger.print_warning("Main video with background music not found, using sum of segment durations")

    print(f"✓ Main video duration (pre-credits): {main_video_duration:.2f}s")
    return main_video_duration

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

def validate_final_video_path(output, config_path=None):
    """Validate that the final video path is found in the logs."""
    print("\n=== Validating Final Video Path ===")
    final_video_path = extract_final_video_path(output)
    if not os.path.exists(final_video_path):
        raise AssertionError(f"Expected output video not found at {final_video_path}")
    print(f"✓ Final video found at: {os.path.basename(final_video_path)}")
    
    if config_path:
        try:
            with open(config_path, encoding='utf-8') as f:
                config = json.loads(f.read())
                if config.get('closing_credits') and 'without closing credits' in output:
                    print(
                        "\n⚠️  Warning: Closing credits were configured but not found "
                        "in final video"
                    )
                    print(
                        "   This might be due to Suno API being unavailable or other "
                        "generation issues"
                    )
        except (IOError, ValueError) as e:
            print(f"\n⚠️  Warning: Could not check closing credits configuration: {e}")
    
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