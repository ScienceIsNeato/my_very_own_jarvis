import pickle

class ConversationHistory:
    def __init__(self):
        self.history = []

    def add_message(self, message, sender):
        # Add a message to the conversation history
        message_data = {
            "type": sender,
            "content": message
        }
        self.history.append(message_data)


    def save_history(self, file_path):
        # Save the conversation history to a file
        with open(file_path, 'wb') as f:
            pickle.dump(self.history, f)
        print(f"Conversation history saved to {file_path}")

    def load_history(self, file_path):
        # Load the conversation history from a file
        try:
            with open(file_path, 'rb') as f:
                self.history = pickle.load(f)
            print(f"Conversation history loaded from {file_path}")
        except FileNotFoundError:
            print(f"Error: File not found at {file_path}")
