from abc import ABC, abstractmethod

class TurnIndicator(ABC):
    @abstractmethod
    def input_terminated(self):
        pass

    @abstractmethod
    def input_started(self):
        pass
