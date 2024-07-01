import concurrent.futures
import time
from logger import Logger
from music_lib import MusicGenerator
from .image_generation import generate_image, generate_image_for_sentence, generate_blank_image
from .story_generation import generate_movie_poster, generate_filtered_story
from .audio_generation import generate_audio
from .video_generation import create_video_segment
from tts import GoogleTTS

tts = GoogleTTS()

def process_sentence(i, sentence, context, style, total_images, tts, skip_generation, query_dispatcher):
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
        filename, success = generate_image(sentence, context, style, i + 1, total_images, query_dispatcher)
        if not success:
            filename = generate_blank_image(sentence, i)

        Logger.print_info(f"{thread_id} Adding audio for image {i + 1} of {total_images} with input text: '{sentence}'")
        Logger.print_info(f"{thread_id} Creating video segment.")
        video_segment_path = f"/tmp/GANGLIA/ttv/segment_{i}.mp4"
        create_video_segment(filename, audio_path, video_segment_path)

        return video_segment_path, sentence, i
    except Exception as e:
        Logger.print_error(f"{thread_id} Error processing sentence '{sentence}': {e}")
        return None, sentence, i 

def process_story(tts, style, story, skip_generation, query_dispatcher, story_title):
    total_images = len(story)
    Logger.print_info(f"Total images to generate: {total_images}")

    video_segments = [None] * total_images
    context = ""
    music_gen = MusicGenerator()

    with concurrent.futures.ThreadPoolExecutor() as executor:
        full_story_text = " ".join(story)

        Logger.print_info("Submitting background music generation task...")
        background_music_future = executor.submit(
            # TODO: need to move this to the configuration file
            music_gen.generate_music, "ambient 16-bit video game music", "chirp-v3-0", 180, False, None, 5, 60, query_dispatcher
        )

        Logger.print_info("Submitting song with lyrics generation task...")
        song_with_lyrics_future = executor.submit(
            music_gen.generate_music, f"Write a song about this story: {full_story_text} in the style of 90s alternative", "chirp-v3-0", 180, True, story, 5, 60, query_dispatcher
        )

        Logger.print_info("Submitting sentence processing tasks...")
        sentence_futures = [executor.submit(process_sentence, i, sentence, context, style, total_images, tts, skip_generation, query_dispatcher) for i, sentence in enumerate(story)]
        
        # Obtain the filtered story JSON before submitting the movie poster generation task
        filtered_story_json = generate_filtered_story(full_story_text, style, story_title, query_dispatcher)

        Logger.print_info("Submitting movie poster generation task...")
        movie_poster_future = executor.submit(generate_movie_poster, filtered_story_json, style, story_title, query_dispatcher)
        
        for future in concurrent.futures.as_completed(sentence_futures):
            result = future.result()
            if result:
                video_segment_path, sentence, index = result
                video_segments[index] = video_segment_path
                context += f" {sentence}"
        
        # Background music generation status tracking
        background_music_job_id = background_music_future.result()
        if background_music_job_id:
            background_music_path = track_status(music_gen, background_music_job_id)
        else:
            background_music_path = None
            Logger.print_error("Failed to get background music job ID.")
        
        # Song with lyrics generation status tracking
        song_with_lyrics_job_id = song_with_lyrics_future.result()
        if song_with_lyrics_job_id:
            song_with_lyrics_path = track_status(music_gen, song_with_lyrics_job_id)
        else:
            song_with_lyrics_path = None
            Logger.print_error("Failed to get song with lyrics job ID.")
        
        try:
            movie_poster_path = movie_poster_future.result()
            Logger.print_info(f"Movie poster generated: {movie_poster_path}")
        except Exception as e:
            Logger.print_error(f"Error generating movie poster: {e}")
            movie_poster_path = None

    return video_segments, background_music_path, song_with_lyrics_path, movie_poster_path

def track_status(music_gen, job_id):
    status = "submitted"
    while status not in ["complete", "error"]:
        time.sleep(10)  # Poll every 10 seconds
        status_response = music_gen.suno_request_handler.query_job_status(job_id)
        
        # If status_response is a list, handle it appropriately
        if isinstance(status_response, list):
            status_response = status_response[0]  # Assuming the response is a list with one item
        
        status = status_response.get("status", "error")
        if status == "complete":
            Logger.print_info(f"Job {job_id} completed successfully.")
            return status_response.get("audio_url")
        elif status == "error":
            Logger.print_error(f"Job {job_id} failed with message: {status_response.get('message', 'No error message provided')}")
            return None
        Logger.print_info(f"Job {job_id} status: {status}. Retrying in 10 seconds.")
    return None


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
