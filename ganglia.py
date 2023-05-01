from dictation import StaticGoogleDictation, LiveAssemblyAIDictation
from query_dispatch import ChatGPTQueryDispatcher
from parse_inputs import parse_args, parse_tts_interface
from session_logger import CLISessionLogger, SessionEvent

def main():
    global args
    args = parse_args()

    # TODO: this is getting to be a lot - should break it up into a loader that has error catching
    tts = parse_tts_interface(args.tts_interface)
    dictation = LiveAssemblyAIDictation()
    query_dispatcher = ChatGPTQueryDispatcher(static_response=args.static_response, pre_prompt=args.pre_prompt)
    session_logger = None if args.suppress_session_logging else CLISessionLogger()

    print("Starting session with GANGLIA. To stop, simply say \"Goodbye\"")

    while True:
        prompt = dictation.getDictatedInput(args.listen_dur_secs, args.device_index)
        if prompt is None:
            continue

        if "goodbye" in prompt.strip().lower():
            response = "Ok, see you later!"
            error_code, file_path = tts.convert_text_to_speech(response)
            tts.play_speech_response(error_code, file_path)
            break
        else:
            response = query_dispatcher.sendQuery(prompt, static_response=args.static_response)
            error_code, file_path = tts.convert_text_to_speech(response)
            tts.play_speech_response(error_code, file_path)

            session_logger.log_session_interaction(SessionEvent(prompt, response))

    session_logger.finalize_session()

    print("Thanks for chatting! Have a great day!")

if __name__ == "__main__":
    main()
