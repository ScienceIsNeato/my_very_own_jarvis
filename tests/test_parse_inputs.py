import pytest
import argparse
from parse_inputs import parse_args, parse_tts_interface
from tts import GoogleTTS, NaturalReadersTTS

def test_parse_tts_interface():
    assert isinstance(parse_tts_interface("google"), GoogleTTS)
    assert isinstance(parse_tts_interface("natural_reader"), NaturalReadersTTS)
    with pytest.raises(ValueError):
        parse_tts_interface("invalid_interface")

def test_parse_args():
    args = ["--device-index", "2", "--tts-interface", "natural_reader", "--suppress-session-logging", "--enable-turn-indicators"]
    parsed_args = parse_args(args)

    assert parsed_args.device_index == 2
    assert parsed_args.tts_interface == "natural_reader"
    assert parsed_args.suppress_session_logging is True
    assert parsed_args.enable_turn_indicators is True

if __name__ == "__main__":
    pytest.main()