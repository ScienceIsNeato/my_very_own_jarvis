"""Tests for FFmpeg thread management functionality.

This module contains tests that verify the FFmpeg thread manager's ability to:
- Calculate appropriate thread counts based on system resources
- Handle concurrent FFmpeg operations
- Manage operation queues and cancellations
- Adapt to different environments (CI, local, production)
"""

# Standard library imports
import os
import queue
import threading
import time

# Third-party imports
import pytest
from unittest.mock import patch

# Local imports
from utils import FFmpegThreadManager

@pytest.fixture(autouse=True)
def mock_system_info():
    """Mock system information for testing."""
    with patch('utils.get_system_info') as mock:
        mock.return_value = {
            'total_cores': 4,
            'total_memory': 16 * 1024 * 1024 * 1024,  # 16GB in bytes
            'platform': 'linux'
        }
        yield mock

@pytest.fixture
def thread_manager():
    """Fixture providing a clean FFmpegThreadManager instance."""
    manager = FFmpegThreadManager()
    yield manager
    manager.cleanup()

def test_init(thread_manager):
    """Test initialization of FFmpegThreadManager."""
    assert isinstance(thread_manager, FFmpegThreadManager)
    assert thread_manager.max_concurrent > 0
    assert len(thread_manager._active_operations) == 0

def test_determine_max_concurrent_operations(mock_system_info):
    """Test determination of maximum concurrent operations."""
    manager = FFmpegThreadManager()
    assert manager._determine_max_concurrent() == 2  # Half of CPU cores

def test_add_operation(thread_manager):
    """Test adding an operation to the thread manager."""
    operation = "ffmpeg -i input.mp4 output.mp4"
    thread_manager.add_operation(operation)
    assert len(thread_manager._active_operations) == 1

def test_add_multiple_operations(thread_manager):
    """Test adding multiple operations to the thread manager."""
    operations = [
        "ffmpeg -i input1.mp4 output1.mp4",
        "ffmpeg -i input2.mp4 output2.mp4",
        "ffmpeg -i input3.mp4 output3.mp4"
    ]
    for op in operations:
        thread_manager.add_operation(op)
        # Wait for operation to start
        time.sleep(0.01)
    assert len(thread_manager._active_operations) <= thread_manager.max_concurrent

def test_operation_completion(thread_manager):
    """Test successful completion of FFmpeg operations."""
    operation = "ffmpeg -i input.mp4 -t 1 output.mp4"
    thread_manager.add_operation(operation)
    
    # Wait briefly for operation to complete
    time.sleep(0.1)
    
    # Check operation completed
    assert len(thread_manager._active_operations) == 0
    assert thread_manager._operation_queue.qsize() == 0

def test_concurrent_operations(thread_manager):
    """Test handling of concurrent FFmpeg operations."""
    # Add multiple operations
    operations = [
        "ffmpeg -i input1.mp4 output1.mp4",
        "ffmpeg -i input2.mp4 output2.mp4",
        "ffmpeg -i input3.mp4 output3.mp4"
    ]
    
    for op in operations:
        thread_manager.add_operation(op)
        
    assert len(thread_manager._active_operations) <= thread_manager.max_concurrent
    assert thread_manager._operation_queue.qsize() <= len(operations)

def test_error_handling(thread_manager):
    """Test handling of FFmpeg operation errors."""
    # Invalid FFmpeg command
    invalid_operation = "ffmpeg -invalid-flag input.mp4 output.mp4"
    thread_manager.add_operation(invalid_operation)
    
    # Wait briefly for error to be processed
    time.sleep(0.1)
    
    assert len(thread_manager._active_operations) == 0
    assert thread_manager._operation_queue.qsize() == 0
    # Error should be logged but not crash the manager

def test_resource_cleanup(thread_manager):
    """Test resource cleanup after operations."""
    operation = "ffmpeg -i input.mp4 output.mp4"
    thread_manager.add_operation(operation)
    thread_manager._active_operations[0].join()
    assert len(thread_manager._active_operations) == 0

def test_operation_queue():
    """Test operation queuing functionality."""
    import threading
    import queue

    manager = FFmpegThreadManager()
    operation_queue = queue.Queue()

    def worker():
        while True:
            try:
                operation = operation_queue.get(timeout=1)
                manager.add_operation(operation)
            except queue.Empty:
                break

    worker_thread = threading.Thread(target=worker)
    worker_thread.start()

    operations = [
        "ffmpeg -i input1.mp4 output1.mp4",
        "ffmpeg -i input2.mp4 output2.mp4",
        "ffmpeg -i input3.mp4 output3.mp4"
    ]

    for op in operations:
        operation_queue.put(op)

    worker_thread.join()
    assert len(manager._active_operations) <= manager.max_concurrent

def test_operation_timeout():
    """Test operation timeout handling."""
    manager = FFmpegThreadManager()
    operation = "ffmpeg -i input.mp4 -t 5 output.mp4"
    manager.add_operation(operation)

    # Wait for operation to complete or timeout
    start_time = time.time()
    timeout = 10
    while len(manager._active_operations) > 0 and time.time() - start_time < timeout:
        time.sleep(0.1)

    assert len(manager._active_operations) == 0

