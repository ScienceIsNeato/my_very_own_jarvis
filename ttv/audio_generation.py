import subprocess
import uuid
import os
from logger import Logger
from utils import get_tempdir

def generate_audio(tts, sentence, silence_padding=0.5):
    """
    Generate audio from text with optional silence padding at start and end.
    
    Args:
        tts: Text-to-speech instance
        sentence: Text to convert to speech
        silence_padding: Seconds of silence to add before and after (default 0.5s)
    """
    try:
        success, file_path = tts.convert_text_to_speech(sentence)
        if success:
            if silence_padding > 0:
                # Create temp path for padded audio
                temp_dir = get_tempdir()
                tts_dir = os.path.join(temp_dir, "tts")
                os.makedirs(tts_dir, exist_ok=True)
                padded_path = os.path.join(tts_dir, f"padded_{os.path.basename(file_path)}")
                
                # Add silence padding using ffmpeg
                cmd = [
                    "ffmpeg", "-y",
                    "-f", "lavfi", "-t", str(silence_padding), "-i", "anullsrc=r=24000:cl=mono",  # Generate silence
                    "-i", file_path,  # Original audio
                    "-f", "lavfi", "-t", str(silence_padding), "-i", "anullsrc=r=24000:cl=mono",  # More silence
                    "-filter_complex", "[0][1][2]concat=n=3:v=0:a=1",  # Concatenate silence + audio + silence
                    "-acodec", "libmp3lame",  # Use MP3 codec
                    padded_path
                ]
                
                try:
                    subprocess.run(cmd, capture_output=True, text=True, check=True)
                    # Remove original file and use padded version
                    os.remove(file_path)
                    file_path = padded_path
                    Logger.print_info(f"Added {silence_padding}s silence padding to audio")
                except subprocess.CalledProcessError as e:
                    Logger.print_error(f"Failed to add silence padding: {e.stderr}")
                    # Keep original file if padding failed
            
            Logger.print_info(f"Audio generation successful for: '{sentence}'. Saved to {file_path}")
            return file_path
        else:
            Logger.print_error(f"Audio generation failed for: '{sentence}'")
            return None
    except (OSError, subprocess.SubprocessError, ValueError) as e:
        Logger.print_error(f"Audio generation failed for: '{sentence}'. Error: {e}")
        return None

def get_audio_duration(audio_file):
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries",
         "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", audio_file],
        stdout=subprocess.PIPE,
        check=True)
    return float(result.stdout)
