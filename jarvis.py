from jarvis_utils import getDictatedInput, sendQueryToServer
from parse_inputs import parse_args, parse_tts_interface

def main():
    global args
    args = parse_args()

    if args.persona:
        persona = args.persona
    else:
        persona = None

    tts = parse_tts_interface(args.tts_interface)

    print("Starting session with Jarvis. To stop, simply say \"Goodbye\"")

    while True:
        prompt = getDictatedInput(args.listen_dur_secs, args.device_index)
        if prompt is None:
            continue

        if prompt.strip().lower() == "goodbye":
            response = "Ok, see you later!"
            error_code, file_path = tts.convert_text_to_speech(response)
            tts.play_speech_response(error_code, file_path)
            break
        else:
            response = sendQueryToServer(prompt, persona)
            error_code, file_path = tts.convert_text_to_speech(response)
            tts.play_speech_response(error_code, file_path)

    print("Thanks for chatting! Have a great day!")

if __name__ == "__main__":
    main()
