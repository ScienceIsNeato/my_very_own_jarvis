"""Audio alignment module for text-to-video generation.

This module provides functionality for aligning audio with video segments,
including:
- Audio duration calculation
- Segment timing adjustment
- Whisper-based audio transcription
- FFmpeg-based audio processing
"""

# Standard library imports
import os
import subprocess
import sys
import threading
import time
import traceback
from dataclasses import dataclass
from functools import partial
from typing import List, Optional

# Third-party imports
import torch
import whisper

# Local imports
from .captions import CaptionEntry
from logger import Logger
from utils import exponential_backoff

# Add parent directory to Python path to import logger
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Monkey patch torch.load to always use weights_only=True
torch.load = partial(torch.load, weights_only=True)

whisper_lock = threading.Lock()

@dataclass
class WordTiming:
    """Represents a word with its start and end times from audio."""
    text: str
    start: float
    end: float

def align_words_with_audio(audio_path: str, text: str, model_size: str = "tiny", max_retries: int = 5) -> List[WordTiming]:
    """
    Analyze audio file to generate word-level timings.
    Uses Whisper ASR to perform forced alignment between the audio and text.
    Falls back to even distribution if Whisper alignment fails after max_retries.
    
    Args:
        audio_path: Path to the audio file (should be wav format)
        text: The expected text content of the audio
        model_size: Size of the Whisper model to use ("tiny", "base", "small")
        max_retries: Maximum number of retry attempts for whisper alignment
        
    Returns:
        List of WordTiming objects containing word-level alignments
    """

    # Use a lock to ensure only one thread can load the Whisper model at a time
    with whisper_lock:
        for attempt in range(max_retries):
            try:
                # Load Whisper model with safe settings
                model = whisper.load_model(
                    model_size,
                    device="cpu",  # Force CPU usage
                    download_root=None,  # Use default download location
                    in_memory=True  # Keep model in memory
                )
                
                # Get word-level timestamps from audio
                result = model.transcribe(
                    audio_path,
                    word_timestamps=True,
                    initial_prompt=text,  # Help guide the transcription
                    condition_on_previous_text=False,  # Don't condition on previous text
                    language="en",  # Pass language in decode_options
                    temperature=0.0,  # Use greedy decoding for more consistent results
                    no_speech_threshold=0.3,  # Lower threshold since we know we have speech
                    logprob_threshold=-0.7,  # More strict about word confidence
                    compression_ratio_threshold=2.0,  # Help detect hallucinations
                    best_of=5  # Try multiple candidates and take the best one
                )
                
                if not result or "segments" not in result:
                    Logger.print_error(f"Failed to transcribe audio on attempt {attempt + 1}")
                    if attempt < max_retries - 1:
                        Logger.print_info(f"Retrying whisper alignment (attempt {attempt + 1}/{max_retries})")
                        time.sleep(0.5)  # Add a small delay between retries
                        continue
                    return create_evenly_distributed_timings(audio_path, text)
                
                # Extract word timings from result
                word_timings = []
                for segment in result["segments"]:
                    if "words" in segment:
                        for word in segment["words"]:
                            # Check if word has the required fields
                            if isinstance(word, dict) and "word" in word and "start" in word and "end" in word:
                                word_timings.append(WordTiming(
                                    text=word["word"].strip(),
                                    start=word["start"],
                                    end=word["end"]
                                ))
                
                if not word_timings:
                    Logger.print_error(f"No word timings found on attempt {attempt + 1}")
                    if attempt < max_retries - 1:
                        Logger.print_info(f"Retrying whisper alignment (attempt {attempt + 1}/{max_retries})")
                        time.sleep(0.5)  # Add a small delay between retries
                        continue
                    return create_evenly_distributed_timings(audio_path, text)
                
                # If we get here, the attempt was successful
                if attempt > 0:
                    Logger.print_info(f"✓ Whisper alignment succeeded on attempt {attempt + 1}")
                return word_timings

            except Exception as e:
                # Just log the error message without the stack trace
                Logger.print_error(f"Whisper alignment failed on attempt {attempt + 1}: {str(e)}")
                if attempt < max_retries - 1:
                    Logger.print_info(f"Retrying whisper alignment (attempt {attempt + 1}/{max_retries})")
                    time.sleep(0.5)  # Add a small delay between retries
                    continue
                return create_evenly_distributed_timings(audio_path, text)
    
    # If we get here, all retries failed
    Logger.print_error(f"All {max_retries} whisper alignment attempts failed, falling back to even distribution")
    return create_evenly_distributed_timings(audio_path, text)

