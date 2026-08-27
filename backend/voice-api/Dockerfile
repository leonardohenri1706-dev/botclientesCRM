FROM python:3.11-slim

WORKDIR /app

# Install system dependencies including ffmpeg for audio conversion
RUN apt-get update && apt-get install -y \
    ffmpeg \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# For Coqui TTS (uncomment if using):
# RUN pip install --no-cache-dir TTS==0.22.0 torch==2.2.0 --index-url https://download.pytorch.org/whl/cu118

# For Piper TTS (uncomment if using):
# RUN apt-get update && apt-get install -y piper-tts && rm -rf /var/lib/apt/lists/*

# Create audio output directory
RUN mkdir -p /app/audio_output

# Copy application code
COPY . .

EXPOSE 8001

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]