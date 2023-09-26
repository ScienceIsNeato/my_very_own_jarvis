from google.cloud import speech_v1p1beta1 as speech
import pyaudio
from google.api_core.exceptions import Unknown  # import the specific exception class
from time import sleep  # for the sleep function

class Transcriber:
    def __init__(self):
        self.client = speech.SpeechClient()

        # audio stream setup
        self.audio_stream = pyaudio.PyAudio().open(
            format=pyaudio.paInt16,
            channels=1,
            rate=16000,
            input=True,
            frames_per_buffer=1024
        )

    def transcribe_stream(self, stream):
        state = 'START'
        while state != 'END':
            finalized_transcript = ''
            
            
            requests = (speech.StreamingRecognizeRequest(audio_content=chunk) for chunk in stream)
            responses = self.client.streaming_recognize(self.get_config(), requests)
            
            for response in responses:
                if not response.results:
                    continue

                result = response.results[0]
                if not result.alternatives:
                    continue

                is_final = result.is_final
                
                if state == 'START':
                    print(f'\033[K{result.alternatives[0].transcript.strip()}\r', end='', flush=True)  # You can consider keeping this as is, or tweaking based on your needs
                    state = 'LISTENING'
                
                if is_final:
                    finalized_transcript += result.alternatives[0].transcript.strip() + ' '
                    print(f'\033[K{result.alternatives[0].transcript.strip()}', flush=True)
                    state = 'START'

                    # TODO need to have this exit somehow - probably a timer
                else:
                    if state == 'LISTENING':
                        print(f'\033[K{result.alternatives[0].transcript.strip()}', end='\r', flush=True)  # You can consider keeping this as is, or tweaking based on your needs
            
            break

    def get_config(self):
        return speech.StreamingRecognitionConfig(
            config=speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
                sample_rate_hertz=16000,
                language_code="en-US",
                enable_automatic_punctuation=True,
                use_enhanced=True
            ),
            interim_results=True,
        )

    def generate_audio_chunks(self):
        while True:
            yield self.audio_stream.read(1024)

    def run(self):

                print("Starting live transcription, say 'quit' to exit...")
                self.transcribe_stream(self.generate_audio_chunks())


if __name__ == "__main__":
    while True:
        transcriber = None  # Initialize to None so we can safely delete it later
        try:
            transcriber = Transcriber()
            transcriber.run()
        except Unknown as e:
            print(f"Warning: An error occurred ({e}). Retrying...")
            
            if transcriber is not None:
                del transcriber  # Delete the object
            
            sleep(2)

