import os
import openai
from datetime import datetime
from abc import ABC, abstractmethod

class QueryDispatcher(ABC):
    @abstractmethod
    def sendQuery(self, prompt, pre_prompt=None):
        pass

class ChatGPTQueryDispatcher:
    openai.api_key = os.environ.get("OPENAI_API_KEY")
    conversation_history = ""

    def __init__(self, pre_prompt=None):
        self.pre_prompt = pre_prompt

    def sendQuery(self, current_input):
        # Add the user's input to the conversation history
        self.conversation_history += f"User: {current_input}\n"

        prompt = f"Pre-Prompt: {self.pre_prompt}, ConversationHistory: {self.conversation_history}, Current-Prompt: {current_input}"

        response = openai.Completion.create(
            engine="text-davinci-003",
            prompt=prompt,
            max_tokens=100,
            n=1,
            stop=None,
            temperature=0.1,
        )

        message = response.choices[0].text.strip()

        # Add the model's response to the conversation history
        self.conversation_history += f"Samantha: {message}\n"

        print(f"Samantha said: {message}")

        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        with open(f"/tmp/chatgpt_output_{timestamp}.txt", "w") as file:
            file.write(message)

        return message


class BardQueryDispatcher(QueryDispatcher):
    def sendQuery(self, prompt, pre_prompt=None):
        # Stubbed method, implement the actual functionality here
        pass
