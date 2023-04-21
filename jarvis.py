import asyncio
from dictation import send_receive
from jarvis_utils import sendQueryToServer
from parse_inputs import parse_args, parse_tts_interface

async def main():
    global args
    args = parse_args()

    if args.pre_prompt:
        pre_prompt = args.pre_prompt
    else:
        pre_prompt = None

    tts = parse_tts_interface(args.tts_interface)

    print("Starting session with Jarvis. To stop, simply say \"Goodbye\"")

    while True:
        prompt = await send_receive(args.listen_dur_secs, args.device_index)
        print("You said: ", prompt)
        if prompt is None:
            continue

        if "goodbye" in prompt.strip().lower():
            response = "Ok, see you later!"
            error_code, file_path = tts.convert_text_to_speech(response)
            tts.play_speech_response(error_code, file_path)
            break
        else:
            response = sendQueryToServer(prompt, pre_prompt)
            error_code, file_path = tts.convert_text_to_speech(response)
            tts.play_speech_response(error_code, file_path)

    print("Thanks for chatting! Have a great day!")

if __name__ == "__main__":
    asyncio.run(main())
