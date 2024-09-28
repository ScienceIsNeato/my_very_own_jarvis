import base64
import json
import os
import asyncio
import time
import speech_recognition as sr
import websockets
from yarl import URL

from logger import Logger
from .dictation import Dictation

class LiveAssemblyAIDictation(Dictation):
    FRAMES_PER_BUFFER = 3200
    RATE = 16000
    ASSEMBLYAI_TOKEN = os.environ.get("ASSEMBLYAI_TOKEN")
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
        self.dictation_results = ""

    def callback(self, recognizer, audio):
        data = audio.get_raw_data(convert_rate=self.RATE, convert_width=2)
        return base64.b64encode(data).decode("utf-8")
    
    def speech_start_detected(self, current_line):
        if self.speech_started:
            return True
        
        if current_line:
            self.speech_started = True
            return True

    def done_speaking(self, current_line):
        global last_call_time
        global last_line
        global initialized
        global dictation_results
        global duration_since_last_detected_change

        done_speaking = False
        current_time = time.time()

        if not initialized:
            if current_line != "":
                last_line = current_line
                last_call_time = current_time
                initialized = True
                return False
        else:
            if current_line != last_line:
                self.duration_since_last_detected_change = 0
                last_line = current_line
                dictation_results.append(current_line)
            else:
                self.duration_since_last_detected_change += current_time - last_call_time

            if (initialized and current_line == "" and
                    self.duration_since_last_detected_change >= self.SILENCE_THRESHOLD):
                done_speaking = True

            last_call_time = current_time
            last_line = current_line

        return done_speaking

    async def send_receive(self, device_index):
        global is_done
        Logger.print_info("\nConnecting to live dictation service...")

        recognizer = sr.Recognizer()
        source = sr.Microphone(device_index=device_index)

        async with websockets.connect(
            URL,
            extra_headers=(("Authorization", self.ASSEMBLYAI_TOKEN),),
            ping_interval=5,
            ping_timeout=20
        ) as _ws:
            await asyncio.sleep(0.1)
            session_begins = await _ws.recv()

            async def send():
                is_done = False
                with sr.Microphone(device_index=device_index) as s:
                    recognizer.adjust_for_ambient_noise(s, duration=1)
                    Logger.print_info("Start Talking!")

                    while not is_done:
                        try:
                            audio = recognizer.record(s, duration=0.2)
                            data = self.callback(recognizer, audio)
                            json_data = json.dumps({"audio_data": str(data)})
                            await _ws.send(json_data)
                        except websockets.exceptions.ConnectionClosedError as e:
                            Logger.print_error(e)
                            break
                        except Exception as e:
                            if "(OK)" not in str(e):
                                Logger.print_error("Error in send:", e)
                            break
                        try:
                            await asyncio.sleep(0.01)
                        except Exception as e:
                            Logger.print_error("cancelled:", e)
                            is_done = True
                            break
                return is_done

            async def receive():
                global dictation_results
                dictation_results = []
                is_done = False
                initialized = False

                while not is_done:
                    try:
                        result_str = await _ws.recv()
                        if result_str:
                            current_phrase = json.loads(result_str)['text']
                            if current_phrase:
                                Logger.print_user_input(current_phrase)

                            is_done = self.done_speaking(current_phrase)
                            if is_done:
                                Logger.print_info("Finished listening.")
                                break
                    except websockets.exceptions.ConnectionClosedError as e:
                        Logger.print_error(e)
                        break
                    except Exception as e:
                        Logger.print_error("Error in receive:", e)
                        break

                final_phrases = ' '.join(dictation_results)
                return final_phrases

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
                Logger.print_error("Error in send_result:", send_result)

            if isinstance(receive_result, Exception):
                Logger.print_error("Error in receive_result:", receive_result)

            return receive_result

    def getDictatedInput(self, device_index, interruptable=False):
        result = asyncio.run(self.send_receive(device_index))
        return result
