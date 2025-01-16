from typing import List
import pytest
import os
import tempfile
import time
import subprocess
from ttv.final_video_generation import assemble_final_video
from ttv import parallel_encoding

def run_ffmpeg_cmd(cmd: List[str]) -> None:
    """Run an ffmpeg command safely using subprocess."""
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        pytest.fail(f"FFmpeg command failed: {e.stderr}")

def get_video_duration(path: str) -> float:
    """Get the duration of a video file."""
    try:
        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            path
        ]
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        return float(result.stdout.strip())
    except (subprocess.CalledProcessError, ValueError) as e:
        pytest.fail(f"Failed to get video duration: {str(e)}")
        return 0.0  # Never reached due to pytest.fail, but keeps type checker happy

def test_concatenate_video_segments() -> None:
    """Test that video segments are correctly concatenated with parallel encoding."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create test video segments with distinct colors and durations
        segments: List[str] = []
        colors = ['red', 'green', 'blue']  # Distinct colors for each segment
        for i, color in enumerate(colors):
            segment_path = os.path.join(temp_dir, f"segment_{i}.mp4")
            cmd = [
                'ffmpeg', '-y',
                '-f', 'lavfi',
                '-i', f'color=c={color}:s=1280x720:d={i+1}',
                '-vf', f"drawtext=text='Segment {i+1} - {i+1}s':fontcolor=white:fontsize=72:x=(w-text_w)/2:y=(h-text_h)/2",
                segment_path
            ]
            run_ffmpeg_cmd(cmd)
            segments.append(segment_path)
        
        # Test with parallel encoding
        start_time = time.time()
        output_dir = os.path.join(temp_dir, "temp_encoded")
        os.makedirs(output_dir, exist_ok=True)
        
        # Encode with max threads
        encoded_segments = parallel_encoding.encode_segments_in_parallel(segments, output_dir)
        output_path = os.path.join(temp_dir, "final_parallel.mp4")
        parallel_encoding.concatenate_encoded_segments(encoded_segments, output_path)
        parallel_time = time.time() - start_time
        
        # Test with single thread
        start_time = time.time()
        output_dir_single = os.path.join(temp_dir, "temp_encoded_single")
        os.makedirs(output_dir_single, exist_ok=True)
        
        # Encode with single thread
        encoded_segments_single = parallel_encoding.encode_segments_in_parallel(segments, output_dir_single, thread_count=1)
        output_path_single = os.path.join(temp_dir, "final_single.mp4")
        parallel_encoding.concatenate_encoded_segments(encoded_segments_single, output_path_single)
        single_time = time.time() - start_time
        
        # Calculate speedup
        speedup_percent = ((single_time - parallel_time) / single_time) * 100
        print("\nPerformance Comparison:")
        print(f"Parallel encoding time: {parallel_time:.2f}s")
        print(f"Single thread time: {single_time:.2f}s")
        print(f"Speedup: {speedup_percent:.1f}%")
        
        assert os.path.exists(output_path)
        # Verify the duration is the sum of input durations (6 seconds)
        duration = get_video_duration(output_path)
        assert abs(duration - 6.0) < 0.1  # Allow small tolerance

def test_assemble_final_video() -> None:
    """Test full video assembly process including background music and credits."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create test video segments with distinct colors and test patterns
        segments: List[str] = []
        colors = ['yellow', 'magenta']  # Distinct colors for main segments
        for i, color in enumerate(colors):
            segment_path = os.path.join(temp_dir, f"segment_{i}.mp4")
            cmd = [
                'ffmpeg', '-y',
                '-f', 'lavfi',
                '-i', f'color=c={color}:s=1280x720:d=1',
                '-vf', f"drawtext=text='Main Video {i+1}':fontcolor=black:fontsize=72:x=(w-text_w)/2:y=(h-text_h)/2",
                segment_path
            ]
            run_ffmpeg_cmd(cmd)
            segments.append(segment_path)
        
        # Create test background music with a sine wave tone
        music_path = os.path.join(temp_dir, "music.mp3")
        cmd = [
            'ffmpeg', '-y',
            '-f', 'lavfi',
            '-i', 'sine=frequency=440:duration=3',  # 440Hz tone for 3s
            '-q:a', '9',
            '-acodec', 'libmp3lame',
            music_path
        ]
        run_ffmpeg_cmd(cmd)
        
        # Create test credits music with a different tone
        credits_music_path = os.path.join(temp_dir, "credits.mp3")
        cmd = [
            'ffmpeg', '-y',
            '-f', 'lavfi',
            '-i', 'sine=frequency=880:duration=2',  # 880Hz tone for 2s
            '-q:a', '9',
            '-acodec', 'libmp3lame',
            credits_music_path
        ]
        run_ffmpeg_cmd(cmd)
        
        # Create test movie poster with text
        poster_path = os.path.join(temp_dir, "poster.png")
        cmd = [
            'ffmpeg', '-y',
            '-f', 'lavfi',
            '-i', 'color=c=cyan:s=1280x720:d=1',
            '-vf', "drawtext=text='Credits Section':fontcolor=black:fontsize=72:x=(w-text_w)/2:y=(h-text_h)/2",
            '-vframes', '1',
            poster_path
        ]
        run_ffmpeg_cmd(cmd)
        
        output_path = os.path.join(temp_dir, "final_with_music.mp4")
        result = assemble_final_video(
            video_segments=segments,
            music_path=music_path,
            song_with_lyrics_path=credits_music_path,
            movie_poster_path=poster_path,
            output_path=output_path
        )
        
        assert result == output_path
        assert os.path.exists(output_path)
        
        # Verify the video has audio streams
        cmd = [
            'ffprobe',
            '-v', 'error',
            '-select_streams', 'a',
            '-show_entries', 'stream=codec_type',
            '-of', 'csv=p=0',
            output_path
        ]
        try:
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            assert "audio" in result.stdout
        except subprocess.CalledProcessError as e:
            pytest.fail(f"Failed to check audio streams: {e.stderr}") 