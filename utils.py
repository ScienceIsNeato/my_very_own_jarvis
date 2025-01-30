import os
import openai
from datetime import datetime
import tempfile
import multiprocessing
import platform
import psutil
from typing import Optional, Callable, Any
from functools import lru_cache
import threading
import time
import random

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
    # Get system info from cached function
    system_info = get_system_info()
    cpu_count = system_info['cpu_count']
    
    # Check if running in CI environment
    if is_ci is None:
        is_ci = os.environ.get('CI', '').lower() == 'true'
    
    if is_ci:
        # In CI: Use cpu_count/2 with min 2, max 4 threads
        # Also consider memory constraints - reduce threads if < 4GB RAM
        memory_gb = system_info['total_memory'] / (1024**3)
        if memory_gb < 4:
            return 2
        
        # For 1-2 cores, always use 2 threads
        if cpu_count <= 2:
            return 2
        
        # For 4 cores, use 4 threads
        if cpu_count == 4:
            return 4
        
        # For >4 cores, use cpu_count/2 but cap at 4
        return min(4, cpu_count // 2)
    
    # In production: Use 1.5x CPU count, capped at 16 threads
    # For single core systems, use just 1 thread
    if cpu_count == 1:
        return 1
    return min(16, int(cpu_count * 1.5))

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
                return max(2, int(base_thread_count / (self._active_operations * 2)))
            
            # For operations up to max_concurrent, distribute threads geometrically
            # This ensures each subsequent operation gets significantly fewer threads
            divisor = 2 ** (self._active_operations)
            return max(2, int(base_thread_count / divisor))
    
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

def exponential_backoff(func: Callable[..., Any], max_retries: int = 5, initial_delay: float = 1.0) -> Any:
    """
    Execute a function with exponential backoff retry logic.
    
    Args:
        func: The function to execute
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay in seconds before first retry
        
    Returns:
        The result of the function if successful
        
    Raises:
        The last exception encountered if all retries fail
    """
    last_exception = None
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            last_exception = e
            if attempt == max_retries - 1:
                raise
            
            delay = initial_delay * (2 ** attempt) + random.uniform(0, 0.1)
            time.sleep(delay)
    
    if last_exception:
        raise last_exception