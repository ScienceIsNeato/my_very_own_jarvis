import os
import openai
from datetime import datetime
import tempfile
import multiprocessing
import platform
import psutil
from typing import Optional
from functools import lru_cache
import threading

openai.api_key = os.environ.get("OPENAI_API_KEY")

def get_tempdir():
    """
    Get the temporary directory in a platform-agnostic way.
    Creates and returns /tmp/GANGLIA for POSIX systems or %TEMP%/GANGLIA for Windows.
    """
    temp_dir = os.getenv('GANGLIA_TEMP_DIR', tempfile.gettempdir())
    temp_dir = os.path.join(temp_dir, 'GANGLIA')
    os.makedirs(temp_dir, exist_ok=True)
    return temp_dir

# Alias for backward compatibility
get_tmp_dir = get_tempdir
setup_tmp_dir = get_tempdir  # This will create the directory as a side effect

def get_config_path():
    """Get the path to the config directory relative to the project root."""
    return os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'ganglia_config.json')

@lru_cache(maxsize=1)
def get_system_info():
    """
    Get system information including CPU count and available memory.
    Cached to avoid repeated system calls.
    """
    return {
        'cpu_count': multiprocessing.cpu_count(),
        'total_memory': psutil.virtual_memory().total,
        'platform': platform.system().lower()
    }

def get_ffmpeg_thread_count(is_ci: Optional[bool] = None) -> int:
    """
    Get the optimal number of threads for FFmpeg operations.
    
    In CI environments, this returns a lower thread count to avoid resource contention.
    CI detection is automatic - GitHub Actions and most CI platforms automatically set CI=true,
    so no manual configuration is needed.
    
    Args:
        is_ci: Optional boolean to force CI behavior. If None, determines from environment.
        
    Returns:
        int: Number of threads to use for FFmpeg operations
    """
    # Get physical CPU cores, excluding hyperthreading
    cpu_count = psutil.cpu_count(logical=False)
    if cpu_count is None:
        cpu_count = os.cpu_count() or 1
    
    # Check if running in CI environment
    # Uses standard CI=true environment variable that GitHub Actions and most CI platforms set automatically
    if is_ci is None:
        is_ci = os.environ.get('CI', '').lower() == 'true'
    
    if is_ci:
        # Use reduced threads in CI to avoid resource contention
        return max(2, min(6, cpu_count // 2))
    
    # In non-CI environments, use all available cores
    return cpu_count

class FFmpegThreadManager:
    """
    Manages FFmpeg thread allocation across multiple concurrent operations.
    Ensures we don't oversubscribe system resources.
    """
    def __init__(self):
        self._active_operations = 0
        self._lock = threading.Lock()
    
    def _determine_max_concurrent(self) -> int:
        """
        Determine maximum number of concurrent FFmpeg operations based on system resources.
        Following Jan Ozer's research and FFmpeg best practices:
        - For x264/x265: Each encode should use ~1.5x the number of threads as physical cores
        - Multiple concurrent encodes are more efficient than single heavily threaded encodes
        - Leave some headroom for system operations
        """
        system_info = get_system_info()
        cpu_count = system_info['cpu_count']
        
        # Calculate available CPU resources
        # Reserve 2 cores or 10% of cores (whichever is larger) for system operations
        reserved_cores = max(2, int(cpu_count * 0.1))
        available_cores = cpu_count - reserved_cores
        
        # Get the base thread count that would be used for a single operation
        base_threads = get_ffmpeg_thread_count()
        
        # Calculate how many operations we can run concurrently
        # based on available cores and thread usage per operation
        max_concurrent = max(1, int(available_cores / base_threads))
        
        # Cap at 6 concurrent operations to prevent I/O bottlenecks
        # This is based on common SSD IOPS limitations
        return min(6, max_concurrent)
    
    def get_threads_for_operation(self) -> int:
        """
        Get the number of threads to allocate for a new FFmpeg operation.
        Takes into account current system load and concurrent operations.
        
        Returns:
            int: Number of threads to allocate for this operation
        """
        with self._lock:
            if self._active_operations == 0:
                # First operation gets full thread count
                return get_ffmpeg_thread_count()
            
            # Get base thread count for calculations
            base_thread_count = get_ffmpeg_thread_count()
            max_concurrent = self._determine_max_concurrent()
            
            if self._active_operations >= max_concurrent:
                # If we're at max concurrent operations, use minimum viable threads
                return max(2, base_thread_count // (self._active_operations * 2))
            
            # For operations up to max_concurrent, distribute threads geometrically
            # This ensures a more balanced distribution while maintaining higher
            # thread counts for earlier operations
            divisor = 2 ** (self._active_operations - 1)
            return max(2, base_thread_count // divisor)
    
    def __enter__(self):
        """Context manager entry - register new FFmpeg operation"""
        with self._lock:
            self._active_operations += 1
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - unregister FFmpeg operation"""
        with self._lock:
            self._active_operations = max(0, self._active_operations - 1)

# Global thread manager instance
ffmpeg_thread_manager = FFmpegThreadManager()