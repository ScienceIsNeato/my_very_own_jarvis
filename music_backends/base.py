from abc import ABC, abstractmethod

class MusicBackend(ABC):
    """Base class for music generation backends."""
    
    @abstractmethod
    def generate_instrumental(self, prompt: str, **kwargs) -> str:
        """Generate instrumental music from a text prompt.
        
        Args:
            prompt (str): Text description of the desired music.
            **kwargs: Additional backend-specific parameters.
            
        Returns:
            str: Path to the generated audio file.
        """
        pass
    
    @abstractmethod
    def generate_with_lyrics(self, prompt: str, story_text: str, **kwargs) -> str:
        """Generate music with lyrics from a text prompt and story.
        
        Args:
            prompt (str): Text description of the desired music style.
            story_text (str): Story text to generate lyrics from.
            **kwargs: Additional backend-specific parameters.
            
        Returns:
            str: Path to the generated audio file.
        """
        pass
    
    @abstractmethod
    def start_generation(self, prompt: str, with_lyrics: bool = False, **kwargs) -> str:
        """Start the generation process and return a job ID or identifier.
        
        Args:
            prompt (str): Text description of the desired music.
            with_lyrics (bool): Whether to generate with lyrics.
            **kwargs: Additional backend-specific parameters.
            
        Returns:
            str: Job ID or identifier for tracking progress.
        """
        pass
    
    @abstractmethod
    def check_progress(self, job_id: str) -> tuple[str, float]:
        """Check the progress of a generation job.
        
        Args:
            job_id (str): Job ID or identifier from start_generation.
            
        Returns:
            tuple[str, float]: Status message and progress percentage (0-100).
        """
        pass
    
    @abstractmethod
    def get_result(self, job_id: str) -> str:
        """Get the result of a completed generation job.
        
        Args:
            job_id (str): Job ID or identifier from start_generation.
            
        Returns:
            str: Path to the generated audio file.
        """
        pass 