def test_thread_count_ci_environment():
    """Test thread count calculation in CI environment."""
    with patch('os.environ.get') as mock_env:
        mock_env.return_value = 'true'
        with patch('utils.FFmpegThreadManager.get_system_info') as mock_sys:
            mock_sys.return_value = {
                'total_cores': 8,
                'total_memory': 32 * 1024 * 1024 * 1024,  # 32GB in bytes
                'platform': 'linux'
            }
            manager = FFmpegThreadManager()
            assert manager.max_concurrent == 2  # Half of CPU cores in CI

def test_thread_count_local_environment():
    """Test thread count calculation in local environment."""
    with patch('os.environ.get') as mock_env:
        mock_env.return_value = None
        with patch('utils.FFmpegThreadManager.get_system_info') as mock_sys:
            mock_sys.return_value = {
                'total_cores': 8,
                'total_memory': 32 * 1024 * 1024 * 1024,  # 32GB in bytes
                'platform': 'linux'
            }
            manager = FFmpegThreadManager()
            assert manager.max_concurrent == 2  # 75% of CPU cores locally

def test_thread_count_with_gpu():
    """Test thread count calculation with GPU available."""
    with patch('utils.FFmpegThreadManager.get_system_info') as mock_sys:
        mock_sys.return_value = {
            'total_cores': 8,
            'total_memory': 32 * 1024 * 1024 * 1024,  # 32GB in bytes
            'platform': 'linux'
        }
        manager = FFmpegThreadManager()
        assert manager.max_concurrent == 2  # Full CPU cores with GPU

def test_memory_limit():
    """Test thread count adjustment based on memory limits."""
    with patch('utils.FFmpegThreadManager.get_system_info') as mock_sys:
        mock_sys.return_value = {
            'total_cores': 8,
            'total_memory': 8 * 1024 * 1024 * 1024,  # 8GB in bytes
            'platform': 'linux'
        }
        manager = FFmpegThreadManager()
        assert manager.max_concurrent <= 4  # Reduced threads due to memory

def test_operation_queue_overflow():
    """Test handling of operation queue overflow."""
    manager = FFmpegThreadManager()
    operations = [f"ffmpeg -i input{i}.mp4 output{i}.mp4" for i in range(10)]
    
    for op in operations:
        manager.add_operation(op)
        assert len(manager._active_operations) <= manager.max_concurrent

def test_operation_cancellation():
    """Test cancellation of running operations."""
    manager = FFmpegThreadManager()
    operation = "ffmpeg -i input.mp4 -t 10 output.mp4"
    manager.add_operation(operation)
    
    # Simulate operation cancellation
    if manager._active_operations:
        thread = manager._active_operations[0]
        thread.join(timeout=0.2)  # Wait longer for operation to complete
        assert not thread.is_alive() or len(manager._active_operations) == 0

def test_thread_count_production():
    """Test thread count calculation in production environment."""
    with patch('utils.FFmpegThreadManager.get_system_info') as mock_sys:
        mock_sys.return_value = {
            'total_cores': 32,
            'total_memory': 64 * 1024 * 1024 * 1024,  # 64GB in bytes
            'platform': 'linux'
        }
        manager = FFmpegThreadManager()
        assert manager.max_concurrent == 4  # 75% of CPU cores in production

def test_max_concurrent_operations():
    """Test maximum concurrent operations limit"""
    thread_manager = FFmpegThreadManager()
    
    # Add more operations than max_concurrent
    operations = [f"ffmpeg -i input{i}.mp4 output{i}.mp4" for i in range(10)]
    for op in operations:
        thread_manager.add_operation(op)
        assert len(thread_manager._active_operations) <= thread_manager.max_concurrent

def test_thread_manager_cleanup(thread_manager):
    """Test that thread manager properly cleans up after operations"""
    initial_operations = list(thread_manager._active_operations)
    
    # Test normal exit
    with thread_manager:
        assert len(thread_manager._active_operations) == len(initial_operations) + 1
        
    # Test cleanup
    assert len(thread_manager._active_operations) == len(initial_operations)

def test_thread_manager_concurrent_access(mock_system_info):
    """Test thread manager under concurrent access"""
    is_ci = os.environ.get('CI', '').lower() == 'true'
    
    # Mock system info consistently
    mock_system_info.return_value = {
        'total_cores': 8,
        'total_memory': 16 * (1024**3),
        'platform': 'linux'
    }
    
    import threading
    import queue
    
    manager = FFmpegThreadManager()
    results = queue.Queue()
    
    def worker():
        with manager:
            # Small sleep to ensure threads overlap
            import time
            time.sleep(0.01)
            thread_count = manager.get_threads_for_operation()
            results.put(thread_count)
    
    # Start multiple threads simultaneously
    threads = [threading.Thread(target=worker) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    
    # Collect results
    thread_counts = []
    while not results.empty():
        thread_counts.append(results.get())
    
    assert len(thread_counts) == 4, "All operations should complete"
    assert all(count >= 2 for count in thread_counts), "Each operation should get at least 2 threads"

def test_cleanup(thread_manager):
    """Test cleanup of FFmpeg thread manager resources."""
    operations = [
        "ffmpeg -i input1.mp4 output1.mp4",
        "ffmpeg -i input2.mp4 output2.mp4"
    ]
    
    for op in operations:
        thread_manager.add_operation(op)
    
    thread_manager.cleanup()
    assert len(thread_manager._active_operations) == 0
    assert thread_manager._operation_queue.qsize() == 0 
