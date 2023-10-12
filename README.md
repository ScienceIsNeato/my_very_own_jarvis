# GANGLIA

GANGLIA:
- <b>G</b>eneral
- <b>A</b>I
- <b>N</b>urturing
- <b>G</b>uided
- <b>L</b>inguistic
- <b>I</b>nterface and
- <b>A</b>utomation (working title)

GANGLIA is a highly modularized, generic personal assistant. Built partially by AI (supervised by software developers), GANGLIA allows users to have multi-modal interactions with AI through natural language conversations. Its flexible architecture allows each component to be replaced or mocked, enabling developers to tailor GANGLIA to their specific needs.

## Modules Overview

| Module              | Possible Values | Default |
|---------------------|-----------------|---------|
| Speech Recognition  | AssemblyAI, Static Google Cloud Speech-to-Text | Live Google Cloud Speech-to-Text |
| Text To Speech      | Google, Natural Reader (Unavailable), Amazon Polly (Unavailable) | Google |
| AI Backend          | GPT-3.5 (Unavailable), GPT-4 | GPT-4 |
| Response Visualizer | CLI, NaturalReaderUI (Unavailable) | CLI |

**Note**: This list is non-exhaustive and can be expanded as needed.

## Getting Started

### Installation

1. Install Python 3.x.
2. Install the necessary libraries using:
```bash
pip install -r requirements.txt
```

## Prerequisites (for google speech to text)

- Google cloud cli
    - pip install google-cloud-speech
    - https://cloud.google.com/docs/authentication/provide-credentials-adc#how-to
        - this is also tell you how to setup Google CLI if you haven't already

## Setting up API keys (Optional)

GANGLIA can be used without API keys for certain features. However, if you want to utilize features that require API keys, you'll need to set up your API keys for the respective services.

To set up the API keys, copy the `.env.template` file in the root directory of the project and rename it to `.env`. Then, update the values for the features you want to use.

Here's a table of features, their implementation names, and the corresponding environment variable names for the `.env` file:

| Feature            | Implementation Name | Environment Variable      |
|--------------------|---------------------|---------------------------|
| Speech Recognition | AssemblyAI          | ASSEMBLYAI_TOKEN          |
| AI Backend         | OpenAI GPT-4        | OPENAI_API_KEY            |

## Usage

To start GANGLIA, run the following command in your terminal:

python GANGLIA.py [-d DEVICE_INDEX] [-t TTS_INTERFACE] [--static-response]

Here's a description of each command-line argument:

- `-d DEVICE_INDEX` or `--device_index DEVICE_INDEX`: Sets the index of the input device to use. The default value is 0.
- `-t TTS_INTERFACE` or `--tts_interface TTS_INTERFACE`: Sets the text-to-speech interface to use. Available options are 'google' or 'natural_reader'. The default value is 'google'.
- `--help` or `-h`: Displays usage instructions and a list of available options.

Once GANGLIA is running, it will listen for voice prompts. When you're ready to ask a question or make a request, simply speak into your microphone. Once you've finished speaking, GANGLIA will generate a response using OpenAI's GPT-3 engine and speak it aloud using the pyttsx3 library.

## TTS (Text To Speech)

- there are a few options for how to render the AI's text response as audio. One option is to use the coqui api.

- `--tts-interface google` [DEFAULT] (only prints input at end of sample collection)
    - the free, simple female google tts voice
- `--tts-interface coqui` (live update of text input as it is being heard)
    - coqui is an incredible voice synthesis service that offers endless options for speechification
    - when using Coqui as TTS, set up the coqui_config.json in the project root (see section below)

#### Setting up Coqui TTS Configuration

If you want to use Coqui as your Text To Speech interface, you need to provide the necessary configurations for the Coqui TTS API. 

Create a file named `coqui_config.json` in the root directory with the following format:

```json
{
    "api_url": "https://app.coqui.ai/api/v2/samples",
    "bearer_token": "<your_token>",
    "voice_id": "<your_voice_id>"
}
```

### AI Session Tuning

- when using chatgpt, the persona of the AI can be tweaked by modifying the config file:
    - `config/chatgpt_session_config.json`
    - see `config/chatgpt_session_config.template` for examples and explanations.

## Setting up Session Logging to the Cloud (Optional)

- If you want store the session events to gcp, use the `--store-logs` command-line flag when running GANGLIA

#### Setup:

1. Install Google Cloud SDK if you haven't already, and authenticate using `gcloud auth application-default login`. 
2. Make sure that you have a Google Cloud Storage bucket where the logs will be stored. Take note of the bucket name and your project name.
3. Update the `.env` file in your project root directory to include the following:
   - `GCP_BUCKET_NAME=<your_bucket_name>`
   - `GCP_PROJECT_NAME=<your_project_name>`

## Contributing

If you would like to contribute to GANGLIA, please fork the repository and submit a pull request with your changes.

## License

GANGLIA is licensed under the MIT License. See the LICENSE file for more information.

## Credits

GANGLIA was created by William R Martin.

## Contact

If you have any questions or feedback about GANGLIA, please contact Will Martin at unique dot will dot martin at gmail.
