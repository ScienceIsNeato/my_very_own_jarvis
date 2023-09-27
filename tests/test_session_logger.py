import json
import pandas as pd
import pytest
from pathlib import Path

@pytest.fixture(scope="module")
def conversation_data(tmp_path_factory):
    conversation = [
        {
            "user_input": "Who are you.",
            "response_output": "[GHOUL] I am the Headless Horseman, come to haunt this driveway on this spooky night!"
        },
        {
            "user_input": "Is there a reason that you're angry tonight.",
            "response_output": "[GHOUL] Yes, I'm angry because I was cursed to haunt this driveway on Halloween night for all eternity!"
        },
        {
            "user_input": "How many years have you been doing this.",
            "response_output": "[GHOUL] I've been doing this for centuries!"
        },
        {
            "user_input": "What's the spookiest thing you've ever done.",
            "response_output": "[GHOUL] The spookiest thing I've ever done was to haunt a graveyard at midnight. I floated through the air, my laughter echoing through the darkness. The chill of the night air sent shivers down my spine as I watched the living cower in fear."
        },
        {
            "user_input": "What's going to happen to our street on Halloween night.",
            "response_output": "[GHOUL] Oh, you don't want to know what's going to happen to your street on Halloween night. It's a night of tricks and treats, and you never know what might be lurking in the shadows. Be careful out there!"
        },
        {
            "user_input": "My name is Timmy.",
            "response_output": "[GHOUL] Timmy, I know your name, but what I don't know is why you have come to my driveway on this spooky night."
        },
        {
            "user_input": "Well. I came because, to be honest, I'm facing my fears.",
            "response_output": "[GHOUL] Ah, so you've come to face your fears, have you? Well, I'm sure you'll find plenty of things to be scared of here on this Halloween night. But beware, for I am the guardian of this driveway, and I will not let you pass without a challenge!"
        },
        {
            "user_input": "What kind of challenge do you have for me.",
            "response_output": "[GHOUL] I challenge you to make it to the end of the driveway without screaming!"
        },
        {
            "user_input": "Scream. Scream, scream. Nah.",
            "response_output": "Just kidding. [GHOUL] Trick or treat!"
        }
    ]

    # Create a temporary file for the conversation data
    file_path = Path(tmp_path_factory.mktemp("data") / "conversation.json")

    # Write the conversation data to the temporary file
    with open(file_path, "w") as f:
        json.dump({"sessionID": "fd1c757b-da49-49e0-86ed-684cf4f5aaa1", "timestamp": "2023-04-24T01:44:07", "conversation": conversation}, f)

    return file_path

def test_session_logger(conversation_data):
    # Load conversation history from JSON file
    with open(conversation_data, 'r') as f:
        data = json.load(f)

    # Extract metadata from the session
    session_id = data['sessionID']
    timestamp = data['timestamp']

    # Extract conversation history from
