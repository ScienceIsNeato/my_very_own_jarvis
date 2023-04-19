import pytest
from jarvis_utils import sendQueryToServer

def test_sendQueryToServer():
    test_prompt = "What is the capital of France?"

    # Call the sendQueryToServer function without mocking
    response = sendQueryToServer(test_prompt)

    # Assertions based on the expected response
    assert "Paris" in response