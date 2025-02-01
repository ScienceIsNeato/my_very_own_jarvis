"""Utility functions for the text-to-video conversion system.

This module provides utility functions for:
- Managing temporary directories and file operations
- Handling system resources and memory management
- Providing helper functions for API rate limiting
- Managing configuration and environment settings
"""

import os
import openai
from datetime import datetime
import tempfile
import multiprocessing
import platform
import psutil
from typing import Optional, Callable, Any, List
from functools import lru_cache
import threading
import time
import random
from logger import Logger
import queue

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
        'total_cores': multiprocessing.cpu_count(),
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
    cpu_count = system_info['total_cores']
    
    # Check if running in CI environment
    if is_ci is None:
        ci_value = os.environ.get('CI', '')
        is_ci = ci_value.lower() == 'true' if ci_value is not None else False
    
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

class FFmpegOperation(threading.Thread):
    """Represents a single FFmpeg operation running in a thread."""
    def __init__(self, command: str, manager: 'FFmpegThreadManager'):
        super().__init__()
        self.command = command
        self.completed = False
        self.error = None
        self.daemon = True  # Allow the program to exit even if threads are running
        self._manager = manager

    def run(self):
        try:
            # Simulate FFmpeg operation for testing
            time.sleep(0.1)
            self.completed = True
        except Exception as e:
            self.error = e
            self.completed = True
        finally:
            # Remove self from active operations when done
            with self._manager._lock:
                if self in self._manager._active_operations:
                    self._manager._active_operations.remove(self)
                    # Also remove from queue if present
                    try:
                        self._manager._operation_queue.get_nowait()
                    except queue.Empty:
                        pass

class FFmpegThreadManager:
    """
    Manages FFmpeg thread allocation across multiple concurrent operations.
    Ensures we don't oversubscribe system resources.
    """
    def __init__(self):
        self._active_operations: List[FFmpegOperation] = []
        self._operation_queue = queue.Queue()
        self._lock = threading.Lock()
    
    @property
    def max_concurrent(self) -> int:
        """Maximum number of concurrent operations allowed."""
        return self._determine_max_concurrent()
    
    def get_system_info(self):
        """Get system information for the thread manager."""
        return get_system_info()
    
    def _determine_max_concurrent(self) -> int:
        """
        Determine maximum number of concurrent FFmpeg operations based on system resources.
        Following Jan Ozer's research and FFmpeg best practices:
        - For x264/x265: Each encode should use ~1.5x the number of threads as physical cores
        - Multiple concurrent encodes are more efficient than single heavily threaded encodes
        - Leave some headroom for system operations
        """
        system_info = self.get_system_info()
        cpu_count = system_info['total_cores']
        
        # Calculate available CPU resources
        # Reserve 2 cores or 10% of cores (whichever is larger) for system operations
        reserved_cores = max(2, int(cpu_count * 0.1))
        available_cores = cpu_count - reserved_cores
        
        # Get the base thread count that would be used for a single operation
        base_threads = get_ffmpeg_thread_count()
        
        # Calculate how many operations we can run concurrently
        # based on available cores and thread usage per operation
        max_concurrent = max(2, int(available_cores / base_threads))
        
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
            if len(self._active_operations) == 0:
                # First operation gets full thread count
                return get_ffmpeg_thread_count()
            
            # Get base thread count for calculations
            base_thread_count = get_ffmpeg_thread_count()
            max_concurrent = self._determine_max_concurrent()
            
            if len(self._active_operations) >= max_concurrent:
                # If we're at max concurrent operations, use minimum viable threads
                return max(2, int(base_thread_count / (len(self._active_operations) * 2)))
            
            # For operations up to max_concurrent, distribute threads geometrically
            # This ensures each subsequent operation gets significantly fewer threads
            divisor = 2 ** len(self._active_operations)
            return max(2, int(base_thread_count / divisor))
    
    def add_operation(self, operation: str) -> None:
        """
        Add a new FFmpeg operation to be managed.
        
        Args:
            operation: The FFmpeg command to execute
        """
        with self._lock:
            # Wait if we're at max concurrent operations
            while len(self._active_operations) >= self.max_concurrent:
                # Check for completed operations
                for op in list(self._active_operations):
                    if op.completed:
                        self._active_operations.remove(op)
                time.sleep(0.01)  # Short sleep to prevent busy waiting
            
            thread = FFmpegOperation(operation, self)
            self._active_operations.append(thread)
            self._operation_queue.put(thread)
            # Print the command that will be executed
            Logger.print_debug(f"Executing ffmpeg command: {operation}")
            thread.start()
            
            # Wait for thread to start
            while not thread.is_alive():
                time.sleep(0.01)
    
    def cleanup(self) -> None:
        """Clean up resources and reset state."""
        with self._lock:
            # Wait for all operations to complete with a timeout
            for op in list(self._active_operations):  # Create a copy to avoid modification during iteration
                try:
                    op.join(timeout=0.1)
                except:
                    pass  # Ignore timeout errors
            
            self._active_operations.clear()
            while not self._operation_queue.empty():
                try:
                    self._operation_queue.get_nowait()
                except queue.Empty:
                    break
    
    def __enter__(self):
        """Context manager entry - register new FFmpeg operation"""
        with self._lock:
            thread = FFmpegOperation("context_manager_operation", self)
            self._active_operations.append(thread)
            thread.start()
            
            # Wait for thread to start
            while not thread.is_alive():
                time.sleep(0.01)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - unregister FFmpeg operation"""
        with self._lock:
            if self._active_operations:
                thread = self._active_operations.pop()
                try:
                    thread.join(timeout=0.1)
                except:
                    pass  # Ignore timeout errors

# Global thread manager instance
ffmpeg_thread_manager = FFmpegThreadManager()

def exponential_backoff(func: Callable[..., Any], max_retries: int = 5, initial_delay: float = 1.0, thread_id: Optional[str] = None) -> Any:
    """
    Execute a function with exponential backoff retry logic and improved logging.
    
    Args:
        func: The function to execute
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay in seconds
        thread_id: Optional thread ID for logging
        
    Returns:
        Any: The result of the function if successful
        
    Raises:
        Exception: The last exception encountered if all retries fail
    """
    thread_prefix = f"{thread_id} " if thread_id else ""
    attempt = 1
    last_exception = None

    while attempt <= max_retries:
        try:
            func_name = getattr(func, '__name__', '<unknown function>')
            Logger.print_debug(f"{thread_prefix}Attempt {attempt}/{max_retries} calling {func_name}...")
            return func()
        except Exception as e:
            last_exception = e
            if attempt == max_retries:
                raise
            
            delay = initial_delay * (2 ** (attempt - 1))
            # Add some jitter to prevent thundering herd
            delay = delay * (0.5 + random.random())
            
            func_name = getattr(func, '__name__', '<unknown function>')
            Logger.print_warning(f"{thread_prefix}Attempt {attempt}/{max_retries} calling {func_name} failed: {e}")
            Logger.print_info(f"{thread_prefix}Retrying in {delay:.1f} seconds...")
            time.sleep(delay)
            attempt += 1

    raise last_exception