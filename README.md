# Jarvis

Jarvis is a Python program that uses OpenAI's GPT-3 engine to generate human-like responses to voice prompts in real-time. It allows users to have natural language conversations with their computer, similar to popular virtual assistants like Siri and Alexa.

## Installation

To use Jarvis, you will need to install Python 3.x and the following libraries:

- SpeechRecognition
- PyAudio
- OpenAI

You can install these libraries using pip by running the following command:

```bash
pip install SpeechRecognition PyAudio openai
```

## Usage

To start Jarvis, run the following command in your terminal:

```bash
python jarvis.py
```

Jarvis will start listening for voice prompts. When you're ready to ask a question or make a request, simply press the space bar on your keyboard to start recording your voice. Once you've finished speaking, Jarvis will generate a response using OpenAI's GPT-3 engine and speak it aloud using the pyttsx3 library.

## Options

Jarvis supports the following options:

- --listen_dur_secs: Sets the duration in seconds that Jarvis will listen for before automatically stopping. By default, this is set to 5 seconds.
- --help or -h: Displays usage instructions and a list of available options.

## Contributing

If you would like to contribute to Jarvis, please fork the repository and submit a pull request with your changes.

## License

Jarvis is licensed under the MIT License. See the LICENSE file for more information.

## Credits

Jarvis was created by [Your Name Here]. It uses OpenAI's GPT-4 engine and several open source libraries, including:

- SpeechRecognition
- PyAudio
- pyttsx3

## Contact

If you have any questions or feedback about Jarvis, please contact Will Martin at unique dot will dot martin at gmail.
