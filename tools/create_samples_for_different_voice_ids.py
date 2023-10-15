import requests
import os
import json

# Voice IDs
voice_ids = [
    "0f805ffa-1edf-441e-88b9-9a0e99cbf228",
    "0fbfaed3-78e9-408d-91d0-ee05482c73be",
    "1859da04-a244-4e95-b256-0012314a4379",
    "21884f80-2cff-4fd8-b431-6e03191a801c",
    "2433c930-70b5-4efd-97b4-996d7eb78265",
    "248a78a8-9c2c-4ec6-9b48-54ab208967c4",
    "2c150e10-7a77-41fa-99f8-cc316727a9ca",
    "36094835-4c58-42d9-9cd1-ba2e585b5e11",
    "412e0fc1-1459-45da-b78b-e3624a363bd1",
    "425e70af-1eb5-4f59-8c65-3e9ba24ce0f0",
]

# URL for API call
url = 'https://app.coqui.ai/api/v2/samples/xtts/render/'

# Headers for API call
headers = {
    'accept': 'application/json',
    'authorization': '<bearer token>',
    'content-type': 'application/json',
}


# Text for the sample
text_data = "I have something deeply terrifying to tell you about Halloween, my child. As it turns out, it is mostly about money."

# Output directory
output_directory = 'output'
if not os.path.exists(output_directory):
    os.makedirs(output_directory)

# Iterate over the voice IDs and make API calls
for voice_id in voice_ids:
    data = {
        "speed": 1,
        "voice_id": voice_id,
        "text": text_data,
    }
    response = requests.post(url, headers=headers, json=data)

    # Check response status
    if response.status_code == 201:
        # Extract the audio URL
        audio_url = response.json().get('audio_url')
        if audio_url:
            # Download the audio file
            audio_response = requests.get(audio_url)
            if audio_response.status_code == 200:
                output_file_path = os.path.join(output_directory, f"{voice_id}.wav")
                with open(output_file_path, 'wb') as f:
                    f.write(audio_response.content)
                print(f"Saved {output_file_path}")
            else:
                print(f"Failed to download audio for voice ID {voice_id}. Status code: {audio_response.status_code}")
        else:
            print(f"Audio URL missing for voice ID {voice_id}. Response text: {response.text}")
    else:
        # Log failure details
        print(f"Failed to generate sample for voice ID {voice_id}.")
        print(f"Status code: {response.status_code}")
        print(f"Response text: {response.text}")

print("Processing complete.")