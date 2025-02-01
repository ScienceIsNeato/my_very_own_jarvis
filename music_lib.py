"""Music generation library providing a unified interface for multiple music generation backends.

This module implements a music generation service that can use different backends (Meta, Suno)
with fallback support, retry mechanisms, and progress tracking.
"""

import os
import time
from logger import Logger
from music_backends import MetaMusicBackend, SunoMusicBackend
from ttv.config_loader import TTVConfig

def _exponential_backoff(attempt, base_delay=1, max_delay=5):
    """Calculate delay with exponential backoff and jitter."""
    delay = min(base_delay * (2 ** attempt), max_delay)
    
    # If we're at max delay, return it without jitter
    if delay >= max_delay:
        return max_delay
        
    # If we're close to max delay, only allow positive jitter up to max
    if delay > max_delay * 0.9:  # Within 10% of max
        max_jitter = min(delay * 0.1, max_delay - delay)  # Cap jitter to not exceed max
        return delay + (max_jitter * (os.urandom(1)[0] / 255.0))  # Only positive jitter
    
    # Normal case: add bidirectional jitter
    jitter = delay * 0.1  # 10% jitter
    return delay + (jitter * (2 * (os.urandom(1)[0] / 255.0) - 1))

class MusicGenerator:
    """Music generation service that uses different backends."""
    
    MAX_RETRIES = 5  # Maximum number of retries before falling back
    
    def __init__(self, backend=None, config=None):
        """Initialize the music generator with a specific backend.
        
        Args:
            backend: Optional backend instance. If None, uses the backend specified in config.
            config: Optional TTVConfig instance. If None, uses default config.
        """
        if backend:
            self.backend = backend
            self.fallback_backend = None
        else:
            if not config:
                config = TTVConfig(style="default", story=[], title="untitled")
            
            # Get backend from config, default to "suno" if not specified
            backend_name = config.get("music_backend", "suno").lower()
            if backend_name == "meta":
                self.backend = MetaMusicBackend()
                self.fallback_backend = None
            else:  # Default to Suno with Meta as fallback
                self.backend = SunoMusicBackend()
                self.fallback_backend = MetaMusicBackend()
            
            Logger.print_info(f"Using {backend_name} backend for music generation with Meta as fallback")
    
    def generate_instrumental(self, prompt: str, **kwargs) -> str:
        """Generate instrumental music from a text prompt."""
        Logger.print_info(f"Generating instrumental music with prompt: {prompt}")
        
        # Try primary backend first with retries
        result = self._try_generate_with_retries(self.backend, prompt, **kwargs)
        if result:
            return result
            
        # If primary failed and we have a fallback, try that
        if self.fallback_backend:
            Logger.print_info("Primary backend failed after retries, attempting fallback to Meta backend...")
            return self._try_generate_with_backend(self.fallback_backend, prompt, **kwargs)
            
        return None
    
    def _try_generate_with_retries(self, backend, prompt: str, **kwargs) -> str:
        """Attempt to generate music with retries and exponential backoff."""
        for attempt in range(self.MAX_RETRIES):
            try:
                if attempt > 0:
                    delay = _exponential_backoff(attempt)
                    Logger.print_info(f"Retry attempt {attempt + 1}/{self.MAX_RETRIES} after {delay:.1f}s delay...")
                    time.sleep(delay)
                
                result = self._try_generate_with_backend(backend, prompt, **kwargs)
                if result:
                    if attempt > 0:
                        Logger.print_info(f"Successfully generated after {attempt + 1} attempts")
                    return result
                
                Logger.print_warning(f"Attempt {attempt + 1}/{self.MAX_RETRIES} failed, will retry...")
                
            except (RuntimeError, IOError, ValueError, TimeoutError) as e:
                Logger.print_error(f"Error on attempt {attempt + 1}: {str(e)}")
                if attempt == self.MAX_RETRIES - 1:
                    Logger.print_error("All retry attempts exhausted")
                    return None
        
        return None
        
    def _try_generate_with_backend(self, backend, prompt: str, **kwargs) -> str:
        """Attempt to generate music with the specified backend."""
        try:
            # Start generation
            job_id = backend.start_generation(prompt, with_lyrics=False, **kwargs)
            if not job_id:
                Logger.print_error(f"Failed to start generation with {backend.__class__.__name__}")
                return None
                
            # Poll for completion
            while True:
                status, progress = backend.check_progress(job_id)
                Logger.print_info(f"Generation progress: {status} ({progress:.1f}%)")
                
                if progress >= 100:
                    break
                    
                time.sleep(5)  # Wait before checking again
            
            # Get result
            result = backend.get_result(job_id)
            if not result:
                Logger.print_error(f"Failed to get result from {backend.__class__.__name__}")
                return None
                
            return result
            
        except (RuntimeError, IOError, ValueError, TimeoutError) as e:
            Logger.print_error(f"Error with {backend.__class__.__name__}: {str(e)}")
            return None
    
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

    def generate_music(self, prompt: str, with_lyrics: bool = False, story_text: str = None,
                      query_dispatcher=None, **_kwargs) -> str:
        """Generate music using the configured backend.
        
        This is a legacy method that maps to either generate_instrumental or generate_with_lyrics.
        
        Args:
            prompt: The text prompt for music generation
            with_lyrics: Whether to generate music with lyrics
            story_text: Optional story text for lyric-based generation
            query_dispatcher: Optional query dispatcher for lyric generation
            **_kwargs: Additional arguments (ignored for backward compatibility)
            
        Returns:
            str: Path to the generated audio file, or None if generation failed
        """
        Logger.print_debug(f"Generating audio with prompt: {prompt}")

        if with_lyrics:
            if not story_text:
                Logger.print_error("Error: Story text is required when generating audio with lyrics.")
                return None
            return self.generate_with_lyrics(prompt, story_text, query_dispatcher=query_dispatcher)
        
        return self.generate_instrumental(prompt)

    