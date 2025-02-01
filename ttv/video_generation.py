from logger import Logger
from .audio_generation import get_audio_duration
from .ffmpeg_wrapper import run_ffmpeg_command
from utils import get_tempdir, ffmpeg_thread_manager
from ttv.log_messages import LOG_VIDEO_SEGMENT_CREATE
import os
import subprocess

def create_video_segment(image_path, audio_path, output_path, thread_id=None):
    """Create a video segment from an image and audio file.
    
    Args:
        image_path: Path to the image file
        audio_path: Path to the audio file
        output_path: Path to save the output video
        thread_id: Optional thread ID for logging
        
    Returns:
        str: Path to the output video if successful, None otherwise
    """
    thread_prefix = f"{thread_id} " if thread_id else ""
    try:
        # Get audio duration
        duration = get_audio_duration(audio_path)
        if duration is None:
            Logger.print_error(f"{thread_prefix}Failed to get audio duration")
            return None

        # Create video segment using thread manager
        with ffmpeg_thread_manager:
            cmd = [
                "ffmpeg", "-y",
                "-loop", "1",
                "-i", image_path,
                "-i", audio_path,
                "-c:v", "libx264",
                "-tune", "stillimage",
                "-c:a", "aac",
                "-b:a", "192k",
                "-pix_fmt", "yuv420p",
                "-shortest",
                output_path
            ]
            result = subprocess.run(
                cmd,
                check=True,
                capture_output=True
            )

        if result.returncode != 0:
            Logger.print_error(f"{thread_prefix}Failed to create video segment: {result.stderr.decode()}")
            return None

        Logger.print_info(f"{thread_prefix}Successfully created video segment at {output_path}")
        return output_path

    except (subprocess.CalledProcessError, OSError) as e:
        Logger.print_error(f"{thread_prefix}Error creating video segment: {str(e)}")
        return None

def create_still_video_with_fade(image_path, audio_path, output_path, thread_id=None):
    """Create a still video with fade effects.
    
    Args:
        image_path: Path to the image file
        audio_path: Path to the audio file
        output_path: Path to save the output video
        thread_id: Optional thread ID for logging
        
    Returns:
        str: Path to the output video if successful, None otherwise
    """
    thread_prefix = f"{thread_id} " if thread_id else ""
    try:
        # Get audio duration
        duration = get_audio_duration(audio_path)
        if duration is None:
            Logger.print_error(f"{thread_prefix}Failed to get audio duration")
            return None

        # Create video with fade using thread manager
        with ffmpeg_thread_manager:
            cmd = [
                "ffmpeg", "-y",
                "-loop", "1",
                "-i", image_path,
                "-i", audio_path,
                "-vf", "fade=t=out:st=25:d=5",
                "-af", f"adelay=3000|3000,afade=t=in:ss=0:d=3,afade=t=out:st={duration}:d=5",
                "-t", str(duration + 4),  # Add 4 seconds for fade effects
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
                "-c:a", "aac",
                "-b:a", "192k",
                output_path
            ]
            result = subprocess.run(
                cmd,
                check=True,
                capture_output=True
            )

        if result.returncode != 0:
            Logger.print_error(f"{thread_prefix}Failed to create video with fade: {result.stderr.decode()}")
            return None

        Logger.print_info(f"{thread_prefix}Successfully created video with fade at {output_path}")
        return output_path

    except (subprocess.CalledProcessError, OSError) as e:
        Logger.print_error(f"{thread_prefix}Error creating video with fade: {str(e)}")
        return None

def create_final_video(video_segments, output_path):
    try:
        concat_list_path = get_tempdir() + "/ttv/concat_list.txt"
        with open(concat_list_path, "w") as f:
            for segment in video_segments:
                f.write(f"file '{segment}'\n")
        Logger.print_info(f"Concatenating video segments: {video_segments}")
        ffmpeg_cmd = [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_list_path,
            "-pix_fmt", "yuv420p", "-c:v", "libx264", "-crf", "23", "-preset", "medium",
            "-c:a", "aac", "-b:a", "192k", output_path
        ]
        result = run_ffmpeg_command(ffmpeg_cmd)
        if result:
            Logger.print_info(f"Main video created: output_path={output_path}")
    except Exception as e:
        Logger.print_error(f"Error concatenating video segments: {e}")

    return output_path

def append_video_segments(video_segments, output_path, thread_id=None):
    """Append multiple video segments together.
    
    Args:
        video_segments: List of video segment paths
        output_path: Path to save the output video
        thread_id: Optional thread ID for logging
        
    Returns:
        str: Path to the output video if successful, None otherwise
    """
    thread_prefix = f"{thread_id} " if thread_id else ""
    try:
        # Re-encode segments with consistent parameters
        reencoded_segments = []
        for i, segment in enumerate(video_segments):
            reencoded_segment = segment.replace(".mp4", "_reencoded.mp4")
            with ffmpeg_thread_manager:
                cmd = [
                    "ffmpeg", "-y",
                    "-i", segment,
                    "-vf", "scale=1024:1024",
                    "-c:v", "libx264",
                    "-c:a", "aac",
                    "-ar", "48000",
                    "-ac", "2",
                    reencoded_segment
                ]
                result = subprocess.run(
                    cmd,
                    check=True,
                    capture_output=True
                )

            if result.returncode != 0:
                Logger.print_error(f"{thread_prefix}Failed to re-encode segment {i}: {result.stderr.decode()}")
                continue

            reencoded_segments.append(reencoded_segment)

        if not reencoded_segments:
            Logger.print_error(f"{thread_prefix}No segments were successfully re-encoded")
            return None

        # Create concat file
        concat_list_path = os.path.join(get_tempdir(), "ttv", "concat_list.txt")
        with open(concat_list_path, "w") as f:
            for segment in reencoded_segments:
                f.write(f"file '{segment}'\n")

        # Concatenate segments using thread manager
        with ffmpeg_thread_manager:
            cmd = [
                "ffmpeg", "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", concat_list_path,
                "-c:v", "libx264",
                "-c:a", "aac",
                "-b:a", "192k",
                "-ar", "48000",
                "-ac", "2",
                output_path
            ]
            result = subprocess.run(
                cmd,
                check=True,
                capture_output=True
            )

        if result.returncode != 0:
            Logger.print_error(f"{thread_prefix}Failed to concatenate segments: {result.stderr.decode()}")
            return None

        Logger.print_info(f"{thread_prefix}Successfully appended video segments to {output_path}")
        return output_path

    except (subprocess.CalledProcessError, OSError) as e:
        Logger.print_error(f"{thread_prefix}Error appending video segments: {str(e)}")
        return None
    finally:
        # Cleanup temporary files
        try:
            if os.path.exists(concat_list_path):
                os.remove(concat_list_path)
            for segment in reencoded_segments:
                if os.path.exists(segment):
                    os.remove(segment)
        except (OSError, UnboundLocalError):
            pass

