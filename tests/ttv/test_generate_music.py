import os
import subprocess
from datetime import datetime
from logger import Logger
from music_lib import MusicGenerator
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def main():
    suno_api_key = os.getenv('SUNO_API_KEY')
    if not suno_api_key:
        raise EnvironmentError("Environment variable 'SUNO_API_KEY' is not set.")
    
    prompt = "background music for a Ken Burns documentary, meaning somber civil war era music"

    music_gen = MusicGenerator()

    # Generate music without lyrics
    audio_path = music_gen.generate_music(
        prompt=prompt,
        model="chirp-v3-0",
        duration=20,
        with_lyrics=False,  # Generate music without lyrics
    )

    if not audio_path:
        Logger.print_error("Failed to generate audio.")
        return

    # Print the result
    print(f"Generated audio path: {audio_path}")

    # Assert that the audio path is not empty and that the file exists
    assert audio_path, "Audio path should not be empty"
    assert os.path.exists(audio_path), "Audio file should exist at the given path"

    Logger.print_info("Music generation test passed successfully.")

    # Play the audio using ffplay
    try:
        subprocess.run(["ffplay", "-nodisp", "-autoexit", audio_path], check=True)
    except (OSError, subprocess.SubprocessError) as e:
        Logger.print_error(f"Failed to play audio: {e}")

if __name__ == "__main__":
    main()
