import os
import openai
from datetime import datetime
from dotenv import load_dotenv
from abc import ABC, abstractmethod
from logger import Logger
from threading import Thread
from time import sleep
from time import time


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
        self.messages = [ {"role": "system", "content": self.pre_prompt} ]
        self.messages.append({"role": "system", "content": "keep answers brief"})
        self.messages.append({"role": "system", "content": "intersperse answer with demonic utterances and laughter in the style of stephen king"})
        self.messages.append({"role": "system", "content": "try not to be repetitive or boring"})
        self.messages.append({"role": "system", "content": "try not to steer the conversation"})
        self.messages.append({"role": "system", "content": "you are oddly obsessed with steven segal"})



    def sendQuery(self, current_input):
        self.messages.append({"role": "user", "content": current_input})
        start_time = time()
        Logger.print_debug("Sending query to AI server...")
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
        with open(f"/tmp/chatgpt_output_{timestamp}_raw.txt", "w") as file:
            file.write(reply)

        with open(f"/tmp/chatgpt_output_{timestamp}_curated.txt", "w") as file:
            file.write(curated_message)

        return reply

class BardQueryDispatcher(QueryDispatcher):
    def sendQuery(self, current_input):
        # Stubbed method, implement the actual functionality here
        pass
