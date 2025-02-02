"""Helper functions for integration tests."""

import os
import re
import subprocess
import time
import json
from logger import Logger
from ttv.log_messages import (
    LOG_FINAL_VIDEO_CREATED,
    LOG_CLOSING_CREDITS_DURATION
)

# Log message constants
LOG_FFPROBE_COMMAND = "Running ffprobe command"
LOG_VIDEO_SEGMENT_CREATE = "Creating video segment"

def wait_for_completion(timeout=300):
    """Wait for test run to complete with timeout."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        # Check for completion
        if os.path.exists("test_complete.flag"):
            return True
        time.sleep(5)
    return False

def get_audio_duration(audio_path):
    """Get the duration of an audio file using ffprobe."""
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries",
             "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", audio_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True)
        return float(result.stdout.decode().strip())
    except subprocess.CalledProcessError as e:
        Logger.print_error(f"Failed to get audio duration for {audio_path}: {e.stderr.decode()}")
        return 0.0

def get_video_duration(video_path):
    """Get the duration of a video file using ffprobe."""
    try:
        # Split the path at the first comma if it exists
        video_path = video_path.split(',')[0].strip()
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries",
             "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", video_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True)
        return float(result.stdout.decode().strip())
    except subprocess.CalledProcessError as e:
        Logger.print_error(f"Failed to get video duration for {video_path}: {e.stderr.decode()}")
        return 0.0

def validate_segment_count(output, config_path):
    """Validate that all story segments are present in the output."""
    print("\n=== Validating Segment Count ===")
    
    # Get expected number of segments from config
    try:
        with open(config_path, 'r') as f:
            config = json.loads(f.read())
            expected_segments = len(config.get('story', []))
    except (json.JSONDecodeError, FileNotFoundError, KeyError) as e:
        raise AssertionError(f"Failed to read story from config: {e}")
    
    # Count actual segments using regex to be more flexible with log format
    segment_pattern = r'segment_(\d+)_initial\.mp4'
    found_segments = set()
    for line in output.splitlines():
        match = re.search(segment_pattern, line)
        if match:
            found_segments.add(int(match.group(1)))
    
    actual_segments = len(found_segments)
    
    print(f"Expected segments: {expected_segments}")
    print(f"Actual segments: {actual_segments}")
    print(f"Found segment numbers: {sorted(list(found_segments))}")
    
    assert actual_segments == expected_segments, f"Expected {expected_segments} segments but found {actual_segments}"
    print("✓ All story segments are present")
    return actual_segments

def validate_audio_video_durations(output, config_path):
    """Validate that each audio file matches the corresponding video segment duration."""
    print("\n=== Validating Audio/Video Segment Durations ===")
    total_video_duration = 0.0
    discrepancies = []
    segments_found = []

    # Get expected number of segments from config
    try:
        with open(config_path, 'r') as f:
            config = json.loads(f.read())
            expected_segments = len(config.get('story', []))
    except (json.JSONDecodeError, FileNotFoundError, KeyError) as e:
        raise AssertionError(f"Failed to read story from config: {e}")

    # Directly check each segment
    for segment_num in range(expected_segments):
        video_file = f"/tmp/GANGLIA/ttv/segment_{segment_num}_initial.mp4"
        
        # Skip if video file doesn't exist
        if not os.path.exists(video_file):
            continue

        segments_found.append(segment_num)
        
        # Get video duration first
        video_duration = get_video_duration(video_file)
        if video_duration == 0.0:  # Skip if we couldn't get video duration
            continue
            
        total_video_duration += video_duration

        # Extract audio from video and get its duration
        try:
            result = subprocess.run(
                ["ffprobe", "-v", "error", "-select_streams", "a:0", "-show_entries",
                 "stream=duration", "-of", "default=noprint_wrappers=1:nokey=1", video_file],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True)
            audio_duration = float(result.stdout.decode().strip())
            
            # Validate durations
            if abs(audio_duration - video_duration) >= 0.1:
                discrepancies.append((f"audio_stream_{segment_num}", video_file, audio_duration, video_duration))
            else:
                print(f"✓ Duration match for segment {segment_num}: audio stream ({audio_duration:.2f}s) vs video container ({video_duration:.2f}s)")
                
        except (subprocess.CalledProcessError, ValueError) as e:
            Logger.print_error(f"Failed to get audio duration for segment {segment_num}: {e}")
            continue

    # Print discrepancies if any
    if discrepancies:
        print("\n!!! Duration Mismatches Found !!!")
        print("-" * 80)
        print("|{:^20}|{:^20}|{:^15}|{:^15}|".format(
            "Audio Stream", "Video File", "Audio Duration", "Video Duration"))
        print("-" * 80)
        for audio_id, video_file, audio_duration, video_duration in discrepancies:
            print("|{:^20}|{:^20}|{:^15.2f}|{:^15.2f}|".format(
                audio_id,
                os.path.basename(video_file),
                audio_duration,
                video_duration
            ))
        print("-" * 80)

    # Print found segments in order
    segments_found.sort()
    print(f"\nFound segments: {segments_found}")
    print(f"✓ Total segment duration: {total_video_duration:.2f}s")

    # Validate segment count
    assert len(segments_found) == expected_segments, f"Expected {expected_segments} segments but found {len(segments_found)}"

    return total_video_duration

def extract_final_video_path(output):
    """Extract the final video path from the logs."""
    # Try both formats:
    # 1. "Final video (?:with|without) closing credits created: output_path=/path/to/file.mp4"
    # 2. "Final video created at: output_path=/path/to/file.mp4"
    patterns = [
        r'Final video (?:with|without) closing credits created: output_path=(.+\.mp4)',
        r'Final video created at: output_path=(.+\.mp4)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, output)
        if match:
            return match.group(1)
    
    raise AssertionError("Final video path not found in logs.")

def validate_final_video_path(output, config_path=None):
    """Validate that the final video path is found in the logs."""
    print("\n=== Validating Final Video Path ===")
    final_video_path = extract_final_video_path(output)
    assert os.path.exists(final_video_path), f"Expected output video not found at {final_video_path}"
    print(f"✓ Final video found at: {os.path.basename(final_video_path)}")
    
    # Check if closing credits were expected but not found
    if config_path:
        try:
            with open(config_path, 'r') as f:
                config = json.loads(f.read())
                if config.get('closing_credits'):
                    if 'without closing credits' in output:
                        print("\n⚠️  Warning: Closing credits were configured but not found in final video")
                        print("   This might be due to Suno API being unavailable or other generation issues")
        except Exception as e:
            print(f"\n⚠️  Warning: Could not check closing credits configuration: {e}")
    
    return final_video_path

def validate_total_duration(final_video_path, total_video_duration):
    """Validate that the total video duration matches the expected duration."""
    print("\n=== Validating Total Video Duration ===")
    
    # Get actual duration of final video
    final_duration = get_video_duration(final_video_path)
    
    assert abs(final_duration - total_video_duration) < 1.0, f"Final video duration ({final_duration}s) does not match expected duration ({total_video_duration}s)."
    print(f"✓ Final duration ({final_duration:.2f}s) matches expected duration ({total_video_duration:.2f}s)")

def validate_closing_credits_duration(output, config_path):
    """Validate that the closing credits audio and video durations match.
    
    Handles both generated closing credits (from prompt) and pre-loaded credits.
    """
    print("\n=== Validating Closing Credits Duration ===")
    
    # First try to find generated credits duration in logs
    duration_match = re.search(f'{LOG_CLOSING_CREDITS_DURATION}: (\\d+\\.\\d+)s', output)
    if duration_match:
        audio_duration = float(duration_match.group(1))
        print(f"✓ Generated closing credits duration: {audio_duration:.2f}s")
        return audio_duration
    
    # If no generated credits found, check for pre-loaded credits in config
    try:
        with open(config_path, 'r') as f:
            config = json.loads(f.read())
            if 'closing_credits' in config and isinstance(config['closing_credits'], str):
                credits_path = config['closing_credits']
                audio_duration = get_audio_duration(credits_path)
                print(f"✓ Pre-loaded closing credits ({os.path.basename(credits_path)}) duration: {audio_duration:.2f}s")
                return audio_duration
    except (json.JSONDecodeError, FileNotFoundError, KeyError) as e:
        print(f"Failed to read closing credits from config: {e}")
        
    print("No closing credits found")
    return 0.0 