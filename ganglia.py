import time
from query_dispatch import ChatGPTQueryDispatcher
from parse_inputs import parse_args, parse_tts_interface, parse_dictation_type
from session_logger import CLISessionLogger, SessionEvent
from audio_turn_indicator import UserTurnIndicator, AiTurnIndicator
import sys
import signal
from logger import Logger


def initialize_conversation(args):
    USER_TURN_INDICATOR = None
    AI_TURN_INDICATOR = None
    session_logger = None if args.suppress_session_logging else CLISessionLogger(args)

    if args.enable_turn_indicators:
        try:
            USER_TURN_INDICATOR = UserTurnIndicator()
            AI_TURN_INDICATOR = AiTurnIndicator()
            Logger.print_debug("Turn Indicators initialized successfully.")
        except Exception as e:
            Logger.print_error(f"Failed to initialize Turn Indicators: {e}")
            sys.exit("Initialization failed. Exiting program...")

    try:
        tts = parse_tts_interface(args.tts_interface)
        if tts == None:
            sys.exit("ERROR - couldn't load tts sinterface")
        Logger.print_debug("Text-to-Speech interface initialized successfully. TTS: ", args.tts_interface)
    except Exception as e:
        Logger.print_error(f"Failed to initialize Text-to-Speech interface: {e}")
        sys.exit("Initialization failed. Exiting program...")

    try:
        dictation = parse_dictation_type(args.dictation_type)
        Logger.print_debug("Dictation type parsed successfully.")
    except Exception as e:
        Logger.print_error(f"Failed to parse Dictation type: {e}")
        sys.exit("Initialization failed. Exiting program...")

    try:
        query_dispatcher = ChatGPTQueryDispatcher()
        Logger.print_debug("Query Dispatcher initialized successfully.")
    except Exception as e:
        Logger.print_error(f"Failed to initialize Query Dispatcher: {e}")
        sys.exit("Initialization failed. Exiting program...")

    Logger.print_info("Starting session with GANGLIA. To stop, simply say \"Goodbye\"")

    return USER_TURN_INDICATOR, AI_TURN_INDICATOR, tts, dictation, query_dispatcher, session_logger

def user_turn(prompt, dictation, USER_TURN_INDICATOR, args):
    if USER_TURN_INDICATOR:
        USER_TURN_INDICATOR.input_in()
    prompt = dictation.getDictatedInput(args.device_index) if dictation else input()
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
        tts.play_speech_response(file_path, response)

    if session_logger:
        session_logger.log_session_interaction(SessionEvent(prompt, response))

    return response

def end_conversation(prompt, force=False):
    if force:
        return True
    return prompt and "goodbye" in prompt.strip().lower()

def signal_handler(sig, frame):
    Logger.print_info("User killed program - exiting gracefully")
    end_conversation(None, force=True)
    exit(0)

def main():
    global args

    args = parse_args()

    initialization_failed = True

    # If there's some spurious problem initializing, wait a bit and try again
    while initialization_failed:
        try:
            USER_TURN_INDICATOR, AI_TURN_INDICATOR, tts, dictation, query_dispatcher, session_logger = initialize_conversation(args)
            initialization_failed = False
        except Exception as e:
            Logger.print_error(f"Error initializing conversation: {e}")
            time.sleep(20)

    Logger.print_legend()

    signal.signal(signal.SIGINT, signal_handler)

    while True:
        try:
            prompt = user_turn(None, dictation, USER_TURN_INDICATOR, args)
            if end_conversation(prompt):
                break
            ai_turn(prompt, query_dispatcher, AI_TURN_INDICATOR, args, tts, session_logger)
        except Exception as e:
            if 'Exceeded maximum allowed stream duration' in str(e):
                Logger.print_info('Stream exceeded max duration. Refreshing convo...')
                continue

            else:
                Logger.print_error(f"Exception in main loop: {str(e)}")


    if session_logger:
        session_logger.finalize_session()

    Logger.print_info("Thanks for chatting! Have a great day!")

if __name__ == "__main__":
    main()
