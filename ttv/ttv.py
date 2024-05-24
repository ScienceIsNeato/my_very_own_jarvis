from .config_loader import load_input
from logger import Logger
from .story_processor import process_story
from .final_video_generation import assemble_final_video

def text_to_video(ttv_config, skip_generation, output_path, tts, query_dispatcher):
    try:
        style, story, title = load_input(ttv_config)
        video_segments, background_music_path, song_with_lyrics_path, movie_poster_path = process_story(tts, style, title, story, skip_generation, query_dispatcher)
  
        if video_segments:
            assemble_final_video(video_segments, background_music_path, song_with_lyrics_path, movie_poster_path, output_path)
    except Exception as e:
        Logger.print_error(f"Error in text_to_video: {e}")
