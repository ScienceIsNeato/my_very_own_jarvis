"""Music generation library providing a unified interface for multiple music generation backends.

This module implements a music generation service that can use different backends (Meta, Suno)
with fallback support, retry mechanisms, and progress tracking.
"""

import os
import time
import subprocess
from logger import Logger
from music_backends import MetaMusicBackend, SunoMusicBackend
from ttv.config_loader import TTVConfig
from typing import Optional, Any, Tuple

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

    def validate_audio_file(self, file_path: str, thread_id: Optional[str] = None) -> bool:
        """Validate that a file exists and is a valid audio file.
        
        Args:
            file_path: Path to the audio file to validate
            thread_id: Optional thread ID for logging
            
        Returns:
            bool: True if file is valid audio, False otherwise
        """
        thread_prefix = f"{thread_id} " if thread_id else ""
        
        if not os.path.exists(file_path):
            Logger.print_error(f"{thread_prefix}Audio file not found at: {file_path}")
            return False
            
        try:
            cmd = [
                "ffprobe", "-v", "error",
                "-select_streams", "a:0",
                "-show_entries", "stream=codec_type",
                "-of", "default=noprint_wrappers=1:nokey=1",
                file_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0 or 'audio' not in result.stdout:
                Logger.print_error(f"{thread_prefix}File is not a valid audio file: {file_path}")
                return False
            return True
            
        except subprocess.SubprocessError as e:
            Logger.print_error(f"{thread_prefix}Failed to validate audio file: {str(e)}")
            return False

    def get_background_music_from_file(self, file_path: str, thread_id: Optional[str] = None) -> Optional[str]:
        """Get background music from a file path.
        
        Args:
            file_path: Path to the audio file
            thread_id: Optional thread ID for logging
            
        Returns:
            Optional[str]: Path to validated audio file or None if invalid
        """
        thread_prefix = f"{thread_id} " if thread_id else ""
        Logger.print_info(f"{thread_prefix}Using background music from file: {file_path}")
        
        if self.validate_audio_file(file_path, thread_id):
            return file_path
        return None

    def get_background_music_from_prompt(
        self,
        prompt: str,
        output_dir: str,
        skip_generation: bool = False,
        thread_id: Optional[str] = None
    ) -> Optional[str]:
        """Generate background music from a prompt.
        
        Args:
            prompt: The prompt to use for generation
            output_dir: Directory to save generated music
            skip_generation: Whether to skip generation
            thread_id: Optional thread ID for logging
            
        Returns:
            Optional[str]: Path to generated audio file or None if generation failed
        """
        thread_prefix = f"{thread_id} " if thread_id else ""
        
        if skip_generation:
            Logger.print_info(f"{thread_prefix}Skipping background music generation due to skip_generation flag")
            return None
            
        Logger.print_info(f"{thread_prefix}Generating background music with prompt: {prompt}")
        background_music_path = self.generate_instrumental(
            prompt=prompt,
            duration=30,  # TODO: Calculate actual duration
            output_path=os.path.join(output_dir, "background_music.mp3")
        )
        
        if background_music_path:
            Logger.print_info(f"{thread_prefix}Successfully generated background music at: {background_music_path}")
            return background_music_path
            
        Logger.print_error(f"{thread_prefix}Failed to generate background music")
        return None

    def get_background_music(
        self,
        config: Any,
        output_dir: str,
        skip_generation: bool = False,
        thread_id: Optional[str] = None
    ) -> Optional[str]:
        """Get background music either from file or by generating from prompt.
        
        Args:
            config: Configuration object containing background music settings
            output_dir: Directory to save generated music
            skip_generation: Whether to skip generation
            thread_id: Optional thread ID for logging
            
        Returns:
            Optional[str]: Path to background music file or None if not available
        """
        thread_prefix = f"{thread_id} " if thread_id else ""
        
        if not hasattr(config, 'background_music') or not config.background_music:
            Logger.print_info(f"{thread_prefix}No background music configuration found")
            return None
            
        # Get file and prompt settings
        background_music_path = getattr(config.background_music, 'file', None)
        background_music_prompt = getattr(config.background_music, 'prompt', None)
        
        # Validate settings
        if background_music_path is not None and background_music_prompt is not None:
            Logger.print_error(
                f"{thread_prefix}Background music path and prompt cannot both be set simultaneously. "
                f"Current path: {background_music_path} and prompt: {background_music_prompt}"
            )
            return None
            
        if background_music_path is None and background_music_prompt is None:
            Logger.print_error(f"{thread_prefix}Background music path and prompt cannot both be None")
            return None
            
        # Get background music from file or generate from prompt
        if background_music_path is not None:
            return self.get_background_music_from_file(background_music_path, thread_id)
        else:
            return self.get_background_music_from_prompt(
                background_music_prompt,
                output_dir,
                skip_generation,
                thread_id
            )

    def get_closing_credits_from_file(self, file_path: str, thread_id: Optional[str] = None) -> Optional[str]:
        """Get closing credits music from a file path.
        
        Args:
            file_path: Path to the audio file
            thread_id: Optional thread ID for logging
            
        Returns:
            Optional[str]: Path to validated audio file or None if invalid
        """
        thread_prefix = f"{thread_id} " if thread_id else ""
        Logger.print_info(f"{thread_prefix}Using closing credits from file: {file_path}")
        
        if self.validate_audio_file(file_path, thread_id):
            return file_path
        return None

    def get_closing_credits_from_prompt(
        self,
        prompt: str,
        story_text: str,
        output_dir: str,
        skip_generation: bool = False,
        query_dispatcher: Optional[Any] = None,
        thread_id: Optional[str] = None
    ) -> Tuple[Optional[str], Optional[str]]:
        """Generate closing credits music from a prompt.
        
        Args:
            prompt: The prompt to use for generation
            story_text: Story text for lyric generation
            output_dir: Directory to save generated music
            skip_generation: Whether to skip generation
            query_dispatcher: Query dispatcher for lyric generation
            thread_id: Optional thread ID for logging
            
        Returns:
            Tuple[Optional[str], Optional[str]]: Tuple containing:
                - Path to generated audio file or None if generation failed
                - Generated lyrics or None if not available
        """
        thread_prefix = f"{thread_id} " if thread_id else ""
        
        if skip_generation:
            Logger.print_info(f"{thread_prefix}Skipping closing credits generation due to skip_generation flag")
            return None, None
            
        Logger.print_info(f"{thread_prefix}Generating closing credits with prompt: {prompt}")
        closing_credits_path = self.generate_with_lyrics(
            prompt=prompt,
            story_text=story_text,
            query_dispatcher=query_dispatcher,
            output_path=os.path.join(output_dir, "closing_credits.mp3")
        )
        
        # TODO: Extract lyrics from generation result
        lyrics = None
        
        if closing_credits_path:
            Logger.print_info(f"{thread_prefix}Successfully generated closing credits at: {closing_credits_path}")
            return closing_credits_path, lyrics
            
        Logger.print_error(f"{thread_prefix}Failed to generate closing credits")
        return None, None

    def get_closing_credits(
        self,
        config: Any,
        story_text: str,
        output_dir: str,
        skip_generation: bool = False,
        query_dispatcher: Optional[Any] = None,
        thread_id: Optional[str] = None
    ) -> Tuple[Optional[str], Optional[str]]:
        """Get closing credits either from file or by generating from prompt.
        
        Args:
            config: Configuration object containing closing credits settings
            story_text: Story text for lyric generation
            output_dir: Directory to save generated music
            skip_generation: Whether to skip generation
            query_dispatcher: Query dispatcher for lyric generation
            thread_id: Optional thread ID for logging
            
        Returns:
            Tuple[Optional[str], Optional[str]]: Tuple containing:
                - Path to closing credits file or None if not available
                - Generated lyrics or None if not available
        """
        thread_prefix = f"{thread_id} " if thread_id else ""
        
        if not hasattr(config, 'closing_credits') or not config.closing_credits:
            Logger.print_info(f"{thread_prefix}No closing credits configuration found")
            return None, None
            
        # Get file and prompt settings
        closing_credits_path = getattr(config.closing_credits, 'file', None)
        closing_credits_prompt = getattr(config.closing_credits, 'prompt', None)
        
        # Validate settings
        if closing_credits_path is not None and closing_credits_prompt is not None:
            Logger.print_error(
                f"{thread_prefix}Closing credits path and prompt cannot both be set simultaneously. "
                f"Current path: {closing_credits_path} and prompt: {closing_credits_prompt}"
            )
            return None, None
            
        if closing_credits_path is None and closing_credits_prompt is None:
            Logger.print_error(f"{thread_prefix}Closing credits path and prompt cannot both be None")
            return None, None
            
        # Get closing credits from file or generate from prompt
        if closing_credits_path is not None:
            return self.get_closing_credits_from_file(closing_credits_path, thread_id), None
        else:
            return self.get_closing_credits_from_prompt(
                closing_credits_prompt,
                story_text,
                output_dir,
                skip_generation,
                query_dispatcher,
                thread_id
            )

    