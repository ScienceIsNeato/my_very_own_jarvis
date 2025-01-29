import os
from datetime import datetime
from openai import OpenAI
from logger import Logger
from utils import get_tempdir
from time import time

class ChatGPTQueryDispatcher:
    def __init__(self, pre_prompt=None, config_file_path=None):
        self.client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        self.config_file_path = config_file_path or os.path.join(os.path.dirname(__file__), 'config', 'ganglia_config.json')
        self.messages = []
        if pre_prompt:
            self.messages.append({"role": "system", "content": pre_prompt})

    def add_system_context(self, context_lines):
        # Add each context line as a system message
        for line in context_lines:
            self.messages.append({"role": "system", "content": line})

    def sendQuery(self, current_input):
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

    def count_tokens(self):
        """Count total tokens in the message history."""
        total_tokens = 0
        for message in self.messages:
            total_tokens += len(message["content"].split())
        return total_tokens

    def filter_content_for_dalle(self, content, max_attempts=3):
        """
        Filter content to ensure it passes DALL-E's content filters.
        
        Args:
            content (str): The content to filter.
            max_attempts (int): Maximum number of filtering attempts.
            
        Returns:
            tuple: (success, filtered_content) where success is a boolean indicating if filtering was successful,
                  and filtered_content is the filtered text if successful, or None if not.
        """
        prompt = self._get_dalle_filter_prompt(content)

        for attempt in range(max_attempts):
            try:
                Logger.print_info(f"Filtering content for DALL-E (attempt {attempt + 1}/{max_attempts})")
                filtered_response = self.sendQuery(prompt)
                filtered_content = filtered_response.strip()
                Logger.print_info(f"Rewritten content:\n{filtered_content}")
                return True, filtered_content
            except Exception as e:
                Logger.print_error(f"Error filtering content (attempt {attempt + 1}): {e}")
                if attempt == max_attempts - 1:  # Last attempt
                    return False, None
        
        return False, None

    def _get_dalle_filter_prompt(self, content):
        """
        Get the prompt for filtering content for DALL-E.
        
        Args:
            content (str): The content to filter.
            
        Returns:
            str: The prompt for filtering content.
        """
        return (
            "Please rewrite this story to pass OpenAI's DALL-E content filters. The rewritten version should:\n"
            "1. Replace all specific names with generic terms (e.g., 'the family', 'the children', 'the adventurers')\n"
            "2. Replace specific locations with generic descriptions (e.g., 'a beautiful lake', 'a scenic garden')\n"
            "3. Remove any potentially sensitive or controversial content\n"
            "4. Keep the core story and emotional tone\n\n"
            "Story to rewrite:\n"
            f"{content}\n\n"
            "Return only the rewritten story with no additional text or explanation."
        )
