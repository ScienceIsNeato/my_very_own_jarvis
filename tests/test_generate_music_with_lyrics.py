import json
import os
import sys

# Add GANGLIA_HOME to sys.path to resolve imports
ganlgia_home = os.getenv('GANGLIA_HOME')
if not ganlgia_home:
    raise EnvironmentError("Environment variable 'GANGLIA_HOME' is not set.")

sys.path.insert(0, ganlgia_home)

from logger import Logger
from query_dispatch import ChatGPTQueryDispatcher
from music_lib import MusicGenerator
import sys
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def main():
    api_key = os.getenv('SUNO_API_KEY')
    if not api_key:
        raise EnvironmentError("Environment variable 'SUNO_API_KEY' is not set.")
    
    # Test case for generating music with lyrics
    story_text = (
        "This is a story about a brave knight named Stephanie, a dragon named Steve, "
        "and their shared love of Philadelphia. They traveled with their friends Arthur, "
        "Bella, and Cassandra to the mystical land of Eldoria. There they met Eldon the wise, "
        "Fiona the fierce, and Gregory the giant, who helped them on their quest to find the "
        "lost city of Atlantis."
    )
    proper_nouns = ["Stephanie", "Steve", "Philadelphia", "Arthur", "Bella", "Cassandra", "Eldon", "Fiona", "Gregory", "Atlantis"]
    
    query_dispatcher = ChatGPTQueryDispatcher()
    music_gen = MusicGenerator()
    
    result = music_gen.generate_music(
        prompt="background music for a Ken Burns documentary, meaning somber civil war era music",
        model="chirp-v3-0",
        duration=10,
        with_lyrics=True,
        story_text=story_text,
        query_dispatcher=query_dispatcher
    )

    # Check that the result is in the expected JSON format
    try:
        result_json = json.loads(result)
        audio_path = result_json.get("path")
    except json.JSONDecodeError:
        Logger.print_error("Result is not in valid JSON format")
        return

    # Print the result
    print(f"Generated audio path: {audio_path}")

    # Assert that the audio path is not empty and that the file exists
    assert audio_path, "Audio path should not be empty"
    assert os.path.exists(audio_path), "Audio file should exist at the given path"

    Logger.print_info("Music generation test passed successfully.")

if __name__ == "__main__":
    main()
