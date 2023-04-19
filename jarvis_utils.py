import os
import openai
import speech_recognition as sr
from datetime import datetime
from gtts import gTTS
from pydub import AudioSegment
from pydub.playback import play

openai.api_key = os.environ.get("OPENAI_API_KEY")


def getDictatedInput(listen_dur_secs, device_index):
    print("Testing audio input access...")
    recognizer = sr.Recognizer()

    with sr.Microphone(device_index=device_index) as source:
        print("Microphone detected.")
        print("Will listen for", listen_dur_secs, "seconds...")
        print("Calibrating microphone...")

        # Calibrate the microphone for ambient noise
        recognizer.adjust_for_ambient_noise(source, duration=1)

        print("Go!")

        # Increase the timeout and phrase_time_limit to allow for longer pauses and better capture
        audio = recognizer.listen(source, timeout=listen_dur_secs, phrase_time_limit=listen_dur_secs*1000)
        print("Finished listening.")

        try:
            text = recognizer.recognize_google(audio)
            print("You said: ", text)
            return text
        except sr.UnknownValueError:
            print("Google Speech Recognition could not understand the audio.")
        except sr.RequestError as e:
            print(f"Could not request results from Google Speech Recognition service; {e}")



def sendQueryToServer(prompt):
    # Load the OpenAI API key from the environment variable
    api_key = os.environ.get("OPENAI_API_KEY")

    # Check if the API key is not loaded
    if not api_key:
        return "Error: OPENAI_API_KEY environment variable not found."

    # Set the API key for OpenAI
    openai.api_key = api_key

    try:
        response = openai.Completion.create(
            model="text-davinci-003",
            prompt=prompt,
            max_tokens=100,
            n=1,
            stop=None,
            temperature=0.5,
        )

        message = response.choices[0].text.strip()

        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        with open(f"/tmp/chatgpt_output_{timestamp}.txt", "w") as file:
            file.write(message)

        # Print the ChatGPT response to the terminal
        print(f"ChatGPT response: {message}")

        return message
    except Exception as e:
        return f"Error: {e}"
    
def convertTextResponseToSpeech(text):
    try:
        tts = gTTS(text=text, lang="en-uk",)

        file_path = f"/tmp/chatgpt_response_{datetime.now().strftime('%Y%m%d-%H%M%S')}.mp3"
        tts.save(file_path)
        return 0, file_path
    except Exception as e:
        print(f"Error converting text to speech: {e}")
        return 1, None

def playSpeechResponse(error_code, file_path):
    if error_code != 0:
        print("Error: Cannot play the speech response due to previous error.")
        return

    try:
        audio = AudioSegment.from_mp3(file_path)
        play(audio)
    except Exception as e:
        print(f"Error playing the speech response: {e}")