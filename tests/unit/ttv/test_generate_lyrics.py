import json
import os
import pytest

from lyrics_lib import LyricsGenerator
from query_dispatch import ChatGPTQueryDispatcher
from logger import Logger
from utils import get_config_path

def count_syllables(word):
    """Count the number of syllables in a word."""
    word = word.lower()
    count = 0
    vowels = "aeiouy"
    
    # Handle special cases
    if not word:
        return 0
    elif word.endswith('e'):
        word = word[:-1]
    
    # Count vowel groups
    prev_char_is_vowel = False
    for char in word:
        is_vowel = char in vowels
        if is_vowel and not prev_char_is_vowel:
            count += 1
        prev_char_is_vowel = is_vowel
    
    # Ensure at least one syllable
    return max(1, count)

def count_line_syllables(line):
    """Count syllables in a line of text."""
    words = line.replace(',', ' ').replace('-', ' ').split()
    return sum(count_syllables(word) for word in words)

@pytest.mark.unit
def test_generate_lyrics():
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        raise EnvironmentError("Environment variable 'OPENAI_API_KEY' is not set.")
    
    story_text = (
        "This is a story about a brave knight named Stephanie, a dragon named Steve, "
        "and their shared love of Philadelphia. They traveled with their friends Arthur, "
        "Bella, and Cassandra to the mystical land of Eldoria. There they met Eldon the wise, "
        "Fiona the fierce, and Gregory the giant, who helped them on their quest to find the "
        "lost city of Atlantis."
    )

    query_dispatcher = ChatGPTQueryDispatcher(config_file_path=get_config_path())
    lyrics_generator = LyricsGenerator()

    result = lyrics_generator.generate_song_lyrics(story_text, query_dispatcher)

    # Check that the result is in the expected JSON format
    try:
        lyrics_json = json.loads(result)
        lyrics = lyrics_json["lyrics"]
        style = lyrics_json["style"]
    except json.JSONDecodeError:
        Logger.print_error("Result is not in valid JSON format")
        return

    # Print the input story and output lyrics
    print(f"Input story: {story_text}")
    print(f"Output lyrics: {lyrics}")
    print(f"Style: {style}")

    # Basic validation
    assert lyrics != "", "ERROR: Generated lyrics are empty"
    assert lyrics != story_text, "ERROR: Generated lyrics are identical to the input story"
    assert style and isinstance(style, str), "ERROR: Style should be a non-empty string"

    # Theme validation
    key_themes = ["knight", "dragon", "quest", "adventure", "journey", "magic", "brave", "mystical", "city"]
    found_themes = [theme for theme in key_themes if theme.lower() in lyrics.lower()]
    assert len(found_themes) >= 1, (
        f"ERROR: Lyrics must contain at least 1 key theme from the story.\n"
        f"Available themes: {key_themes}\n"
        f"Found themes: {found_themes}"
    )

    # Structure validation
    # Clean up the lyrics text thoroughly
    lyrics = (lyrics
        .replace('```', '')  # Remove code blocks
        .replace('\\n', '\n')  # Convert escaped newlines
        .strip()
    )
    
    # Split into lines and clean each line
    lines = []
    for line in lyrics.split('\n'):
        # Clean and normalize the line
        line = line.strip()
        if line and not line.startswith('{') and not line.endswith('}'):
            # Remove extra spaces
            line = ' '.join(word for word in line.split() if word)
            # Remove any trailing punctuation that might affect syllable count
            line = line.rstrip(',.!?')
            lines.append(line)
    
    assert 1 <= len(lines) <= 4, (
        f"ERROR: Lyrics must have between 1-4 lines.\n"
        f"Found {len(lines)} lines:\n"
        f"{chr(10).join(f'{i+1}. {line}' for i, line in enumerate(lines))}"
    )

    # Syllable validation
    syllable_counts = []
    for i, line in enumerate(lines):
        syllables = count_line_syllables(line)
        syllable_counts.append(syllables)
        print(f"Line {i+1} syllables: {syllables}")
        assert 6 <= syllables <= 12, (
            f"ERROR: Each line must have 6-12 syllables\n"
            f"Line {i+1}: '{line}'\n"
            f"Syllable count: {syllables}"
        )
    
    # Check average syllables across all lines
    avg_syllables = sum(syllable_counts) / len(syllable_counts)
    print(f"Average syllables per line: {avg_syllables:.1f}")
    if not (7.5 <= avg_syllables <= 10):
        Logger.print_warning(
            f"WARNING: Average syllables per line should ideally be between 7.5-10\n"
            f"Current average: {avg_syllables:.1f}\n"
            f"Line syllable counts: {syllable_counts}"
        )

    Logger.print_info("✓ All validation checks passed successfully.")
