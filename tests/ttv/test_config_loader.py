"""Test the TTV config loader."""

import unittest
import os
from ttv.config_loader import load_input, TTVConfig, MusicConfig, ClosingCreditsConfig

class TestConfigLoader(unittest.TestCase):
    """Test cases for TTV config loading."""

    def test_load_file_based_config(self):
        """Test loading a config that uses file-based resources."""
        config_path = os.path.join("tests", "ttv", "test_data", "file_based_config.json")
        result = load_input(config_path)

        # Check basic fields
        self.assertIsInstance(result, TTVConfig)
        self.assertEqual(result.style, "digital art")
        self.assertEqual(len(result.story), 3)
        self.assertEqual(result.title, "The Curious Cat")
        self.assertEqual(result.caption_style, "static")

        # Check background music config
        self.assertIsInstance(result.background_music, MusicConfig)
        self.assertEqual(result.background_music.file, "tests/ttv/test_data/background_music.mp3")
        self.assertIsNone(result.background_music.prompt)

        # Check closing credits config
        self.assertIsInstance(result.closing_credits, ClosingCreditsConfig)
        self.assertEqual(result.closing_credits.music.file, "tests/ttv/test_data/closing_credits.mp3")
        self.assertIsNone(result.closing_credits.music.prompt)
        self.assertIsNone(result.closing_credits.poster.file)
        self.assertEqual(
            result.closing_credits.poster.prompt,
            "A curious black cat watching a red butterfly, digital art style"
        )

    def test_load_prompt_based_config(self):
        """Test loading a config that uses prompt-based resources."""
        config_path = os.path.join("tests", "ttv", "test_data", "prompt_based_config.json")
        result = load_input(config_path)

        # Check basic fields
        self.assertIsInstance(result, TTVConfig)
        self.assertEqual(result.style, "digital art")
        self.assertEqual(len(result.story), 3)
        self.assertEqual(result.title, "The Curious Cat")
        self.assertEqual(result.caption_style, "dynamic")

        # Check background music config
        self.assertIsInstance(result.background_music, MusicConfig)
        self.assertIsNone(result.background_music.file)
        self.assertEqual(
            result.background_music.prompt,
            "Create ambient electronic music that captures the curiosity of a cat"
        )

        # Check closing credits config
        self.assertIsInstance(result.closing_credits, ClosingCreditsConfig)
        self.assertIsNone(result.closing_credits.music.file)
        self.assertEqual(
            result.closing_credits.music.prompt,
            "Create upbeat celebratory music with cat-themed lyrics"
        )
        self.assertIsNone(result.closing_credits.poster.file)
        self.assertEqual(
            result.closing_credits.poster.prompt,
            "A curious black cat watching a red butterfly, digital art style"
        )

if __name__ == "__main__":
    unittest.main() 