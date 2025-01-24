import argparse
import pytest
from parse_inputs import parse_args, parse_tts_interface
from tts import GoogleTTS

@pytest.mark.unit
def test_parse_tts_interface():
    assert isinstance(parse_tts_interface("google"), GoogleTTS)
    with pytest.raises(ValueError):
        parse_tts_interface("invalid_interface")

@pytest.mark.unit
def test_parse_args():
    args = ["--device-index", "2", "--tts-interface", "google", "--suppress-session-logging", "--enable-turn-indicators"]
    parsed_args = parse_args(args)

    assert parsed_args.device_index == 2
    assert parsed_args.tts_interface == "google"
    assert parsed_args.suppress_session_logging is True
    assert parsed_args.enable_turn_indicators is True