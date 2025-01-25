FROM python:3.9

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    portaudio19-dev \
    ffmpeg \
    libsndfile1 \
    fonts-dejavu \
    fonts-noto-color-emoji \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install numpy and pandas together to ensure compatibility
RUN pip install --no-cache-dir "numpy==1.26.4" "pandas==2.2.3"

# Install torch and other large dependencies first
RUN pip install --no-cache-dir \
    torch==2.0.0 \
    torchaudio==2.0.0 \
    transformers==4.36.0 \
    keyboard \
    google-cloud-speech \
    google-cloud-texttospeech \
    openai-whisper \
    accelerate \
    safetensors \
    fonts

# Install remaining dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Set non-sensitive environment variables
ENV PYTHONUNBUFFERED=1
ENV GANGLIA_FONT_PATH=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf
ENV GANGLIA_EMOJI_FONT_PATH=/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf
ENV PLAYBACK_MEDIA_IN_TESTS=false

# Default command (interactive shell)
CMD ["/bin/bash"] 
