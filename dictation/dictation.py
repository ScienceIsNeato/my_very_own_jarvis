from abc import ABC, abstractmethod

class Dictation(ABC):
    @abstractmethod
    def getDictatedInput(self, device_index, interruptable=False):
        pass

    @abstractmethod
    def done_speaking(self, current_line):
        pass

    def set_session_logger(self, session_logger):
        """Sets the session logger."""
        self.session_logger = session_logger