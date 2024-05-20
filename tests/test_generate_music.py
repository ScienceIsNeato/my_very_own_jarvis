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
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def main():
    api_key = os.getenv('OPENAI_API_KEY')
    suno_api_key = os.getenv('SUNO_API_KEY')
    if not api_key:
        raise EnvironmentError("Environment variable 'OPENAI_API_KEY' is not set.")
    if not suno_api_key:
        raise EnvironmentError("Environment variable 'SUNO_API_KEY' is not set.")
    
    prompt = "background music for a Ken Burns documentary, meaning somber civil war era music"
    story_text = (
        "This is a story about a brave knight named Stephanie, a dragon named Steve, "
        "and their shared love of Philadelphia. They traveled with their friends Arthur, "
        "Bella, and Cassandra to the mystical land of Eldoria. There they met Eldon the wise, "
        "Fiona the fierce, and Gregory the giant, who helped them on their quest to find the "
        "lost city of Atlantis."
    )

    query_dispatcher = ChatGPTQueryDispatcher()
    music_gen = MusicGenerator()

    result = music_gen.generate_music(
        prompt=prompt,
        model="chirp-v3-0",
        duration=20,
        with_lyrics=True,
        story_text=story_text,
        query_dispatcher=query_dispatcher
    )

    # Check if the result is a path to an audio file
    if isinstance(result, str) and os.path.isfile(result):
        Logger.print_info(f"Audio file generated successfully: {result}")
    else:
        Logger.print_error(f"Failed to generate audio: {result}")

    # Print the output
    print(f"Result: {result}")

if __name__ == "__main__":
    main()
