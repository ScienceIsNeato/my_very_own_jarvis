import argparse
from jarvis_utils import getDictatedInput, sendQueryToServer, convertTextResponseToSpeech, playSpeechResponse


def parse_args():
    parser = argparse.ArgumentParser(description="Jarvis - AI Assistant")
    parser.add_argument("-l", "--listen_dur_secs", type=int, default=5, help="Duration in seconds to listen for user input")
    parser.add_argument("-d", "--device_index", type=int, default=0, help="Index of the input device to use.")
    parser.add_argument("-p", "--persona", type=str, default=None, help="Persona string for guiding the AI's behavior")
    return parser.parse_args()


def main():
    global args
    args = parse_args()

    if args.persona:
        persona = args.persona
    else:
        persona = None

    print("Starting session with Jarvis. To stop, simply say \"Goodbye\"")

    while True:
        prompt = getDictatedInput(args.listen_dur_secs, args.device_index)
        if prompt is None:
            continue

        # Check if the prompt contains the case-insensitive word "Goodbye" and has only one word
        if prompt.strip().lower() == "goodbye":
            response = "Ok, see you later!"
            error_code, file_path = convertTextResponseToSpeech(response)
            playSpeechResponse(error_code, file_path)
            break
        else:
            response = sendQueryToServer(prompt, persona)
            error_code, file_path = convertTextResponseToSpeech(response)
            playSpeechResponse(error_code, file_path)

    # Print a fun exit message
    print("Thanks for chatting! Have a great day!")


if __name__ == '__main__':
    main()
