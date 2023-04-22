import os
import openai
from datetime import datetime
from abc import ABC, abstractmethod

class QueryDispatcher(ABC):
    @abstractmethod
    def sendQuery(self, prompt, pre_prompt=None):
        pass

class ChatGPTQueryDispatcher(QueryDispatcher):
    openai.api_key = os.environ.get("OPENAI_API_KEY")

    def sendQuery(self, prompt, pre_prompt=None):
        if pre_prompt:
            prompt = f"Pre-Prompt: {pre_prompt}. Prompt: {prompt}"

        response = openai.Completion.create(
            engine="text-davinci-003",
            prompt=prompt,
            max_tokens=100,
            n=1,
            stop=None,
            temperature=0.1,
        )

        message = response.choices[0].text.strip()

        print(f"chatGPT said: {message}")

        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        with open(f"/tmp/chatgpt_output_{timestamp}.txt", "w") as file:
            file.write(message)

        return message


class BardQueryDispatcher(QueryDispatcher):
    def sendQuery(self, prompt, pre_prompt=None):
        # Stubbed method, implement the actual functionality here
        pass
