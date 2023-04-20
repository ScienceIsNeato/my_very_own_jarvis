import os
import openai
import speech_recognition as sr
from datetime import datetime

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
        audio = recognizer.listen(source, timeout=listen_dur_secs, phrase_time_limit=50000)
        print("Finished listening.")

        try:
            text = recognizer.recognize_google(audio)
            print("You said: ", text)
            return text
        except sr.UnknownValueError:
            print("Google Speech Recognition could not understand the audio.")
        except sr.RequestError as e:
            print(f"Could not request results from Google Speech Recognition service; {e}")



def sendQueryToServer(prompt, persona=None):
    # Prepend the persona to the prompt if it is provided
    if persona:
        prompt = f"You are to assume the following persona: {persona}. As that persona, will you answer the following question? {prompt}"

    response = openai.Completion.create(
        engine="text-davinci-003",
        prompt=prompt,
        max_tokens=100,
        n=1,
        stop=None,
        temperature=0.1,
    )

    message = response.choices[0].text.strip()

    # Print the response to the terminal with the preface
    print(f"chatGPT said: {message}")

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    with open(f"/tmp/chatgpt_output_{timestamp}.txt", "w") as file:
        file.write(message)

    return message
