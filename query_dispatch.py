"""Query dispatcher module for handling OpenAI API interactions.

This module provides a ChatGPT query dispatcher that manages conversations with OpenAI's API,
handles session history, and provides content filtering capabilities for DALL-E compatibility.
"""

# Standard library imports
import os
from datetime import datetime
from time import time

# Third-party imports
from openai import OpenAI

# Local imports
from logger import Logger
from utils import get_tempdir

class ChatGPTQueryDispatcher:
    """A dispatcher for managing conversations with OpenAI's ChatGPT.
    
    This class handles the interaction with OpenAI's API, manages conversation history,
    and provides utilities for content filtering and token management.
    """

    def __init__(self, pre_prompt=None, config_file_path=None):
        """Initialize the ChatGPT query dispatcher.
        
        Args:
            pre_prompt (str, optional): Initial system prompt to set context
            config_file_path (str, optional): Path to configuration file
        """
        self.client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        default_config = os.path.join(os.path.dirname(__file__), 'config', 'ganglia_config.json')
        self.config_file_path = config_file_path or default_config
        self.messages = []
        if pre_prompt:
            self.messages.append({"role": "system", "content": pre_prompt})

    def add_system_context(self, context_lines):
        """Add system context messages to the conversation.
        
        Args:
            context_lines (list[str]): Lines of context to add as system messages
        """
        for line in context_lines:
            self.messages.append({"role": "system", "content": line})

    def send_query(self, current_input):
        """Send a query to the ChatGPT API and get the response.
        
        Args:
            current_input (str): The user's input to send to ChatGPT
            
        Returns:
            str: The AI's response
        """
        self.messages.append({"role": "user", "content": current_input})
        start_time = time()

        self.rotate_session_history()  # Ensure history stays under the max length

        Logger.print_debug("Sending query to AI server...")

        chat = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=self.messages
        )
        reply = chat.choices[0].message.content
        self.messages.append({"role": "assistant", "content": reply})

        Logger.print_info(f"AI response received in {time() - start_time:.1f} seconds.")

        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        temp_dir = get_tempdir()

        with open(os.path.join(temp_dir, f"chatgpt_output_{timestamp}_raw.txt"), "w", encoding='utf-8') as file:
            file.write(reply)

        return reply

    def rotate_session_history(self):
        """Rotate session history to keep token count under limit."""
        total_tokens = 0
        for message in self.messages:
            total_tokens += len(message["content"].split())

        max_tokens = 4097  # Constant should be uppercase but used locally

        while total_tokens > max_tokens:
            removed_message = self.messages.pop(0)
            removed_length = len(removed_message["content"].split())
            total_tokens -= removed_length
            debug_msg = (
                f"Conversation history getting long - dropping oldest content: "
                f"{removed_message['content']} ({removed_length} tokens)"
            )
            Logger.print_debug(debug_msg)

    def count_tokens(self):
        """Count total tokens in the message history."""
        total_tokens = 0
        for message in self.messages:
            total_tokens += len(message["content"].split())
        return total_tokens

    def filter_content_for_dalle(self, content, max_attempts=3):
        """Filter content to ensure it passes DALL-E's content filters.
        
        Args:
            content (str): The content to filter.
            max_attempts (int): Maximum number of filtering attempts.
            
        Returns:
            tuple: (success, filtered_content) where success is a boolean indicating if 
                  filtering was successful, and filtered_content is the filtered text 
                  if successful, or None if not.
        """
        prompt = self._get_dalle_filter_prompt(content)

        for attempt in range(max_attempts):
            try:
                attempt_msg = f"Filtering content for DALL-E (attempt {attempt + 1}/{max_attempts})"
                Logger.print_info(attempt_msg)
                filtered_response = self.send_query(prompt)
                filtered_content = filtered_response.strip()
                Logger.print_info(f"Rewritten content:\n{filtered_content}")
                return True, filtered_content
            except (ValueError, IOError, RuntimeError, TimeoutError) as e:
                error_msg = f"Error filtering content (attempt {attempt + 1}): {e}"
                Logger.print_error(error_msg)
                if attempt == max_attempts - 1:  # Last attempt
                    return False, None
        
        return False, None

    def _get_dalle_filter_prompt(self, content):
        """Get the prompt for filtering content for DALL-E.
        
        Args:
            content (str): The content to filter.
            
        Returns:
            str: The prompt for filtering content.
        """
        filter_instructions = [
            "Please rewrite this story to pass OpenAI's DALL-E content filters. ",
            "The rewritten version should:",
            "1. Replace all specific names with generic terms (e.g., 'the family', 'the children')",
            "2. Replace specific locations with generic descriptions (e.g., 'a beautiful lake')",
            "3. Remove any potentially sensitive or controversial content",
            "4. Keep the core story and emotional tone\n",
            f"\nStory to rewrite:\n{content}\n",
            "\nReturn only the rewritten story with no additional text or explanation."
        ]
        return "".join(filter_instructions)
