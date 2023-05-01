from dictation import StaticGoogleDictation, LiveAssemblyAIDictation
from query_dispatch import ChatGPTQueryDispatcher
from parse_inputs import parse_args, parse_tts_interface
from session_logger import CLISessionLogger, SessionEvent
from audio_turn_indicator import UserTurnIndicator, AiTurnIndicator
import logging
import signal

def initialize_conversation(args):
    USER_TURN_INDICATOR = None
    AI_TURN_INDICATOR = None

    if args.enable_turn_indicators:
        USER_TURN_INDICATOR = UserTurnIndicator()
        AI_TURN_INDICATOR = AiTurnIndicator()

    tts = parse_tts_interface(args.tts_interface)
    dictation = LiveAssemblyAIDictation()
    query_dispatcher = ChatGPTQueryDispatcher(static_response=args.static_response, pre_prompt=args.pre_prompt)
    session_logger = None if args.suppress_session_logging else CLISessionLogger()

    print("Starting session with GANGLIA. To stop, simply say \"Goodbye\"")

    return USER_TURN_INDICATOR, AI_TURN_INDICATOR, tts, dictation, query_dispatcher, session_logger

def user_turn(prompt, dictation, USER_TURN_INDICATOR, args):
    if USER_TURN_INDICATOR:
        USER_TURN_INDICATOR.input_in()
    prompt = dictation.getDictatedInput(args.listen_dur_secs, args.device_index) if dictation else input()
    if USER_TURN_INDICATOR:
        USER_TURN_INDICATOR.input_out()
    return prompt

def ai_turn(prompt, query_dispatcher, AI_TURN_INDICATOR, args, tts, session_logger):
    if AI_TURN_INDICATOR:
        AI_TURN_INDICATOR.input_in()
    response = query_dispatcher.sendQuery(prompt, static_response=args.static_response)
    if AI_TURN_INDICATOR:
        AI_TURN_INDICATOR.input_out()

    if tts:
        error_code, file_path = tts.convert_text_to_speech(response)
        tts.play_speech_response(error_code, file_path)

    if session_logger:
        session_logger.log_session_interaction(SessionEvent(prompt, response))

    return response

def end_conversation(prompt, force=False):
    if force:
        return True
    return prompt and "goodbye" in prompt.strip().lower()

def signal_handler(sig, frame):
    print("User killed program - exiting gracefully")
    end_conversation(None, force=True)
    exit(0)

def main():
    global args
    args = parse_args()
    USER_TURN_INDICATOR, AI_TURN_INDICATOR, tts, dictation, query_dispatcher, session_logger = initialize_conversation(args)

    signal.signal(signal.SIGINT, signal_handler)

    while True:
        try:
            prompt = user_turn(None, dictation, USER_TURN_INDICATOR, args)
            if end_conversation(prompt):
                response = "Ok, see you later!"
                break

            response = ai_turn(prompt, query_dispatcher, AI_TURN_INDICATOR, args, tts, session_logger)

        except Exception as e:
            logging.warning(f"Exception occurred during main loop: {str(e)}")

    if session_logger:
        session_logger.finalize_session()

    print("Thanks for chatting! Have a great day!")

if __name__ == "__main__":
    main()
