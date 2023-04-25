from abc import ABC, abstractmethod
from pydub import AudioSegment
from pydub.playback import play


class TurnIndicator(ABC):
    def __init__(self, in_file_path, out_file_path):
        self.in_file_path = in_file_path
        self.out_file_path = out_file_path

    @abstractmethod
    def input_in(self):
        pass

    @abstractmethod
    def input_out(self):
        pass


class UserTurnIndicator(TurnIndicator):
    def input_in(self):
        audio = AudioSegment.from_file(self.in_file_path)
        play(audio)

    def input_out(self):
        audio = AudioSegment.from_file(self.out_file_path)
        play(audio)


class AiTurnIndicator(TurnIndicator):
    def input_in(self):
        audio = AudioSegment.from_file(self.in_file_path)
        play(audio)

    def input_out(self):
        audio = AudioSegment.from_file(self.out_file_path)
        play(audio)
