import unittest
import json
from unittest.mock import Mock, patch
from ttv.story_processor import process_story
from ttv.config_loader import TTVConfig, MusicConfig
from query_dispatch import ChatGPTQueryDispatcher

class TestStoryProcessor(unittest.TestCase):
    def test_closing_credits_prompt_used(self):
        """Test that the closing credits prompt from config is used when generating music."""
        # Mock dependencies
        mock_tts = Mock()
        mock_tts.convert_text_to_speech.return_value = (True, "/tmp/GANGLIA/tts/test_audio.mp3")
        mock_query_dispatcher = Mock(spec=ChatGPTQueryDispatcher)
        mock_music_gen = Mock()
        
        # Set up mock responses
        mock_query_dispatcher.sendQuery.return_value = json.dumps({
            "filtered_text": "Test filtered text",
            "is_safe": True
        })

        # Create a test config with a specific closing credits prompt
        test_config = TTVConfig(
            style="test style",
            story=["Test story line 1", "Test story line 2"],
            title="Test Title",
            closing_credits=MusicConfig(
                prompt="Test closing credits prompt"
            )
        )

        with patch('ttv.story_processor.MusicGenerator', return_value=mock_music_gen):
            # Call process_story
            process_story(
                mock_tts,
                test_config.style,
                test_config.story,
                skip_generation=False,
                query_dispatcher=mock_query_dispatcher,
                story_title=test_config.title,
                config=test_config
            )

            # Verify that the closing credits prompt was used
            mock_music_gen.generate_music.assert_called_with(
                prompt="Test closing credits prompt",
                model="chirp-v3-0",
                duration=30,
                with_lyrics=True,
                story_text="\n".join(test_config.story),
                query_dispatcher=mock_query_dispatcher
            )

if __name__ == '__main__':
    unittest.main() 