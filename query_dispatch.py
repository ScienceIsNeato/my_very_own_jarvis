import os
import openai
from datetime import datetime
from dotenv import load_dotenv
from abc import ABC, abstractmethod

RESPONDER_NAME = "Them"

class QueryDispatcher(ABC):
    @abstractmethod
    def sendQuery(self, current_input, static_response=False):
        pass

class ChatGPTQueryDispatcher:
    load_dotenv()
    openai.api_key = os.environ.get("OPENAI_API_KEY")

    conversation_history = ""

    def __init__(self, static_response=False, pre_prompt=None):
        self.pre_prompt = pre_prompt
        self.static_response = static_response

    def sendQuery(self, current_input, static_response=False):
        # Add the user's input to the conversation history
        if not self.static_response:
            self.conversation_history += f"User: {current_input}\n"

        prompt = ""

        # Add the pre-prompt to the prompt if it hasn't already been added to the conversation history
        if self.pre_prompt and not self.conversation_history.endswith(self.pre_prompt):
            prompt += f"Pre-Prompt: {self.pre_prompt}, "

        # Add the current input to the prompt
        prompt += f"Current-Prompt: {current_input}"

        response = openai.Completion.create(
            engine="text-davinci-003",
            prompt=prompt,
            max_tokens=100,
            n=1,
            stop=None,
            temperature=0.1,
        )

        raw_message = response.choices[0].text.strip()
        curated_message = f"{RESPONDER_NAME}: {raw_message}"

        # Add the model's response to the conversation history
        if not self.static_response:
            self.conversation_history += f"{RESPONDER_NAME}: {raw_message}\n"

        print(f"{RESPONDER_NAME}: {raw_message}")

        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        with open(f"/tmp/chatgpt_output_{timestamp}_raw.txt", "w") as file:
            file.write(raw_message)

        with open(f"/tmp/chatgpt_output_{timestamp}_curated.txt", "w") as file:
            file.write(curated_message)

        return raw_message

class BardQueryDispatcher(QueryDispatcher):
    def sendQuery(self, current_input, static_response=False):
        # Stubbed method, implement the actual functionality here
        pass
