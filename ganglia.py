from threading import Thread
import time
from query_dispatch import ChatGPTQueryDispatcher
from parse_inputs import load_config, parse_tts_interface, parse_dictation_type
from session_logger import CLISessionLogger, SessionEvent
from audio_turn_indicator import UserTurnIndicator, AiTurnIndicator
from ttv.ttv import text_to_video
import sys
import os
import signal
from logger import Logger
from hotwords import HotwordManager
from conversation_context import ContextManager
from pubsub import PubSub
from motion_sensor import MotionDetectionSensor
import datetime
from ttv.image_generation import generate_image, save_image_with_caption, generate_blank_image, save_image_without_caption
from ttv.audio_generation import generate_audio, get_audio_duration
from ttv.video_generation import create_video_segment, create_still_video_with_fade
from music_lib import MusicGenerator
from ttv.story_processor import process_story, generate_image_for_sentence
from ttv.final_video_generation import assemble_final_video, concatenate_video_segments



class GangliaRateLimiter:
    def __init__(self):
        self.last_request_time = None
        self.request_interval = 60  # Set request interval to 60 seconds (1 minute)

    def can_make_request(self):
        """Check if a minute has passed since the last request."""
        current_time = time.time()
        if self.last_request_time is None:
            self.last_request_time = current_time
            return True  # Allow the first request
        return (current_time - self.last_request_time) >= self.request_interval

    def update_last_request_time(self):
        """Update the timestamp of the last request."""
        self.last_request_time = time.time()

# Initialize the rate limiter
rate_limiter = GangliaRateLimiter()

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

    # QueryDispatcher setup
    try:
        query_dispatcher = ChatGPTQueryDispatcher()
        Logger.print_debug("Query Dispatcher initialized successfully.")
    except Exception as e:
        Logger.print_error(f"Failed to initialize Query Dispatcher: {e}")
        sys.exit("Initialization failed. Exiting program...")

    # HotwordManager setup
    hotword_manager = None
    try:
        hotword_manager = HotwordManager('config/ganglia_config.json')  # Updated config path
        Logger.print_debug("HotwordManager initialized successfully.")
    except Exception as e:
        Logger.print_error(f"Failed to initialize HotwordManager: {e}")

    # ContextManager setup
    context_manager = None
    try:
        context_manager = ContextManager('config/ganglia_config.json')  # Load conversation context
        Logger.print_debug("ContextManager initialized successfully.")

        # Feed the context into the query dispatcher
        query_dispatcher.add_system_context(context_manager.context)

    except Exception as e:
        Logger.print_error(f"Failed to initialize ContextManager: {e}")


    Logger.print_info("Starting session with GANGLIA. To stop, simply say \"Goodbye\"")

    return USER_TURN_INDICATOR, AI_TURN_INDICATOR, tts, dictation, query_dispatcher, session_logger, hotword_manager

def user_turn(prompt, dictation, USER_TURN_INDICATOR, args):
    while True:  # Keep asking for input until a non-empty prompt is received.
        if USER_TURN_INDICATOR:
            USER_TURN_INDICATOR.input_in()

        got_input = False
        while not got_input:
            try:
                prompt = dictation.getDictatedInput(args.device_index, interruptable=False) if dictation else input()

                # If the input is empty restart the loop
                if not prompt.strip():
                    continue

                got_input = True # Break out of the input loop

                if USER_TURN_INDICATOR:
                    USER_TURN_INDICATOR.input_out()

                return prompt
            except KeyboardInterrupt:
                Logger.print_info("User killed program - exiting gracefully")
                should_end_conversation(None)
                exit(0)
        
        # Print a fun little prompt at the beginning of the user's turn
        Logger.print_info(dictation.generate_random_phrase())
        prompt = dictation.getDictatedInput(args.device_index, interruptable=False) if dictation else input()


def ai_turn(prompt, query_dispatcher, AI_TURN_INDICATOR, args, hotword_manager, tts, session_logger, predetermined_response=None):
    hotword_detected, hotword_phrase = hotword_manager.detect_hotwords(prompt)

    if AI_TURN_INDICATOR:
        AI_TURN_INDICATOR.input_in()

    if hotword_detected:
        # Hotword detected, skip query dispatcher
        response = hotword_phrase
    elif predetermined_response:
        response = prompt
    else:
        response = query_dispatcher.sendQuery(prompt)

    if AI_TURN_INDICATOR:
        AI_TURN_INDICATOR.input_out()

    if tts:
        # Generate speech response
        _, file_path = tts.convert_text_to_speech(response)
        tts.play_speech_response(file_path, response)

        # If this response is coming from a hotword, then we want to clear the screen shortly afterwards (scavenger hunt mode)
        if hotword_detected:
            clear_screen_after_hotword(tts)

    if session_logger:
        # Log interaction
        session_logger.log_session_interaction(SessionEvent(prompt, response))

def should_end_conversation(prompt):
    return prompt and "goodbye" in prompt.strip().lower()

def end_conversation(session_logger=None):
    Logger.print_info("Ending session with GANGLIA. Goodbye!")
    if session_logger:
        session_logger.finalize_session()
    sys.exit(0)

def signal_handler(sig, frame):
    Logger.print_info("User killed program - exiting gracefully")
    end_conversation()

def clear_screen_after_hotword(tts):
    output = "hotword detected - clearing response from screen after playback"
    _, file_path = tts.convert_text_to_speech(output)
    tts.play_speech_response(file_path, output)
    os.system('cls' if os.name == 'nt' else 'clear')

def setup_tmp_dir():
    # Determine the base directory based on the operating system
    if os.name == 'nt':  # Windows
        base_dir = os.path.join(tempfile.gettempdir(), "GANGLIA")
    else:  # Unix-based systems
        base_dir = "/tmp/GANGLIA"

    # Ensure the directory exists
    os.makedirs(base_dir, exist_ok=True)

