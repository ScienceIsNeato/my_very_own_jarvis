import unittest
from unittest.mock import Mock, patch, MagicMock
import json
import os
from ttv.story_generation import generate_filtered_story, generate_movie_poster, filter_text, save_image_without_caption

class TestStoryGeneration(unittest.TestCase):
    def setUp(self):
        self.query_dispatcher = Mock()
        self.context = "A story about a friendly robot"
        self.style = "science fiction"
        self.story_title = "Robot Dreams"

    def test_generate_filtered_story_success(self):
        # Mock response from query dispatcher
        mock_response = json.dumps({
            "style": "science fiction",
            "title": "Robot Dreams",
            "story": "A heartwarming tale about an AI learning about friendship"
        })
        self.query_dispatcher.sendQuery.return_value = mock_response

        result = generate_filtered_story(self.context, self.style, self.story_title, self.query_dispatcher)
        result_json = json.loads(result)

        self.assertIn("style", result_json)
        self.assertIn("title", result_json)
        self.assertIn("story", result_json)
        self.query_dispatcher.sendQuery.assert_called_once()

    def test_generate_filtered_story_failure(self):
        # Mock an exception from query dispatcher
        self.query_dispatcher.sendQuery.side_effect = Exception("API Error")

        result = generate_filtered_story(self.context, self.style, self.story_title, self.query_dispatcher)
        result_json = json.loads(result)

        self.assertEqual(result_json["story"], "No story generated")
        self.assertEqual(result_json["style"], self.style)
        self.assertEqual(result_json["title"], self.story_title)

    @patch('openai.Image.create')
    def test_generate_movie_poster_success(self, mock_create):
        # Mock OpenAI response
        mock_response = MagicMock()
        mock_response.data = [{'url': 'http://example.com/image.png'}]
        mock_create.return_value = mock_response

        filtered_story = json.dumps({
            "style": "science fiction",
            "title": "Robot Dreams",
            "story": "A heartwarming tale about an AI"
        })

        with patch('ttv.story_generation.save_image_without_caption') as mock_save:
            result = generate_movie_poster(filtered_story, self.style, self.story_title, self.query_dispatcher)
            
            self.assertIsNotNone(result)
            mock_create.assert_called_once()
            mock_save.assert_called_once()

    def test_filter_text_success(self):
        mock_response = '{"text": "A friendly robot learns about human emotions"}'
        self.query_dispatcher.sendQuery.return_value = mock_response

        result = filter_text(
            "A robot learns about emotions",
            self.context,
            self.style,
            self.query_dispatcher
        )

        self.assertIn("text", result)
        self.query_dispatcher.sendQuery.assert_called_once()

    @patch('requests.get')
    def test_save_image_without_caption(self, mock_get):
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b"fake image content"
        mock_get.return_value = mock_response

        test_filename = "/tmp/test_image.png"
        
        with patch('builtins.open', unittest.mock.mock_open()) as mock_file:
            save_image_without_caption("http://example.com/image.png", test_filename)
            mock_get.assert_called_once_with("http://example.com/image.png", timeout=30)
            mock_file.assert_called_once_with(test_filename, 'wb')

if __name__ == '__main__':
    unittest.main() 