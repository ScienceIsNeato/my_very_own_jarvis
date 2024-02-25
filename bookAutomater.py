import openai
import os
import requests
from PIL import Image, ImageDraw, ImageFont
import argparse
import subprocess
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Set your OPENAI_API_KEY in the environment variables for security reasons
openai.api_key = os.getenv("OPENAI_API_KEY")

if not openai.api_key:
    logging.error("OpenAI API key not found. Please set the OPENAI_API_KEY environment variable.")
    raise ValueError("OpenAI API key not found. Please set the OPENAI_API_KEY environment variable.")

parser = argparse.ArgumentParser(description='Generate images in a conversational style.')
parser.add_argument('--skip-generation', action='store_true', help='Skip image generation and compile existing images.')
args = parser.parse_args()

# Style setup for the image generation
style = "futuristic 4k grunge"

def generate_image(sentence, style, image_index):
    logging.info(f"Generating image for: '{sentence}' with style '{style}'")
    prompt = f"Create an image that matches the description: '{sentence}', while keeping the style of {style}."
    try:
        response = openai.Image.create(prompt=prompt, n=1, size="1024x1024")
        if response.data:
            image_url = response['data'][0]['url']
            filename = f"/tmp/image_{image_index}.png"  # Save to /tmp/ directory
            save_image_with_caption(image_url, filename, sentence)
            return filename
        else:
            logging.warning(f"No image was returned for the sentence: '{sentence}'")
            return None
    except Exception as e:
        logging.error(f"An error occurred while generating the image: {e}")
        return None

def save_image_with_caption(image_url, filename, caption):
    logging.info(f"Saving image with caption: '{caption}' to {filename}")
    response = requests.get(image_url)
    if response.status_code == 200:
        with open(filename, 'wb') as file:
            file.write(response.content)
        image = Image.open(filename)
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype("Arial.ttf", 20)  # Ensure font path is correct

    caption_area_height = 60  # Adjust as needed
    new_image_height = image.height + caption_area_height
    new_image = Image.new("RGB", (image.width, new_image_height), "white")
    new_image.paste(image, (0, 0))

    text_x = 10
    text_y = image.height + (caption_area_height - 20) // 2  # Adjust text position
    draw = ImageDraw.Draw(new_image)
    draw.text((text_x, text_y), caption, fill="black", font=font)

    new_image.save(filename)
    print(f"Saved {filename} with caption.")

def create_video_from_images(image_count):
    # The filelist now needs to be in /tmp/ as well, or provide the full path
    filelist_path = "/tmp/filelist.txt"
    with open(filelist_path, "w") as filelist:
        for i in range(0, image_count):
            filelist.write(f"file '/tmp/image_{i}.png'\nduration 5\n")

    # The output path for the final video can also be directed to /tmp/ or any desired path
    output_video_path = "/tmp/final_video.mp4"

    # Create a slideshow video from the images
    subprocess.run([
        "ffmpeg", "-f", "concat", "-safe", "0", "-i", filelist_path,
        "-vsync", "vfr", "-pix_fmt", "yuv420p", output_video_path
    ], check=True)

    print(f"Video created as {output_video_path}")

# Main execution
if __name__ == "__main__":
    story = "a banana with a hair dryer. the next moment, the hair dryer is gone"  # Your story text
    sentences = story.split('. ')

    for i, sentence in enumerate(sentences):
        if sentence.strip() and not args.skip_generation:  # Ensure the sentence is not empty and generation is not skipped
            filename = generate_image(sentence.strip(), style, i)
            if filename is None:
                logging.info("Retrying the image generation.")
                filename = generate_image(sentence.strip(), style, i)  # Retry once
                if filename is None:
                    logging.error("Exiting due to consecutive failures in image generation.")
                    break  # Exit if the image generation fails twice consecutively

    if args.skip_generation:
        # If skipping generation, use the number of existing images
        image_count = len([filename for filename in os.listdir('.') if filename.endswith('.png')])
    else:
        image_count = len(sentences)

    create_video_from_images(image_count)
