import pytest

def pytest_configure(config):
    """Register custom marks."""
    config.addinivalue_line(
        "markers",
        "musicgen: mark test as a musicgen model test"
    ) 