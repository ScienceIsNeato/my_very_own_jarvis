from logger import Logger
from .ffmpeg_wrapper import run_ffmpeg_command
import os
import multiprocessing
from concurrent.futures import ThreadPoolExecutor
from typing import List, Optional

def split_segments_for_parallel_processing(segments: List[str], thread_count: int) -> List[List[str]]:
    """Split video segments into roughly equal chunks for parallel processing."""
    if not segments:
        return []
    
    # Calculate chunk size to distribute segments evenly
    chunk_size = len(segments) // thread_count
    remainder = len(segments) % thread_count
    
    chunks = []
    start = 0
    for i in range(thread_count):
        # Add one extra item to some chunks if we have a remainder
        current_chunk_size = chunk_size + (1 if i < remainder else 0)
        end = start + current_chunk_size
        chunks.append(segments[start:end])
        start = end
    
    return chunks

def determine_optimal_thread_count() -> int:
    """Determine optimal number of threads based on system resources."""
    cpu_count = multiprocessing.cpu_count()
    # Use CPU count - 1 to leave one core free for system
    return max(1, cpu_count - 1)

def encode_segment(segment: str, output_dir: str) -> Optional[str]:
    """Encode a single video segment using ffmpeg."""
    try:
        output_path = os.path.join(output_dir, f"encoded_{os.path.basename(segment)}")
        ffmpeg_cmd = [
            "ffmpeg", "-y",
            "-i", segment,
            "-c:v", "libx264",
            "-preset", "ultrafast",  # Fastest encoding
            "-crf", "23",  # Balance quality/size
            "-c:a", "aac",
            "-b:a", "192k",
            output_path
        ]
        
        result = run_ffmpeg_command(ffmpeg_cmd)
        if result and os.path.exists(output_path):
            return output_path
        return None
    except Exception as e:
        Logger.print_error(f"Error encoding segment {segment}: {str(e)}")
        return None

def encode_segments_in_parallel(
    segments: List[str],
    output_dir: str,
    thread_count: Optional[int] = None
) -> List[str]:
    """Encode multiple video segments in parallel using a thread pool."""
    if thread_count is None:
        thread_count = determine_optimal_thread_count()
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Split segments into chunks
    segment_chunks = split_segments_for_parallel_processing(segments, thread_count)
    
    encoded_segments = []
    with ThreadPoolExecutor(max_workers=thread_count) as executor:
        # Submit encoding jobs for each segment
        future_to_segment = {
            executor.submit(encode_segment, segment, output_dir): segment
            for chunk in segment_chunks
            for segment in chunk
        }
        
        # Collect results in order
        for segment in segments:
            for future in future_to_segment:
                if future_to_segment[future] == segment:
                    result = future.result()
                    if result:
                        encoded_segments.append(result)
                    break
    
    return encoded_segments

def concatenate_encoded_segments(segments: List[str], output_path: str) -> Optional[str]:
    """Concatenate encoded segments in the correct order using ffmpeg."""
    try:
        # Create temporary file list
        list_file = os.path.join(os.path.dirname(output_path), "segments_list.txt")
        with open(list_file, "w") as f:
            for segment in segments:
                f.write(f"file '{segment}'\n")
        
        # Concatenate using ffmpeg
        ffmpeg_cmd = [
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", list_file,
            "-c", "copy",  # Fast copy without re-encoding
            output_path
        ]
        
        result = run_ffmpeg_command(ffmpeg_cmd)
        
        # Clean up
        os.remove(list_file)
        
        if result and os.path.exists(output_path):
            return output_path
        return None
    except Exception as e:
        Logger.print_error(f"Error concatenating segments: {str(e)}")
        return None 