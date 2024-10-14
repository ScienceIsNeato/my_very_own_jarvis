import unittest
import os
from tts import GoogleTTS

class TestGoogleTTS(unittest.TestCase):
    def test_convert_text_to_speech(self):
        tts_instance = GoogleTTS()

        # Abraham Lincoln quotes
        quotes = [
            "I am a slow walker, but I never walk back.",
            "The best way to predict the future is to create it.",
            "Whatever you are, be a good one.",
            "Give me six hours to chop down a tree and I will spend the first four sharpening the axe."
        ]

        # List to store file paths for cleanup
        generated_files = []
        
        for quote in quotes:
            # Convert text to speech
            success, file_path = tts_instance.convert_text_to_speech(quote)
            
            # Verify that the conversion was successful
            self.assertTrue(success, "Text-to-speech conversion failed.")
            
            # Verify that the file was created
            self.assertTrue(os.path.isfile(file_path), f"Audio file not created for quote: {quote}")
            
            # Append file path for cleanup
            generated_files.append(file_path)
            
            # Print the file path
            print(f"Generated audio file for quote: '{quote}'")
            print(f"File path: {file_path}")

if __name__ == '__main__':
    unittest.main()
