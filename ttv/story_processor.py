import concurrent.futures
import time
import os
import json
from logger import Logger
from music_lib import MusicGenerator
from .image_generation import generate_image, generate_blank_image, save_image_without_caption
from .story_generation import generate_movie_poster, generate_filtered_story
from .audio_generation import generate_audio
from .video_generation import create_video_segment
from .captions import CaptionEntry, create_dynamic_captions
from .audio_alignment import create_word_level_captions
from tts import GoogleTTS
from utils import get_tempdir

tts = GoogleTTS()

def process_sentence(i, sentence, context, style, total_images, tts, skip_generation, query_dispatcher):
    thread_id = f"[Thread-{i}]"
    try:
        if skip_generation:
            Logger.print_info(f"{thread_id} Skipping image generation as per the flag.")
            return None, sentence, i

        Logger.print_info(f"{thread_id} Converting text to speech...")
        audio_path = generate_audio(tts, sentence)
        if not audio_path:
            Logger.print_error(f"{thread_id} Failed to generate audio for sentence: {sentence}")
            return None, sentence, i

        Logger.print_info(f"{thread_id} Generating image for sentence.")
        filename, success = generate_image(sentence, context, style, i + 1, total_images, query_dispatcher)
        if not success:
            Logger.print_warning(f"{thread_id} Image generation failed, using blank image.")
            filename = generate_blank_image(sentence, i)
        else:
            # Save image without caption since we'll add dynamic captions later
            temp_image = filename.replace(".png", "_nocaption.png")
            if not save_image_without_caption(filename, temp_image):
                Logger.print_error(f"{thread_id} Failed to save image without caption")
                return None, sentence, i
            filename = temp_image

        Logger.print_info(f"{thread_id} Creating initial video segment.")
        temp_dir = get_tempdir()
        initial_segment_path = os.path.join(temp_dir, "ttv", f"segment_{i}_initial.mp4")
        if not create_video_segment(filename, audio_path, initial_segment_path):
            Logger.print_error(f"{thread_id} Failed to create video segment")
            return None, sentence, i

        # Add dynamic captions using word-level alignment
        Logger.print_info(f"{thread_id} Adding dynamic captions to video segment.")
        try:
            captions = create_word_level_captions(audio_path, sentence)
            if not captions:
                Logger.print_error(f"{thread_id} Failed to create word-level captions")
                return None, sentence, i
        except Exception as e:
            Logger.print_error(f"{thread_id} Error creating word-level captions: {e}")
            return None, sentence, i

        final_segment_path = os.path.join(temp_dir, "ttv", f"segment_{i}.mp4")
        captioned_path = create_dynamic_captions(
            input_video=initial_segment_path,
            captions=captions,
            output_path=final_segment_path,
            min_font_size=32,
            max_font_size=48,
            box_color="black@0",  # Fully transparent background
            position="bottom",
            margin=40,
            max_window_height_ratio=0.3
        )

        if captioned_path:
            return captioned_path, sentence, i
        else:
            Logger.print_error(f"{thread_id} Failed to add captions, using uncaptioned video")
            return initial_segment_path, sentence, i

    except Exception as e:
        Logger.print_error(f"{thread_id} Error processing sentence '{sentence}': {str(e)}")
        import traceback
        Logger.print_error(f"{thread_id} Traceback: {traceback.format_exc()}")
        return None, sentence, i

