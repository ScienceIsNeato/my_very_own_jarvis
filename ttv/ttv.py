from .config_loader import load_input
from logger import Logger
from .story_processor import process_story
from .final_video_generation import assemble_final_video
from utils import get_tempdir
import os
import datetime

def text_to_video(ttv_config, skip_generation, output_path, tts, query_dispatcher):
    try:
        config = load_input(ttv_config)
        style, story, story_title = config
        current_datetime = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
        temp_dir = get_tempdir()
        output_path = os.path.join(temp_dir, "ttv", f"final_output_{current_datetime}.mp4")
        video_segments, background_music_path, song_with_lyrics_path, movie_poster_path = process_story(tts, style, story, skip_generation, query_dispatcher, story_title, config)
  
        if video_segments:
            assemble_final_video(video_segments, background_music_path, song_with_lyrics_path, movie_poster_path, output_path, config)
    except Exception as e:
        Logger.print_error(f"Error in text_to_video: {e}")
