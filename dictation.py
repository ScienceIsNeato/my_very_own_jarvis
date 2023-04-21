import websockets
import asyncio
import base64
import json
import time
import speech_recognition as sr
import logging
import re

FRAMES_PER_BUFFER = 3200
RATE = 16000
SILENCE_THRESHOLD = 3.75  # seconds

# globals
last_call_time = time.time()
last_line = ""
speech_started = False
duration_since_last_detected_change = 0.0
silence_detected = False
audio_detected = False
initialized = False
start_msg_printed = False
first_audio_detected = False
dictation_result = ""


listen_dur_secs = 400
device_index = 3 # My External USB mic. Use the script in tools to find yours. 

recognizer = sr.Recognizer()
source = sr.Microphone(device_index=device_index)

URL = "wss://api.assemblyai.com/v2/realtime/ws?sample_rate=16000"

logging.basicConfig(level=logging.INFO)

def callback(recognizer, audio):
    data = audio.get_raw_data(convert_rate=RATE, convert_width=2)
    return base64.b64encode(data).decode("utf-8")


def done_speaking(current_line):
    global last_call_time
    global last_line
    global duration_since_last_detected_change
    global initialized
    global dictation_result

    done_speaking = False  # init

    # Record the current time
    current_time = time.time()

    if not initialized:
        if current_line != "":
            last_line = current_line
            last_call_time = current_time
            initialized = True
            logging.info("Initialized and awaiting input...")
            return False
    else:
        if current_line != last_line:
            # There has been a change in the input since the last call
            duration_since_last_detected_change = 0
            last_line = current_line
            dictation_result.append(current_line)
        else:
            # New input! Reset duration_since_last_detected_change to 0
            duration_since_last_detected_change += current_time - last_call_time

        # Determine if done speaking
        if (initialized and
            current_line == "" and
            duration_since_last_detected_change >= SILENCE_THRESHOLD):
            done_speaking = True

        # Update the last_call_time and last_line global variables
        last_call_time = current_time
        last_line = current_line

    return done_speaking



async def send_receive():
    print(f'Connecting websocket to url {URL}')
    async with websockets.connect(
        URL,
        extra_headers=(("Authorization", "9d9f9ecf616446fe8b39a23cd18b2cef"),),
        ping_interval=5,
        ping_timeout=20
    ) as _ws:
        await asyncio.sleep(0.1)
        session_begins = await _ws.recv()
        print(session_begins)

        async def send():
            with source as s:
                recognizer.adjust_for_ambient_noise(s, duration=1)
                logging.info("Start Talking!")
                start_time = time.time()

                while True:
                    try:
                        audio = recognizer.record(s, duration=0.2)
                        data = callback(recognizer, audio)
                        json_data = json.dumps({"audio_data": str(data)})
                        await _ws.send(json_data)
                    except websockets.exceptions.ConnectionClosedError as e:
                        print(e)
                        assert e.code == 4008
                        break
                    except Exception as e:
                        if "(OK)" not in str(e):
                            print("Error in send:", e)
                        break
                    await asyncio.sleep(0.01)

            return True

        async def receive():
            global dictation_result
            dictation_result = []
            is_done = False

            while not is_done:
                try:
                    result_str = await _ws.recv()
                    if result_str:
                        current_phrase = json.loads(result_str)['text']
                        if current_phrase:
                            print(current_phrase)

                        # Send the current phrase to the done_speaking method
                        is_done = done_speaking(current_phrase)
                        if is_done:
                            logging.info("Finished listening.")
                            await _ws.close()
                            break
                except websockets.exceptions.ConnectionClosedError as e:
                    print(e)
                    assert e.code == 4008
                    break
                except Exception as e:
                    print("Error in receive:", e)
                    break

            # Print the final set of complete phrases
            if dictation_result:
                final_phrases = {phrase for phrase in dictation_result if re.match(r'^[A-Z].*\.$', phrase)}
                print("\nDictation result: {}".format(list(final_phrases)))
            else:
                print("\nNo phrases detected.")
            return is_done

        send_result, receive_result = await asyncio.gather(send(), receive(), return_exceptions=True)

        if isinstance(send_result, Exception):
            print("Error in send_result:", send_result)

        if isinstance(receive_result, Exception):
            print("Error in receive_result:", receive_result)

def main():
    asyncio.run(send_receive())

if __name__ == '__main__':
    main()
