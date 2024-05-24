import os
from logger import Logger
from lyrics_lib import LyricsGenerator
from suno_request_handler import SunoRequestHandler

class MusicGenerator:
    def __init__(self):
        self.api_key = os.getenv('SUNO_API_KEY')
        if not self.api_key:
            raise EnvironmentError("Environment variable 'SUNO_API_KEY' is not set.")

        self.lyrics_generator = LyricsGenerator()
        self.suno_request_handler = SunoRequestHandler()

    def generate_music(self, prompt, model="chirp-v3-0", duration=10, with_lyrics=False, story_text=None, retries=5, wait_time=60, query_dispatcher=None):
        Logger.print_debug(f"Generating audio with prompt: {prompt}")

        if with_lyrics and story_text:
            prompt = self.lyrics_generator.generate_song_lyrics(story_text, query_dispatcher)
            Logger.print_info(f"Generated lyrics: {prompt}")

        if with_lyrics and not story_text:
            Logger.print_error("Error: Story text is required when generating audio with lyrics.")
            return "Error: Story text is required when generating audio with lyrics."

        endpoint, data = self.suno_request_handler.build_request_data(prompt, model, duration, with_lyrics)
        return self.suno_request_handler.send_request(endpoint, data, retries, wait_time)
