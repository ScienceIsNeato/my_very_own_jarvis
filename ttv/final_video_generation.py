"""Final video generation module.

This module handles the final stages of video generation, including:
- Combining video segments with transitions
- Adding audio tracks and background music
- Applying captions and overlays
- Generating closing credits
- Managing temporary files and cleanup
"""

import os
import subprocess
import tempfile
from datetime import datetime
from typing import List, Optional, Dict

from logger import Logger
from utils import get_tempdir

from .audio_alignment import create_word_level_captions
from .captions import CaptionEntry, create_dynamic_captions, create_static_captions
from .ffmpeg_wrapper import run_ffmpeg_command
from .log_messages import (
    LOG_CLOSING_CREDITS_DURATION,
    LOG_BACKGROUND_MUSIC_SUCCESS,
    LOG_BACKGROUND_MUSIC_FAILURE
)
from .video_generation import append_video_segments, create_video_segment

def run_ffmpeg_command(cmd: List[str]) -> subprocess.CompletedProcess:
    """Run an FFmpeg command and handle errors.
    
    Args:
        cmd: List of command arguments
        
    Returns:
        subprocess.CompletedProcess: The completed process result
        
    Raises:
        subprocess.CalledProcessError: If the command fails
        OSError: If there's a system-level error
    """
    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True
        )
        return result
    except (subprocess.CalledProcessError, OSError) as e:
        Logger.print_error(f"FFmpeg command failed: {e.stderr.decode() if hasattr(e, 'stderr') else str(e)}")
        raise

def read_file_contents(file_path: str, encoding: str = "utf-8") -> Optional[str]:
    """Read contents of a file with proper encoding.
    
    Args:
        file_path: Path to file to read
        encoding: File encoding (default: utf-8)
        
    Returns:
        Optional[str]: File contents if successful, None otherwise
    """
    try:
        with open(file_path, "r", encoding=encoding) as f:
            return f.read()
    except (OSError, IOError) as e:
        Logger.print_error(f"Failed to read file {file_path}: {str(e)}")
        return None

