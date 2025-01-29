import os
import torch
import numpy as np
import soundfile as sf
import threading
import json
import time
from datetime import datetime
from utils import get_tempdir
from transformers import AutoProcessor, MusicgenForConditionalGeneration
from logger import Logger
from music_backends.base import MusicBackend
import subprocess

# Set environment variables to avoid warnings
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["TORCH_WARN_COPY_TENSOR"] = "0"  # Suppress tensor copy warning

class MetaMusicBackend(MusicBackend):
    """Meta's MusicGen implementation for music generation."""
    
    def __init__(self):
        """Initialize the Meta MusicGen model and processor."""
        self.model = None
        self.processor = None
        self.model_name = "facebook/musicgen-small"
        self.sample_rate = 32000
        self.audio_directory = os.path.join(get_tempdir(), "music")
        self.progress_directory = os.path.join(get_tempdir(), "progress")
        os.makedirs(self.audio_directory, exist_ok=True)
        os.makedirs(self.progress_directory, exist_ok=True)
        self.active_jobs = {}  # job_id -> thread
    
    def _ensure_model_loaded(self):
        """Ensure the model and processor are loaded."""
        if self.model is None:
            Logger.print_info(f"Loading MusicGen model and processor from {self.model_name}")
            
            # Set environment variables to avoid warnings
            os.environ["TOKENIZERS_PARALLELISM"] = "false"
            
            # Initialize model with specific dtype and attention implementation
            self.model = MusicgenForConditionalGeneration.from_pretrained(
                self.model_name,
                attn_implementation="eager",  # Fix for scaled_dot_product_attention warning
                torch_dtype=torch.float32,    # Fix for tensor construction warning
                use_safetensors=True         # Use safetensors to avoid tensor copy warnings
            )
            self.processor = AutoProcessor.from_pretrained(self.model_name)
            
            if torch.cuda.is_available():
                Logger.print_info("Moving model to CUDA")
                self.model = self.model.to("cuda")
            else:
                Logger.print_info("CUDA not available, using CPU")
    
    def start_generation(self, prompt: str, **kwargs) -> str:
        """Start the generation process in a separate thread."""
        job_id = f"musicgen_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hash(prompt)}"
        progress_file = os.path.join(self.progress_directory, f"{job_id}.json")
        
        # Initialize progress file
        with open(progress_file, 'w') as f:
            json.dump({
                'status': 'Starting',
                'progress': 0,
                'output_path': None,
                'error': None
            }, f)
        
        # Start generation thread
        thread = threading.Thread(
            target=self._generation_thread,
            args=(job_id, prompt),
            kwargs=kwargs
        )
        thread.start()
        self.active_jobs[job_id] = thread
        
        return job_id
    
    def check_progress(self, job_id: str) -> tuple[str, float]:
        """Check the progress of a generation job."""
        progress_file = os.path.join(self.progress_directory, f"{job_id}.json")
        
        try:
            with open(progress_file, 'r') as f:
                data = json.load(f)
                return data['status'], data['progress']
        except (FileNotFoundError, json.JSONDecodeError, KeyError):
            return "Error reading progress", 0
    
    def get_result(self, job_id: str) -> str:
        """Get the result of a completed generation job."""
        progress_file = os.path.join(self.progress_directory, f"{job_id}.json")
        
        try:
            with open(progress_file, 'r') as f:
                data = json.load(f)
                if data.get('error'):
                    Logger.print_error(f"Generation failed: {data['error']}")
                    return None
                return data.get('output_path')
        except (FileNotFoundError, json.JSONDecodeError):
            return None
    
    def _update_progress(self, job_id: str, status: str, progress: float, output_path: str = None, error: str = None):
        """Update the progress file for a job."""
        progress_file = os.path.join(self.progress_directory, f"{job_id}.json")
        with open(progress_file, 'w') as f:
            json.dump({
                'status': status,
                'progress': progress,
                'output_path': output_path,
                'error': error
            }, f)
    
    def _generation_thread(self, job_id: str, prompt: str, **kwargs):
        """Thread function for generating audio."""
        try:
            self._update_progress(job_id, "Loading model", 0)
            self._ensure_model_loaded()
            
            self._update_progress(job_id, "Processing prompt", 10)
            inputs = self.processor(
                text=[prompt],
                padding=True,
                return_tensors="pt",
            )
            
            if torch.cuda.is_available():
                inputs = {k: v.to("cuda") for k, v in inputs.items()}
            
            self._update_progress(job_id, "Starting generation", 20)
            max_new_tokens = kwargs.get('max_new_tokens', 256)
            self.model.generation_config.max_new_tokens = max_new_tokens
            
            # Start progress update thread
            generation_complete = threading.Event()
            progress_thread = threading.Thread(
                target=self._progress_updater,
                args=(job_id, generation_complete)
            )
            progress_thread.start()
            
            # Generate audio
            audio_values = self.model.generate(
                **inputs,
                do_sample=True
            )
            
            # Signal completion and wait for progress thread
            generation_complete.set()
            progress_thread.join()
            
            self._update_progress(job_id, "Processing audio", 98)
            audio_data = audio_values.cpu().numpy().squeeze()
            if len(audio_data.shape) == 1:
                audio_data = audio_data.reshape(1, -1)
            
            self._update_progress(job_id, "Saving audio", 99)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            sanitized_prompt = ''.join(c if c.isalnum() else '_' for c in prompt)[:50]
            audio_path = os.path.join(
                self.audio_directory,
                f"musicgen_{sanitized_prompt}_{timestamp}.wav"
            )
            
            sf.write(audio_path, audio_data.T, self.sample_rate)
            self._update_progress(job_id, "Complete", 100, audio_path)
            
            # Auto-play the generated audio
            try:
                if os.uname().sysname == 'Darwin':  # macOS
                    subprocess.Popen(['afplay', audio_path])
                else:  # Linux/Others - requires vlc
                    subprocess.Popen(['vlc', '--play-and-exit', audio_path])
            except Exception as e:
                Logger.print_error(f"Failed to auto-play audio: {str(e)}")
            
        except Exception as e:
            Logger.print_error(f"Generation failed: {str(e)}")
            self._update_progress(job_id, "Failed", 0, error=str(e))
        
        finally:
            if job_id in self.active_jobs:
                del self.active_jobs[job_id]
    
    def _progress_updater(self, job_id: str, complete_event: threading.Event):
        """Update progress periodically while generation is running."""
        start_time = time.time()
        estimated_duration = 30  # Estimated duration in seconds
        
        while not complete_event.is_set():
            elapsed = time.time() - start_time
            progress = min(20 + (elapsed / estimated_duration * 70), 97)  # Progress from 20% to 97%
            self._update_progress(job_id, f"Generating audio ({elapsed:.1f}s)", progress)
            time.sleep(0.5)  # Update every half second
    
    def generate_instrumental(self, prompt: str, **kwargs) -> str:
        job_id = self.start_generation(prompt, **kwargs)
        while True:
            status, progress = self.check_progress(job_id)
            if progress >= 100:
                return self.get_result(job_id)
            time.sleep(1)

    def generate_with_lyrics(self, prompt: str, story_text: str, **kwargs) -> str:
        """Generate music with lyrics from a text prompt and story.
        
        This method is not implemented for the Meta backend as MusicGen does not support lyrics generation.
        """
        raise NotImplementedError("MusicGen does not support generating music with lyrics") 