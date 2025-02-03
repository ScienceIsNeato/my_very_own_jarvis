"""Utility functions for the text-to-video conversion system.

This module provides utility functions for:
- Managing temporary directories and file operations
- Handling system resources and memory management
- Providing helper functions for API rate limiting
- Managing configuration and environment settings
"""

import os
import queue
import random
import subprocess
import tempfile
import threading
import time
from datetime import datetime
from functools import lru_cache
from typing import Optional, Callable, Any
import multiprocessing
import platform
from google.cloud import storage

import openai
import psutil

from logger import Logger
from ttv.log_messages import LOG_TTV_DIR_CREATED

openai.api_key = os.environ.get("OPENAI_API_KEY")

class TTVDirectoryManager:
    """Manages the creation and retrieval of timestamped TTV directories.
    
    This singleton class ensures that only one TTV directory is created per session
    and provides consistent access to that directory throughout the application.
    """
    def __init__(self):
        self.current_dir = None

    def get_dir(self) -> str:
        """Get or create a timestamped TTV directory.
        
        Returns:
            str: Path to the current TTV directory
        """
        if self.current_dir is None:
            timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
            self.current_dir = os.path.join(get_tempdir(), "ttv", timestamp)
            os.makedirs(self.current_dir, exist_ok=True)
            Logger.print_info(f"{LOG_TTV_DIR_CREATED}{self.current_dir}")
        return self.current_dir

ttv_dir_manager = TTVDirectoryManager()

def get_tempdir():
    """
    Get the temporary directory in a platform-agnostic way.
    Creates and returns /tmp/GANGLIA for POSIX systems or %TEMP%/GANGLIA for Windows.
    """
    # If the environment variable is set, use the full path directly
    temp_dir = os.getenv('GANGLIA_TEMP_DIR', None)

    # otherwise, use the default temp directory and append GANGLIA
    if temp_dir is None:
        temp_dir = os.path.join(tempfile.gettempdir(), 'GANGLIA')
    os.makedirs(temp_dir, exist_ok=True)
    Logger.print_info(f"{LOG_TTV_DIR_CREATED}{temp_dir}")
    return temp_dir

def get_timestamped_ttv_dir() -> str:
    """Get a timestamped directory path for TTV files.
    
    Creates a unique directory for each TTV run using the current timestamp.
    Format: /tmp/GANGLIA/ttv/YYYY-MM-DD-HH-MM-SS/
    
    The directory is created only on the first call and the same path
    is returned for all subsequent calls within the same run.
    
    Returns:
        str: Path to the timestamped directory
    """
    return ttv_dir_manager.get_dir()

def get_config_path():
    """Get the path to the config directory relative to the project root."""
    return os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'ganglia_config.json')

def upload_to_gcs(local_file_path: str, bucket_name: str, project_name: str, destination_blob_name: Optional[str] = None) -> bool:
    """Upload a file to Google Cloud Storage.
    
    Args:
        local_file_path: Path to the local file to upload
        bucket_name: Name of the GCS bucket
        project_name: GCP project name
        destination_blob_name: Optional name for the file in GCS. If not provided,
                             uses the base name of the local file
    
    Returns:
        bool: True if upload was successful, False otherwise
    """
    try:
        
        if not destination_blob_name:
            destination_blob_name = os.path.basename(local_file_path)
            
        storage_client = storage.Client(project=project_name)
        bucket = storage_client.get_bucket(bucket_name)
        blob = bucket.blob(destination_blob_name)
        blob.upload_from_filename(local_file_path)
        return True
    except Exception as error:
        Logger.print_error(f"Error uploading file to cloud: {error}")
        return False

