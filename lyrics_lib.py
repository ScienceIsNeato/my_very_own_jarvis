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

    def generate_song_lyrics(self, story_text, query_dispatcher, song_context="theme song for the closing credits of a movie - you know - the kind that sums up the movie. Good examples are the MC Hammer Addams Family song and I'll Remember from With Honors"):
        Logger.print_info("Generating song lyrics with ChatGPT.")
        
        lyrical_style = self.determine_lyrical_style(story_text, query_dispatcher)
        
        prompt = (
            f"Write a song with lyrics inspired by this story:\n\n{story_text}\n\n"
            f"Craft the lyrics to capture the essence of the story while adding creative twists and variations. "
            "Avoid directly mirroring the plot or mentioning specific nouns in the same order as in the story. "
            "Instead, rearrange and reinterpret the events and characters to create a unique lyrical narrative. "
            "Infuse the lyrics with emotion and imagery that resonates with the story's themes.\n\n"
            "Feel free to incorporate your own creative flair, but ensure that the lyrics remain relevant to the story's core. "
            "Avoid explicit references to the song's meta-information (e.g., lyrical style, song context) to maintain a seamless experience for the listener.\n\n"
            "Please format the lyrics in the following JSON structure:\n"
            "{\n"
            "  \"context\": \"<insert song context here>\",\n"
            "  \"style\": \"<insert lyrical style here>\",\n"
            "  \"lyrics\": \"<insert lyrics here>\"\n"
            "}"
        )



        try:
            response = query_dispatcher.sendQuery(prompt)
            response_json = json.loads(response)
            context = response_json.get("context", song_context)
            style = response_json.get("style", lyrical_style)
            lyrics = response_json.get("lyrics", story_text)  # Fallback to story_text if "lyrics" key is not found
            
            Logger.print_info(f"Generated lyrics: {lyrics}")
            return json.dumps({
                "context": context,
                "style": style,
                "lyrics": lyrics
            })
        except Exception as e:
            Logger.print_error(f"Error generating lyrics: {e}")
            return json.dumps({
                "context": song_context,
                "style": lyrical_style,
                "lyrics": story_text
            })

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
