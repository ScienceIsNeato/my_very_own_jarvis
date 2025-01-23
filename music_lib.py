import os
import time
import json
import requests
import re
from datetime import datetime
from lyrics_lib import LyricsGenerator
from logger import Logger
from music_backends import MetaMusicBackend, SunoMusicBackend
from ttv.config_loader import TTVConfig

class MusicGenerator:
    """Music generation service that uses different backends."""
    
    def __init__(self, backend=None, config=None):
        """Initialize the music generator with a specific backend.
        
        Args:
            backend: Optional backend instance. If None, uses the backend specified in config.
            config: Optional TTVConfig instance. If None, uses default config.
        """
        if backend:
            self.backend = backend
        else:
            if not config:
                config = TTVConfig(style="default", story=[], title="untitled")
            
            # Get backend from config, default to "suno" if not specified
            backend_name = config.get("music_backend", "suno").lower()
            if backend_name == "meta":
                self.backend = MetaMusicBackend()
            else:  # Default to Suno
                self.backend = SunoMusicBackend()
            
            Logger.print_info(f"Using {backend_name} backend for music generation")
    
    def generate_instrumental(self, prompt: str, **kwargs) -> str:
        """Generate instrumental music from a text prompt."""
        Logger.print_info(f"Generating instrumental music with prompt: {prompt}")
        
        # Start generation
        job_id = self.backend.start_generation(prompt, with_lyrics=False, **kwargs)
        if not job_id:
            Logger.print_error("Failed to start generation")
            return None
            
        # Poll for completion
        while True:
            status, progress = self.backend.check_progress(job_id)
            Logger.print_info(f"Generation progress: {status} ({progress:.1f}%)")
            
            if progress >= 100:
                break
                
            time.sleep(5)  # Wait before checking again
        
        # Get result
        return self.backend.get_result(job_id)
    
    def generate_with_lyrics(self, prompt: str, story_text: str, **kwargs) -> str:
        """Generate music with lyrics from a text prompt and story."""
        Logger.print_info(f"Generating music with lyrics. Prompt: {prompt}, Story length: {len(story_text)}")
        
        # Start generation
        kwargs['story_text'] = story_text
        kwargs['query_dispatcher'] = kwargs.get('query_dispatcher')  # Forward query_dispatcher
        job_id = self.backend.start_generation(prompt, with_lyrics=True, **kwargs)
        if not job_id:
            Logger.print_error("Failed to start generation")
            return None
            
        # Poll for completion
        while True:
            status, progress = self.backend.check_progress(job_id)
            Logger.print_info(f"Generation progress: {status} ({progress:.1f}%)")
            
            if progress >= 100:
                break
                
            time.sleep(5)  # Wait before checking again
        
        # Get result
        return self.backend.get_result(job_id)

    def generate_music(self, prompt, model="chirp-v3-5", duration=10, with_lyrics=False, story_text=None, retries=5, wait_time=60, query_dispatcher=None):
        """Generate music using the configured backend.
        
        This is a legacy method that maps to either generate_instrumental or generate_with_lyrics.
        """
        Logger.print_debug(f"Generating audio with prompt: {prompt}")

        if with_lyrics:
            if not story_text:
                Logger.print_error("Error: Story text is required when generating audio with lyrics.")
                return None
            return self.generate_with_lyrics(prompt, story_text, query_dispatcher=query_dispatcher)
        else:
            return self.generate_instrumental(prompt)

    