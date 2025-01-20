"""Tests for audio alignment functionality."""

import sys
sys.path.append("..")  # Add parent directory to Python path
# pylint: disable=import-error,wrong-import-position
from tts import GoogleTTS
import os
from ttv.audio_alignment import align_words_with_audio, create_word_level_captions
import pytest
import wave
import numpy as np
import whisper

def test_word_alignment():
    # Create test audio using TTS
    tts = GoogleTTS()
    test_text = "This is a test sentence for word alignment"
    success, audio_path = tts.convert_text_to_speech(test_text)
    assert success and audio_path is not None, "Failed to generate test audio"

    try:
        # Test word alignment
        word_timings = align_words_with_audio(audio_path, test_text)
        assert word_timings is not None, "Failed to generate word timings"
        assert len(word_timings) > 0, "No word timings generated"
        
        # Verify words are in order and have valid timings
        for i in range(len(word_timings) - 1):
            assert word_timings[i].end <= word_timings[i + 1].start, "Word timings are not in order"
            assert word_timings[i].start >= 0, "Invalid start time"
            assert word_timings[i].end > word_timings[i].start, "Invalid timing duration"
    finally:
        # Cleanup
        if os.path.exists(audio_path):
            os.remove(audio_path)

def test_caption_generation_from_audio():
    # Create test audio using TTS
    tts = GoogleTTS()
    test_text = "Testing caption generation from audio file"
    success, audio_path = tts.convert_text_to_speech(test_text)
    assert success and audio_path is not None, "Failed to generate test audio"

    try:
        # Test caption generation
        captions = create_word_level_captions(audio_path, test_text)
        assert captions is not None, "Failed to generate captions"
        assert len(captions) > 0, "No captions generated"
        
        # Verify caption timings are in order
        for i in range(len(captions) - 1):
            assert captions[i].end_time <= captions[i + 1].start_time, "Caption timings are not in order"
            assert captions[i].start_time >= 0, "Invalid start time"
            assert captions[i].end_time > captions[i].start_time, "Invalid timing duration"
    finally:
        # Cleanup
        if os.path.exists(audio_path):
            os.remove(audio_path)

def test_closing_credits_with_music():
    """Test word alignment with the closing credits song."""
    try:
        print("\nTesting closing credits song transcription:")
        music_path = "tests/ttv/test_data/closing_credits.mp3"
        
        # Use base model as it provides cleaner transcription
        model = whisper.load_model("base", device="cpu")
        result = model.transcribe(
            music_path,
            language="en",
            word_timestamps=True,
            fp16=False
        )
        
        assert result and "text" in result, "Failed to transcribe closing credits"
        transcribed_text = result["text"].strip()
        
        # Validate key aspects of the transcription
        assert transcribed_text.lower().startswith("in the quiet of a shadowed room"), "Unexpected start of lyrics"
        assert "in every flutter eternity" in transcribed_text.lower(), "Missing expected ending lyrics"
        
        # Get word timings
        word_timings = align_words_with_audio(music_path, transcribed_text)
        assert word_timings is not None, "Failed to generate word timings"
        assert len(word_timings) > 150, "Expected at least 150 words in the song"  # Based on previous runs
        
        # Verify word timing order and non-negative times
        for i in range(len(word_timings) - 1):
            assert word_timings[i].start >= 0, "Invalid start time"
            assert word_timings[i].end >= word_timings[i].start, "End time before start time"
            assert word_timings[i].end <= word_timings[i + 1].start, "Word timings are not in order"

    except FileNotFoundError:
        print("Test data file not found. Please ensure tests/ttv/test_data/closing_credits.mp3 exists.")
        assert False, "Test data file not found" 