import time
import openai
import os
import requests
from PIL import Image, ImageDraw, ImageFont
import argparse
import subprocess
import logging
import json
from datetime import datetime
from tts import GoogleTTS
import textwrap
from logger import Logger
from music_lib import MusicGenerator  # Import the new music generation library

# Function to load JSON input
def load_input(ttv_config):
    with open(ttv_config, 'r') as json_file:
        data = json.load(json_file)
    return data['style'], data['story']

def generate_image(sentence, context, style, image_index, total_images):
    Logger.print_debug(f"Generating image for: '{sentence}' using a style of '{style}' DALL·E 3")
    # Incorporate both the specific sentence and the accumulated context into the prompt
    prompt = f"With the context of: {context}. Create an image that matches the description: '{sentence}', while keeping the style of {style}."
    try:
        response = openai.Image.create(
            model="dall-e-3",
            prompt=prompt,
            size="1024x1024",
            quality="hd",  # Can be "standard" or "hd" for DALL·E 3
            n=1
        )
        if response.data:
            image_url = response['data'][0]['url']
            filename = f"/tmp/image_{image_index}.png"  # Save to /tmp/ directory
            save_image_with_caption(image_url, filename, sentence, image_index, total_images)
            
            return filename, True  # Return True to indicate success
        else:
            Logger.print_error(f"No image was returned for the sentence: '{sentence}'")
            return None, False  # Return False to indicate failure
    except Exception as e:
        Logger.print_error(f"An error occurred while generating the image: {e}")
        return None, False

def save_image_with_caption(image_url, filename, caption, current_step, total_steps):
    start_time = datetime.now()
    Logger.print_info(f"Starting to save image with caption: '{caption}' to {filename}")

    # Download the image
    download_start_time = datetime.now()
    response = requests.get(image_url)
    if response.status_code == 200:
        with open(filename, 'wb') as file:
            file.write(response.content)
    download_end_time = datetime.now()
    Logger.print_info(f"Image downloaded in {(download_end_time - download_start_time).total_seconds()} seconds.")

    # Load the image
    image = Image.open(filename)
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype("Arial.ttf", 20)

    # Wrap text
    margin = 10
    max_width = image.width - 2 * margin
    wrapped_text = textwrap.fill(caption, width=40)  # Adjust 'width' as needed
    wrapped_text += f" ({current_step}/{total_steps})"  # Add step information

    # Calculate text size and create a new image with extra space for text
    text_size = draw.textsize(wrapped_text, font=font)
    text_height = text_size[1] * wrapped_text.count('\n') + margin * (wrapped_text.count('\n') + 1)  # Adjust spacing between lines
    new_image_height = image.height + text_height + margin * 2
    new_image = Image.new("RGB", (image.width, new_image_height), "white")
    new_image.paste(image, (0, 0))

    # Draw text on the new image
    draw = ImageDraw.Draw(new_image)
    draw.multiline_text((margin, image.height + margin), wrapped_text, fill="black", font=font, spacing=5)  # Adjust spacing if needed

    # Save the new image
    saving_start_time = datetime.now()
    new_image.save(filename)
    saving_end_time = datetime.now()
    Logger.print_info(f"Image saved in {(saving_end_time - saving_start_time).total_seconds()} seconds.")

    end_time = datetime.now()
    Logger.print_info(f"Total time to save image with caption: {(end_time - start_time).total_seconds()} seconds. Saved to {filename}")

def get_audio_duration(audio_file):
    """
    Get the duration of an audio file using ffprobe.
    """
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries",
         "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", audio_file],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT
    )
    return float(result.stdout)

