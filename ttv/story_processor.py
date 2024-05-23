import concurrent.futures
import time
from logger import Logger
from music_lib import MusicGenerator
from .image_generation import generate_image_for_sentence, generate_blank_image
from .story_generation import generate_movie_poster
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

def process_story(tts, style, story, skip_generation, query_dispatcher):
    total_images = len(story)
    Logger.print_info(f"Total images to generate: {total_images}")

    video_segments = [None] * total_images
    context = ""
    music_gen = MusicGenerator()

    with concurrent.futures.ThreadPoolExecutor() as executor:
        full_story_text = " ".join(story)

        Logger.print_info("Submitting background music generation task...")
        background_music_future = executor.submit(
            music_gen.generate_music, "background music for the final video", "chirp-v3-0", 180, story_text=None, with_lyrics=False, query_dispatcher=query_dispatcher
        )

        Logger.print_info("Submitting song with lyrics generation task...")
        song_with_lyrics_future = executor.submit(
            music_gen.generate_music, f"Write a song about this story: {full_story_text}", "chirp-v3-0", 180, story_text=story, with_lyrics=True, query_dispatcher=query_dispatcher
        )
        Logger.print_info("Submitting sentence processing tasks...")
        sentence_futures = [executor.submit(process_sentence, i, sentence, context, style, total_images, tts, skip_generation) for i, sentence in enumerate(story)]
        
        Logger.print_info("Submitting movie poster generation task...")
        movie_poster_future = executor.submit(generate_movie_poster, context, style, full_story_text)
        
        for future in concurrent.futures.as_completed(sentence_futures):
            result = future.result()
            if result:
                video_segment_path, sentence, index = result
                video_segments[index] = video_segment_path
                context += f" {sentence}"
        
        try:
            background_music_path = background_music_future.result()
            Logger.print_info(f"Background music generated: {background_music_path}")
        except Exception as e:
            Logger.print_error(f"Error generating background music: {e}")
            background_music_path = None
        
        try:
            song_with_lyrics_path = song_with_lyrics_future.result()
            Logger.print_info(f"Song with lyrics generated: {song_with_lyrics_path}")
        except Exception as e:
            Logger.print_error(f"Error generating song with lyrics: {e}")
            song_with_lyrics_path = None
        
        try:
            movie_poster_path = movie_poster_future.result()
            Logger.print_info(f"Movie poster generated: {movie_poster_path}")
        except Exception as e:
            Logger.print_error(f"Error generating movie poster: {e}")
            movie_poster_path = None

    return video_segments, background_music_path, song_with_lyrics_path, movie_poster_path

def retry_on_rate_limit(func, *args, retries=5, wait_time=60, **kwargs):
    for attempt in range(retries):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if 'Rate limit exceeded' in str(e):
                Logger.print_error(f"Rate limit exceeded. Retrying in {wait_time} seconds... (Attempt {attempt + 1} of {retries})")
                time.sleep(wait_time)
            else:
                raise e
    raise Exception(f"Failed to complete {func.__name__} after {retries} attempts due to rate limiting.")
