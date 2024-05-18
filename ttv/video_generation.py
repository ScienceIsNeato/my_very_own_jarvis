import subprocess
from logger import Logger
from .audio_generation import get_audio_duration
from .ffmpeg_wrapper import run_ffmpeg_command

def create_video_segment(image_path, audio_path, output_path):
    Logger.print_info("Creating video segment.")
    ffmpeg_cmd = [
        "ffmpeg", "-y", "-loop", "1", "-i", image_path, "-i", audio_path,
        "-c:v", "libx264", "-tune", "stillimage", "-c:a", "aac", "-b:a", "192k",
        "-pix_fmt", "yuv420p", "-shortest", "-t", str(get_audio_duration(audio_path) + 1), output_path
    ]
    result = run_ffmpeg_command(ffmpeg_cmd)
    if result:
        Logger.print_info(f"Video segment created at {output_path}")

def create_still_video_with_fade(image_path, audio_path, output_path):
    Logger.print_info("Creating still video with fade.")
    ffmpeg_cmd = [
        "ffmpeg", "-y", "-loop", "1", "-i", image_path, "-i", audio_path,
        "-vf", "fade=t=out:st=25:d=5", "-t", "30", "-c:v", "libx264",
        "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", output_path
    ]
    result = run_ffmpeg_command(ffmpeg_cmd)
    if result:
        Logger.print_info(f"Still video with fade created at {output_path}")

def create_final_video(video_segments, output_path):
    Logger.print_info("ffmpeg started for creating final video.")
    with open("/tmp/GANGLIA/ttv/concat_list.txt", "w") as f:
        for segment in video_segments:
            f.write(f"file '{segment}'\n")
    try:
        subprocess.run([
            "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", "/tmp/GANGLIA/ttv/concat_list.txt",
            "-pix_fmt", "yuv420p", "-c:v", "libx264", "-crf", "23", "-preset", "medium", 
            "-c:a", "aac", "-b:a", "192k", output_path
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        Logger.print_info("ffmpeg stopped with success for creating final video.")
    except subprocess.CalledProcessError as e:
        Logger.print_error(f"ffmpeg failed with error: {e}")

def append_video_segments(video_segments, output_path):
    with open("/tmp/GANGLIA/ttv/concat_list.txt", "w") as f:
        for segment in video_segments:
            f.write(f"file '{segment}'\n")
    try:
        subprocess.run([
            "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", "/tmp/GANGLIA/ttv/concat_list.txt",
            "-pix_fmt", "yuv420p", "-c:v", "libx264", "-crf", "23", "-preset", "medium", 
            "-c:a", "aac", "-b:a", "192k", output_path
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        Logger.print_info(f"Final video with closing credits created at {output_path}")
        subprocess.run(["ffplay", "-autoexit", output_path])
    except subprocess.CalledProcessError as e:
        Logger.print_error(f"ffmpeg failed with error: {e}")
