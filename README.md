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
| Speech Recognition  | Static Google Cloud Speech-to-Text | Live Google Cloud Speech-to-Text |
| Text To Speech      | Google, Natural Reader (Unavailable), Amazon Polly (Unavailable) | Google |
| AI Backend          | GPT-3.5 (Unavailable), GPT-4 | GPT-4 |
| Response Visualizer | CLI, NaturalReaderUI (Unavailable) | CLI |

**Note**: This list is non-exhaustive and can be expanded as needed.

## Prerequisites

- Python 3.9 or higher
- FFmpeg installed and available in PATH
- DejaVu fonts installed (required for video captions)
  - On Ubuntu/Debian: `sudo apt-get install fonts-dejavu`
  - On macOS: `brew install font-dejavu`
  - On Windows: Download and install from [DejaVu Fonts](https://dejavu-fonts.github.io/)

## Getting Started

### Installation

1. Install Homebrew (if not already installed):
   ```bash
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

2. Install brew dependencies:
`brew install python pyenv zinit direnv openssl readline sqlite3 xz zlib portaudio ffmpeg opencv gh wget`

3. Install Python 3.x.
4. Install the necessary libraries using:
```bash
pip install -r requirements.txt
```

## Prerequisites (for google speech to text)

- Google cloud cli
    - pip install google-cloud-speech
    - https://cloud.google.com/docs/authentication/provide-credentials-adc#how-to
        - this is also tell you how to setup Google CLI if you haven't already

## Usage

To start GANGLIA, run the following command in your terminal:

python GANGLIA.py [-d DEVICE_INDEX] [-t TTS_INTERFACE] [--static-response]

Here's a description of each command-line argument:

- `-d DEVICE_INDEX` or `--device_index DEVICE_INDEX`: Sets the index of the input device to use. The default value is 0.
- `-t TTS_INTERFACE` or `--tts_interface TTS_INTERFACE`: Sets the text-to-speech interface to use. Available options are 'google'. The default value is 'google'.
- `--help` or `-h`: Displays usage instructions and a list of available options.

Once GANGLIA is running, it will listen for voice prompts. When you're ready to ask a question or make a request, simply speak into your microphone. Once you've finished speaking, GANGLIA will generate a response using OpenAI's GPT-3 engine and speak it aloud using the pyttsx3 library.

## Setting up API keys (Optional)

GANGLIA can be used without API keys for certain features. However, if you want to utilize features that require API keys, you'll need to set up your API keys for the respective services.

To set up the API keys, copy the `.env.template` file in the root directory of the project and rename it to `.env`. Then, update the values for the features you want to use.

Here's a table of features, their implementation names, and the corresponding environment variable names for the `.env` file:

| Feature            | Implementation Name | Environment Variable      |
|--------------------|---------------------|---------------------------|
| AI Backend         | OpenAI GPT-4        | OPENAI_API_KEY            |

## TTS (Text To Speech)

- there are a few options for how to render the AI's text response as audio. One option is to use the coqui api.

- `--tts-interface google` [DEFAULT]
    - the free, simple female google tts voice
- `--tts-interface coqui`
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

## Hotwords

- GANGLIA can be configured to listen for a hotword (a word or phrase that triggers GANGLIA to generate a pre-determined response)
- see example hotword config in `config/hotword_config.json.template`
- copy your input/output pairs to `config/hotword_config.json` and try saying them during a chat session. You should observe GANGLIA responding to the hotword with the output you've provided right away.

## Windows Support

- this program should work on windows. If you don't want the console output to look wierd, download Windows Console and use that to run the program

## Contributing

If you would like to contribute to GANGLIA, please fork the repository and submit a pull request with your changes.

## License

GANGLIA is licensed under the MIT License. See the LICENSE file for more information.

## Credits

GANGLIA was created by William R Martin.

## Contact

If you have any questions or feedback about GANGLIA, please contact Will Martin at unique dot will dot martin at gmail.

## Text-to-Video Configuration

When using the text-to-video feature, you can customize various aspects of the video generation through a configuration file. A template configuration file is provided at `config/ttv_config.template.json`.

### Configuration Options

Here's a comprehensive list of all available configuration options:

#### Required Fields

- `style` (string): The visual style to apply to generated images. Example: "digital art", "photorealistic", "anime"
- `story` (array of strings): The story to convert into a video, with each string representing one scene
- `title` (string): The title of the video, used in credits and file naming

#### Optional Fields

- `caption_style` (string, default: "static"): Controls how captions are displayed in the video
  - `"static"`: Traditional subtitles that appear at the bottom of the screen
  - `"dynamic"`: Word-by-word captions that are synchronized with the audio and use dynamic positioning and sizing

- `background_music` (object): Configuration for the background music that plays during the main video
  - Can be either file-based or prompt-based:
    ```json
    {
        "file": "path/to/music.mp3",  // Use an existing audio file
        "prompt": null
    }
    ```
    or
    ```json
    {
        "file": null,
        "prompt": "ambient piano music with a gentle mood"  // Generate music using this prompt
    }
    ```

- `closing_credits` (object): Configuration for the closing credits section
  - `music` (object): Music to play during credits
    - Same format as background_music (file or prompt-based)
  - `poster` (object): Image to show during credits
    - Can be file-based or prompt-based:
      ```json
      {
          "file": "path/to/poster.png",  // Use an existing image
          "prompt": null
      }
      ```
      or
      ```json
      {
          "file": null,
          "prompt": "A beautiful sunset scene"  // Generate image using this prompt
      }
      ```

### Example Configuration

See `config/ttv_config.template.json` for a complete example configuration. Here's a minimal example:

```json
{
    "style": "digital art",
    "story": [
        "A mysterious figure emerges from the shadows",
        "They walk through a glowing portal"
    ],
    "title": "The Portal",
    "caption_style": "dynamic"
}
```

### Notes

- All paths in the configuration file should be relative to the project root
- When using file-based resources (music/images), ensure the files exist before running
- When using prompt-based generation, ensure you have the necessary API access configured

## Environment Setup

GANGLIA uses `direnv` to manage environment variables. This ensures that environment variables are automatically loaded when you enter the project directory and unloaded when you leave.

### Setting up direnv

1. Install direnv:
   ```bash
   # On macOS
   brew install direnv

   # On Linux
   # Follow instructions at https://direnv.net/docs/installation.html
   ```

2. Add direnv hook to your shell:
   ```bash
   # For zsh (add to ~/.zshrc)
   eval "$(direnv hook zsh)"

   # For bash (add to ~/.bashrc)
   eval "$(direnv hook bash)"
   ```

3. Create your local environment file:
   ```bash
   cp .envrc.template .envrc
   ```

4. Edit `.envrc` with your actual values:
   - OpenAI API key for GPT interactions and DALL-E image generation
   - Google Cloud configuration for speech and storage
   - MusicGen/AudioGen credentials
   - Optional: Custom temporary directory path via `GANGLIA_TEMP_DIR`
   - Other service-specific settings

5. Allow direnv to load the environment:
   ```bash
   direnv allow
   ```

### Environment Variables

The `.envrc` file contains all required environment variables, including:

#### Required Variables
- `OPENAI_API_KEY`: Your OpenAI API key for GPT and DALL-E
- `GOOGLE_APPLICATION_CREDENTIALS`: Path to Google Cloud credentials
- `GCP_BUCKET_NAME`: Google Cloud Storage bucket name
- `GCP_PROJECT_NAME`: Google Cloud project name
- `SUNO_API_KEY`: API key for MusicGen/AudioGen

#### Optional Variables
- `GANGLIA_TEMP_DIR`: Override the default temporary directory location
  - If not set, uses system temp directory (`/tmp` on Unix, `%TEMP%` on Windows)
  - GANGLIA will create a subdirectory named 'GANGLIA' within this location
- `PLAYBACK_MEDIA_IN_TESTS`: Enable/disable media playback during tests

When you enter the project directory, these variables will be automatically loaded, and when you leave, they'll be unloaded.

## Google Cloud Credentials

GANGLIA uses Google Cloud services for speech-to-text and text-to-speech. The credentials are handled differently depending on the environment:

### Local Development
For local development, set the `GOOGLE_APPLICATION_CREDENTIALS` environment variable to point to your credentials file:
```bash
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/your/credentials.json"
```

### Docker Local Development

For running tests in Docker, you'll need to have Docker installed and running on your system. The Docker environment is automatically handled by `run_tests.sh` - see the [test README](tests/README.md) for more details.

If you need to run Docker commands manually:

```bash
docker build --build-arg GOOGLE_CREDENTIALS_PATH=/path/to/your/credentials.json -t ganglia:latest .
```

### CI Environment
In CI, credentials are handled automatically through GitHub Secrets. No additional setup is required.

## Development Setup

### Setting up your development environment

1. Create and activate a Python 3.9 virtual environment:
```bash
python3.9 -m venv .venv
source .venv/bin/activate  # On Unix/macOS
# or
.venv\Scripts\activate  # On Windows
```

2. Install core dependencies (includes test dependencies):
```bash
pip install -r requirements_core.txt
```

3. Install additional dependencies if needed:
```bash
pip install -r requirements_large.txt  # For ML/AI features
```

### Running Tests

Always run tests from within the virtual environment to ensure you're using the correct dependencies:

```bash
# Activate virtual environment first
source .venv/bin/activate  # On Unix/macOS
# or
.venv\Scripts\activate  # On Windows

# Then run tests
python -m pytest  # Run all tests
python -m pytest tests/unit  # Run unit tests
python -m pytest tests/integration  # Run integration tests
python -m pytest tests/smoke  # Run smoke tests
```

Note: Always use `python -m pytest` instead of calling `pytest` directly to ensure you're using the version installed in your virtual environment.

Common pytest options:
- `-v`: Verbose output
- `-s`: Show print statements (don't capture stdout)
- `-k "test_name"`: Run tests matching the given name
- `--pdb`: Drop into debugger on test failures
