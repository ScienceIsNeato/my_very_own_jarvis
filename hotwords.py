import json
from logger import Logger


class HotwordManager:
    def __init__(self, config_file_path):
        self.hotwords_config = self.load_config(config_file_path)

    def load_config(self, config_file_path):
        try:
            with open(config_file_path, 'r') as json_file:
                config = json.load(json_file)

                # Navigate to the hotwords section inside interactive_keywords
                hotwords_config = config.get("conversation", {}).get("interactive_keywords", {}).get("hotwords", {})

                # Ensure that all hotwords are stored as lowercase for case-insensitive matching
                lowercase_hotwords = {hotword.lower(): phrase for hotword, phrase in hotwords_config.items()}

                Logger.print_info(f"Loaded {len(lowercase_hotwords)} hotword mappings from config file")

                for hotword in lowercase_hotwords:
                    Logger.print_info(f"Loaded hotword: {hotword}")

                return lowercase_hotwords

        except FileNotFoundError:
            Logger.print_error(f"Hotword config file not found at: {config_file_path}")
            return {}  # Return an empty dictionary in case of file not found
        except json.JSONDecodeError as e:
            Logger.print_error(f"Failed to parse hotword config file: {e}")
            return {}  # Return an empty dictionary in case of JSON decoding error

    def detect_hotwords(self, prompt):
        prompt = prompt.lower()

        hotword_detected = False
        hotword_phrase = ""

        for hotword, phrase in self.hotwords_config.items():
            if hotword in prompt:
                hotword_detected = True
                hotword_phrase = phrase
                break

        return hotword_detected, hotword_phrase