def _get_timestamped_filename(base_name: str) -> str:
    """Generate a timestamped filename.
    
    Args:
        base_name: Base name for the file
        
    Returns:
        str: Filename with timestamp and .mp4 extension
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{base_name}_{timestamp}.mp4"

def concatenate_video_segments(
    video_segments: List[str],
    output_path: str
) -> Optional[str]:
    """Concatenate multiple video segments into a single video.
    
    Args:
        video_segments: List of video file paths to concatenate
        output_path: Path to save the concatenated video
        
    Returns:
        Optional[str]: Path to output video if successful, None otherwise
    """
    list_file = None
    try:
        if not video_segments:
            Logger.print_error("No video segments provided")
            return None
            
        # Create temporary file list
        temp_dir = get_tempdir()
        list_file = os.path.join(temp_dir, "segments.txt")
        
        with open(list_file, "w", encoding="utf-8") as f:
            for segment in video_segments:
                f.write(f"file '{os.path.abspath(segment)}'\n")
                
        # Run FFmpeg command to concatenate videos
        cmd = [
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", list_file,
            "-c", "copy",
            output_path
        ]
        
        result = run_ffmpeg_command(cmd)
        if not result:
            Logger.print_error("Failed to concatenate video segments")
            return None
            
        return output_path
            
    except (OSError, IOError) as e:
        Logger.print_error(f"Error concatenating video segments: {str(e)}")
        return None
    finally:
        # Clean up temporary file
        try:
            if list_file and os.path.exists(list_file):
                os.remove(list_file)
        except OSError as e:
            Logger.print_error(f"Error cleaning up list file: {str(e)}")

def add_background_music(
    video_path: str,
    music_path: str,
    output_path: str,
    music_volume: float = 0.3
) -> Optional[str]:
    """Add background music to a video.
    
    Args:
        video_path: Path to input video
        music_path: Path to music file
        output_path: Path to save the output video
        music_volume: Volume level for music (default: 0.3)
        
    Returns:
        Optional[str]: Path to output video if successful, None otherwise
    """
    try:
        # Create FFmpeg filter complex with careful audio format normalization
        filter_complex = (
            # First upsample mono audio to 48kHz, then convert to stereo using pan
            "[0:a]aresample=48000,aformat=sample_fmts=fltp[mono];"
            "[mono]pan=stereo|c0=c0|c1=c0[v];"
            # Process background music
            f"[1:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,volume={music_volume}[m];"
            # Mix the streams
            "[v][m]amix=inputs=2:duration=first:dropout_transition=2[aout]"
        )
        
        # Run FFmpeg command
        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-i", music_path,
            "-filter_complex", filter_complex,
            "-map", "0:v",
            "-map", "[aout]",
            "-c:v", "copy",
            "-c:a", "aac",
            "-b:a", "192k",
            output_path
        ]
        
        try:
            run_ffmpeg_command(cmd)
            Logger.print_info(LOG_BACKGROUND_MUSIC_SUCCESS)
            return output_path
        except (subprocess.CalledProcessError, OSError):
            Logger.print_error(LOG_BACKGROUND_MUSIC_FAILURE)
            return None
            
    except Exception as e:
        Logger.print_error(f"Error adding background music: {str(e)}")
        return None

def assemble_final_video(video_segments, music_path=None, song_with_lyrics_path=None, movie_poster_path=None, output_path=None, config=None, closing_credits_lyrics=None):
    """
    Assembles the final video from given segments, adds background music, and generates closing credits.

    Args:
        video_segments (list): List of paths to video segments.
        music_path (str, optional): Path to the background music file. If None, no background music is added.
        song_with_lyrics_path (str, optional): Path to the song with lyrics file for closing credits. If None, no closing credits are added.
        movie_poster_path (str, optional): Path to the movie poster image for closing credits. Required if song_with_lyrics_path is provided.
        output_path (str, optional): Path to save the final output video.
        config (TTVConfig, optional): Configuration object containing caption style and other settings.
        closing_credits_lyrics (str, optional): The lyrics to use for word alignment in closing credits.

    Returns:
        str: Path to the most recent successfully generated video.
    """
    main_video_path = None
    main_video_with_background_music_path = None
    final_output_path = None

    try:
        temp_dir = get_tempdir()
        if not output_path:
            output_path = os.path.join(temp_dir, "ttv", _get_timestamped_filename("final_output"))

        main_video_path = os.path.join(temp_dir, "ttv", _get_timestamped_filename("main_video"))
        Logger.print_info("Concatenating video segments...")
        main_video_path = concatenate_video_segments(video_segments, main_video_path)
        final_output_path = main_video_path  # Update the final output path after this step

        # Handle background music
        if music_path and os.path.exists(music_path):
            Logger.print_info("Adding background music to main video...")
            # Create a new path for the video with background music
            main_video_with_music_path = os.path.join(temp_dir, "ttv", _get_timestamped_filename("main_video_with_music"))
            main_video_with_background_music_path = add_background_music(
                video_path=main_video_path,
                music_path=music_path,
                output_path=main_video_with_music_path
            )
            if main_video_with_background_music_path:
                final_output_path = main_video_with_background_music_path
                Logger.print_info(f"Successfully added background music from {music_path}")
            else:
                Logger.print_warning("Failed to add background music, using video without music")
                main_video_with_background_music_path = main_video_path
        else:
            main_video_with_background_music_path = main_video_path

        # Handle closing credits
        if song_with_lyrics_path and os.path.exists(song_with_lyrics_path):
            Logger.print_info("Generating closing credits...")
            if movie_poster_path and os.path.exists(movie_poster_path):
                closing_credits = generate_closing_credits(movie_poster_path, song_with_lyrics_path, output_path, config, closing_credits_lyrics)
                if closing_credits:
                    # now all we have to do is stitch together the main content and the credits
                    fully_assembled_movie_path = append_video_segments([main_video_with_background_music_path, closing_credits], output_path)
                    if fully_assembled_movie_path:
                        final_output_path = fully_assembled_movie_path
                        Logger.print_info(f"Successfully added closing credits from {song_with_lyrics_path}")
                    else:
                        Logger.print_warning("Failed to append closing credits, using video without credits")
                        final_output_path = main_video_with_background_music_path
                else:
                    Logger.print_warning("Failed to generate closing credits, using video without credits")
                    final_output_path = main_video_with_background_music_path
            else:
                Logger.print_warning("No movie poster available for closing credits, using video without credits")
                final_output_path = main_video_with_background_music_path
        else:
            final_output_path = main_video_with_background_music_path

        play_video(final_output_path)
        return final_output_path

    except (OSError, subprocess.SubprocessError) as e:
        Logger.print_error(f"Error creating final video with music: {e}")
        if final_output_path:
            Logger.print_info(f"Final video created at: output_path={final_output_path}")
            return final_output_path
        elif main_video_path:
            Logger.print_info(f"Final video created at: output_path={main_video_path}")
            return main_video_path
        else:
            fallback_path = os.path.join(get_tempdir(), "ttv", _get_timestamped_filename("fallback_video"))
            Logger.print_info(f"Final video created at: output_path={fallback_path}")
            return fallback_path

def generate_closing_credits(movie_poster_path, song_with_lyrics_path, output_path, config=None, lyrics=None):
    """Generate closing credits video with dynamic captions for song lyrics."""
    # Create initial video with poster and music
    temp_dir = get_tempdir()
    initial_credits_video_path = os.path.join(temp_dir, "initial_credits.mp4")
    closing_credits_video_path = os.path.join(temp_dir, "closing_credits.mp4")

    try:
        # Get video duration from audio file
        ffprobe_cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            song_with_lyrics_path
        ]
        result = subprocess.run(
            ffprobe_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True
        )
        duration = float(result.stdout.decode('utf-8').strip())
        Logger.print_info(f"{LOG_CLOSING_CREDITS_DURATION}: {duration}s")

        # Create video from poster image with duration matching audio
        ffmpeg_cmd = [
            "ffmpeg", "-y",
            "-loop", "1",
            "-i", movie_poster_path,
            "-i", song_with_lyrics_path,
            "-c:v", "libx264",
            "-tune", "stillimage",
            "-c:a", "aac",
            "-b:a", "192k",
            "-pix_fmt", "yuv420p",
            "-shortest",
            initial_credits_video_path
        ]

        try:
            run_ffmpeg_command(ffmpeg_cmd)
        except (subprocess.CalledProcessError, OSError):
            Logger.print_error("Failed to generate initial closing credits video")
            return None

        # Get caption style from config
        caption_style = getattr(config, 'caption_style', 'static') if config else 'static'

        # Create captions for the song lyrics - use provided lyrics if available
        captions = create_word_level_captions(song_with_lyrics_path, lyrics if lyrics else "")
        if not captions:
            Logger.print_error("Failed to create captions for closing credits")
            return initial_credits_video_path

        if caption_style == "dynamic":
            # Add dynamic captions to the video
            captioned_path = create_dynamic_captions(
                input_video=initial_credits_video_path,
                captions=captions,
                output_path=closing_credits_video_path,
                min_font_size=32,
                max_font_size=48
            )
        else:
            # Combine all captions into one for static display
            combined_text = " ".join(c.text for c in captions)
            static_captions = [CaptionEntry(combined_text, 0.0, duration)]
            
            # Add static captions to the video
            captioned_path = create_static_captions(
                input_video=initial_credits_video_path,
                captions=static_captions,
                output_path=closing_credits_video_path,
                font_size=40
            )

        if captioned_path:
            Logger.print_info(f"Generated closing credits video with captions at {closing_credits_video_path}")
            return closing_credits_video_path
        else:
            Logger.print_error("Failed to add captions to closing credits video")
            return initial_credits_video_path

    except (subprocess.CalledProcessError, OSError) as e:
        Logger.print_error(f"Error generating closing credits: {str(e)}")
        return None

def play_video(video_path):
    """Play a video file if playback is enabled."""
    if os.getenv('PLAYBACK_MEDIA_IN_TESTS', 'false').lower() == 'true':
        try:
            subprocess.run(["ffplay", "-autoexit", video_path], check=True)
        except subprocess.CalledProcessError as e:
            Logger.print_error(f"Error playing video: {e}")

def get_video_duration(video_path: str) -> Optional[float]:
    """Get duration of a video file in seconds.
    
    Args:
        video_path: Path to video file
        
    Returns:
        Optional[float]: Duration in seconds if successful, None otherwise
    """
    try:
        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            video_path
        ]
        
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True
        )
        
        duration = float(result.stdout.decode().strip())
        return duration
            
    except (subprocess.CalledProcessError, ValueError, OSError) as e:
        Logger.print_error(f"Error getting video duration: {str(e)}")
        return None

def create_video_with_captions(
    segments: List[Dict[str, str]],
    output_path: str,
    thread_id: Optional[str] = None
) -> Optional[str]:
    """Create a video with captions from segments.
    
    Args:
        segments: List of segment dictionaries with paths
        output_path: Path to save final video
        thread_id: Optional thread ID for logging
        
    Returns:
        Optional[str]: Path to final video if successful
    """
    thread_prefix = f"{thread_id} " if thread_id else ""
    temp_dir = get_tempdir()
    
    try:
        # Create video segments
        video_segments = []
        for i, segment in enumerate(segments):
            try:
                # Generate captions
                captions = create_word_level_captions(
                    segment["audio"],
                    segment["text"],
                    thread_id=thread_id
                )
                if not captions:
                    raise ValueError(
                        f"Failed to generate captions for segment {i + 1}"
                    )
                    
                # Create video segment
                video_path = create_video_segment(
                    image_path=segment["image"],
                    audio_path=segment["audio"],
                    output_path=os.path.join(temp_dir, "ttv", f"segment_{i}_initial.mp4")
                )
                if not video_path:
                    raise ValueError(
                        f"Failed to create video for segment {i + 1}"
                    )
                    
                video_segments.append(video_path)
            except Exception as e:
                Logger.print_error(f"{thread_prefix}Error creating video segment {i + 1}: {str(e)}")
                return None
                
        # Concatenate video segments
        result = concatenate_video_segments(video_segments, output_path)
        if not result:
            Logger.print_error(f"{thread_prefix}Failed to concatenate video segments")
            return None
            
        return output_path
            
    except Exception as e:
        Logger.print_error(f"{thread_prefix}Error creating video with captions: {str(e)}")
        return None
