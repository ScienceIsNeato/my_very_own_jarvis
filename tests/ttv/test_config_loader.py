import unittest
import json
import os
from ttv.config_loader import load_input

class TestConfigLoader(unittest.TestCase):
    def setUp(self):
        self.test_data_dir = os.path.join(os.path.dirname(__file__), "test_data")
        
    def test_basic_config_loading(self):
        """Test loading a basic valid config with required fields."""
        config_path = os.path.join(self.test_data_dir, "file_based_config.json")
        result = load_input(config_path)
        self.assertEqual(result.style, "digital art")
        self.assertEqual(result.story, [
            "A small black cat sat by the window.",
            "She watched the birds flutter past with curious eyes.",
            "Suddenly, a bright red butterfly caught her attention."
        ])
        self.assertEqual(result.title, "The Curious Cat")
        self.assertIsNotNone(result.background_music)
        self.assertEqual(result.background_music.sources[0].type, "file")
        self.assertTrue(result.background_music.sources[0].enabled)
        self.assertIsNotNone(result.closing_credits)
        self.assertEqual(result.closing_credits.sources[0].type, "file")
        self.assertTrue(result.closing_credits.sources[0].enabled)

    def test_missing_required_fields(self):
        """Test that appropriate errors are raised for missing required fields."""
        invalid_configs = [
            {},  # Empty config
            {"style": "digital art"},  # Missing title and story
            {"style": "digital art", "story": []},  # Missing title
            {"title": "Test", "story": []}  # Missing style
        ]
        
        for config in invalid_configs:
            config_path = os.path.join(self.test_data_dir, "temp_config.json")
            with open(config_path, "w", encoding='utf-8') as f:
                json.dump(config, f)
            with self.assertRaises(KeyError):
                load_input(config_path)
            os.remove(config_path)
                
    def test_music_config_loading(self):
        """Test loading config with optional music settings."""
        config_path = os.path.join(self.test_data_dir, "file_based_config.json")
        result = load_input(config_path)
        # Test music configs
        self.assertIsNotNone(result.background_music)
        self.assertEqual(result.background_music.sources[0].type, "file")
        self.assertEqual(result.background_music.sources[0].path, "tests/ttv/test_data/background_music.mp3")
        self.assertTrue(result.background_music.sources[0].enabled)
        
        self.assertIsNotNone(result.closing_credits)
        self.assertEqual(result.closing_credits.sources[0].type, "file")
        self.assertEqual(result.closing_credits.sources[0].path, "tests/ttv/test_data/closing_credits.mp3")
        self.assertTrue(result.closing_credits.sources[0].enabled)

    def test_config_unpacking(self):
        """Test that the config can be unpacked into style, story, and title."""
        config_path = os.path.join(self.test_data_dir, "file_based_config.json")
        result = load_input(config_path)
        # This is how ttv.py tries to use the result
        style, story, story_title = result
        self.assertEqual(style, "digital art")
        self.assertEqual(story, [
            "A small black cat sat by the window.",
            "She watched the birds flutter past with curious eyes.",
            "Suddenly, a bright red butterfly caught her attention."
        ])
        self.assertEqual(story_title, "The Curious Cat")

    def test_prompt_based_config_loading(self):
        """Test loading of prompt-based music config"""
        config_path = "tests/ttv/test_data/prompt_based_config.json"
        result = load_input(config_path)
        self.assertIsNotNone(result.background_music)
        self.assertEqual(result.background_music.sources[0].type, "prompt")
        self.assertTrue(result.background_music.sources[0].enabled)
        self.assertIsNotNone(result.closing_credits)
        self.assertEqual(result.closing_credits.sources[0].type, "prompt")
        self.assertTrue(result.closing_credits.sources[0].enabled)

if __name__ == "__main__":
    unittest.main() 