def create_evenly_distributed_timings(audio_path: str, text: str) -> List[WordTiming]:
    """
    Create evenly distributed word timings when Whisper alignment fails.
    
    Args:
        audio_path: Path to the audio file
        text: The text to create timings for
        
    Returns:
        List of WordTiming objects with evenly distributed timings
    """
    try:
        # Get total audio duration using ffprobe
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries",
             "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", audio_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True)
        total_duration = float(result.stdout)
        
        # Split text into words
        words = text.split()
        if not words:
            return []
        
        # Calculate time per word
        time_per_word = total_duration / len(words)
        
        # Create evenly distributed timings
        word_timings = []
        for i, word in enumerate(words):
            start_time = i * time_per_word
            end_time = (i + 1) * time_per_word
            word_timings.append(WordTiming(
                text=word,
                start=start_time,
                end=end_time
            ))
        
        Logger.print_info(f"Created fallback evenly distributed timings for {len(words)} words over {total_duration:.2f}s")
        return word_timings
        
    except Exception as e:
        Logger.print_error(f"Error creating evenly distributed timings: {str(e)}")
        return []

def create_word_level_captions(
    audio_file: str,
    text: str,
    model_name: str = "base",
    thread_id: str = None
) -> List[CaptionEntry]:
    """Create word-level captions by aligning text with audio using Whisper.
    
    Args:
        audio_file: Path to the audio file
        text: Text to align with audio
        model_name: Whisper model name to use (default: "base")
        thread_id: Optional thread ID for logging
        
    Returns:
        List[CaptionEntry]: List of caption entries with word-level timings
    """
    thread_prefix = f"{thread_id} " if thread_id else ""
    
    try:
        Logger.print_info(
            f"{thread_prefix}Creating word-level captions for: {audio_file}"
        )

        # Load model with retries using exponential backoff
        def load_and_process_model():
            with whisper_lock:
                model = whisper.load_model(
                    model_name,
                    device="cpu",  # Force CPU usage
                    download_root=None,  # Use default download location
                    in_memory=True  # Keep model in memory
                )
                result = model.transcribe(
                    audio_file,
                    word_timestamps=True,
                    initial_prompt=text,  # Add text as initial prompt to guide transcription
                    condition_on_previous_text=False,  # Don't condition on previous text
                    language="en",  # Pass language in decode_options
                    temperature=0.0,  # Use greedy decoding for more consistent results
                    no_speech_threshold=0.3,  # Lower threshold since we know we have speech
                    logprob_threshold=-0.7,  # More strict about word confidence
                    compression_ratio_threshold=2.0,  # Help detect hallucinations
                    best_of=5  # Try multiple candidates and take the best one
                )
                return model, result

        # Use exponential backoff for model loading and processing
        model, result = exponential_backoff(
            load_and_process_model,
            max_retries=5,
            initial_delay=1.0,
            thread_id=thread_id
        )

        # Extract word timings
        words = []
        for segment in result["segments"]:
            for word in segment.get("words", []):
                # Debug log the word structure
                Logger.print_debug(f"{thread_prefix}Word data: {word}")
                
                # Get word text with fallback to empty string
                word_text = word.get("text", word.get("word", ""))
                if not word_text:
                    Logger.print_warning(f"{thread_prefix}Empty word text in segment")
                    continue
                    
                words.append({
                    "text": word_text,
                    "start": word.get("start", 0),
                    "end": word.get("end", 0)
                })

        # If no words were found, fall back to evenly distributed
        if not words:
            Logger.print_warning(f"{thread_prefix}No words found in Whisper output, falling back to even distribution")
            return create_evenly_distributed_captions(audio_file, text, thread_id)

        # Create caption entries
        captions = []
        for i, word in enumerate(words):
            caption = CaptionEntry(
                text=word["text"],
                start_time=word["start"],
                end_time=word["end"]
            )
            captions.append(caption)

        return captions

    except (RuntimeError, torch.cuda.OutOfMemoryError) as e:
        Logger.print_error(f"{thread_prefix}Error creating word-level captions: {str(e)}")
        Logger.print_error(f"{thread_prefix}Full traceback: {traceback.format_exc()}")
        Logger.print_info(f"{thread_prefix}Falling back to evenly distributed captions")
        return create_evenly_distributed_captions(audio_file, text, thread_id)
    except (OSError, IOError) as e:
        Logger.print_error(
            f"{thread_prefix}Error reading audio file: {str(e)}"
        )
        Logger.print_error(f"Traceback: {traceback.format_exc()}")
        Logger.print_info(f"{thread_prefix}Falling back to evenly distributed captions")
        return create_evenly_distributed_captions(audio_file, text, thread_id)
    except Exception as e:
        Logger.print_error(
            f"{thread_prefix}Unexpected error in create_word_level_captions: {str(e)}"
        )
        Logger.print_error(f"Traceback: {traceback.format_exc()}")
        Logger.print_info(f"{thread_prefix}Falling back to evenly distributed captions")
        return create_evenly_distributed_captions(audio_file, text, thread_id)

