import openai
import os
import requests
from PIL import Image, ImageDraw, ImageFont
import argparse
import subprocess
import logging
import json
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Set your OPENAI_API_KEY in the environment variables for security reasons
openai.api_key = os.getenv("OPENAI_API_KEY")

if not openai.api_key:
    logging.error("OpenAI API key not found. Please set the OPENAI_API_KEY environment variable.")
    raise ValueError("OpenAI API key not found. Please set the OPENAI_API_KEY environment variable.")

parser = argparse.ArgumentParser(description='Generate images in a conversational style.')
parser.add_argument('--skip-generation', action='store_true', help='Skip image generation and compile existing images.')
parser.add_argument('--json-input', type=str, help='Path to the JSON input file', required=True)

args = parser.parse_args()

# Function to load JSON input
def load_input(json_input_path):
    with open(json_input_path, 'r') as json_file:
        data = json.load(json_file)
    return data['style'], data['story']

def generate_image(sentence, context, style, image_index, total_images):
    logging.info(f"Generating image for: '{sentence}' with context '{context}' and style '{style}' using DALL·E 3")
    # Incorporate both the specific sentence and the accumulated context into the prompt
    prompt = f"With the context of: {context}. Create an image that matches the description: '{sentence}', while keeping the style of {style}."
    try:
        response = openai.Image.create(
            model="dall-e-3",
            prompt=prompt,
            size="1792x1024",
            quality="hd",  # Can be "standard" or "hd" for DALL·E 3
            n=1
        )
        if response.data:
            image_url = response['data'][0]['url']
            filename = f"/tmp/image_{image_index}.png"  # Save to /tmp/ directory
            save_image_with_caption(image_url, filename, sentence, image_index, total_images)
            
            return filename, True  # Return True to indicate success
        else:
            logging.warning(f"No image was returned for the sentence: '{sentence}'")
            return None, False  # Return False to indicate failure
    except Exception as e:
        logging.error(f"An error occurred while generating the image: {e}")
        return None, False

def save_image_with_caption(image_url, filename, caption, current_step, total_steps):
    start_time = datetime.now()
    logging.info(f"Starting to save image with caption: '{caption}' to {filename}")

    # Measure downloading time
    download_start_time = datetime.now()
    response = requests.get(image_url)
    if response.status_code == 200:
        with open(filename, 'wb') as file:
            file.write(response.content)
    download_end_time = datetime.now()
    logging.info(f"Image downloaded in {(download_end_time - download_start_time).total_seconds()} seconds.")

    # Measure image processing time
    processing_start_time = datetime.now()
    image = Image.open(filename)
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype("Arial.ttf", 20)  # Ensure font path is correct

    caption_area_height = 60  # Adjust as needed
    new_image_height = image.height + caption_area_height
    new_image = Image.new("RGB", (image.width, new_image_height), "white")
    new_image.paste(image, (0, 0))

    text_x = 10
    text_y = image.height + (caption_area_height - 20) // 2

    # Update the caption to include the relative progress
    updated_caption = f"{caption} ({current_step}/{total_steps})"

    draw = ImageDraw.Draw(new_image)
    draw.text((text_x, text_y), updated_caption, fill="black", font=font)

    processing_end_time = datetime.now()
    logging.info(f"Image processing (including drawing caption) completed in {(processing_end_time - processing_start_time).total_seconds()} seconds.")

    # Measure saving time
    saving_start_time = datetime.now()
    new_image.save(filename)
    saving_end_time = datetime.now()
    logging.info(f"Image saved in {(saving_end_time - saving_start_time).total_seconds()} seconds.")

    end_time = datetime.now()
    logging.info(f"Total time to save image with caption: {(end_time - start_time).total_seconds()} seconds. Saved to {filename}")


def create_video_from_images(image_count):
    filelist_path = "/tmp/filelist.txt"
    missing_files = 0

    with open(filelist_path, "w") as filelist:
        for i in range(image_count):
            image_path = f"/tmp/image_{i}.png"
            if os.path.exists(image_path):
                filelist.write(f"file '{image_path}'\nduration 4\n")
            else:
                logging.warning(f"Image file {image_path} not found. Skipping...")
                missing_files += 1

        # Ensure the last image (if exists) stays for the duration
        if image_count - missing_files > 0:
            last_image_path = f"/tmp/image_{image_count - missing_files - 1}.png"
            filelist.write(f"file '{last_image_path}'\nduration 4\n")

    output_video_path = "/tmp/final_video.mp4"

    # Run ffmpeg only if there's at least one image file
    if image_count - missing_files > 0:
        subprocess.run([
            "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", filelist_path,
            "-vsync", "vfr", "-pix_fmt", "yuv420p", output_video_path
        ], check=True)
        logging.info(f"Video created as {output_video_path}")
    else:
        logging.error("No images were found for video creation.")

def generate_blank_image(sentence, image_index):
    # Code to generate a blank image
    blank_image = Image.new('RGB', (1024, 768), 'white') 

    # Code to add caption to blank image
    draw = ImageDraw.Draw(blank_image)
    font = ImageFont.truetype("Arial.ttf", 36)
    draw.text((20, 20), sentence, fill='black', font=font)

    # Save blank image 
    blank_filename = f"/tmp/blank_image_{image_index}.png"
    blank_image.save(blank_filename)

    return blank_filename

if __name__ == "__main__":
    # Load style and story from JSON input
    style, story = load_input(args.json_input)

    context = ""  # Start with an empty context
    success_count = 0  # To keep track of successful image generations

    total_images = len(story)
    for i, sentence in enumerate(story):
        if sentence.strip() and not args.skip_generation:
            filename, success = generate_image(sentence.strip(), context, style, i + 1, total_images)
            if success:
                success_count += 1
                # Update context with the current sentence for continuity in subsequent images
                context += (" " + sentence.strip()) if context else sentence.strip()
            else:
                logging.warning("Image generation failed. Generating blank image with caption.")
                filename = generate_blank_image(sentence, i)

                progress = (i/total_images)*100
                logging.info(f"Progress: {progress:.1f}%")
    if success_count > 0:
        create_video_from_images(success_count)
    else:
        logging.error("No images were successfully generated.")

    # Automatically play the video at the end of the script
    logging.info("Playing the video.")
    subprocess.run(["ffplay", "-autoexit", "/tmp/final_video.mp4"])
