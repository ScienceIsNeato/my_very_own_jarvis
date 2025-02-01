"""Tests for the story processor module.

This module contains tests that verify the functionality of the story processor,
including:
- Story processing with file-based credits
- Image and movie poster generation
- Video segment creation
- Error handling and failure cases
"""

# Standard library imports
import json
import os
import unittest
from unittest.mock import Mock, patch, MagicMock

# Third-party imports
import pytest

# Local imports
from query_dispatch import ChatGPTQueryDispatcher
from ttv.config_loader import TTVConfig, MusicConfig
from ttv.story_processor import process_story
from utils import get_tempdir

@pytest.fixture
def tts_mock():
    """Provide a mock TTS instance for testing.
    
    Returns:
        MagicMock: A mock TTS instance that returns a test audio file path
    """
    mock = MagicMock()
    mock.convert_text_to_speech.return_value = (
        True, 
        os.path.join(get_tempdir(), "tts/test_audio.mp3")
    )
    return mock

class TestStoryProcessor(unittest.TestCase):
    """Test suite for the story processor module.
    
    Tests the end-to-end functionality of the story processor, including:
    - Story processing with file-based credits
    - Image and movie poster generation
    - Video segment creation
    - Error handling and failure cases
    """

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = get_tempdir()  # Use the base temp dir
        os.makedirs(os.path.join(self.temp_dir, "images"), exist_ok=True)
        os.makedirs(os.path.join(self.temp_dir, "tts"), exist_ok=True)
        os.makedirs(os.path.join(self.temp_dir, "ttv"), exist_ok=True)

    @patch('ttv.story_processor.generate_movie_poster')
    @patch('ttv.story_processor.generate_image')
    @patch('ttv.story_processor.create_video_segment')
    def test_story_processor_with_file_based_credits(
        self, mock_create_video, mock_generate_image, mock_generate_poster
    ):
        """Test story processor with file-based credits.
        
        Verifies that the story processor correctly handles all aspects of
        video generation when using file-based credits, including:
        - TTS conversion
        - Image generation
        - Movie poster generation
        - Video segment creation
        """
        # Mock dependencies
        mock_tts = Mock()
        mock_tts.convert_text_to_speech.return_value = (
            True, 
            os.path.join(self.temp_dir, "tts/test_audio.mp3")
        )
        mock_query_dispatcher = Mock(spec=ChatGPTQueryDispatcher)
        mock_music_gen = Mock()

        # Mock movie poster generation
        mock_generate_poster.return_value = os.path.join(
            self.temp_dir, "ttv", "movie_poster.png"
        )

        # Mock image generation for each sentence
        mock_generate_image.return_value = (
            os.path.join(self.temp_dir, "images", "test_image.png"), 
            True
        )

        # Mock video segment creation
        mock_create_video.return_value = True

        # Set up mock responses for content filtering
        mock_query_dispatcher.send_query.return_value = json.dumps({
            "filtered_text": "Test filtered text",
            "is_safe": True
        })

        # Create a test config with file-based closing credits
        test_config = TTVConfig(
            style="test style",
            story=["Test story line 1", "Test story line 2"],
            title="Test Title",
            closing_credits=MusicConfig(
                file="tests/unit/ttv/test_data/closing_credits.mp3",
                prompt=None
            )
        )

        with patch('ttv.story_processor.MusicGenerator', 
                  return_value=mock_music_gen):
            # Call process_story
            result = process_story(
                mock_tts,
                test_config.style,
                test_config.story,
                output_dir=self.temp_dir,  # Use the base temp dir
                skip_generation=False,
                query_dispatcher=mock_query_dispatcher,
                story_title=test_config.title,
                config=test_config
            )

            # Verify the overall result
            self.assertTrue(result, "Story processing should succeed")

            # Verify TTS calls
            expected_calls = len(test_config.story)
            self.assertEqual(
                mock_tts.convert_text_to_speech.call_count,
                expected_calls,
                "TTS should be called for each story line"
            )
            for i, story_line in enumerate(test_config.story):
                mock_tts.convert_text_to_speech.assert_any_call(
                    story_line,
                    thread_id=f"[Thread {i+1}/{len(test_config.story)}]"
                )

            # Verify that the movie poster was generated with correct parameters
            mock_generate_poster.assert_called_once_with(
                json.dumps({
                    "style": test_config.style,
                    "title": test_config.title,
                    "story": test_config.story
                }),
                test_config.style,
                test_config.title,
                mock_query_dispatcher,
                output_dir=self.temp_dir  # Use the base temp dir
            )

            # Verify that images were generated for each sentence
            self.assertEqual(
                mock_generate_image.call_count,
                len(test_config.story),
                "Image generation should be called for each story line"
            )
            mock_generate_image.assert_any_call(
                "Test story line 1",
                "",  # context
                test_config.style,
                0,  # index
                2,  # total_images
                mock_query_dispatcher,
                preloaded_images_dir=None,
                thread_id="[Thread 1/2]",
                output_dir=self.temp_dir  # Add output_dir parameter
            )
            mock_generate_image.assert_any_call(
                "Test story line 2",
                "",  # context
                test_config.style,
                1,  # index
                2,  # total_images
                mock_query_dispatcher,
                preloaded_images_dir=None,
                thread_id="[Thread 2/2]",
                output_dir=self.temp_dir  # Add output_dir parameter
            )

            # Verify that video segments were created with correct parameters
            self.assertEqual(
                mock_create_video.call_count,
                len(test_config.story),
                "Video segment creation should be called for each story line"
            )
            for i in range(len(test_config.story)):
                mock_create_video.assert_any_call(
                    os.path.join(self.temp_dir, "images", "test_image.png"),
                    os.path.join(self.temp_dir, "tts/test_audio.mp3"),
                    os.path.join(self.temp_dir, "ttv", f"segment_{i}_initial.mp4")
                )

            # Verify that music generation was NOT called for file-based credits
            mock_music_gen.generate_music.assert_not_called()

    @patch('ttv.story_processor.generate_movie_poster')
    @patch('ttv.story_processor.generate_image')
    @patch('ttv.story_processor.create_video_segment')
    def test_handles_generation_failures(
        self, mock_create_video, mock_generate_image, mock_generate_poster
    ):
        """Test that the story processor handles failures gracefully.
        
        Verifies proper error handling for various failure scenarios:
        - TTS conversion failure
        - Image generation failure
        - Movie poster generation failure
        - Video segment creation failure
        - Content filtering failure
        """
        # Mock dependencies with failures
        mock_failing_tts = Mock()
        mock_failing_tts.convert_text_to_speech.return_value = (False, None)
        mock_query_dispatcher = Mock(spec=ChatGPTQueryDispatcher)
        mock_music_gen = Mock()

        # Mock failures
        mock_generate_poster.return_value = None  # Poster generation failure
        mock_generate_image.return_value = (None, False)  # Image generation failure
        mock_create_video.return_value = False  # Video creation failure

        # Set up mock responses
        mock_query_dispatcher.send_query.return_value = json.dumps({
            "filtered_text": None,
            "is_safe": False  # Content filtering failure
        })

        test_config = TTVConfig(
            style="test style",
            story=["Test story line"],
            title="Test Title",
            closing_credits=MusicConfig(
                file="tests/unit/ttv/test_data/closing_credits.mp3",
                prompt=None
            )
        )

        with patch('ttv.story_processor.MusicGenerator', 
                  return_value=mock_music_gen):
            # Call process_story
            result = process_story(
                mock_failing_tts,
                test_config.style,
                test_config.story,
                output_dir=self.temp_dir,
                skip_generation=False,
                query_dispatcher=mock_query_dispatcher,
                story_title=test_config.title,
                config=test_config
            )

            # Verify that the result indicates failure
            self.assertIsInstance(result, tuple)
            self.assertTrue(
                all(x is None for x in result),
                "All result components should be None on failure"
            )

if __name__ == '__main__':
    unittest.main() 