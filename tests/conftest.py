import pytest

def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers",
        "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers",
        "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers",
        "third_party: mark test as a third party integration test"
    )
    config.addinivalue_line(
        "markers",
        "costly: mark test as computationally expensive or time-consuming"
    )
    config.addinivalue_line(
        "markers",
        "smoke: mark test as a smoke test (key functionality with mocks)"
    )