def process_story(tts, style, story, skip_generation, query_dispatcher, story_title, config=None):
    """
    Process a story by generating images, audio, and video segments.
    
    Args:
        tts: Text-to-speech interface
        style: Style for image generation
        story: List of story sentences
        skip_generation: Whether to skip generation steps
        query_dispatcher: Query dispatcher for API calls
        story_title: Title of the story
        config: Optional dictionary containing configuration options including music settings
    """
    total_images = len(story)
    Logger.print_info(f"Total images to generate: {total_images}")

    video_segments = [None] * total_images
    context = ""
    music_gen = MusicGenerator()

    with concurrent.futures.ThreadPoolExecutor() as executor:
        # Create a properly formatted story JSON for the movie poster
        try:
            filtered_story_json = json.dumps({
                "style": style,
                "title": story_title,
                "story": story  # Pass the list of sentences, not the joined text
            })
            Logger.print_info(f"Created story JSON for movie poster: {filtered_story_json}")
        except Exception as e:
            Logger.print_error(f"Error creating story JSON: {str(e)}")
            filtered_story_json = None

        Logger.print_info("Submitting background music generation task...")
        background_music_enabled = False
        background_music_prompt = None
        background_music_path = None
        if config and config.background_music:
            for source in config.background_music.sources:
                if source.enabled:
                    if source.type == "file":
                        background_music_path = source.path
                        break
                    elif source.type == "prompt":
                        background_music_enabled = True
                        background_music_prompt = source.prompt
                        break

        # Get closing credits music configuration
        closing_credits_enabled = False
        closing_credits_prompt = None
        closing_credits_path = None
        if config and config.closing_credits:
            for source in config.closing_credits.sources:
                if source.enabled:
                    if source.type == "file":
                        closing_credits_path = source.path
                        break
                    elif source.type == "prompt":
                        closing_credits_enabled = True
                        closing_credits_prompt = source.prompt
                        break

        # Submit background music generation if enabled and no file path provided
        background_music_future = None
        if not skip_generation and background_music_enabled and not background_music_path:
            Logger.print_info("Generating background music...")
            background_music_future = executor.submit(
                music_gen.generate_music,
                prompt=background_music_prompt,
                model="chirp-v3-0",
                duration=20,
                with_lyrics=False
            )

        # Submit song with lyrics generation if enabled and no file path provided
        song_with_lyrics_future = None
        if not skip_generation and closing_credits_enabled and not closing_credits_path:
            Logger.print_info("Generating closing credits music...")
            song_with_lyrics_future = executor.submit(
                music_gen.generate_music,
                prompt=closing_credits_prompt,
                model="chirp-v3-0",
                duration=20,
                with_lyrics=True,
                story_text="\n".join(story),  # Join story sentences with newlines
                query_dispatcher=query_dispatcher
            )
        else:
            Logger.print_info("Using file-based music, skipping lyrics generation.")

        Logger.print_info("Submitting sentence processing tasks...")
        sentence_futures = [executor.submit(process_sentence, i, sentence, context, style, total_images, tts, skip_generation, query_dispatcher) for i, sentence in enumerate(story)]
        
        if filtered_story_json:
            Logger.print_info("Submitting movie poster generation task...")
            movie_poster_future = executor.submit(generate_movie_poster, filtered_story_json, style, story_title, query_dispatcher)
        else:
            Logger.print_warning("Skipping movie poster generation due to JSON creation error")
            movie_poster_future = None
        
        for future in concurrent.futures.as_completed(sentence_futures):
            result = future.result()
            if result:
                video_segment_path, sentence, index = result
                video_segments[index] = video_segment_path
                context += f" {sentence}"
        
        # Get the background music path from future if we generated it
        if not background_music_path and background_music_future:
            background_music_path = background_music_future.result()
            if not background_music_path:
                Logger.print_error("Failed to generate background music.")
        
        # Get the song with lyrics path from future if we generated it
        if not closing_credits_path and song_with_lyrics_future:
            closing_credits_path = song_with_lyrics_future.result()
            if not closing_credits_path:
                Logger.print_error("Failed to generate song with lyrics.")
        
        # Get the movie poster path
        movie_poster_path = None
        if movie_poster_future:
            try:
                movie_poster_path = movie_poster_future.result()
                if movie_poster_path:
                    Logger.print_info(f"Movie poster generated: {movie_poster_path}")
                else:
                    Logger.print_error("Movie poster generation returned None")
            except Exception as e:
                Logger.print_error(f"Error generating movie poster: {str(e)}")
                import traceback
                Logger.print_error(f"Traceback: {traceback.format_exc()}")

    return video_segments, background_music_path, closing_credits_path, movie_poster_path


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
