from logger import Logger
from .audio_generation import get_audio_duration
from .ffmpeg_wrapper import run_ffmpeg_command
from utils import get_tempdir
from ttv.log_messages import LOG_VIDEO_SEGMENT_CREATE
import os
import uuid

def create_video_segment(image_path, audio_path, output_path=None):
    """Create a video segment from an image and audio file.
    
    Args:
        image_path: Path to the image file
        audio_path: Path to the audio file
        output_path: Optional path for the output video. If not provided, generates one.
        
    Returns:
        str: Path to the created video segment, or None if creation failed
    """
    try:
        if not output_path:
            temp_dir = get_tempdir()
            output_path = os.path.join(temp_dir, "ttv", f"segment_{uuid.uuid4()}.mp4")
        
        Logger.print_info(f"{LOG_VIDEO_SEGMENT_CREATE}={output_path}, audio_path={audio_path}, image_path={image_path}")
        # Get exact audio duration including padding
        duration = get_audio_duration(audio_path)
        
        ffmpeg_cmd = [
            "ffmpeg", "-y",
            "-loop", "1", "-i", image_path,  # Input 1: looped image
            "-i", audio_path,                # Input 2: audio with padding
            "-map", "0:v:0",                 # Map video from first input
            "-map", "1:a:0",                 # Map audio from second input
            "-c:v", "libx264",
            "-tune", "stillimage", 
            "-c:a", "aac",
            "-b:a", "192k",
            "-ar", "48000",
            "-ac", "2",
            "-pix_fmt", "yuv420p",
            "-t", str(duration),             # Exact duration including padding
            output_path
        ]
        result = run_ffmpeg_command(ffmpeg_cmd)
        if result:
            Logger.print_info(f"Video segment created: output_path={output_path}")
            return output_path
        else:
            Logger.print_error("Failed to create video segment")
            return None
    except Exception as e:
        Logger.print_error(f"Error creating video segment: {str(e)}")
        import traceback
        Logger.print_error(f"Traceback: {traceback.format_exc()}")
        return None

def create_still_video_with_fade(image_path, audio_path, output_path):
    Logger.print_info("Creating still video with fade.")
    audio_delay = "adelay=3000|3000"  # Delay audio by 3000ms (3 seconds)
    audio_fade_in = "afade=t=in:ss=0:d=3"  # Fade-in effect over 3 seconds
    audio_fade_out = "afade=t=out:st={}:d=5".format(get_audio_duration(audio_path))  # Fade-out effect starting at the end

    # Combine audio filters
    audio_filters = f"{audio_delay},{audio_fade_in},{audio_fade_out}"

    ffmpeg_cmd = [
        "ffmpeg", "-y", "-loop", "1", "-i", image_path, "-i", audio_path,
        "-vf", "fade=t=out:st=25:d=5", "-af", audio_filters,
        "-t", str(get_audio_duration(audio_path) + 1 + 3),  # Add 3 seconds to the duration for the delay
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", output_path
    ]
    result = run_ffmpeg_command(ffmpeg_cmd)
    if result:
        Logger.print_info(f"Still video with fade created: output_path={output_path}")
    return output_path


def create_final_video(video_segments, output_path):
    try:
        concat_list_path = "/tmp/GANGLIA/ttv/concat_list.txt"
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

def append_video_segments(video_segments, output_path):
    try:
        reencoded_segments = []
        for segment in video_segments:
            reencoded_segment = segment.replace(".mp4", "_reencoded.mp4")
            ffmpeg_cmd = [
                "ffmpeg", "-y", "-i", segment,
                "-vf", "scale=1024:1024", "-c:v", "libx264", "-c:a", "aac", "-ar", "48000", "-ac", "2",
                reencoded_segment
            ]
            Logger.print_info(f"Re-encoding video segment: {segment} to {reencoded_segment}")
            result = run_ffmpeg_command(ffmpeg_cmd)
            if result:
                Logger.print_info(f"Re-encoded video segment created: reencoded_segment={reencoded_segment}")
                reencoded_segments.append(reencoded_segment)
            else:
                Logger.print_error(f"Error re-encoding video segment: {segment}")
                return

        concat_list_path = "/tmp/GANGLIA/ttv/concat_list.txt"
        with open(concat_list_path, "w") as f:
            for segment in reencoded_segments:
                f.write(f"file '{segment}'\n")
        Logger.print_info(f"Appending video segments: {reencoded_segments}")

        ffmpeg_cmd = [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_list_path,
            "-c:v", "libx264",  # Re-encode video to ensure consistent duration
            "-c:a", "aac",      # Re-encode audio to ensure consistent duration
            "-b:a", "192k",     # Consistent audio bitrate
            "-ar", "48000",     # Consistent audio sample rate
            "-ac", "2",         # Consistent audio channels
            output_path
        ]
        result = run_ffmpeg_command(ffmpeg_cmd)
        if result:
            Logger.print_info(f"Final video with closing credits created: output_path={output_path}")
        else:
            Logger.print_error("Error appending re-encoded video segments")

    except Exception as e:
        Logger.print_error(f"Error appending video segments: {e}")

    return output_path

