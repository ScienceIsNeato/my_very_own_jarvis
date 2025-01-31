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

# Copy requirements files
COPY requirements.txt .
COPY requirements_core.txt .
COPY requirements_large.txt .

RUN pip install --no-cache-dir -r requirements_large.txt

# Install remaining dependencies
RUN pip install --no-cache-dir -r requirements_core.txt

# Copy application code
COPY . .

# Set non-sensitive environment variables
ENV PYTHONUNBUFFERED=1
ENV GANGLIA_FONT_PATH=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf
ENV GANGLIA_EMOJI_FONT_PATH=/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf
ENV PLAYBACK_MEDIA_IN_TESTS=false

# Default command (interactive shell)
CMD ["/bin/bash"] 
