from dictation import StaticGoogleDictation, LiveAssemblyAIDictation
from query_dispatch import ChatGPTQueryDispatcher
from parse_inputs import parse_args, parse_tts_interface
from session_logger import CLISessionLogger, SessionEvent
from audio_turn_indicator import AudioTurnIndicator
import os
import logging

TURN_INDICATOR = AudioTurnIndicator(os.path.join("media", "zapsplat_multimedia_ui_window_minimize_short_swipe_whoosh_71502.mp3"), os.path.join("media", "zapsplat_multimedia_ui_window_maximize_short_swipe_whoosh_001_71500.mp3"))

def main():
    global args
    args = parse_args()

    # TODO: this is getting to be a lot - should break it up into a loader that has error catching
    try:
        tts = parse_tts_interface(args.tts_interface)
    except Exception as e:
        logging.warning(f"Failed to initialize TTS interface: {str(e)}")
        tts = None

    try:
        dictation = LiveAssemblyAIDictation()
    except Exception as e:
        logging.warning(f"Failed to initialize dictation: {str(e)}")
        dictation = None

    query_dispatcher = ChatGPTQueryDispatcher(static_response=args.static_response, pre_prompt=args.pre_prompt)

    try:
        session_logger = None if args.suppress_session_logging else CLISessionLogger()
    except Exception as e:
        logging.warning(f"Failed to initialize session logger: {str(e)}")
        session_logger = None

    print("Starting session with Jarvis. To stop, simply say \"Goodbye\"")

    while True:
        try:
            TURN_INDICATOR.input_started() # indicate start of turn
            prompt = dictation.getDictatedInput(args.listen_dur_secs, args.device_index) if dictation else input()
            TURN_INDICATOR.input_terminated() # indicate end of turn
            if prompt is None:
                continue

            if "goodbye" in prompt.strip().lower():
                response = "Ok, see you later!"
            else:
                TURN_INDICATOR.input_started() # indicate start of turn
                response = query_dispatcher.sendQuery(prompt, static_response=args.static_response)
                TURN_INDICATOR.input_terminated() # indicate end of turn

            if tts:
                error_code, file_path = tts.convert_text_to_speech(response)
                tts.play_speech_response(error_code, file_path)

            if session_logger:
                session_logger.log_session_interaction(SessionEvent(prompt, response))
        except Exception as e:
            logging.warning(f"Exception occurred during main loop: {str(e)}")

        if prompt and "goodbye" in prompt.strip().lower():
            break

    if session_logger:
        session_logger.finalize_session()

    print("Thanks for chatting! Have a great day!")

if __name__ == "__main__":
    main()
