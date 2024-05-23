import json
import os
import sys
from dotenv import load_dotenv

ganlgia_home = os.getenv('GANGLIA_HOME')
if not ganlgia_home:
    raise EnvironmentError("Environment variable 'GANGLIA_HOME' is not set.")

# Add GANGLIA_HOME to sys.path to resolve imports
sys.path.insert(0, ganlgia_home)

from lyrics_lib import LyricsGenerator
from query_dispatch import ChatGPTQueryDispatcher
from logger import Logger

# Load environment variables from .env file
load_dotenv()

def main():
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        raise EnvironmentError("Environment variable 'OPENAI_API_KEY' is not set.")
    
    story_text = (
        "This is a story about a brave knight named Stephanie, a dragon named Steve, "
        "and their shared love of Philadelphia. They traveled with their friends Arthur, "
        "Bella, and Cassandra to the mystical land of Eldoria. There they met Eldon the wise, "
        "Fiona the fierce, and Gregory the giant, who helped them on their quest to find the "
        "lost city of Atlantis."
    )
    proper_nouns = ["Stephanie", "Steve", "Philadelphia", "Arthur", "Bella", "Cassandra", "Eldoria", "Eldon", "Fiona", "Gregory"]

    query_dispatcher = ChatGPTQueryDispatcher()
    lyrics_generator = LyricsGenerator()

    result = lyrics_generator.generate_song_lyrics(
        story_text, query_dispatcher, 
        song_context="theme song for the closing credits of a movie - you know - the kind that sums up the movie. Good examples are the MC Hammer Addams Family song and I'll Remember from With Honors"
    )

    # Check that the result is in the expected JSON format
    try:
        lyrics_json = json.loads(result)
        lyrics = lyrics_json["lyrics"]
    except json.JSONDecodeError:
        Logger.print_error("Result is not in valid JSON format")
        return

    # Print the input story and output lyrics
    print(f"Input story: {story_text}")
    print(f"Output lyrics: {lyrics}")

    # Check that the lyrics are not empty and are different from the story text
    assert lyrics != "", "Lyrics should not be empty"
    assert lyrics != story_text, "Lyrics should not be the same as the story text"

    # Check that at least 8 out of 10 proper nouns from the story text are in the lyrics
    found_nouns = [noun for noun in proper_nouns if noun in lyrics]
    assert len(found_nouns) >= 8, f"At least 8 proper nouns should be in the lyrics, found: {found_nouns}"

    # Check that the proper nouns are not presented in the exact same order as in the story
    story_order = [noun for noun in proper_nouns if noun in story_text]
    lyrics_order = [noun for noun in proper_nouns if noun in lyrics]
    assert story_order != lyrics_order, "Proper nouns should not be in the same order as in the story"

    Logger.print_info("All checks passed successfully.")

if __name__ == "__main__":
    main()
