import pytest
from query_dispatch import ChatGPTQueryDispatcher

def test_load_git_repo_into_history():
    dispatcher = ChatGPTQueryDispatcher(pre_prompt="Test pre-prompt")
    token_count = dispatcher.count_tokens()

    assert isinstance(token_count, int)
    assert token_count > 0
