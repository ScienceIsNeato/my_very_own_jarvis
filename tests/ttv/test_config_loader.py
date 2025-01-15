import unittest
import json
import os
import tempfile
from ttv.config_loader import load_input

class TestConfigLoader(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        
    def create_test_config(self, config_data):
        config_path = os.path.join(self.temp_dir, "test_config.json")
        with open(config_path, "w", encoding='utf-8') as f:
            json.dump(config_data, f)
        return config_path
        
    def test_basic_config_loading(self):
        """Test loading a basic valid config with required fields."""
        config = {
            "style": "digital art",
            "title": "Test Story",
            "story": ["Line 1", "Line 2"]
        }
        config_path = self.create_test_config(config)
        result = load_input(config_path)
        self.assertEqual(result.style, "digital art")
        self.assertEqual(result.story, ["Line 1", "Line 2"])
        self.assertEqual(result.title, "Test Story")
        
    def test_missing_required_fields(self):
        """Test that appropriate errors are raised for missing required fields."""
        invalid_configs = [
            {},  # Empty config
            {"style": "digital art"},  # Missing title and story
            {"style": "digital art", "story": []},  # Missing title
            {"title": "Test", "story": []}  # Missing style
        ]
        
        for config in invalid_configs:
            config_path = self.create_test_config(config)
            with self.assertRaises(KeyError):
                load_input(config_path)
                
    def test_music_config_loading(self):
        """Test loading config with optional music settings."""
        config = {
            "style": "digital art",
            "title": "Test Story",
            "story": ["Line 1"],
            "background_music": {
                "sources": [
                    {
                        "type": "file",
                        "path": "tests/test_data/background_music.mp3",
                        "enabled": True
                    }
                ]
            },
            "closing_credits": {
                "sources": [
                    {
                        "type": "prompt",
                        "prompt": "epic rock song",
                        "enabled": True
                    }
                ]
            }
        }
        config_path = self.create_test_config(config)
        result = load_input(config_path)
        # Current implementation should still work with additional fields
        self.assertEqual(result.style, "digital art")
        self.assertEqual(result.story, ["Line 1"])
        self.assertEqual(result.title, "Test Story")
        # Test music configs
        self.assertIsNotNone(result.background_music)
        self.assertEqual(result.background_music.sources[0].type, "file")
        self.assertEqual(result.background_music.sources[0].path, "tests/test_data/background_music.mp3")
        self.assertTrue(result.background_music.sources[0].enabled)
        
        self.assertIsNotNone(result.closing_credits)
        self.assertEqual(result.closing_credits.sources[0].type, "prompt")
        self.assertEqual(result.closing_credits.sources[0].prompt, "epic rock song")
        self.assertTrue(result.closing_credits.sources[0].enabled)

if __name__ == "__main__":
    unittest.main() 