"""Module for aligning text with audio to generate word-level timings."""

from typing import List
import whisper
import torch
from dataclasses import dataclass
from .captions import CaptionEntry
from functools import partial
import sys
import os
import subprocess
import time
import threading

# Add parent directory to Python path to import logger
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from logger import Logger

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
                    language="en",
                    word_timestamps=True,
                    initial_prompt=text,  # Help guide the transcription
                    fp16=False  # Force FP32
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

def create_word_level_captions(audio_path: str, text: str = "", is_music: bool = False) -> List[CaptionEntry]:
    """
    Create word-level caption entries from audio file.
    
    Args:
        audio_path: Path to the audio file
        text: The text content of the audio, or empty string to auto-transcribe
        is_music: Whether the audio contains music (uses a larger model and music-specific prompt)
        
    Returns:
        List of CaptionEntry objects, one per word
    """
    try:
        # Choose model size based on whether we're processing music
        model_size = "base" if is_music else "tiny"
        
        if not text:
            # Only transcribe if no text was provided
            model = whisper.load_model(
                model_size,
                device="cpu",
                download_root=None,
                in_memory=True
            )
            
            # Add an initial prompt if we're transcribing music
            initial_prompt = "This is a song with lyrics. The lyrics are:" if is_music else None
            
            result = model.transcribe(
                audio_path,
                language="en",
                initial_prompt=initial_prompt,
                fp16=False
            )
            
            if result and "text" in result:
                text = result["text"].strip()
                Logger.print_info(f"Transcribed {'lyrics' if is_music else 'text'}: {text}")
            else:
                Logger.print_error("Failed to transcribe audio")
                return []
        else:
            # Use provided text directly
            Logger.print_info(f"Using provided {'lyrics' if is_music else 'text'}: {text}")

        # Now get word timings using the text
        word_timings = align_words_with_audio(audio_path, text, model_size)
        if not word_timings:
            Logger.print_error(f"No word timings available for: {text}")
            return []
        
        # Convert to caption entries
        captions = []
        for timing in word_timings:
            captions.append(CaptionEntry(
                text=timing.text,
                start_time=timing.start,
                end_time=timing.end,
                timed_words=[(timing.text, timing.start, timing.end)]
            ))
        
        if not captions:
            Logger.print_error(f"Failed to create captions from word timings for: {text}")
            return []
            
        return captions
    except Exception as e:
        Logger.print_error(f"Error in create_word_level_captions: {str(e)}")
        import traceback
        Logger.print_error(f"Traceback: {traceback.format_exc()}")
        return [] 