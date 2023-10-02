import time
import random
import subprocess
import os
from multiprocessing import Process

class TimeKiller:
    def __init__(self, folder_path: str):
        self.folder_path = folder_path
        self.files = [f for f in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, f))]
        self.stopped = False
        self.process = None

    def play_random_audio(self):
        while not self.stopped:
            audio_file = random.choice(self.files)
            audio_path = os.path.join(self.folder_path, audio_file)
            print(f"Loading audio file: {audio_file}")
            subprocess.run(["ffplay", "-nodisp", "-autoexit", audio_path], check=True)
            print(f"Finished playing: {audio_file}")
            time.sleep(3)  # Pause of at least a few seconds between utterances

    def start_killing_time(self):
        print("Starting to kill time...")
        self.stopped = False
        self.process = Process(target=self.play_random_audio)
        self.process.start()
        time.sleep(1) # Delay of at least a second before starting
        print("Killing time has begun.")

    def stop_killing_time(self):
        print("Stopping time killing...")
        self.stopped = True
        if self.process:
            self.process.join() # Wait for the current audio to finish playing
            time.sleep(1) # Delay of at least a second after the last utterance
        print("Time killing has stopped.")
