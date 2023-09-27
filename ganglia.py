import time
from query_dispatch import ChatGPTQueryDispatcher
from parse_inputs import parse_args, parse_tts_interface, parse_dictation_type
from session_logger import CLISessionLogger, SessionEvent
from audio_turn_indicator import UserTurnIndicator, AiTurnIndicator
import sys
import signal


def initialize_conversation(args):
    USER_TURN_INDICATOR = None
    AI_TURN_INDICATOR = None
    session_logger = None if args.suppress_session_logging else CLISessionLogger()

    if args.enable_turn_indicators:
        try:
            USER_TURN_INDICATOR = UserTurnIndicator()
            AI_TURN_INDICATOR = AiTurnIndicator()
            print("Turn Indicators initialized successfully.")
        except Exception as e:
            print(f"Failed to initialize Turn Indicators: {e}")
            sys.exit("Initialization failed. Exiting program...")

    try:
        tts = parse_tts_interface(args.tts_interface)
        if tts == None:
            sys.exit("ERROR - couldn't load tts sinterface")
        print("Text-to-Speech interface initialized successfully. TTS: ", tts)
    except Exception as e:
        print(f"Failed to initialize Text-to-Speech interface: {e}")
        sys.exit("Initialization failed. Exiting program...")

    try:
        dictation = parse_dictation_type(args.dictation_type)
        print("Dictation type parsed successfully.")
    except Exception as e:
        print(f"Failed to parse Dictation type: {e}")
        sys.exit("Initialization failed. Exiting program...")

    try:
        query_dispatcher = ChatGPTQueryDispatcher(pre_prompt=args.pre_prompt)
        print("Query Dispatcher initialized successfully.")
    except Exception as e:
        print(f"Failed to initialize Query Dispatcher: {e}")
        sys.exit("Initialization failed. Exiting program...")

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
    response = query_dispatcher.sendQuery(prompt)
    if AI_TURN_INDICATOR:
        AI_TURN_INDICATOR.input_out()

    if tts:
        error_code, file_path = tts.convert_text_to_speech(response)
        tts.play_speech_response(file_path)

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

    # TODO fix this
    # print("USER_TURN_INDICATOR: %s", USER_TURN_INDICATOR)
    # print("AI_TURN_INDICATOR: %s", AI_TURN_INDICATOR)
    # print("tts: %s", tts)
    # print("dictation: %s", dictation)
    # print("query_dispatcher: %s", query_dispatcher)
    # print("session_logger: %s", session_logger)

    signal.signal(signal.SIGINT, signal_handler)

    while True:
        try:
            prompt = user_turn(None, dictation, USER_TURN_INDICATOR, args)
            if end_conversation(prompt):
                break
            ai_turn(prompt, query_dispatcher, AI_TURN_INDICATOR, args, tts, session_logger)
        except Exception as e:
            print(f"Exception occurred during main loop: {str(e)}")

    if session_logger:
        session_logger.finalize_session()

    print("Thanks for chatting! Have a great day!")

if __name__ == "__main__":
    main()
