from .config_loader import load_input
from .story_processor import process_story
from .final_video_generation import assemble_final_video
from tts import GoogleTTS
from logger import Logger

def text_to_video(config_path, skip_generation=False, output_path=None, tts=None, query_dispatcher=None):
    """Convert text to video using the provided configuration."""
    try:
        # Load configuration
        config = load_input(config_path)
        if not config:
            Logger.print_error("Failed to load configuration")
            return None
        
        # Log loaded config
        Logger.print_info(f"Loaded config: {config}")

        # Use provided TTS or initialize a new one
        if not tts:
            tts = GoogleTTS()

        # Process story and generate video segments
        video_segments, background_music_path, closing_credits_path, movie_poster_path, closing_credits_lyrics = process_story(
            tts=tts,
            style=config.style,
            story=config.story,
            skip_generation=skip_generation,
            query_dispatcher=query_dispatcher,
            story_title=config.title,
            config=config
        )

        # Assemble final video
        return assemble_final_video(
            video_segments=video_segments,
            music_path=background_music_path,
            song_with_lyrics_path=closing_credits_path,
            movie_poster_path=movie_poster_path,
            config=config,
            closing_credits_lyrics=closing_credits_lyrics,
            output_path=output_path
        )

    except Exception as e:
        Logger.print_error(f"Error in text_to_video: {str(e)}")
        import traceback
        Logger.print_error(f"Traceback: {traceback.format_exc()}")
        return None
