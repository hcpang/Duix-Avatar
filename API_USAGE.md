# Duix Avatar API Usage Guide

This guide explains how to generate videos directly via the Duix Avatar API, bypassing the client application.

## Prerequisites

1. Docker services must be running (all 3 containers)
2. Python 3.6+ installed
3. `requests` library: `pip install requests`

## Quick Start

### 1. Test the APIs

First, verify that the APIs are accessible:

```bash
python test_api.py
```

This should show that both the Video Generation API and TTS API are running.

### 2. Generate Video from Existing Audio

If you already have an audio file and an avatar video:

```bash
python generate_video.py \
  "D:/duix_avatar_data/face2face/temp/your_audio.wav" \
  "D:/duix_avatar_data/face2face/temp/20251113182348159.mp4"
```

**Parameters:**
- First argument: Path to audio file (WAV format)
- Second argument: Path to your avatar video (MP4 format)

### 3. Generate Video from Text (with TTS)

To generate a complete video from text:

```bash
python generate_from_text.py \
  "Hello, this is my AI avatar speaking!" \
  "D:/duix_avatar_data/face2face/temp/20251113182348159.mp4" \
  "/voice/reference_audio.wav" \
  "This is the reference audio text"
```

**Parameters:**
- Text to speak
- Path to avatar video
- Path to reference audio for voice cloning
- Text from the reference audio

## API Endpoints

### Video Generation API

**Submit Video Generation:**
- URL: `http://127.0.0.1:8383/easy/submit`
- Method: POST
- Content-Type: application/json

```json
{
  "audio_url": "/path/to/audio.wav",
  "video_url": "/path/to/avatar.mp4",
  "code": "unique-task-id",
  "chaofen": 0,
  "watermark_switch": 0,
  "pn": 1
}
```

**Response:**
```json
{
  "code": 10000,
  "msg": "success"
}
```

**Query Video Status:**
- URL: `http://127.0.0.1:8383/easy/query?code={task_code}`
- Method: GET

**Response (Processing):**
```json
{
  "code": 10000,
  "data": {
    "status": 1,
    "progress": 45,
    "msg": "Processing..."
  }
}
```

**Response (Success):**
```json
{
  "code": 10000,
  "data": {
    "status": 2,
    "progress": 100,
    "msg": "Complete",
    "result": "temp/task-uuid-r.mp4"
  }
}
```

**Status Codes:**
- `status: 1` - Processing
- `status: 2` - Success
- `status: 3` - Failed

### TTS (Text-to-Speech) API

**Synthesize Audio:**
- URL: `http://127.0.0.1:18180/v1/invoke`
- Method: POST
- Content-Type: application/json

```json
{
  "speaker": "unique-speaker-id",
  "text": "Text to synthesize",
  "format": "wav",
  "topP": 0.7,
  "max_new_tokens": 1024,
  "chunk_length": 100,
  "repetition_penalty": 1.2,
  "temperature": 0.7,
  "need_asr": false,
  "streaming": false,
  "is_fixed_seed": 0,
  "is_norm": 0,
  "reference_audio": "/path/to/reference.wav",
  "reference_text": "Text from reference audio"
}
```

**Response:**
- Binary WAV audio file

## File Paths

All file paths should be:
1. **Absolute paths** starting with `D:/` (or your drive letter)
2. Accessible from the Docker container via the volume mapping
3. Located in `D:/duix_avatar_data/` to ensure Docker can access them

### Volume Mappings (from docker-compose.yml)

- `D:/duix_avatar_data/face2face` → `/code/data` (video generation)
- `D:/duix_avatar_data/voice/data` → `/code/data` (TTS)

## Examples

### Example 1: Simple Video Generation

```python
import requests
import uuid

# Submit task
task_code = str(uuid.uuid4())
submit_data = {
    "audio_url": "D:/duix_avatar_data/face2face/temp/audio.wav",
    "video_url": "D:/duix_avatar_data/face2face/temp/avatar.mp4",
    "code": task_code,
    "chaofen": 0,
    "watermark_switch": 0,
    "pn": 1
}

response = requests.post("http://127.0.0.1:8383/easy/submit", json=submit_data)
print(response.json())

# Check status
status_response = requests.get(f"http://127.0.0.1:8383/easy/query?code={task_code}")
print(status_response.json())
```

### Example 2: Using curl

```bash
# Submit video generation
curl -X POST http://127.0.0.1:8383/easy/submit \
  -H "Content-Type: application/json" \
  -d '{
    "audio_url": "D:/duix_avatar_data/face2face/temp/audio.wav",
    "video_url": "D:/duix_avatar_data/face2face/temp/avatar.mp4",
    "code": "test-12345",
    "chaofen": 0,
    "watermark_switch": 0,
    "pn": 1
  }'

# Check status
curl "http://127.0.0.1:8383/easy/query?code=test-12345"
```

## Troubleshooting

### APIs Not Accessible

Check that all Docker containers are running:
```bash
docker ps
```

You should see:
- duix-avatar-gen-video (port 8383)
- duix-avatar-tts (port 18180)
- duix-avatar-asr (port 10095)

### File Not Found Errors

Make sure:
1. Files are in `D:/duix_avatar_data/` directory
2. Paths use forward slashes: `D:/path/to/file.wav`
3. Files exist and have correct permissions

### Video Generation Timeout

Video generation can take several minutes depending on:
- Audio length
- System resources
- GPU availability

The script waits up to 10 minutes by default.

## Output Files

Generated videos are saved to:
```
D:/duix_avatar_data/face2face/temp/<task-uuid>-r.mp4
```

The exact path is returned in the API response under `data.result`.
