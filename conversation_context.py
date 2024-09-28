import json
from logger import Logger


class ContextManager:
    def __init__(self, config_file_path):
        self.context = self.load_context(config_file_path)

    def load_context(self, config_file_path):
        try:
            with open(config_file_path, 'r') as json_file:
                config = json.load(json_file)

                # Navigate to the conversation context section
                conversation_context = config.get("conversation", {}).get("conversation_context", [])

                if conversation_context:
                    Logger.print_info(f"Loaded {len(conversation_context)} lines of conversation context from config.")
                    for line in conversation_context:
                        Logger.print_info(f"Context: {line}")
                else:
                    Logger.print_info("No conversation context found in config file.")

                return conversation_context

        except FileNotFoundError:
            Logger.print_error(f"Context config file not found at: {config_file_path}")
            return []  # Return an empty list in case of file not found
        except json.JSONDecodeError as e:
            Logger.print_error(f"Failed to parse context config file: {e}")
            return []  # Return an empty list in case of JSON decoding error
