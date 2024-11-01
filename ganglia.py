import tempfile
from threading import Thread
import time

import cv2
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

def user_turn(prompt, dictation, USER_TURN_INDICATOR, args, pubsub):
    """Capture user input or stop when 'user_turn_end' event is triggered."""

    # Flag to monitor end-turn state
    end_turn = False

    # Event handler to set end_turn flag when 'user_turn_end' event is published
    def on_end_turn_event(message):
        nonlocal end_turn
        end_turn = True

    # Subscribe to the 'user_turn_end' event
    pubsub.subscribe("user_turn_end", on_end_turn_event)

    # Main loop for user input
    while not end_turn:
        if USER_TURN_INDICATOR:
            USER_TURN_INDICATOR.input_in()

        got_input = False
        while not got_input and not end_turn:
            try:
                prompt = dictation.getDictatedInput(args.device_index) if dictation else input()

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
        
        # If turn isn't ended, log a prompt and continue getting input
        if not end_turn:
            Logger.print_info(dictation.generate_random_phrase())
            prompt = dictation.getDictatedInput(args.device_index) if dictation else input()

    # Unsubscribe after use to clean up
    pubsub.unsubscribe("user_turn_end", on_end_turn_event)


def ai_turn(prompt, query_dispatcher, AI_TURN_INDICATOR, args, hotword_manager, tts, session_logger, predetermined_response=None, pubsub=None):
    hotword_detected, hotword_phrase = hotword_manager.detect_hotwords(prompt)

    if AI_TURN_INDICATOR:
        AI_TURN_INDICATOR.input_in()

    if hotword_detected:
        # Hotword detected, check for "PREVIEW"
        print
        if hotword_phrase == "Let me see if that passphrase works and if I can access this new feature...":
            
            # Setup the one-time motion detector with max_events=1
            def preview_motion_sensor():
                motion_sensor = MotionDetectionSensor(pubsub, video_src=args.video_src, debug=True, max_events=1)
                motion_sensor.thread.join()  # Wait for the motion detection thread to complete
                if session_logger:
                    # Log interaction
                    session_logger.log_session_interaction(SessionEvent(prompt, response))
                return

            # Start the preview motion sensor in a new thread
            Thread(target=preview_motion_sensor).start()

        # Provide the hotword response as usual
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

def handle_motion_event(frame, query_dispatcher, session_logger, AI_TURN_INDICATOR, args, hotword_manager, tts, dictation, pubsub):
    """Handles the motion event by saving the image to disk just before sending the query."""
    try:
        pubsub.publish("pause_main_loop", "Pausing main loop due to motion event.")
        time.sleep(0.1)  # Allow time for the pause to take effect
        pubsub.publish("user_turn_end", "Ending user turn due to external trigger")

        # Save the image to disk temporarily
        temp_dir = tempfile.gettempdir()
        timestamp = int(time.time())
        image_path = os.path.join(temp_dir, f"ganglia_image_{timestamp}.png")
        cv2.imwrite(image_path, frame)
        
        # Send image and get AI response using the file path
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
                query_dispatcher, AI_TURN_INDICATOR, args, hotword_manager, tts, session_logger, predetermined_response=True, pubsub=pubsub)

        pubsub.publish("unpause_main_loop", "Resuming main loop after motion event.")

        return response

    except Exception as e:
        Logger.print_error(f"Error handling motion event: {e}")
        if session_logger:
            session_logger.log_session_interaction(
                SessionEvent("SYSTEM ERROR", f"Error handling motion event: {e}")
            )


def motion_sensor_event_handler(frame, query_dispatcher, session_logger, AI_TURN_INDICATOR, args, hotword_manager, tts, dictation, pubsub):
    """Callback for the motion sensor event."""
    if rate_limiter.can_make_request():
        Logger.print_info("Motion detected, sending query...")
        # Create a new thread for the AI query to avoid blocking the main thread
        Thread(target=handle_motion_event, args=(frame, query_dispatcher, session_logger, AI_TURN_INDICATOR, args, hotword_manager, tts, dictation, pubsub)).start()
        rate_limiter.update_last_request_time()  # Update the request time after a successful query

def setup_motion_sensor(pubsub, query_dispatcher, session_logger, AI_TURN_INDICATOR, args, hotword_manager, tts, dictation):
    """Sets up the motion sensor and subscribes to its events."""
    # Subscribe to the "motion_sensor" topic
    pubsub.subscribe("motion_sensor", lambda message: motion_sensor_event_handler(message, query_dispatcher, session_logger, AI_TURN_INDICATOR, args, hotword_manager, tts, dictation, pubsub))

    # Create the motion sensor instance (it will publish events on its own)

    Logger.print_info("Motion sensor initialized and event handler subscribed.")
    motion_sensor = MotionDetectionSensor(pubsub, video_src=args.video_src, debug=False, max_events=1)
    return motion_sensor

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
    paused = False  # Flag to control main loop

    # Initialize PubSub and subscribe to pause/unpause events
    pubsub = PubSub()

    # Event handlers to update the paused flag
    def on_pause_event(message):
        nonlocal paused
        paused = True

    def on_unpause_event(message):
        nonlocal paused
        paused = False

    pubsub.subscribe("pause_main_loop", on_pause_event)
    pubsub.subscribe("unpause_main_loop", on_unpause_event)
    pubsub.subscribe("motion_sensor", lambda frame: motion_sensor_event_handler(
        frame, query_dispatcher, session_logger, AI_TURN_INDICATOR, args, hotword_manager, tts, dictation, pubsub))


    # Initialization of components
    initialization_failed = True
    while initialization_failed:
        try:
            USER_TURN_INDICATOR, AI_TURN_INDICATOR, tts, dictation, query_dispatcher, session_logger, hotword_manager = initialize_conversation(args)
            dictation.set_session_logger(session_logger)
            initialization_failed = False
        except Exception as e:
            Logger.print_error(f"Error initializing conversation: {e}")
            time.sleep(20)

    # Main loop
    while True:
        if paused:
            time.sleep(0.1)  # Avoid busy waiting
            continue

        try:
            prompt = user_turn(None, dictation, USER_TURN_INDICATOR, args, pubsub)
            if should_end_conversation(prompt):
                Logger.print_info("User ended conversation")
                ai_turn(prompt, query_dispatcher, AI_TURN_INDICATOR, args, hotword_manager, tts, session_logger)
                end_conversation(session_logger)
                break
            ai_turn(prompt, query_dispatcher, AI_TURN_INDICATOR, args, hotword_manager, tts, session_logger, pubsub=pubsub)
        except Exception as e:
            if 'Exceeded maximum allowed stream duration' in str(e) or 'Long duration elapsed without audio' in str(e):
                continue
            else:
                session_logger.log_session_interaction(
                    SessionEvent(
                        user_input="SYSTEM ERROR",
                        response_output=f"Unexpected error: {str(e)}"
                    )
                )

    end_conversation(session_logger)
    Logger.print_info("Thanks for chatting! Have a great day!")

if __name__ == "__main__":
    main()
