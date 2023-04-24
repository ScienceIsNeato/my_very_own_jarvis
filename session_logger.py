import json
import os
import time
from abc import ABC, abstractmethod
from uuid import uuid4
from typing import List

class SessionEvent:
    def __init__(self, user_input: str, response_output: str):
        self.user_input = user_input
        self.response_output = response_output

    def to_dict(self):
        return {
            "user_input": self.user_input,
            "response_output": self.response_output
        }

class Session:
    def __init__(self, session_id: str, timestamp: str, conversation: List[SessionEvent]):
        self.session_id = session_id
        self.timestamp = timestamp
        self.conversation = conversation

    def to_dict(self):
        return {
            "sessionID": self.session_id,
            "timestamp": self.timestamp,
            "conversation": [event.to_dict() for event in self.conversation]
        }

class SessionLogger(ABC):

    @abstractmethod
    def log_session_interaction(self, session_event: SessionEvent):
        pass

    @abstractmethod
    def finalize_session(self):
        pass


class CLISessionLogger(SessionLogger):

    def __init__(self):
        self.session_id = str(uuid4())
        self.timestamp = time.strftime("%Y-%m-%dT%H:%M:%S")
        self.conversation = []

    def log_session_interaction(self, session_event: SessionEvent):
        self.conversation.append(session_event)

    def finalize_session(self):
            session = Session(self.session_id, self.timestamp, self.conversation)
            json_data = json.dumps(session.to_dict(), indent=2)
            file_name = f"/tmp/Jarvis_session_{self.timestamp}.json"
            with open(file_name, "w") as f:
                f.write(json_data)
            print(f"Session log saved as {file_name}")
            return file_name
