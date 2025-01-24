import sys
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).resolve().parent.parent))

from query_dispatch import ChatGPTQueryDispatcher

@pytest.mark.unit
def test_sendQuery():
    expected_in_response = "Paris"
    query_dispatcher = ChatGPTQueryDispatcher()

    test_prompt = "What is the capital of France?"

    print("Query: ", test_prompt)

    # Call the sendQuery function without mocking
    response = query_dispatcher.sendQuery(test_prompt)

    print("response: ", response)
    print("expected_in_response: ", expected_in_response)

    # Assertions based on the expected response
    assert expected_in_response in response