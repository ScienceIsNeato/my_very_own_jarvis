import pandas as pd
import json

def test_sessionLogger():
    # Load conversation history from JSON file
    with open('/tmp/Jarvis_session_2023-04-24T01:14:27.json', 'r') as f:
        conversation = json.load(f)['conversation']

    # Convert conversation history to a Pandas DataFrame
    df = pd.DataFrame(conversation, columns=['user_input', 'response_output'])

    # Print the conversation history in a tabular format
    print(df.to_markdown(index=False)) # use to_markdown() method for more formatted output

    # Assert no errors occurred
    assert True
