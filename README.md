# GANGLIA

GANGLIA:
    General 
    AI
    Nurturing
    Guided
    Linguistic
    Interface and
    Automation (working title)

GANGLIA is a highly modularized, generic personal assistant. GANGLIA has been built in part by AI (monitored by software developers).

GANGLIA allows users to have interface with AI using natural language conversations. It is highly customizable and can be easily extended to incorporate additional functionality. Each component of GANGLIA can be swapped or mocked, allowing developers to customize GANGLIA to meet their specific needs.

Here's a table of possible modules, potential values, and defaults:

Module              | Possible Values                              | Default Value
------------------- | ------------------------------------------- | -------------
Speech Recognition  | AssemblyAI, Google Cloud Speech-to-Text      | AssemblyAI
Text To Speech      | Google Text-to-Speech, Natural Reader (Unavailable), Amazon Polly (Unavailable) | Google Text-to-Speech
AI Backend          | GPT-3.5 (Unavailable), GPT-4, Bard (Unavailable)             | GPT-4
Response Visualizer | cli, NaturalReaderUI (Unavailable)           | cli


Note: This is not an exhaustive list and the table can be easily extended to incorporate additional modules as needed.

## Installation

To use GANGLIA, you will need to install Python 3.x and the following libraries:

- SpeechRecognition
- PyAudio
- OpenAI

You can install these libraries using pip by running the following command:

pip install SpeechRecognition PyAudio openai

## Usage

To start GANGLIA, run the following command in your terminal:

python GANGLIA.py [-l LISTEN_DUR_SECS] [-d DEVICE_INDEX] [--pre_prompt PRE_PROMPT] [-t TTS_INTERFACE] [--static-response]

Here's a description of each command-line argument:

- `-l LISTEN_DUR_SECS` or `--listen_dur_secs LISTEN_DUR_SECS`: Sets the duration in seconds that GANGLIA will listen for before automatically stopping. The default value is 5 seconds.
- `-d DEVICE_INDEX` or `--device_index DEVICE_INDEX`: Sets the index of the input device to use. The default value is 0.
- `--pre_prompt PRE_PROMPT`: Sets any context you want for the session (should take the form of a prompt). The default value is None.
- `-t TTS_INTERFACE` or `--tts_interface TTS_INTERFACE`: Sets the text-to-speech interface to use. Available options are 'google' or 'natural_reader'. The default value is 'google'.
- `--static-response`: Sets whether to provide responses without conversation history. The default value is False.
- `--help` or `-h`: Displays usage instructions and a list of available options.


Once GANGLIA is running, it will listen for voice prompts. When you're ready to ask a question or make a request, simply speak into your microphone. Once you've finished speaking, GANGLIA will generate a response using OpenAI's GPT-3 engine and speak it aloud using the pyttsx3 library.

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
