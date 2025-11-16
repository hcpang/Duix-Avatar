FROM nvidia/cuda:11.8.0-cudnn8-runtime-ubuntu22.04

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV CUDA_HOME=/usr/local/cuda

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3.10 \
    python3-pip \
    git \
    ffmpeg \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# Set Python 3.10 as default
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.10 1 && \
    update-alternatives --install /usr/bin/pip pip /usr/bin/pip3 1

# Upgrade pip
RUN pip install --no-cache-dir --upgrade pip

# Install PyTorch 2.5 with CUDA support (2.6 has compatibility issues with TTS)
RUN pip install --no-cache-dir torch==2.5.1 torchvision==0.20.1 torchaudio==2.5.1 --index-url https://download.pytorch.org/whl/cu118

# Install original Bark from Suno
RUN pip install --no-cache-dir git+https://github.com/suno-ai/bark.git

# Install Flask for API server and audio processing libraries
RUN pip install --no-cache-dir flask flask-cors numpy scipy nltk

# Download NLTK punkt tokenizer data
RUN python -m nltk.downloader punkt

# Create working directory
WORKDIR /code

# Copy API server
COPY bark_api_server.py /code/

# Create data directory
RUN mkdir -p /code/data

# Expose port
EXPOSE 8080

# Run API server
CMD ["python", "/code/bark_api_server.py"]
