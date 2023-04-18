import os
import openai
import speech_recognition as sr
import pyttsx3
import argparse
import keyboard
import threading
import time
from datetime import datetime


# Parse command line arguments
def parse_args():
    parser = argparse.ArgumentParser(description="Jarvis - AI Assistant")
    parser.add_argument("-l", "--listen_dur_secs", type=int, default=5, help="Duration in seconds to listen for user input")
    return parser.parse_args()


# Initialize OpenAI API key
openai.api_key = "your_openai_api_key"


# Class to handle Mac dictation audio input
class MacDictationAudioInput:
    def __init__(self):
        self.recording = False
        self.text = None

    def on_spacebar_pressed(self, e):
        if not self.recording:
            self.start_recording()
        else:
            self.stop_recording()

    def start_recording(self):
        self.recording = True
        print("Recording started.")
        with sr.Microphone() as source:
            recognizer = sr.Recognizer()
            audio = recognizer.listen(source, timeout=args.listen_dur_secs)
            try:
                self.text = recognizer.recognize_google(audio)
                print(f"Recognized text: {self.text}")
            except sr.UnknownValueError:
                print("Google Speech Recognition could not understand the audio.")
            except sr.RequestError as e:
                print(f"Could not request results from Google Speech Recognition service; {e}")
            except Exception as e:
                print(f"An error occurred while processing audio; {e}")
        self.recording = False
        print("Recording stopped.")

    def stop_recording(self):
        self.recording = False

    def get_input(self):
        if self.text is None:
            return None
        return self.text


# Function to listen for spacebar press
def listen_for_spacebar(audio_input):
    keyboard.on_press_key("space", audio_input.on_spacebar_pressed)


# Main function
def main():
    # Parse command line arguments
    global args
    args = parse_args()

    # Initialize audio input and listener thread
    audio_input = MacDictationAudioInput()
    listener_thread = threading.Thread(target=listen_for_spacebar, args=(audio_input,))
    listener_thread.start()

    # Listen for audio input and generate response
    while True:
        prompt = None
        while prompt is None:
            time.sleep(0.1)
            prompt = audio_input.get_input()

        response = openai.Completion.create(
            engine="davinci-codex",
            prompt=prompt,
            max_tokens=100,
            n=1,
            stop=None,
            temperature=0.5,
        )

        message = response.choices[0].text.strip()

        # Save the output to the /tmp folder
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        with open(f"/tmp/chatgpt_output_{timestamp}.txt", "w") as file:
            file.write(message)

        # Speak the message
        engine = pyttsx3.init()
        engine.say(message)
        engine.runAndWait()


if __name__ == '__main__':
    main()