def create_evenly_distributed_captions(
    audio_file: str,
    text: str,
    thread_id: Optional[str] = None
) -> List[CaptionEntry]:
    """Create evenly distributed captions when Whisper alignment fails.
    
    Args:
        audio_file: Path to the audio file
        text: Text to create captions for
        thread_id: Optional thread ID for logging
        
    Returns:
        List[CaptionEntry]: List of caption entries with evenly distributed timings
    """
    thread_prefix = f"{thread_id} " if thread_id else ""
    try:
        # Get total audio duration using ffprobe
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries",
             "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", audio_file],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True)
        total_duration = float(result.stdout)
        
        # Split text into words
        words = text.split()
        if not words:
            return []
        
        # Calculate time per word
        time_per_word = total_duration / len(words)
        
        # Create evenly distributed captions
        captions = []
        for i, word in enumerate(words):
            start_time = i * time_per_word
            end_time = (i + 1) * time_per_word
            captions.append(CaptionEntry(
                text=word,
                start_time=start_time,
                end_time=end_time
            ))
        
        Logger.print_info(f"{thread_prefix}Created evenly distributed captions for {len(words)} words over {total_duration:.2f}s")
        return captions
        
    except Exception as e:
        Logger.print_error(f"{thread_prefix}Error creating evenly distributed captions: {str(e)}")
        return []

def get_audio_duration(audio_file: str, thread_id: str = None) -> float:
    """Get the duration of an audio file in seconds.
    
    Args:
        audio_file: Path to the audio file
        thread_id: Optional thread ID for logging
        
    Returns:
        float: Duration in seconds
    """
    try:
        thread_prefix = f"{thread_id} " if thread_id else ""
        Logger.print_info(
            f"{thread_prefix}Getting duration for audio file: {audio_file}"
        )

        # Use ffprobe to get duration
        cmd = [
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", audio_file
        ]
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
            text=True
        )
        duration = float(result.stdout.strip())

        Logger.print_info(
            f"{thread_prefix}Audio duration: {duration:.2f} seconds"
        )
        return duration

    except subprocess.CalledProcessError as e:
        Logger.print_error(
            f"{thread_prefix}FFprobe error: {e.stderr.decode()}"
        )
        raise
    except (ValueError, OSError) as e:
        Logger.print_error(
            f"{thread_prefix}Error getting audio duration: {str(e)}"
        )
        raise
