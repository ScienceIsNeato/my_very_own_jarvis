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
        self.config_file_path = os.path.join("config", "ganglia_config.json")
        self.messages = []
        self.load_config()

    def load_conversation_context(self, contexts):
        """
        Loads a series of conversation context prompts into the conversation and simulates an acknowledgment for each.

        Parameters:
            contexts (list): List of context strings from the config file.
        """
        # Start the spoofed exchange to simulate loading context without eliciting reactions
        initial_prompt = "Ok friend, I'm going to feed you a bunch of conversation context that I'd like you to be aware of. I don't want any reaction or discussion at all - just let me know you got the message with 'ack' and keep saying 'ack' to each message until I'm done feeding context."
        spoofed_response = "ack"
        self.sendQuery(initial_prompt, spoof=True, spoofed_response=spoofed_response)

        # Load each context as a spoofed user input and simulate 'ack' from the system for each
        for context in contexts:
            self.sendQuery(context, spoof=True, spoofed_response=spoofed_response)

        # End the context loading with a final real exchange asking for a summary
        final_prompt = "Ok, that's all the context I'll provide. From this point on, you can start responding normally. Please keep the context top of mind as we continue chatting. If you are ready to proceed with this context, give me an enthusiastic holler!"
        final_response = "Ohhh, yeah! Let's do this!"
        self.sendQuery(final_prompt, spoof=False, spoofed_response=final_response)

    def summarize_conversation_context(self):
        """Asks the AI to summarise the conversation context that was previously loaded."""

        prompt = "Ok, a new user is walking up to start interacting with you. Can you give them a quick rundown of the conversation context they're walking into? Keep it brief and fun so they're eager to jump in!"
        summary_response = self.sendQuery(prompt, spoof=False)

        Logger.print_debug(f"Summary of context: {summary_response}")
        return summary_response

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


    def sendQuery(self, current_input, spoof=False, spoofed_response=""):
        """
        Sends a query to the AI model or uses a spoofed response based on the spoof flag.

        Parameters:
            current_input (str): The user's input to send or spoof.
            spoof (bool): Indicates whether to use the spoofed response.
            spoofed_response (str): The response to use if spoof is True.

        Returns:
            str: The AI's or spoofed response.
        """
        self.messages.append({"role": "user", "content": current_input})
        start_time = time()

        self.rotate_session_history()  # Ensure history stays under the max length

        if spoof:
            reply = spoofed_response
        else:
            Logger.print_debug("Sending query to AI server...")
            chat = openai.ChatCompletion.create(
                model="gpt-3.5-turbo", 
                messages=self.messages
            )
            reply = chat.choices[0].message.content

        self.messages.append({"role": "assistant", "content": reply})

        if not spoofed_response:
            Logger.print_info(f"AI response received in {time() - start_time:.1f} seconds.")

        # Store the response for auditing purposes
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        temp_dir = tempfile.gettempdir()

        with open(os.path.join(temp_dir, f"ganglia_output_{timestamp}_raw.txt"), "w") as file:
            file.write(reply)

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
