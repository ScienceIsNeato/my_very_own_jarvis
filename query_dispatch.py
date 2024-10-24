import os
import openai
from datetime import datetime
from dotenv import load_dotenv
from logger import Logger
import tempfile
from time import time
import base64

class ChatGPTQueryDispatcher:
    def __init__(self):
        load_dotenv()
        openai.api_key = os.getenv("OPENAI_API_KEY")
        ganglia_home = os.getenv('GANGLIA_HOME', os.getcwd())
        self.config_file_path = os.path.join(ganglia_home, 'config', 'ganglia_config.json')
        self.messages = []

    def add_system_context(self, context_lines):
        # Add each context line as a system message
        for line in context_lines:
            self.messages.append({"role": "system", "content": line})

    def sendQuery(self, current_input, image_path=None):
        """
        Send query to OpenAI with optional image for GPT-4 Vision model.
        :param current_input: The user's text input
        :param image_path: Optional, the path to an image file
        :return: The assistant's reply
        """
        # Add the user's input as a message
        self.messages.append({"role": "user", "content": current_input})
        start_time = time()

        self.rotate_session_history()  # Ensure history stays under the max length

        # Prepare the content with or without an image
        if image_path:
            # Encode the image to base64 if an image path is provided
            base64_image = self.encode_image(image_path)

            content = [
                {"type": "text", "text": current_input},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{base64_image}"}
                }
            ]
        else:
            # If no image, it's a regular text query
            content = current_input

        Logger.print_debug("Sending query to AI server...")

        chat = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "user", "content": content}
            ]
        )
        reply = chat.choices[0].message.content
        self.messages.append({"role": "assistant", "content": reply})

        Logger.print_info(f"AI response received in {time() - start_time:.1f} seconds.")

        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        temp_dir = tempfile.gettempdir()

        with open(os.path.join(temp_dir, f"chatgpt_output_{timestamp}_raw.txt"), "w") as file:
            file.write(reply)

        return reply

    def encode_image(self, image_path):
        """Encode an image from a file to base64."""
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

    def rotate_session_history(self):
        """Trim conversation history to fit within token limits."""
        total_tokens = 0
        for message in self.messages:
            total_tokens += len(message["content"].split())

        MAX_TOKENS = 128000

        while total_tokens > MAX_TOKENS:
            removed_message = self.messages.pop(0)
            removed_length = len(removed_message["content"].split())
            total_tokens -= removed_length
            Logger.print_debug(f"Conversation history getting long - dropping oldest content: {removed_message['content']} ({removed_length} tokens)")

