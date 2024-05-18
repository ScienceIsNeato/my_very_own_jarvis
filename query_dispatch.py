import os
import openai
import json
from datetime import datetime
from dotenv import load_dotenv
from abc import ABC, abstractmethod
from logger import Logger
import tempfile
from time import time

class QueryDispatcher(ABC):
    @abstractmethod
    def sendQuery(self, current_input):
        pass

class ChatGPTQueryDispatcher(QueryDispatcher):
    def __init__(self):
        load_dotenv()
        openai.api_key = os.environ.get("OPENAI_API_KEY")
        self.config_file_path = os.path.join(os.path.dirname(__file__), "..", "config", "chatgpt_session_config.json")
        self.messages = []
        self.load_config()

    def load_config(self):
        try:
            Logger.print_debug("DEBUG FP: ", self.config_file_path)
            with open(self.config_file_path) as f:
                config = json.load(f)
            
            Logger.print_debug("DEBUG CONFIG: ", config)
            pre_prompts = config.get("pre_prompts")
            if pre_prompts:
                for prompt in pre_prompts:
                    self.messages.append({"role": "system", "content": prompt})
            Logger.print_debug("Loaded pre-prompts from config file: ", pre_prompts)

        except FileNotFoundError:
            Logger.print_error(f"Error: Config file `{self.config_file_path}` not found")

        except json.JSONDecodeError:
            Logger.print_error(f"Error: Invalid JSON in config file: `{self.config_file_path}`")

    def sendQuery(self, current_input):
        self.messages.append({"role": "user", "content": current_input})
        start_time = time()

        self.rotate_session_history()  # Ensure history stays under the max length

        Logger.print_debug("Sending query to AI server...")

        chat = openai.ChatCompletion.create(
            model="gpt-3.5-turbo", 
            messages=self.messages
        )
        reply = chat.choices[0].message.content
        self.messages.append({"role": "assistant", "content": reply})

        Logger.print_info(f"AI response received in {time() - start_time:.1f} seconds.")

        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        temp_dir = tempfile.gettempdir()

        with open(os.path.join(temp_dir, f"chatgpt_output_{timestamp}_raw.txt"), "w") as file:
            file.write(reply)

        return reply

    def rotate_session_history(self):
        total_tokens = 0
        for message in self.messages:
            total_tokens += len(message["content"].split())

        MAX_TOKENS = 4097

        while total_tokens > MAX_TOKENS:
            removed_message = self.messages.pop(0)
            removed_length = len(removed_message["content"].split())
            total_tokens -= removed_length
            Logger.print_debug(f"Conversation history getting long - dropping oldest content: {removed_message['content']} ({removed_length} tokens)")
