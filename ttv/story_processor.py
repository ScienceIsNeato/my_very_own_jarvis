import concurrent.futures
import logging
from logger import Logger
from music_lib import MusicGenerator
from .image_generation import generate_image_for_sentence, generate_blank_image
from .audio_generation import generate_audio
from .video_generation import create_video_segment
from tts import GoogleTTS

tts = GoogleTTS()

def process_sentence(i, sentence, context, style, total_images, tts, skip_generation):
    thread_id = f"[Thread-{i}]"
    try:
        if skip_generation:
            Logger.print_info(f"{thread_id} Skipping image generation as per the flag.")
            return None

        Logger.print_info(f"{thread_id} Converting text to speech...")
        audio_path = generate_audio(tts, sentence)
        if not audio_path:
            return None, sentence, i  # Ensure it returns 3 values

        Logger.print_info(f"{thread_id} Generating image for sentence.")
        filename = generate_image_for_sentence(sentence, context, style, i + 1, total_images)
        if not filename:
            filename = generate_blank_image(sentence, i)

        Logger.print_info(f"{thread_id} Adding audio for image {i + 1} of {total_images} with input text: '{sentence}'")
        Logger.print_info(f"{thread_id} Creating video segment.")
        video_segment_path = f"/tmp/GANGLIA/ttv/segment_{i}.mp4"
        create_video_segment(filename, audio_path, video_segment_path)

        return video_segment_path, sentence, i
    except Exception as e:
        Logger.print_error(f"{thread_id} Error processing sentence '{sentence}': {e}")
        return None, sentence, i  # Ensure it returns 3 values


def process_story(tts, style, story, skip_generation):
    total_images = len(story)
    Logger.print_info(f"Total images to generate: {total_images}")
    
    video_segments = [None] * total_images
    context = ""

    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [executor.submit(process_sentence, i, sentence, context, style, total_images, tts, skip_generation) for i, sentence in enumerate(story)]
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            if result:
                video_segment_path, sentence, index = result
                video_segments[index] = video_segment_path
                context += f" {sentence}"

    return video_segments, context


def generate_music_concurrently(full_story_text):
    try:
        music_gen = MusicGenerator()
        with concurrent.futures.ThreadPoolExecutor() as executor:
            logging.info("Submitting music generation tasks...")
            background_music_future = executor.submit(music_gen.generate_instrumental_music, "background music for the final video", "chirp-v3-0", 180)
            song_with_lyrics_future = executor.submit(music_gen.generate_song_with_lyrics, f"Write a song about this story: {full_story_text}", "chirp-v3-0", 180)

            music_path = background_music_future.result()
            logging.info(f"Background music generated: {music_path}")

            song_with_lyrics_path = song_with_lyrics_future.result()
            logging.info(f"Song with lyrics generated: {song_with_lyrics_path}")

        return music_path, song_with_lyrics_path
    except Exception as e:
        logging.error(f"Error generating music concurrently: {e}")
        return None, None