import base64
import time
import websockets
import asyncio
import json
import re
import speech_recognition as sr
from abc import ABC, abstractmethod

listen_dur_secs = 400
device_index = 3 # My External USB mic. Use the script in tools to find yours. 

URL = "wss://api.assemblyai.com/v2/realtime/ws?sample_rate=16000"

class Dictation(ABC):
    @abstractmethod
    def getDictatedInput(self, listen_dur_secs, device_index):
        pass

    @abstractmethod
    def done_speaking(self, current_line):
        pass


class StaticGoogleDictation(Dictation):
    def getDictatedInput(self, listen_dur_secs, device_index):
        print("Testing audio input access...")
        recognizer = sr.Recognizer()

        with sr.Microphone(device_index=device_index) as source:
            print("Microphone detected.")
            print("Will listen for", listen_dur_secs, "seconds...")
            print("Calibrating microphone...")

            recognizer.adjust_for_ambient_noise(source, duration=1)

            print("Go!")

            audio = recognizer.listen(source, timeout=listen_dur_secs, phrase_time_limit=50000)
            print("Finished listening.")

            try:
                text = recognizer.recognize_google(audio)
                print("You said: ", text)
                return text
            except sr.UnknownValueError:
                print("Google Speech Recognition could not understand the audio.")
            except sr.RequestError as e:
                print(f"Could not request results from Google Speech Recognition service; {e}")

    def done_speaking(self, current_line):
        pass

class LiveAssemblyAIDictation(Dictation):
    FRAMES_PER_BUFFER = 3200
    RATE = 16000

    # TODO - make silence threshold configurable?
    SILENCE_THRESHOLD = 1.5  # seconds

    URL = "wss://api.assemblyai.com/v2/realtime/ws?sample_rate=16000"

    def __init__(self):
        self.last_call_time = time.time()
        self.last_line = ""
        self.speech_started = False
        self.duration_since_last_detected_change = 0.0
        self.silence_detected = False
        self.audio_detected = False
        self.initialized = False
        self.start_msg_printed = False
        self.first_audio_detected = False
        self.dictation_result = ""

    def callback(self, recognizer, audio):
        data = audio.get_raw_data(convert_rate=self.RATE, convert_width=2)
        return base64.b64encode(data).decode("utf-8")

    def done_speaking(self, current_line):
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
                print("Initialized and awaiting input...")
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
                duration_since_last_detected_change >= self.SILENCE_THRESHOLD):
                done_speaking = True

            # Update the last_call_time and last_line global variables
            last_call_time = current_time
            last_line = current_line

        return done_speaking

    async def send_receive(self, listen_dur_secs, device_index):
        global is_done
        print("\nConnecting to live dictation service...")

        # Put the recognizer and source creation inside the send_receive function
        recognizer = sr.Recognizer()
        source = sr.Microphone(device_index=device_index)


        async with websockets.connect(
            URL,
            extra_headers=(("Authorization", "9d9f9ecf616446fe8b39a23cd18b2cef"),),
            ping_interval=5,
            ping_timeout=20
        ) as _ws:
            await asyncio.sleep(0.1)
            session_begins = await _ws.recv()
            # print(session_begins)

            async def send():
                is_done = False
                with sr.Microphone(device_index=device_index) as s:
                    recognizer.adjust_for_ambient_noise(s, duration=1)
                    print("Start Talking!")

                    while not is_done:
                        try:
                            audio = recognizer.record(s, duration=0.2)
                            data = self.callback(recognizer, audio)
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
                return is_done

            async def receive():
                global dictation_result
                global initialized
                dictation_result = []
                is_done = False
                initialized = False
                final_phrases = set() 

                while not is_done:
                    try:
                        result_str = await _ws.recv()
                        if result_str:
                            current_phrase = json.loads(result_str)['text']
                            if current_phrase:
                                print(current_phrase)

                            # Send the current phrase to the done_speaking method
                            is_done = self.done_speaking(current_phrase)
                            if is_done:
                                print("Finished listening.")
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
                    #print("\nDictation result: {}".format(list(final_phrases)))
                else:
                    print("\nNo phrases detected.")
                
                final_phrase = ' '.join(final_phrases)
                print("You said: ", final_phrase)
                return final_phrase

            send_task = asyncio.create_task(send())
            receive_task = asyncio.create_task(receive())

            done, pending = await asyncio.wait([send_task, receive_task], return_when=asyncio.FIRST_COMPLETED)
            
            for task in pending:
                task.cancel()

            if send_task in done:
                send_result = send_task.result()
            else:
                send_result = None

            if receive_task in done:
                receive_result = receive_task.result()
            else:
                receive_result = None

            if isinstance(send_result, Exception):
                print("Error in send_result:", send_result)

            if isinstance(receive_result, Exception):
                print("Error in receive_result:", receive_result)

            # Return the result from the receive() function
            return receive_result

    def getDictatedInput(self, listen_dur_secs, device_index):
        result = asyncio.run(self.send_receive(listen_dur_secs, device_index))
        return result
