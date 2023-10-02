# GANGLIA

GANGLIA:
- <b>G</b>eneral
- <b>A</b>I
- <b>N</b>urturing
- <b>G</b>uided
- <b>L</b>inguistic
- <b>I</b>nterface and
- <b>A</b>Automation (working title)

GANGLIA is a highly modularized, generic personal assistant. GANGLIA has been built in part by AI (monitored by software developers).

GANGLIA allows users to have multi-modal interactions with AI using natural language conversations. It is highly customizable and can be easily extended to incorporate additional functionality. Each component of GANGLIA can be swapped or mocked, allowing developers to customize GANGLIA to meet their specific needs.

Here's a table of possible modules, potential values, and defaults:

Module              | Possible Values                              | Default Value
------------------- | ------------------------------------------- | -------------
Speech Recognition  | AssemblyAI, Google Cloud Speech-to-Text      | Google Cloud Speech-to-Text
Text To Speech      | Google Text-to-Speech, Natural Reader (Unavailable), Amazon Polly (Unavailable) | Google Text-to-Speech
AI Backend          | GPT-3.5 (Unavailable), GPT-4, Bard (Unavailable)             | GPT-4
Response Visualizer | cli, NaturalReaderUI (Unavailable)           | cli


Note: This is not an exhaustive list and the table can be easily extended to incorporate additional modules as needed.

## Installation

To use GANGLIA, you will need to install Python 3.x and the following libraries:

- SpeechRecognition
- PyAudio
- OpenAI
- DotEnv

You can install these libraries using pip by running the following command:

`pip install SpeechRecognition PyAudio openai python-dotenv`

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

python GANGLIA.py [-l LISTEN_DUR_SECS] [-d DEVICE_INDEX] [--pre_prompt PRE_PROMPT] [-t TTS_INTERFACE] [--static-response]

Here's a description of each command-line argument:

- `-l LISTEN_DUR_SECS` or `--listen_dur_secs LISTEN_DUR_SECS`: Sets the duration in seconds that GANGLIA will listen for before automatically stopping. The default value is 5 seconds.
- `-d DEVICE_INDEX` or `--device_index DEVICE_INDEX`: Sets the index of the input device to use. The default value is 0.
- `--pre_prompt PRE_PROMPT`: Sets any context you want for the session (should take the form of a prompt). The default value is None.
- `-t TTS_INTERFACE` or `--tts_interface TTS_INTERFACE`: Sets the text-to-speech interface to use. Available options are 'google' or 'natural_reader'. The default value is 'google'.
- `--help` or `-h`: Displays usage instructions and a list of available options.


Once GANGLIA is running, it will listen for voice prompts. When you're ready to ask a question or make a request, simply speak into your microphone. Once you've finished speaking, GANGLIA will generate a response using OpenAI's GPT-3 engine and speak it aloud using the pyttsx3 library.

## TTS (Text To Speech)
- there are a few options for how to render the AI's text response as audio. One option is to use the coqui api.

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
    - see `config/chatgpt_session_config.json.template` for examples and explanations. 

## Contributing

If you would like to contribute to GANGLIA, please fork the repository and submit a pull request with your changes.

## License

GANGLIA is licensed under the MIT License. See the LICENSE file for more information.

## Credits

GANGLIA was created by William R Martin. It uses OpenAI's GPT-4 engine and several open source libraries, including:

- SpeechRecognition
- PyAudio
- pyttsx3
and more

## Contact

If you have any questions or feedback about GANGLIA, please contact Will Martin at unique dot will dot martin at gmail.
