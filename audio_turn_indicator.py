import os
from abc import ABC
from pydub import AudioSegment
from pydub.playback import play

# Default file paths for UserTurnIndicator
USER_TURN_START_PATH = os.path.join("media", "zapsplat_multimedia_button_click_fast_short_004_79288.mp3")
USER_TURN_END_PATH = os.path.join("media", "zapsplat_multimedia_button_click_bright_001_92098.mp3")

# Default file paths for AiTurnIndicator
AI_TURN_START_PATH = os.path.join("media", "zapsplat_multimedia_ui_window_minimize_short_swipe_whoosh_71502.mp3")
AI_TURN_END_PATH = os.path.join("media", "zapsplat_multimedia_ui_window_maximize_short_swipe_whoosh_001_71500.mp3")

class TurnIndicator(ABC):
    def __init__(self, in_file_path, out_file_path):
        self.in_file_path = in_file_path
        self.out_file_path = out_file_path

    def input_in(self):
        audio = AudioSegment.from_file(self.in_file_path)
        play(audio)

    def input_out(self):
        audio = AudioSegment.from_file(self.out_file_path)
        play(audio)

class UserTurnIndicator(TurnIndicator):
    def __init__(self, in_file_path=USER_TURN_START_PATH, out_file_path=USER_TURN_END_PATH):
        super().__init__(in_file_path, out_file_path)

class AiTurnIndicator(TurnIndicator):
    def __init__(self, in_file_path=AI_TURN_START_PATH, out_file_path=AI_TURN_END_PATH):
        super().__init__(in_file_path, out_file_path)