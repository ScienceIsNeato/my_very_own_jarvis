from .config_loader import load_input
from logger import Logger
from .story_processor import process_story
from .final_video_generation import create_final_video_with_music

def text_to_video(ttv_config, skip_generation, output_path, tts):
    try:
        style, story = load_input(ttv_config)
        video_segments, context = process_story(tts, style, story, skip_generation)
        if video_segments:
            create_final_video_with_music(video_segments, style, context, ' '.join(story), tts, skip_generation, output_path)
    except Exception as e:
        Logger.print_error(f"Error in text_to_video: {e}")
