import subprocess
from logger import Logger

def run_ffmpeg_command(ffmpeg_cmd):
    try:
        Logger.print_info(f"Running ffmpeg command: {' '.join(ffmpeg_cmd)}")
        result = subprocess.run(ffmpeg_cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        Logger.print_info(f"ffmpeg output: {result.stdout.decode('utf-8')}")
        return result
    except subprocess.CalledProcessError as e:
        Logger.print_error(f"ffmpeg failed with error: {e.stderr.decode('utf-8')}")
        Logger.print_error(f"ffmpeg command was: {' '.join(ffmpeg_cmd)}")
        return None
