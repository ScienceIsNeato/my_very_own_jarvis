import websockets
import asyncio
import base64
import json
import time
import speech_recognition as sr

FRAMES_PER_BUFFER = 3200
RATE = 16000
listen_dur_secs = 400
device_index = None

recognizer = sr.Recognizer()
source = sr.Microphone(device_index=device_index)

URL = "wss://api.assemblyai.com/v2/realtime/ws?sample_rate=16000"

def callback(recognizer, audio):
    data = audio.get_raw_data(convert_rate=RATE, convert_width=2)
    return base64.b64encode(data).decode("utf-8")

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
            while True:
                try:
                    result_str = await _ws.recv()
                    print(json.loads(result_str)['text'])
                except websockets.exceptions.ConnectionClosedError as e:
                    print(e)
                    assert e.code == 4008
                    break
                except Exception as e:
                    assert False, "Not a websocket 4008 error"

        send_result, receive_result = await asyncio.gather(send(), receive())

def main():
    asyncio.run(send_receive())

if __name__ == '__main__':
    main()