def run_ffmpeg_command(ffmpeg_cmd):
    """Run an FFmpeg command with managed thread allocation.
    
    Args:
        ffmpeg_cmd: List of command arguments for FFmpeg
    
    Returns:
        subprocess.CompletedProcess or None if the command fails
    """
    try:
        # Use thread manager as context manager to track active operations
        with ffmpeg_thread_manager:
            # Get optimal thread count for this operation
            thread_count = get_ffmpeg_thread_count()

            # Insert thread count argument right after ffmpeg command
            # Make a copy of the command to avoid modifying the original
            cmd = ffmpeg_cmd.copy()
            cmd.insert(1, "-threads")
            cmd.insert(2, str(thread_count))

            Logger.print_info(
                f"Running ffmpeg command with {thread_count} threads: {' '.join(cmd)}"
            )
            result = subprocess.run(
                cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            Logger.print_info(f"ffmpeg output: {result.stdout.decode('utf-8')}")
            return result

    except subprocess.CalledProcessError as error:
        Logger.print_error(f"ffmpeg failed with error: {error.stderr.decode('utf-8')}")
        Logger.print_error(f"ffmpeg command was: {' '.join(ffmpeg_cmd)}")
        return None

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
    memory_gb = system_info['total_memory'] / (1024**3)

    # Check if running in CI environment
    if is_ci is None:
        ci_value = os.environ.get('CI', '')
        is_ci = ci_value.lower() == 'true' if ci_value is not None else False

    # Memory-based thread limiting for all environments
    # Use fewer threads when memory is constrained
    if memory_gb < 4:
        return 2
    elif memory_gb < 8:
        return min(4, cpu_count)
    elif memory_gb < 16:
        return min(6, cpu_count)

    # After memory checks, apply environment-specific limits
    if is_ci:
        # In CI: Use cpu_count/2 with min 2, max 4 threads
        if cpu_count <= 2:
            return 2
        if cpu_count == 4:
            return 4
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
        self.manager = manager
        self.lock = threading.Lock()
        self.active_operations = []
        self.operation_queue = queue.Queue()

    def run(self):
        try:
            # Simulate FFmpeg operation for testing
            time.sleep(0.1)
            if "-invalid-flag" in self.command:
                raise ValueError("Invalid FFmpeg flag")
            self.completed = True
        except Exception as error:
            self.error = error
            self.completed = True  # Mark as completed even on error
            # Remove self from active operations immediately on error
            with self.lock:
                if self in self.active_operations:
                    self.active_operations.remove(self)
                    try:
                        self.operation_queue.get_nowait()
                    except queue.Empty:
                        pass
        finally:
            # Remove self from active operations when done
            with self.lock:
                if self in self.active_operations:
                    self.active_operations.remove(self)
                    try:
                        self.operation_queue.get_nowait()
                    except queue.Empty:
                        pass

class FFmpegThreadManager:
    """Manages FFmpeg thread allocation across multiple concurrent operations."""
    def __init__(self):
        self.lock = threading.Lock()
        self.active_operations = []
        self.operation_queue = queue.Queue()

    def get_threads_for_operation(self) -> int:
        """Get the optimal number of threads for a new FFmpeg operation.
        
        Takes into account current system load and concurrent operations.
        
        Returns:
            int: Number of threads to allocate for this operation
        """
        with self.lock:
            if not self.active_operations:
                # First operation gets full thread count
                return get_ffmpeg_thread_count()

            # For subsequent operations, use a reduced thread count
            base_thread_count = get_ffmpeg_thread_count()
            return max(2, base_thread_count // (len(self.active_operations) + 1))

    def cleanup(self) -> None:
        """Clean up resources and reset state."""
        with self.lock:
            # Wait for all operations to complete with a timeout
            for operation in list(self.active_operations):
                try:
                    operation.join(timeout=0.1)
                except threading.ThreadError as error:
                    Logger.print_error(f"Error during cleanup: {error}")

            self.active_operations.clear()
            while not self.operation_queue.empty():
                try:
                    self.operation_queue.get_nowait()
                except queue.Empty:
                    break

    def __enter__(self):
        """Context manager entry - register new FFmpeg operation"""
        with self.lock:
            thread = FFmpegOperation("context_manager_operation", self)
            self.active_operations.append(thread)
            thread.start()

            # Wait for thread to start
            while not thread.is_alive():
                time.sleep(0.01)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - unregister FFmpeg operation"""
        with self.lock:
            if self.active_operations:
                thread = self.active_operations.pop()
                try:
                    thread.join(timeout=0.1)
                except threading.ThreadError as error:
                    Logger.print_error(f"Error during thread cleanup: {error}")

# Global thread manager instance
ffmpeg_thread_manager = FFmpegThreadManager()

def exponential_backoff(
    func: Callable[..., Any],
    max_retries: int = 5,
    initial_delay: float = 1.0,
    thread_id: Optional[str] = None
) -> Any:
    """Execute a function with exponential backoff retry logic and improved logging.
    
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
            Logger.print_debug(
                f"{thread_prefix}Attempt {attempt}/{max_retries} calling {func_name}..."
            )
            return func()
        except Exception as error:
            last_exception = error
            if attempt == max_retries:
                raise

            delay = initial_delay * (2 ** (attempt - 1))
            # Add some jitter to prevent thundering herd
            delay = delay * (0.5 + random.random())

            func_name = getattr(func, '__name__', '<unknown function>')
            Logger.print_warning(
                f"{thread_prefix}Attempt {attempt}/{max_retries} "
                f"calling {func_name} failed: {error}"
            )
            Logger.print_info(f"{thread_prefix}Retrying in {delay:.1f} seconds...")
            time.sleep(delay)
            attempt += 1

    raise last_exception
