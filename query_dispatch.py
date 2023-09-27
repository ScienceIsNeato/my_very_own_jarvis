import os
import openai
from datetime import datetime
from dotenv import load_dotenv
from abc import ABC, abstractmethod

RESPONDER_NAME = "Them"

class QueryDispatcher(ABC):
    @abstractmethod
    def sendQuery(self, current_input):
        pass

class ChatGPTQueryDispatcher:
    load_dotenv()
    openai.api_key = os.environ.get("OPENAI_API_KEY")

    def __init__(self, pre_prompt=None):
        self.pre_prompt = pre_prompt

    def sendQuery(self, current_input):
        prompt = f"Current-Prompt: {current_input}"

        response = openai.Completion.create(
            engine="text-davinci-003",
            prompt=prompt,
            max_tokens=3500,
            n=1,
            stop=None,
            temperature=0.1,
        )

        raw_message = response.choices[0].text.strip()
        curated_message = f"{RESPONDER_NAME}: {raw_message}"

        print(f"{RESPONDER_NAME}: {raw_message}")

        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        with open(f"/tmp/chatgpt_output_{timestamp}_raw.txt", "w") as file:
            file.write(raw_message)

        with open(f"/tmp/chatgpt_output_{timestamp}_curated.txt", "w") as file:
            file.write(curated_message)

        return raw_message

class BardQueryDispatcher(QueryDispatcher):
    def sendQuery(self, current_input):
        # Stubbed method, implement the actual functionality here
        pass
