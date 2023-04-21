import websockets
import asyncio
import base64
import json
import time
import speech_recognition as sr
import logging

FRAMES_PER_BUFFER = 3200
RATE = 16000
SILENCE_THRESHOLD = 0.75  # seconds

# globals
last_call_time = time.time()
last_line = ""
speech_started = False
duration_since_last_detected_change = 0.0
silence_detected = False
audio_detected = False
initialized = False

listen_dur_secs = 400
device_index = None

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
    global speech_started
    global duration_since_last_detected_change
    global silence_detected
    global audio_detected
    global initialized


    try:
        # Record the current time
        current_time = time.time()

        if not initialized:
            last_line = current_line
            last_call_time = current_time
            initialized = True

        # If this is the first call with actual audio, set speech_started to true and last_call_time to the current time
        if not speech_started and current_line:
            speech_started = True
            last_line = current_line
            last_call_time = time.time()
            logging.info("Initialized started speech detection...")

        if not initialized or not speech_started:
            # Either this is the first call or we haven't detected any audio yet
            return False

        # Determine if the current input is identical to the previous input
        if current_line == last_line:
            # Increment duration_since_last_detected_change by the difference between the last call and this call
            duration_since_last_detected_change += current_time - last_call_time
            last_call_time = current_time
        else:
            # Reset duration_since_last_detected_change to 0
            duration_since_last_detected_change = 0

        # Determine if silence has been detected
        if duration_since_last_detected_change >= SILENCE_THRESHOLD:
            silence_detected = True
        else:
            silence_detected = False

        # Update the last_call_time and last_line global variables
        last_call_time = current_time
        last_line = current_line

        if audio_detected:
            logging.info(f"Time elapsed since last change: {current_time - last_call_time:.2f}")

        return silence_detected

    except Exception as e:
        logging.error(f"done_speaking error: {e}")
        return False

async def send_receive():
    print(f'Connecting websocket to url {URL}')
    async with websockets.connect(
        URL,
        extra_headers=(("Authorization", "9d9f9ecf616446fe8b39a23cd18b2cef"),),
        ping_interval=5,
        ping_timeout=20
    ) as _ws:
        await asyncio.sleep(0.1)
        print("Receiving SessionBegins ...")
        session_begins = await _ws.recv()
        print(session_begins)
        print("Sending messages ...")

        async def send():
            with source as s:
                recognizer.adjust_for_ambient_noise(s, duration=1)
                print("Go!")
                start_time = time.time()

                while True:
                    try:
                        audio = recognizer.record(s, duration=0.2)
                        data = callback(recognizer, audio)
                        json_data = json.dumps({"audio_data": str(data)})
                        await _ws.send(json_data)

                        if time.time() - start_time >= listen_dur_secs:
                            print("Finished listening.")
                            await _ws.close()
                            break
                    except websockets.exceptions.ConnectionClosedError as e:
                        print(e)
                        assert e.code == 4008
                        break
                    except Exception as e:
                        assert False, "Not a websocket 4008 error"
                    await asyncio.sleep(0.01)

            return True

        async def receive():
            is_done = False
            while True:
                try:
                    result_str = await _ws.recv()
                    if result_str:
                        current_phrase = json.loads(result_str)['text']
                        if current_phrase:
                            print(current_phrase)
                            # Send the current phrase to the done_speaking method
                            is_done = done_speaking(current_phrase)

                except websockets.exceptions.ConnectionClosedError as e:
                    print(e)
                    assert e.code == 4008
                    break
                except Exception as e:
                    assert False, "Not a websocket 4008 error"

            return is_done

        send_result, receive_result = await asyncio.gather(send(), receive())

def main():
    asyncio.run(send_receive())

if __name__ == '__main__':
    main()
