import pytest
from unittest.mock import patch, MagicMock
from utils import FFmpegThreadManager, get_ffmpeg_thread_count, get_system_info
import utils  # Import the module to clear cache

@pytest.fixture(autouse=True)
def clear_cache():
    """Clear the LRU cache before each test"""
    get_system_info.cache_clear()
    yield

@pytest.fixture
def mock_system_info():
    """Fixture to provide mock system info with 8 cores and 16GB RAM"""
    return {
        'cpu_count': 8,
        'total_memory': 16 * (1024 ** 3),  # 16GB in bytes
        'platform': 'darwin'
    }

@pytest.fixture
def thread_manager():
    """Fixture to provide a clean thread manager instance"""
    return FFmpegThreadManager()

def test_thread_count_ci_environment():
    """Test thread count calculation in CI environment"""
    with patch('utils.get_system_info') as mock_info:
        # Test with different CPU counts in CI
        test_cases = [
            {'cpu_count': 1, 'memory': 8 * (1024**3), 'expected': 2},  # Minimum 2 threads
            {'cpu_count': 2, 'memory': 8 * (1024**3), 'expected': 2},
            {'cpu_count': 4, 'memory': 8 * (1024**3), 'expected': 4},
            {'cpu_count': 8, 'memory': 8 * (1024**3), 'expected': 4},  # Max 4 threads in CI
            # Test memory constraint cases
            {'cpu_count': 4, 'memory': 3 * (1024**3), 'expected': 2},  # < 4GB RAM
        ]
        
        for case in test_cases:
            get_system_info.cache_clear()  # Clear cache before each case
            mock_info.return_value = {
                'cpu_count': case['cpu_count'],
                'total_memory': case['memory'],
                'platform': 'linux'
            }
            thread_count = get_ffmpeg_thread_count(is_ci=True)
            assert thread_count == case['expected'], \
                f"CI with {case['cpu_count']} cores and {case['memory']/(1024**3)}GB RAM should use {case['expected']} threads"

def test_thread_count_production():
    """Test thread count calculation in production environment"""
    with patch('utils.get_system_info') as mock_info:
        test_cases = [
            {'cpu_count': 4, 'expected': 6},    # 4 cores -> 6 threads (1.5x)
            {'cpu_count': 12, 'expected': 16},  # 12 cores -> 16 threads (capped)
            {'cpu_count': 24, 'expected': 16},  # 24 cores -> 16 threads (capped)
            {'cpu_count': 1, 'expected': 1},    # Single core -> 1 thread
        ]
        
        for case in test_cases:
            get_system_info.cache_clear()  # Clear cache before each case
            mock_info.return_value = {
                'cpu_count': case['cpu_count'],
                'total_memory': 16 * (1024**3),
                'platform': 'linux'
            }
            thread_count = get_ffmpeg_thread_count(is_ci=False)
            assert thread_count == case['expected'], \
                f"Production with {case['cpu_count']} cores should use {case['expected']} threads"

def test_concurrent_operations():
    """Test thread allocation with concurrent operations"""
    thread_manager = FFmpegThreadManager()
    
    # First operation should get full thread count
    with thread_manager:
        thread_count = thread_manager.get_threads_for_operation()
        assert thread_count >= 2, "Should get at least 2 threads for first operation"
        first_thread_count = thread_count
    
    # Test multiple concurrent operations
    thread_counts = []
    with thread_manager:
        thread_counts.append(thread_manager.get_threads_for_operation())
        with thread_manager:
            thread_counts.append(thread_manager.get_threads_for_operation())
            with thread_manager:
                thread_counts.append(thread_manager.get_threads_for_operation())
    
    # Verify thread distribution
    assert all(count >= 2 for count in thread_counts), "All operations should get at least 2 threads"
    assert thread_counts[0] > thread_counts[1] > thread_counts[2], "Thread counts should decrease with more operations"
    assert thread_counts[0] <= first_thread_count, "Concurrent operations should not exceed initial thread count"
    
    # Verify reasonable thread distribution
    assert thread_counts[0] >= thread_counts[1] * 1.5, "First concurrent operation should get significantly more threads"
    assert thread_counts[1] >= thread_counts[2] * 1.5, "Second concurrent operation should get significantly more threads"

def test_max_concurrent_operations(mock_system_info):
    """Test maximum concurrent operations calculation"""
    with patch('utils.get_system_info', return_value=mock_system_info):
        manager = FFmpegThreadManager()
        max_concurrent = manager._determine_max_concurrent()
        
        # With 8 cores:
        # - Reserved cores = max(2, 8 * 0.1) = 2
        # - Available cores = 8 - 2 = 6
        # - Max concurrent = 6 / (8 * 1.5) ≈ 0.5, rounded up to 1
        assert max_concurrent >= 1, "Should allow at least 1 concurrent operation"
        assert max_concurrent <= 6, "Should not exceed I/O bottleneck limit"

def test_thread_manager_cleanup(thread_manager):
    """Test that thread manager properly cleans up after operations"""
    initial_operations = thread_manager._active_operations
    
    # Test normal exit
    with thread_manager:
        assert thread_manager._active_operations == initial_operations + 1
    assert thread_manager._active_operations == initial_operations
    
    # Test exception case
    try:
        with thread_manager:
            assert thread_manager._active_operations == initial_operations + 1
            raise Exception("Test exception")
    except Exception:
        pass
    assert thread_manager._active_operations == initial_operations, "Should clean up even after exception"

@patch('utils.get_system_info')
def test_thread_manager_concurrent_access(mock_info):
    """Test thread manager under concurrent access"""
    # Mock system info consistently
    mock_info.return_value = {
        'cpu_count': 8,
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
    assert all(count >= 2 for count in thread_counts), "All operations should get at least 2 threads"
    assert len(set(thread_counts)) >= 2, "Thread counts should be distributed"
    assert max(thread_counts) >= min(thread_counts) * 2, "Should have significant thread count variation" 