def get_tmp_dir():
    # Determine the base directory based on the operating system
    if os.name == 'nt':  # Windows
        base_dir = os.path.join(tempfile.gettempdir(), "GANGLIA")
    else:  # Unix-based systems
        base_dir = "/tmp/GANGLIA"

    return base_dir

def handle_motion_event(image_path, query_dispatcher, session_logger, AI_TURN_INDICATOR, args, hotword_manager, tts):
    """Handles the motion event by sending an image-based query with rate limiting."""
    try:
        # Send image and get AI response
        response = query_dispatcher.sendQuery(
            current_input="say hello to any humans in this image, making sure to comment on some unique feature or piece of clothing. Just focus on the humans, not the objects in the background",
            image_path=image_path
        )

        Logger.print_info(f"AI response: {response}")

        # Log the event
        if session_logger:
            session_logger.log_session_interaction(
                SessionEvent("Motion Detected", response)
            )

        # Update the request time after a successful query
        rate_limiter.update_last_request_time()

        # Initiate AI turn based on the response
        ai_turn(response, 
                query_dispatcher, AI_TURN_INDICATOR, args, hotword_manager, tts, session_logger, predetermined_response=True)

        return response


    except Exception as e:
        Logger.print_error(f"Error handling motion event: {e}")
        if session_logger:
            session_logger.log_session_interaction(
                SessionEvent("SYSTEM ERROR", f"Error handling motion event: {e}")
            )


def motion_sensor_event_handler(message, query_dispatcher, session_logger, AI_TURN_INDICATOR, args, hotword_manager, tts):
    """Callback for the motion sensor event."""
    # Extract the image path from the message
    if "Image saved at:" in message:
        image_path = message.split("Image saved at: ")[1].strip()

        if rate_limiter.can_make_request():
            Logger.print_info("Motion detected, sending query...")
            # Create a new thread for the AI query to avoid blocking the main thread
            Thread(target=handle_motion_event, args=(image_path, query_dispatcher, session_logger, AI_TURN_INDICATOR, args, hotword_manager, tts)).start()
            rate_limiter.update_last_request_time()  # Update the request time after a successful query

def setup_motion_sensor(pubsub, query_dispatcher, session_logger, AI_TURN_INDICATOR, args, hotword_manager, tts):
    """Sets up the motion sensor and subscribes to its events."""
    # Subscribe to the "motion_sensor" topic
    pubsub.subscribe("motion_sensor", lambda message: motion_sensor_event_handler(message, query_dispatcher, session_logger, AI_TURN_INDICATOR, args, hotword_manager, tts))

    # Create the motion sensor instance (it will publish events on its own)
    motion_sensor = MotionDetectionSensor(pubsub, debug=False)

    Logger.print_info("Motion sensor initialized and event handler subscribed.")

def send_image_query_with_rate_limit(image_path, query_dispatcher):
    """Send an image query ensuring no more than one request per minute."""
    if rate_limiter.can_make_request():
        # Send the image query
        response = query_dispatcher.send_image_query(image_path)
        rate_limiter.update_last_request_time()  # Update the request time after a successful query
        return response
    else:
        Logger.print_info("Skipping query: Still within the 1-minute cooldown period.")
        return None

def main():
    global args

    args = load_config()

    setup_tmp_dir()

    # If there's some spurious problem initializing, wait a bit and try again
    initialization_failed = True
    while initialization_failed:
        try:
            USER_TURN_INDICATOR, AI_TURN_INDICATOR, tts, dictation, query_dispatcher, session_logger, hotword_manager = initialize_conversation(args)
            dictation.set_session_logger(session_logger)
            initialization_failed = False
        except Exception as e:
            Logger.print_error(f"Error initializing conversation: {e}")
            time.sleep(20)

    # Currently, the text-to-video functionality is its own code path
    if args.text_to_video:
        if not args.ttv_config:
            Logger.print_error("JSON input file is required for --text-to-video.")
            sys.exit(1)
        current_datetime = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
        output_path = f"/tmp/GANGLIA/ttv/final_output_{current_datetime}.mp4"
        tts_client = parse_tts_interface(args.tts_interface)
        text_to_video(args.ttv_config, args.skip_image_generation, output_path, tts_client, query_dispatcher)
        sys.exit(0)  # Exit after processing the video generation to avoid entering the conversational loop

    Logger.print_legend()

    signal.signal(signal.SIGINT, signal_handler)

        # Setup PubSub and motion sensor
    pubsub = PubSub()
    setup_motion_sensor(pubsub, query_dispatcher, session_logger, AI_TURN_INDICATOR, args, hotword_manager, tts)

    while True:
        try:
            prompt = user_turn(None, dictation, USER_TURN_INDICATOR, args)
            if should_end_conversation(prompt):
                Logger.print_info("User ended conversation")
                ai_turn(prompt, query_dispatcher, AI_TURN_INDICATOR, args, hotword_manager, tts, session_logger)
                end_conversation(session_logger)
                break
            ai_turn(prompt, query_dispatcher, AI_TURN_INDICATOR, args, hotword_manager, tts, session_logger)
        except Exception as e:
            if 'Exceeded maximum allowed stream duration' in str(e) or 'Long duration elapsed without audio' in str(e):
                continue
            else:
                # Treat the exception as part of the conversation
                session_logger.log_session_interaction(
                    SessionEvent(
                        user_input="SYSTEM ERROR",
                        response_output=f"Exception occurred: {str(e)}"
                    )
                )


    end_conversation(session_logger)

    Logger.print_info("Thanks for chatting! Have a great day!")

if __name__ == "__main__":
    main()
