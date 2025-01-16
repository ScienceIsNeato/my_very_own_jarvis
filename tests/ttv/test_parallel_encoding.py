import pytest
import os
import tempfile
from ttv import parallel_encoding

def test_split_segments_for_parallel_processing():
    # Test that segments are split evenly across threads
    segments = [f"segment_{i}.mp4" for i in range(10)]
    thread_count = 3
    
    chunks = parallel_encoding.split_segments_for_parallel_processing(segments, thread_count)
    
    assert len(chunks) == thread_count
    # Check that all segments are included
    all_segments = [seg for chunk in chunks for seg in chunk]
    assert sorted(all_segments) == sorted(segments)
    # Check that chunks are roughly even in size
    chunk_sizes = [len(chunk) for chunk in chunks]
    assert max(chunk_sizes) - min(chunk_sizes) <= 1

def test_determine_optimal_thread_count():
    # Test that thread count is reasonable based on CPU cores
    thread_count = parallel_encoding.determine_optimal_thread_count()
    
    import multiprocessing
    cpu_count = multiprocessing.cpu_count()
    
    # Should use at most CPU count - 1 threads to leave one core free
    assert thread_count <= cpu_count - 1
    # Should use at least 1 thread
    assert thread_count >= 1

def test_encode_segments_in_parallel():
    # Create temporary test video segments
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create dummy video files
        input_segments = []
        for i in range(3):
            segment_path = os.path.join(temp_dir, f"segment_{i}.mp4")
            # Create a 1-second test video
            os.system(f"ffmpeg -y -f lavfi -i color=c=black:s=1280x720:d=1 -c:v libx264 {segment_path}")
            input_segments.append(segment_path)
        
        # Test parallel encoding
        output_dir = os.path.join(temp_dir, "encoded")
        os.makedirs(output_dir, exist_ok=True)
        
        encoded_segments = parallel_encoding.encode_segments_in_parallel(
            input_segments,
            output_dir,
            thread_count=2
        )
        
        # Verify outputs
        assert len(encoded_segments) == len(input_segments)
        for segment in encoded_segments:
            assert os.path.exists(segment)
            # Verify file size is non-zero
            assert os.path.getsize(segment) > 0

def test_concatenate_encoded_segments():
    # Test that segments are concatenated in the correct order
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create dummy video files
        input_segments = []
        for i in range(3):
            segment_path = os.path.join(temp_dir, f"segment_{i}.mp4")
            # Create test videos with different durations
            os.system(f"ffmpeg -y -f lavfi -i color=c=black:s=1280x720:d={i+1} {segment_path}")
            input_segments.append(segment_path)
        
        output_path = os.path.join(temp_dir, "final.mp4")
        result = parallel_encoding.concatenate_encoded_segments(input_segments, output_path)
        
        assert os.path.exists(result)
        # Verify the duration is the sum of input durations (6 seconds)
        duration_cmd = f"ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 {result}"
        duration = float(os.popen(duration_cmd).read().strip())
        assert abs(duration - 6.0) < 0.1  # Allow small tolerance 