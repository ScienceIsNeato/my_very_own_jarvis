import pytest
import os
from query_dispatch import ChatGPTQueryDispatcher
from utils import get_config_path

@pytest.mark.unit
def test_load_git_repo_into_history():
    dispatcher = ChatGPTQueryDispatcher(pre_prompt="Test pre-prompt")
    token_count = dispatcher.count_tokens()

    assert isinstance(token_count, int)
    assert token_count > 0

def test_query_dispatcher_init():
    dispatcher = ChatGPTQueryDispatcher(pre_prompt="Test pre-prompt", config_file_path=get_config_path())
    assert dispatcher.messages == [{"role": "system", "content": "Test pre-prompt"}]
