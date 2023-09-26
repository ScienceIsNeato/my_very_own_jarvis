from google.cloud import speech_v1p1beta1 as speech
import pyaudio
import io

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
        requests = (speech.StreamingRecognizeRequest(audio_content=chunk)
                    for chunk in stream)
        responses = self.client.streaming_recognize(self.get_config(), requests)

        for response in responses:
            if not response.results:
                continue

            result = response.results[0]
            if not result.alternatives:
                continue

            transcript = result.alternatives[0].transcript
            print(f"Transcribed: {transcript}")

    def get_config(self):
        return speech.StreamingRecognitionConfig(
            config=speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
                sample_rate_hertz=16000,
                language_code="en-US",
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
    transcriber = Transcriber()
    transcriber.run()
