import os
from google.cloud import speech
from datetime import datetime
import sys

# Simple Logger implementation
class Logger:
    @staticmethod
    def print_info(message):
        print(f"[INFO] {message}")

    @staticmethod
    def print_error(message):
        print(f"[ERROR] {message}", file=sys.stderr)

def transcribe_audio_gcs(gcs_uri, language_code='en-US'):
    """
    Transcribes the audio file specified by the GCS URI using Google Cloud Speech-to-Text API.

    Args:
        gcs_uri (str): GCS URI of the audio file (e.g., gs://ganglia-scratch-space/audio_out_converted.wav).
        language_code (str): Language code for transcription.

    Returns:
        str: Transcribed text.
    """
    client = speech.SpeechClient()

    audio = speech.RecognitionAudio(uri=gcs_uri)

    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,  # Must match your audio file
        sample_rate_hertz=16000,  # Must match your audio file
        language_code=language_code,
        enable_automatic_punctuation=True,  # Adds punctuation for readability
        use_enhanced=True,  # Enables enhanced models for better accuracy
        model='phone_call',  # Choose 'video' for better context understanding; options include 'default', 'video', 'phone_call', etc.
        speech_contexts=[
            speech.SpeechContext(
                phrases=[
                    "Brian Head",
                    "Revolution",
                    "Rite Aid",
                    "Univision",
                    "kontakt",
                    "Am I to model in Quad",
                    # Add any other domain-specific phrases to improve recognition
                ]
            )
        ],
        # Optional: Enable speaker diarization if multiple speakers are present
        # diarization_config=speech.SpeakerDiarizationConfig(
        #     enable_speaker_diarization=True,
        #     min_speaker_count=1,
        #     max_speaker_count=2,
        # ),
    )

    Logger.print_info(f"Starting transcription for audio file: {gcs_uri}")

    try:
        operation = client.long_running_recognize(config=config, audio=audio)
    except Exception as e:
        Logger.print_error(f"Failed to start transcription operation: {e}")
        return ""

    Logger.print_info("Waiting for transcription to complete...")
    try:
        response = operation.result(timeout=600)  # Increased timeout for longer files
    except Exception as e:
        Logger.print_error(f"Transcription operation failed or timed out: {e}")
        return ""

    transcript = ""
    for result in response.results:
        # If speaker diarization is enabled, you can include speaker labels
        # For simplicity, we're ignoring speaker labels here
        transcript += result.alternatives[0].transcript + " "

    Logger.print_info("Transcription completed.")
    return transcript.strip()

def main():
    # Hardcoded GCS URI
    gcs_uri = "gs://ganglia-scratch-space/audio_out_converted.wav"
    language_code = "en-US"  # Change if your audio is in a different language

    # Optional: Allow overriding the hardcoded values via environment variables
    # This adds flexibility without relying on command-line arguments
    gcs_uri_env = os.getenv("GCS_URI")
    language_code_env = os.getenv("LANGUAGE_CODE")

    if gcs_uri_env:
        gcs_uri = gcs_uri_env

    if language_code_env:
        language_code = language_code_env

    transcript = transcribe_audio_gcs(gcs_uri, language_code)
    if not transcript:
        Logger.print_error("No transcript generated.")
        sys.exit(1)

    timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    output_file = f"transcript_{timestamp}.txt"

    try:
        with open(output_file, 'w') as f:
            f.write(transcript)
        Logger.print_info(f"Transcript saved to {output_file}")
    except Exception as e:
        Logger.print_error(f"Failed to write transcript to file: {e}")

if __name__ == "__main__":
        main()