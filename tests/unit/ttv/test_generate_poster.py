import os
import pytest
from logger import Logger
from query_dispatch import ChatGPTQueryDispatcher
from ttv.story_generation import generate_movie_poster, generate_filtered_story
from utils import get_config_path, get_timestamped_ttv_dir


def test_generate_movie_poster():
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        raise EnvironmentError("Environment variable 'OPENAI_API_KEY' is not set.")
    
    story_title = "The Great Adventure"
    context = (
        "Once upon a time, at Crater Lake, the Martins and Taylors gathered, their adventures to begin and their very lives at stake. "
        "Laughing and playing, they shared jokes and fun, under the bright sun's warm embrace, their day had begun. "
        "In the car, they take time to scream, Matt's off-key voice joining the melody. "
        "From Denver's gardens to Oregon's coast, these two families have explored and laughed the most. "
        "Like in Salt Lake City, the good old days, or Dead Horse Point 50k, and all that pain. "
        "So many memories the families shared, from weddings in Portland to the Newport Aquarium. "
        "In Crater Lake, this group is a wild pack, gas-lighting Rozzie like she was back at the high-school track! "
        "Milo will lead the way, leading them to places never before seen by tourists or locals. "
        "Maybe this time, Angie will do something risky and take a big chance, or maybe she will laugh so hard she wet her pants. "
        "They were sure that Crater Lake would not disappoint, providing endless joy and memories to cherish."
    )
    style = "Whimsical adventure"

    query_dispatcher = ChatGPTQueryDispatcher(config_file_path=get_config_path())

    filtered_story_json = generate_filtered_story(context, style, story_title, query_dispatcher)

    # Get a timestamped directory for the output
    output_dir = get_timestamped_ttv_dir()

    Logger.print_info("Submitting movie poster generation task...")
    movie_poster_path = generate_movie_poster(filtered_story_json, style, story_title, query_dispatcher, output_dir=output_dir)

    assert movie_poster_path is not None, "Failed to generate movie poster"
    assert os.path.exists(movie_poster_path), "Movie poster file does not exist"

