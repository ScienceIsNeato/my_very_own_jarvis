import os
import openai
from datetime import datetime
from dotenv import load_dotenv
from abc import ABC, abstractmethod
from logger import Logger
from threading import Thread
from time import sleep
from time import time
import json
import tempfile


RESPONDER_NAME = "Them"

class QueryDispatcher(ABC):
    @abstractmethod
    def sendQuery(self, current_input):
        pass

class ChatGPTQueryDispatcher:
    load_dotenv()
    openai.api_key = os.environ.get("OPENAI_API_KEY")

    def __init__(self):
        self.config_file_path = os.path.join("config", "chatgpt_session_config.json")
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
                # Each line here represents a rule that the AI will attempt to follow when generating responses
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

        self.rotate_session_history() # Ensure history stays under the max length

        Logger.print_debug("Sending query to AI server (takes 2-20 secs depending on length of response)...")
        prompt = f"Current-Prompt: {current_input}"

        response = openai.Completion.create(
            engine="text-davinci-003",
            prompt=prompt,
            max_tokens=3500,
            n=1,
            stop=None,
            temperature=0.1,
        )
        chat = openai.ChatCompletion.create(
            model="gpt-3.5-turbo", 
            messages=self.messages
        )
        reply = chat.choices[0].message.content
        self.messages.append({"role": "assistant", "content": reply})
        curated_message = f"{RESPONDER_NAME}: {reply}"

        Logger.print_info(f"AI response received in {time() - start_time:.5f} seconds.")

        raw_message = response.choices[0].text.strip()
        curated_message = f"{RESPONDER_NAME}: {raw_message}"

        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")

        temp_dir = tempfile.gettempdir()

        with open(os.path.join(temp_dir, f"chatgpt_output_{timestamp}_raw.txt"), "w") as file:
            file.write(reply)

        with open(os.path.join(temp_dir, f"chatgpt_output_{timestamp}_curated.txt"), "w") as file:
            file.write(curated_message)

        return reply

    def rotate_session_history(self):
        """
        Rotates the session history by removing old messages
        to prevent context length from exceeding model limits.
        """
        
        # Calculate number of tokens used so far
        total_tokens = 0
        for message in self.messages:
            total_tokens += len(message["content"].split())

        # Define max tokens allowed
        MAX_TOKENS = 4097 # this should be defaulted to this value and loaded from a config

        # If over limit, remove oldest messages until under limit
        while total_tokens > MAX_TOKENS:
            removed_message = self.messages.pop(0)
            removed_length = len(removed_message["content"].split())
            total_tokens -= removed_length
            
            # Log removed message and new length
            Logger.print_debug(f"Conversation history getting long - dropping oldest content: {removed_message['content']} ({removed_length} tokens)")

class BardQueryDispatcher(QueryDispatcher):
    def sendQuery(self, current_input):
        # Stubbed method, implement the actual functionality here
        pass
