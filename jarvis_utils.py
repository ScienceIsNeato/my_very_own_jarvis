import os
import openai
from datetime import datetime

openai.api_key = os.environ.get("OPENAI_API_KEY")

def sendQueryToServer(prompt, pre_prompt=None):
    # Prepend the pre-prompt to the prompt if it is provided
    if pre_prompt:
        prompt = f"Pre-Prompt: {pre_prompt}. Prompt: {prompt}"

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
