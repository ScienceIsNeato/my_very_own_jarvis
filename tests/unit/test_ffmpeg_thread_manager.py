"""Tests for FFmpeg thread management functionality.

This module contains tests that verify the FFmpeg thread manager's ability to:
- Calculate appropriate thread counts based on system resources
- Handle concurrent FFmpeg operations
- Manage operation queues and cancellations
- Adapt to different environments (CI, local, production)
"""

# Standard library imports
import queue
import threading
import time
from unittest.mock import patch

# Third-party imports
import pytest

# Local imports
from utils import FFmpegThreadManager, get_ffmpeg_thread_count

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
def thread_mgr():
    """Fixture providing a clean FFmpegThreadManager instance."""
    manager = FFmpegThreadManager()
    yield manager
    manager.cleanup()

def test_init(thread_mgr):
    """Test initialization of FFmpegThreadManager."""
    assert isinstance(thread_mgr, FFmpegThreadManager)
    assert isinstance(thread_mgr.active_operations, list)
    assert isinstance(thread_mgr.operation_queue, queue.Queue)

def test_get_threads_for_operation(thread_mgr):
    """Test thread count calculation for operations."""
    thread_count = thread_mgr.get_threads_for_operation()
    assert thread_count > 0
    assert thread_count <= get_ffmpeg_thread_count()

def test_context_manager(thread_mgr):
    """Test using FFmpegThreadManager as a context manager."""
    with thread_mgr:
        assert len(thread_mgr.active_operations) == 1
    assert len(thread_mgr.active_operations) == 0

def test_concurrent_operations(thread_mgr):
    """Test handling of concurrent FFmpeg operations."""
    with thread_mgr:
        assert len(thread_mgr.active_operations) == 1
        with thread_mgr:
            assert len(thread_mgr.active_operations) == 2
        assert len(thread_mgr.active_operations) == 1
    assert len(thread_mgr.active_operations) == 0

def test_error_handling(thread_mgr):
    """Test handling of FFmpeg operation errors."""
    try:
        with thread_mgr:
            raise ValueError("Test error")
    except ValueError:
        pass
    assert len(thread_mgr.active_operations) == 0
    assert thread_mgr.operation_queue.empty()

def test_resource_cleanup(thread_mgr):
    """Test resource cleanup after operations."""
    with thread_mgr:
        pass
    assert len(thread_mgr.active_operations) == 0
    assert thread_mgr.operation_queue.empty()

def test_thread_count_ci_environment():
    """Test thread count calculation in CI environment."""
    with patch('os.environ.get') as mock_env:
        mock_env.return_value = 'true'
        with patch('utils.get_system_info') as mock_sys:
            mock_sys.return_value = {
                'total_cores': 8,
                'total_memory': 32 * 1024 * 1024 * 1024,  # 32GB in bytes
                'platform': 'linux'
            }
            manager = FFmpegThreadManager()
            with manager:
                thread_count = manager.get_threads_for_operation()
                assert thread_count <= 4  # CI environment should limit threads

def test_thread_count_local_environment():
    """Test thread count calculation in local environment."""
    with patch('os.environ.get') as mock_env:
        mock_env.return_value = None
        with patch('utils.get_system_info') as mock_sys:
            mock_sys.return_value = {
                'total_cores': 8,
                'total_memory': 32 * 1024 * 1024 * 1024,  # 32GB in bytes
                'platform': 'linux'
            }
            manager = FFmpegThreadManager()
            with manager:
                thread_count = manager.get_threads_for_operation()
                assert thread_count > 0  # Local environment should use more threads

def test_memory_limit():
    """Test thread count adjustment based on memory limits."""
    with patch('utils.get_system_info') as mock_sys:
        mock_sys.return_value = {
            'total_cores': 8,
            'total_memory': 8 * 1024 * 1024 * 1024,  # 8GB in bytes
            'platform': 'linux'
        }
        manager = FFmpegThreadManager()
        with manager:
            thread_count = manager.get_threads_for_operation()
            assert thread_count <= 4  # Limited by memory

def test_thread_manager_cleanup(thread_mgr):
    """Test that thread manager properly cleans up after operations"""
    with thread_mgr:
        assert len(thread_mgr.active_operations) == 1
    assert len(thread_mgr.active_operations) == 0
    assert thread_mgr.operation_queue.empty()

def test_thread_manager_concurrent_access():
    """Test thread manager under concurrent access"""
    manager = FFmpegThreadManager()
    threads = []
    results = queue.Queue()

    def worker():
        with manager:
            time.sleep(0.01)  # Small sleep to ensure overlap
            thread_count = manager.get_threads_for_operation()
            results.put(thread_count)

    # Start multiple threads simultaneously
    for _ in range(4):
        thread = threading.Thread(target=worker)
        thread.start()
        threads.append(thread)

    # Wait for all threads to complete
    for thread in threads:
        thread.join()

    # Verify results
    thread_counts = []
    while not results.empty():
        thread_counts.append(results.get())

    assert len(thread_counts) == 4, "All operations should complete"
    assert all(count > 0 for count in thread_counts), "Each operation should get threads"
    assert len(manager.active_operations) == 0, "All operations should be cleaned up"

def test_operation_completion():
    """Test successful completion of FFmpeg operations."""
    manager = FFmpegThreadManager()
    with manager:
        assert len(manager.active_operations) == 1
        time.sleep(0.1)  # Allow operation to complete
    assert len(manager.active_operations) == 0
    assert manager.operation_queue.empty()

def test_cleanup_with_active_operations(thread_mgr):
    """Test cleanup behavior with active operations."""
    with thread_mgr:
        pass  # Operation is started and completed
    thread_mgr.cleanup()
    assert len(thread_mgr.active_operations) == 0
    assert thread_mgr.operation_queue.empty()

if __name__ == "__main__":
    pytest.main(["-v", __file__])
