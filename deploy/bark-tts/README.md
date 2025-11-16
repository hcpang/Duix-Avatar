# Bark TTS Service for Duix.Avatar

This directory contains the Bark TTS integration using Coqui TTS, replacing Fish Speech.

## Features

- **Highly Expressive Speech**: Bark generates natural, conversational speech with emotion
- **Voice Cloning**: Clone voices from 5-13 second audio samples
- **Multilingual Support**: Supports multiple languages
- **Compatible API**: Drop-in replacement for Fish Speech API

## Building the Image

From the `deploy` directory:

```bash
docker-compose -f docker-compose-bark.yml build duix-avatar-tts-bark
```

## Running the Service

### Stop Fish Speech (if running)
```bash
docker stop duix-avatar-tts
```

### Start Bark TTS
```bash
cd deploy
docker-compose -f docker-compose-bark.yml up -d duix-avatar-tts-bark
```

### Start All Services with Bark
```bash
cd deploy
docker-compose -f docker-compose-bark.yml up -d
```

## Testing the Service

### Health Check
```bash
curl http://127.0.0.1:18180/health
```

### Basic TTS
```bash
curl -X POST http://127.0.0.1:18180/v1/invoke \
  -H "Content-Type: application/json" \
  -d '{
    "speaker": "test-speaker",
    "text": "Hello, this is Bark TTS speaking!",
    "format": "wav",
    "temperature": 0.7
  }' \
  --output test_output.wav
```

### With Voice Cloning
```bash
curl -X POST http://127.0.0.1:18180/v1/invoke \
  -H "Content-Type: application/json" \
  -d '{
    "speaker": "my-voice",
    "text": "This should sound like my voice",
    "format": "wav",
    "temperature": 0.7,
    "reference_audio": "/code/data/reference_voice.wav"
  }' \
  --output cloned_output.wav
```

## Using with generate_from_text.py

The existing `scripts/generate_from_text.py` works without modification! Just ensure Bark TTS is running on port 18180.

```bash
python scripts/generate_from_text.py "Hello world!" \
  /code/data/temp/avatar.mp4 \
  /code/data/reference_audio.wav \
  "Reference text"
```

## Parameters

- **text**: Text to synthesize (required)
- **speaker**: Unique speaker ID (default: random UUID)
- **temperature**: Controls expressiveness (0.5-1.0, default: 0.7)
  - Lower = more monotone, consistent
  - Higher = more expressive, varied
- **reference_audio**: Path to reference audio for voice cloning (optional)
- **reference_text**: Transcript of reference audio (optional, not used by Bark but kept for compatibility)

## Performance Notes

- **First Generation**: ~30-60 seconds (model loading)
- **Subsequent Generations**: ~10-30 seconds depending on text length
- **GPU Required**: Bark is extremely slow on CPU
- **VRAM Usage**: ~4-6GB

## Troubleshooting

### Container won't start
```bash
# Check logs
docker logs duix-avatar-tts-bark

# Verify GPU access
docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi
```

### Model download issues
The first run will download the Bark model (~2GB). Check logs:
```bash
docker logs -f duix-avatar-tts-bark
```

### Audio quality issues
- Increase temperature for more expressiveness: `"temperature": 0.85`
- Ensure reference audio is 5-13 seconds for voice cloning
- Use WAV format for reference audio

## Switching Back to Fish Speech

```bash
docker-compose -f docker-compose-bark.yml down
docker-compose -f docker-compose.yml up -d
```

## File Paths

Make sure audio files are in a location accessible by Docker:
- Host: `D:/duix_avatar_data/voice/data/`
- Container: `/code/data/`

Example:
- Host path: `D:/duix_avatar_data/voice/data/my_voice.wav`
- API path: `/code/data/my_voice.wav`
