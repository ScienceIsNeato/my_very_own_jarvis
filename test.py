import openai
import base64
import os
from dotenv import load_dotenv

# Load API key from .env file
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

# Function to encode the image to base64
def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

# Path to the local image file
image_path = '/var/folders/qz/l66xwrv15w1fjmfvf1s490b00000gn/T/ganglia_image_1729671665.png'

# Encode the image to base64
base64_image = encode_image(image_path)

# Make the request to GPT-4 with vision capabilities
response = openai.ChatCompletion.create(
    model="gpt-4o-mini",
    messages=[
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "Describe the person(s) in this image and what they are wearing in as much detail as possible. This is a statis camera in front of a Halloween display and the background never changes, so I don't need to know any information at all about anything other than the people in the frame."},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{base64_image}"  # Use base64-encoded image
                    }
                }
            ]
        }
    ],
    max_tokens=300,
)

# Print the AI's response
print(response.choices[0]['message']['content'])
