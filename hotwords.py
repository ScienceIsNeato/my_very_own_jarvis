import json
from logger import Logger
from load_config import ConfigLoader

class HotwordManager:
    def __init__(self):
        config = ConfigLoader()
        self.hotwords = config.get('hotwords')

    def detect_hotwords(self, prompt):
        prompt = prompt.lower()
        
        hotword_detected = False
        hotword_phrase = ""

        for hotword, phrase in self.hotwords.items():
            if prompt.find(hotword) != -1:
                hotword_detected = True
                hotword_phrase = phrase
                break

        return hotword_detected, hotword_phrase
