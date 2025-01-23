import json
import random

from logger import Logger

example_lyrical_styles = [
    "rock", "pop", "jazz", "blues", "hip hop", 
    "country", "classical", "reggae", "metal", "folk"
]

class LyricsGenerator:
    def __init__(self):
        pass

    def generate_song_lyrics(self, story_text, query_dispatcher):
        """Generate song lyrics based on the story text."""
        prompt = f"""
        Generate concise lyrics for a 30-second jingle or song based on the following story.
        The lyrics should be:
        - 4 lines maximum (2-3 lines is ideal)
        - No repetition of lines
        - Each line should be 8-10 syllables
        - Focus on the key theme/message
        - Suitable for a trailer or closing credits

        Story:
        {story_text}

        Return the lyrics in JSON format with the following structure:
        {{
            "style": "upbeat pop",  # or another appropriate style
            "lyrics": "the generated lyrics here"
        }}

        The lyrics should capture the essence of the story while being brief and memorable.
        """

        response = query_dispatcher.sendQuery(prompt)
        
        # Try to parse the response as JSON
        try:
            json_data = json.loads(response)
            return json.dumps(json_data)  # Return the properly formatted JSON
        except json.JSONDecodeError:
            # If response is not valid JSON, try to extract style and lyrics from text
            lines = response.strip().split('\n')
            style = "upbeat pop"  # Default style
            lyrics = []
            
            for line in lines:
                line = line.strip()
                if line.startswith('"style":'):
                    style = line.split(':')[1].strip().strip('",')
                elif line.startswith('"lyrics":'):
                    lyrics = [line.split(':')[1].strip().strip('",')]
                elif not line.startswith('{') and not line.startswith('}'):
                    lyrics.append(line.strip().strip('",'))
            
            # Create a properly formatted JSON response
            formatted_response = {
                "style": style,
                "lyrics": "\n".join(lyrics)
            }
            return json.dumps(formatted_response)

    def determine_lyrical_style(self, story_text, query_dispatcher):
        Logger.print_info("Determining lyrical style with ChatGPT.")
        
        prompt = (
            f"Based on the following story, suggest an appropriate lyrical style for a song:\n\n{story_text}\n\n"
            "Possible styles include: " + ", ".join(example_lyrical_styles) + ".\n\n"
            "Return the style as a single word or phrase that best fits the story."
        )

        try:
            response = query_dispatcher.sendQuery(prompt)
            lyrical_style = response.strip().split('\n')[0]

            if lyrical_style not in example_lyrical_styles:
                lyrical_style = random.choice(example_lyrical_styles)

            Logger.print_info(f"Determined lyrical style: {lyrical_style}")
            return lyrical_style
        except Exception as e:
            Logger.print_error(f"Error determining lyrical style: {e}")
            return random.choice(example_lyrical_styles)
