import subprocess
from logger import Logger
from utils import ffmpeg_thread_manager

def run_ffmpeg_command(ffmpeg_cmd):
    """
    Run an FFmpeg command with managed thread allocation.
    
    Args:
        ffmpeg_cmd: List of command arguments for FFmpeg
    
    Returns:
        subprocess.CompletedProcess or None if the command fails
    """
    try:
        # Use thread manager as context manager to track active operations
        with ffmpeg_thread_manager as mgr:
            # Get optimal thread count for this operation
            thread_count = mgr.get_threads_for_operation()

            # Insert thread count argument right after ffmpeg command
            # Make a copy of the command to avoid modifying the original
            cmd = ffmpeg_cmd.copy()
            cmd.insert(1, "-threads")
            cmd.insert(2, str(thread_count))

            Logger.print_info(f"Running ffmpeg command with {thread_count} threads: {' '.join(cmd)}")
            result = subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            Logger.print_info(f"ffmpeg output: {result.stdout.decode('utf-8')}")
            return result

    except subprocess.CalledProcessError as e:
        Logger.print_error(f"ffmpeg failed with error: {e.stderr.decode('utf-8')}")
        Logger.print_error(f"ffmpeg command was: {' '.join(ffmpeg_cmd)}")
        return None