def create_video_segment(image_path, audio_path, output_path):
    """
    Create a video segment from an image and an audio file, suppressing ffmpeg verbose output.
    """
    Logger.print_info("ffmpeg started for creating video segment.")
    try:
        subprocess.run([
            "ffmpeg", "-y", "-loop", "1", "-i", image_path, "-i", audio_path,
            "-c:v", "libx264", "-tune", "stillimage", "-c:a", "aac", "-b:a", "192k",
            "-pix_fmt", "yuv420p", "-shortest", "-t", str(get_audio_duration(audio_path) + 1), output_path
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        Logger.print_info("ffmpeg stopped with success for creating video segment.")
    except subprocess.CalledProcessError as e:
        Logger.print_error("ffmpeg failed with error: {}".format(e))

def create_final_video(video_segments, output_path):
    """
    Concatenate video segments into a final video with re-encoding to ensure compatibility,
    suppressing ffmpeg verbose output.
    """
    Logger.print_info("ffmpeg started for creating final video.")
    with open("/tmp/concat_list.txt", "w") as f:
        for segment in video_segments:
            f.write(f"file '{segment}'\n")
    try:
        subprocess.run([
            "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", "/tmp/concat_list.txt",
            "-pix_fmt", "yuv420p", "-c:v", "libx264", "-crf", "23", "-preset", "medium", 
            "-c:a", "aac", "-b:a", "192k", output_path
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        Logger.print_info("ffmpeg stopped with success for creating final video.")
    except subprocess.CalledProcessError as e:
        Logger.print_error(f"ffmpeg failed with error: {e}")

def add_background_music(video_path, music_path, output_path):
    """
    Add background music to the final video.
    """
    Logger.print_info("ffmpeg started for adding background music to final video.")
    try:
        subprocess.run([
            "ffmpeg", "-y", "-i", video_path, "-i", music_path, "-filter_complex",
            "[0:a][1:a]amix=inputs=2:duration=first:dropout_transition=2", "-c:v", "copy",
            "-c:a", "aac", "-b:a", "192k", output_path
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        Logger.print_info("ffmpeg stopped with success for adding background music.")
    except subprocess.CalledProcessError as e:
        Logger.print_error(f"ffmpeg failed with error: {e}")

def generate_blank_image(sentence, image_index):
    # Code to generate a blank image
    blank_image = Image.new('RGB', (1024, 1024), 'white') 

    # Code to add caption to blank image
    draw = ImageDraw.Draw(blank_image)
    font = ImageFont.truetype("Arial.ttf", 36)
    draw.text((20, 20), sentence, fill='black', font=font)

    # Save blank image 
    blank_filename = f"/tmp/blank_image_{image_index}.png"
    blank_image.save(blank_filename)

    return blank_filename

def generate_music():
    music_gen = MusicGenerator()
    description_prompt = "a song for a fine scottish evening"
    duration = 180  # Hardcoded duration for simplicity, adjust as needed

    response = music_gen.generate_music(description_prompt, duration=duration)
    if 'error' in response:
        Logger.print_error(f"Music generation error: {response['message']}")
        return None
    
    song_id = response['data'][0]['song_id']
    Logger.print_info(f"Generated Song ID for music: {song_id}")

    # Polling the status until the song is ready
    status = "queued"
    while status in ["queued", "processing", "streaming"]:
        time.sleep(5)
        status_response = music_gen.query_music_status(song_id)
        status = status_response['data']['status']
        Logger.print_info(f"Current music generation status: {status}")

    if status == "complete":
        audio_url = status_response['data']['audio_url']
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_path = f"/tmp/ken_burns_music_{timestamp}.mp3"
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        if music_gen.download_audio(audio_url, output_path):
            Logger.print_info(f"Music downloaded to {output_path}")
            return output_path
        else:
            Logger.print_error("Failed to download music.")
            return None
    else:
        Logger.print_error("Music generation failed or was not completed.")
        return None

def text_to_video(ttv_config, skip_generation):
    # Initialize TTS
    tts = GoogleTTS()

    # Load JSON input
    style, story = load_input(ttv_config)

    # Prepare for processing
    video_segments = []
    context = ""  # Maintain context for image generation
    total_images = len(story)

    Logger.print_info(f"Total images to generate: {total_images}")

    for i, sentence in enumerate(story):
        if skip_generation:
            Logger.print_info("Skipping image generation as per the flag.")
            # Assuming you have a way to handle skipped generation, e.g., using existing images or placeholders
            continue

        # Generate audio for the sentence first
        audio_success, audio_path = tts.convert_text_to_speech(sentence)
        if audio_success:
            Logger.print_info(f"Audio generation successful for: '{sentence}'. Saved to {audio_path}")
        else:
            Logger.print_error(f"Audio generation failed for: '{sentence}'. Skipping this sentence.")
            continue  # Skip this iteration if audio generation fails

        # Generate image with updated method signature
        filename, success = generate_image(sentence, context, style, i + 1, total_images)

        if not success:
            logging.warning(f"Image generation failed for: '{sentence}'. Generating blank image.")
            filename = generate_blank_image(sentence, i)

        # Create video segment using the image and audio
        video_segment_path = f"/tmp/segment_{i}.mp4"
        create_video_segment(filename, audio_path, video_segment_path)
        video_segments.append(video_segment_path)

        # Update context
        context += f" {sentence}"

    if video_segments:
        # Concatenate video segments into the final video
        final_video_path = "/tmp/final_video.mp4"
        create_final_video(video_segments, final_video_path)
        Logger.print_info(f"Final video created at {final_video_path}")

        # Generate background music
        music_path = generate_music()
        if music_path:
            # Add background music to the final video
            final_video_with_music_path = "/tmp/final_video_with_music.mp4"
            add_background_music(final_video_path, music_path, final_video_with_music_path)
            Logger.print_info(f"Final video with background music created at {final_video_with_music_path}")

            # Optionally play the final video with background music
            Logger.print_info("Playing the final video with background music.")
            subprocess.run(["ffplay", "-autoexit", final_video_with_music_path])
        else:
            Logger.print_error("Background music generation failed. Playing final video without background music.")
            subprocess.run(["ffplay", "-autoexit", final_video_path])
    else:
        Logger.print_error("No video segments were created. Final video not generated.")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate and test music creation.")
    parser.add_argument('--log-level', default='INFO', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                        help='Set the logging level')

    args = parser.parse_args()
    log_level = getattr(logging, args.log_level.upper(), logging.INFO)
    text_to_video('path/to/your/config.json', skip_generation=False)  # Update with actual path to your JSON config
