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
from .captions import CaptionEntry, create_dynamic_captions, create_static_captions
from .audio_alignment import create_word_level_captions
from tts import GoogleTTS
from utils import get_tempdir
import subprocess
from concurrent.futures import ThreadPoolExecutor

tts = GoogleTTS()

def process_sentence(i, sentence, context, style, total_images, tts, skip_generation, query_dispatcher, config):
    """Process a single sentence into a video segment with audio and captions.

    This function handles the complete pipeline for converting a single sentence into a video segment:
    1. Generates or loads an image based on the sentence
    2. Generates audio narration for the sentence
    3. Creates a video segment combining the image and audio
    4. Adds captions to the video segment (either static or dynamic based on config)

    Args:
        i (int): Index of the sentence in the story sequence
        sentence (str): The sentence text to process
        context (str): Additional context to help with image generation
        style (str): The visual style to use for image generation
        total_images (int): Total number of images/sentences in the story
        tts (GoogleTTS): Text-to-speech interface for audio generation
        skip_generation (bool): If True, generates blank images instead of using DALL-E
        query_dispatcher (QueryDispatcher): Interface for making API calls
        config (Config): Configuration object containing settings for image/caption generation

    Returns:
        tuple: A tuple containing (video_path, index) where:
            - video_path (str or None): Path to the generated video segment, or None if generation failed
            - index (int): The original sentence index
            
    Note:
        The function may return (None, index) at various points if any step fails:
        - Image generation/loading fails
        - Audio generation fails
        - Video segment creation fails
        - Caption addition fails (falls back to uncaptioned video)
    """
    thread_id = f"[Thread {i+1}/{total_images}]"
    Logger.print_info(f"{thread_id} Processing sentence: {sentence}")

    # Create necessary directories
    temp_dir = get_tempdir()
    os.makedirs(os.path.join(temp_dir, "ttv"), exist_ok=True)
    os.makedirs(os.path.join(temp_dir, "tts"), exist_ok=True)
    os.makedirs(os.path.join(temp_dir, "images"), exist_ok=True)

    # Get preloaded images directory from config
    preloaded_images_dir = config.get("preloaded_images_dir")

    # Generate image for this sentence
    filename = None
    if skip_generation:
        filename = generate_blank_image(sentence, i, thread_id=thread_id)
    else:
        filename, success = generate_image(
            sentence, 
            context, 
            style, 
            i, 
            total_images, 
            query_dispatcher, 
            preloaded_images_dir=preloaded_images_dir,
            thread_id=thread_id
        )
        if not success:
            return None, i
    if not filename:
        return None, i

    # Generate audio for this sentence
    Logger.print_info(f"{thread_id} Generating audio for sentence.")
    success, audio_path = tts.convert_text_to_speech(sentence, thread_id=thread_id)
    if not success:
        Logger.print_error(f"{thread_id} Failed to generate audio")
        return None, i

    # Create initial video segment
    Logger.print_info(f"{thread_id} Creating initial video segment.")
    temp_dir = get_tempdir()
    initial_segment_path = os.path.join(temp_dir, "ttv", f"segment_{i}_initial.mp4")
    if not create_video_segment(filename, audio_path, initial_segment_path):
        Logger.print_error(f"{thread_id} Failed to create video segment")
        return None, i

    # Get caption style from config
    caption_style = getattr(config, 'caption_style', 'static')

    if caption_style == "dynamic":
        # Add dynamic captions using word-level alignment
        Logger.print_info(f"{thread_id} Adding dynamic captions to video segment.")
        try:
            captions = create_word_level_captions(audio_path, sentence)
            if not captions:
                Logger.print_error(f"{thread_id} Failed to create word-level captions")
                return None, i
        except Exception as e:
            Logger.print_error(f"{thread_id} Error creating word-level captions: {e}")
            return None, i

        final_segment_path = os.path.join(temp_dir, "ttv", f"segment_{i}.mp4")
        captioned_path = create_dynamic_captions(
            input_video=initial_segment_path,
            captions=captions,
            output_path=final_segment_path,
            min_font_size=32,
            max_font_size=48
        )

        if captioned_path:
            Logger.print_info(f"{thread_id} Successfully added dynamic captions")
            return captioned_path, i
        else:
            Logger.print_error(f"{thread_id} Failed to add captions, using uncaptioned video")
            return initial_segment_path, i
    else:
        # Add static captions
        Logger.print_info(f"{thread_id} Adding static captions to video segment.")
        final_segment_path = os.path.join(temp_dir, "ttv", f"segment_{i}.mp4")
        captions = [CaptionEntry(sentence, 0.0, float('inf'))]  # Show for entire duration
        captioned_path = create_static_captions(
            input_video=initial_segment_path,
            captions=captions,
            output_path=final_segment_path,
            font_size=40
        )

        if captioned_path:
            Logger.print_info(f"{thread_id} Successfully added static captions")
            return captioned_path, i
        else:
            Logger.print_error(f"{thread_id} Failed to add captions, using uncaptioned video")
            return initial_segment_path, i

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

        # Calculate estimated total duration based on average sentence duration
        estimated_duration = len(story) * 5  # Estimate 5 seconds per sentence
        Logger.print_info(f"Estimated total duration: {estimated_duration} seconds")

        # Submit background music generation task early
        background_music_path = None
        background_music_future = None
        if config and config.background_music:
            file_path = getattr(config.background_music, 'file', '')
            prompt = getattr(config.background_music, 'prompt', '')
            if file_path:
                background_music_path = file_path
                Logger.print_info(f"Using file-based background music: {background_music_path}")
            elif prompt:
                Logger.print_info("Submitting background music generation task...")
                background_music_future = executor.submit(
                    music_gen.generate_music,
                    prompt=prompt,
                    model="chirp-v3-0",
                    duration=estimated_duration,  # Use estimated duration for background music
                    with_lyrics=False
                )

        # Submit closing credits music generation task early
        closing_credits_path = None
        closing_credits_future = None
        closing_credits_lyrics = None
        if config and hasattr(config, 'closing_credits') and config.closing_credits:
            file_path = getattr(config.closing_credits, 'file', None)
            prompt = getattr(config.closing_credits, 'prompt', None)
            if file_path:
                closing_credits_path = file_path
                Logger.print_info(f"Using file-based closing credits music: {closing_credits_path}")
            elif prompt:
                Logger.print_info("Submitting closing credits music generation task...")
                closing_credits_future = executor.submit(
                    music_gen.generate_music,
                    prompt=prompt,
                    model="chirp-v3-0",
                    duration=30,  # Use 30 seconds for closing credits
                    with_lyrics=True,
                    story_text="\n".join(story),
                    query_dispatcher=query_dispatcher
                )
            else:
                Logger.print_info("No closing credits configuration found (both file and prompt are None)")

        # Submit movie poster generation task if JSON was created successfully
        if filtered_story_json:
            Logger.print_info("Submitting movie poster generation task...")
            movie_poster_future = executor.submit(generate_movie_poster, filtered_story_json, style, story_title, query_dispatcher)
        else:
            Logger.print_warning("Skipping movie poster generation due to JSON creation error")
            movie_poster_future = None

        # Submit sentence processing tasks...
        Logger.print_info("Submitting sentence processing tasks...")
        sentence_futures = [executor.submit(process_sentence, i, sentence, context, style, total_images, tts, skip_generation, query_dispatcher, config) for i, sentence in enumerate(story)]
        
        # Wait for all futures to complete
        video_segments = []
        failed_segments = []
        for i, future in enumerate(sentence_futures):
            try:
                Logger.print_info(f"Processing result for segment {i}...")
                result = future.result()
                
                if not result:
                    Logger.print_error(f"Segment {i} processing returned None")
                    failed_segments.append(i)
                    continue
                    
                video_path, index = result
                if not video_path:
                    Logger.print_error(f"Segment {i} returned None for video path")
                    failed_segments.append(i)
                    continue
                    
                if not os.path.exists(video_path):
                    Logger.print_error(f"Video path does not exist for segment {i}: {video_path}")
                    failed_segments.append(i)
                    continue
                    
                # Verify it's a valid video file
                try:
                    ffprobe_cmd = ["ffprobe", "-v", "error", "-select_streams", "v:0", 
                                  "-show_entries", "stream=codec_type", "-of", "csv=p=0", video_path]
                    Logger.print_info(f"Running ffprobe command: {ffprobe_cmd}")
                    result = subprocess.run(ffprobe_cmd, capture_output=True, text=True)
                    Logger.print_info(f"FFprobe result: {result.stdout.strip()}")
                    if result.stdout.strip() != "video":
                        Logger.print_error(f"Invalid video file for segment {i}: {video_path}")
                        failed_segments.append(i)
                        continue
                except Exception as e:
                    Logger.print_error(f"Error validating video for segment {i}: {str(e)}")
                    failed_segments.append(i)
                    continue
                
                Logger.print_info(f"Successfully processed segment {index}: {video_path}")
                video_segments.append((index, video_path))
                
            except Exception as e:
                Logger.print_error(f"Error processing segment {i}: {str(e)}")
                import traceback
                Logger.print_error(f"Traceback for segment {i}: {traceback.format_exc()}")
                failed_segments.append(i)

        if not video_segments:
            Logger.print_error("No video segments were successfully created")
            Logger.print_error(f"Failed segments: {failed_segments}")
            return None, None, None, None, None

        # Sort video segments by index
        video_segments.sort(key=lambda x: x[0])
        Logger.print_info(f"Sorted {len(video_segments)} segments")
        
        # Check for missing segments
        expected_indices = set(range(len(story)))
        actual_indices = set(x[0] for x in video_segments)
        missing_indices = expected_indices - actual_indices
        
        if missing_indices:
            Logger.print_error(f"Missing segments for indices: {missing_indices}")
            Logger.print_error("This may cause issues with video continuity")
        
        video_segments = [segment[1] for segment in video_segments]
        Logger.print_info(f"Final video segments: {video_segments}")

        # Calculate actual total duration of video segments
        total_duration = 0
        for segment in video_segments:
            try:
                result = subprocess.run(
                    ["ffprobe", "-v", "error", "-show_entries",
                     "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", segment],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=True)
                duration = float(result.stdout)
                total_duration += duration
            except Exception as e:
                Logger.print_error(f"Error getting duration for segment {segment}: {e}")

        Logger.print_info(f"Total video duration: {total_duration} seconds")

        # Get the background music path from future if we generated it
        if background_music_future:
            background_music_path = background_music_future.result()
            if not background_music_path:
                Logger.print_error("Failed to generate background music.")
        
        # Get the closing credits path from future if we generated it
        if closing_credits_future:
            closing_credits_result = closing_credits_future.result()
            if isinstance(closing_credits_result, tuple) and len(closing_credits_result) == 2:
                closing_credits_path, closing_credits_lyrics = closing_credits_result
                Logger.print_info(f"Generated closing credits with lyrics: {closing_credits_lyrics}")
            else:
                closing_credits_path = closing_credits_result
                Logger.print_error("Failed to get lyrics from closing credits generation.")
        
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

    return video_segments, background_music_path, closing_credits_path, movie_poster_path, closing_credits_lyrics


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
