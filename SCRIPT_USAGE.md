# Duix Avatar Script Usage Guide

This guide shows you how to use the Python and Bash scripts to generate avatar videos from text or audio.

## Table of Contents
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Scripts Overview](#scripts-overview)
- [Common Workflows](#common-workflows)
- [Troubleshooting](#troubleshooting)

---

## Prerequisites

1. **Docker services running**: All 3 containers must be running
   ```bash
   docker ps
   # Should show: duix-avatar-gen-video, duix-avatar-tts, duix-avatar-asr
   ```

2. **Python 3.6+** with `requests` library:
   ```bash
   pip install requests
   ```

3. **Data directory**: `D:/duix_avatar_data/` must exist and be accessible to Docker

---

## Quick Start

### Generate a video from text (simplest method):

```bash
# Create a text file with your content
echo "Hello! This is my AI avatar speaking." > my_script.txt

# Generate the video (uses default avatar and voice)
MSYS_NO_PATHCONV=1 python scripts/generate_from_text.py my_script.txt \
  "/code/data/temp/20251113182348159.mp4" \
  "/code/data/reference_audio.wav" \
  "呃，嗯嗯嗯嗯嗯嗯懂啊，头部梳头术，没有爱是幸福是啊黄色。"
```

The video will be saved to `D:/duix_avatar_data/face2face/temp/`

---

## Scripts Overview

### 1. `test_api.py` - Test API Connectivity

**Purpose**: Verify that both the Video Generation API and TTS API are accessible.

**Usage**:
```bash
python scripts/test_api.py
```

**Expected Output**:
```
============================================================
Duix Avatar API Test
============================================================
Testing Video Generation API...
  ✓ Video API is accessible

Testing TTS API...
  ✓ TTS API is accessible

============================================================
Test Summary:
  Video API: ✓ OK
  TTS API: ✓ OK
============================================================
```

---

### 2. `generate_from_text.py` - Complete Text-to-Video Pipeline

**Purpose**: Generates a complete avatar video from text input by:
1. Synthesizing audio from text using TTS
2. Generating video with the avatar speaking

**Syntax**:
```bash
MSYS_NO_PATHCONV=1 python scripts/generate_from_text.py <text_input> [avatar_video] [reference_audio] [reference_text]
```

**Parameters**:
- `text_input`: Can be:
  - Path to a text file (e.g., `my_script.txt`)
  - Direct text string (e.g., `"Hello world!"`)
  - `-` to read from stdin
- `avatar_video`: (Optional) Path to avatar video. Default: `/code/data/temp/20251113182348159.mp4`
- `reference_audio`: (Optional) Path to reference audio for voice cloning
- `reference_text`: (Optional) Text content of the reference audio

**Examples**:

#### Example 1: From a text file with default settings
```bash
# Create your text file
cat > presentation.txt << 'EOF'
Welcome to today's presentation. We'll be discussing the latest advances
in artificial intelligence and machine learning.
EOF

# Generate video
MSYS_NO_PATHCONV=1 python scripts/generate_from_text.py presentation.txt \
  "/code/data/temp/20251113182348159.mp4" \
  "/code/data/reference_audio.wav" \
  "呃，嗯嗯嗯嗯嗯嗯懂啊，头部梳头术，没有爱是幸福是啊黄色。"
```

#### Example 2: From direct text input
```bash
MSYS_NO_PATHCONV=1 python scripts/generate_from_text.py \
  "Hello! This is a short message." \
  "/code/data/temp/20251113182348159.mp4" \
  "/code/data/reference_audio.wav" \
  "呃，嗯嗯嗯嗯嗯嗯懂啊，头部梳头术，没有爱是幸福是啊黄色。"
```

#### Example 3: From stdin (pipe input)
```bash
echo "Welcome to our service!" | MSYS_NO_PATHCONV=1 python scripts/generate_from_text.py - \
  "/code/data/temp/20251113182348159.mp4" \
  "/code/data/reference_audio.wav" \
  "呃，嗯嗯嗯嗯嗯嗯懂啊，头部梳头术，没有爱是幸福是啊黄色。"
```

#### Example 4: Long-form content
```bash
# The ML trading script example (942 characters)
MSYS_NO_PATHCONV=1 python scripts/generate_from_text.py ml_trading_script.txt \
  "/code/data/temp/20251113182348159.mp4" \
  "/code/data/reference_audio.wav" \
  "呃，嗯嗯嗯嗯嗯嗯懂啊，头部梳头术，没有爱是幸福是啊黄色。"
```

**Output**:
- Audio file: `D:/duix_avatar_data/face2face/temp/<uuid>.wav`
- Video file: `D:/duix_avatar_data/face2face/temp/<task-id>-r.mp4`

**Time**: 2-5 minutes depending on text length

---

### 3. `generate_video.sh` - Video Generation from Existing Audio

**Purpose**: Generates a video from an existing audio file. Use this when you already have audio and just need the video.

**Syntax**:
```bash
MSYS_NO_PATHCONV=1 bash scripts/generate_video.sh <audio_path> <avatar_video_path>
```

**Parameters**:
- `audio_path`: Path to your audio file (must be in WAV format, container path)
- `avatar_video_path`: Path to the avatar video template

**Examples**:

#### Example 1: Generate video from existing audio
```bash
MSYS_NO_PATHCONV=1 bash scripts/generate_video.sh \
  "/code/data/temp/my_audio.wav" \
  "/code/data/temp/20251113182348159.mp4"
```

#### Example 2: Batch processing multiple audio files
```bash
for audio in /code/data/temp/*.wav; do
  MSYS_NO_PATHCONV=1 bash scripts/generate_video.sh \
    "$audio" \
    "/code/data/temp/20251113182348159.mp4"
done
```

**Output**:
- Video file: `D:/duix_avatar_data/face2face/temp/<task-id>-r.mp4`

**Time**: 1-3 minutes depending on audio length

---

## Common Workflows

### Workflow 1: Quick Test

Test everything is working with a simple message:

```bash
# 1. Test APIs
python scripts/test_api.py

# 2. Generate a test video
echo "Test message" | MSYS_NO_PATHCONV=1 python scripts/generate_from_text.py - \
  "/code/data/temp/20251113182348159.mp4" \
  "/code/data/reference_audio.wav" \
  "呃，嗯嗯嗯嗯嗯嗯懂啊，头部梳头术，没有爱是幸福是啊黄色。"

# 3. Check the output
ls -lh D:/duix_avatar_data/face2face/temp/*.mp4 | tail -1
```

---

### Workflow 2: Create Multiple Videos from Scripts

Generate videos for multiple text files:

```bash
# Create your scripts
cat > intro.txt << 'EOF'
Welcome to our tutorial series on AI and machine learning.
EOF

cat > chapter1.txt << 'EOF'
In this first chapter, we'll explore the fundamentals of neural networks.
EOF

cat > outro.txt << 'EOF'
Thank you for watching. See you in the next video!
EOF

# Generate all videos
for script in intro.txt chapter1.txt outro.txt; do
  echo "Generating video for $script..."
  MSYS_NO_PATHCONV=1 python scripts/generate_from_text.py "$script" \
    "/code/data/temp/20251113182348159.mp4" \
    "/code/data/reference_audio.wav" \
    "呃，嗯嗯嗯嗯嗯嗯懂啊，头部梳头术，没有爱是幸福是啊黄色。"
done
```

---

### Workflow 3: Separate TTS and Video Generation

If you want more control, you can split the process:

```bash
# 1. Generate audio only using TTS API directly
curl -X POST http://127.0.0.1:18180/v1/invoke \
  -H "Content-Type: application/json" \
  -d '{
    "speaker": "my-speaker",
    "text": "Your text here",
    "format": "wav",
    "reference_audio": "/code/data/reference_audio.wav",
    "reference_text": "呃，嗯嗯嗯嗯嗯嗯懂啊，头部梳头术，没有爱是幸福是啊黄色。"
  }' \
  --output D:/duix_avatar_data/face2face/temp/my_audio.wav

# 2. Generate video from the audio
MSYS_NO_PATHCONV=1 bash scripts/generate_video.sh \
  "/code/data/temp/my_audio.wav" \
  "/code/data/temp/20251113182348159.mp4"
```

---

## Understanding File Paths

### Windows Paths vs Container Paths

The Docker containers map directories differently:

| Windows Path | Container Path (TTS) | Container Path (Video) |
|--------------|---------------------|------------------------|
| `D:/duix_avatar_data/voice/data/` | `/code/data/` | N/A |
| `D:/duix_avatar_data/face2face/` | N/A | `/code/data/` |
| `D:/duix_avatar_data/face2face/temp/` | N/A | `/code/data/temp/` |

**Important**: Always use container paths when calling scripts:
```bash
# ✓ CORRECT - Container path
MSYS_NO_PATHCONV=1 python scripts/generate_from_text.py text.txt "/code/data/temp/avatar.mp4"

# ✗ WRONG - Windows path
python generate_from_text.py text.txt "D:/duix_avatar_data/face2face/temp/avatar.mp4"
```

---

## Environment Variables

### MSYS_NO_PATHCONV

On Windows with Git Bash, you **must** use `MSYS_NO_PATHCONV=1` to prevent path conversion issues:

```bash
# Required on Windows Git Bash
MSYS_NO_PATHCONV=1 python scripts/generate_from_text.py ...

# Not needed on Linux/Mac
python generate_from_text.py ...
```

---

## Output Files

### Generated Audio Files
- Location: `D:/duix_avatar_data/face2face/temp/<uuid>.wav`
- Format: WAV
- Size: ~1MB per minute of speech
- Example: `144fd900-40e1-4ef3-a6bc-77c5b799a280.wav`

### Generated Video Files
- Location: `D:/duix_avatar_data/face2face/temp/<task-id>-r.mp4`
- Format: MP4
- Size: ~10-50MB depending on length
- Example: `task-1763096318-r.mp4`

### Finding Your Latest Video
```bash
# List all videos by date (newest first)
ls -lht D:/duix_avatar_data/face2face/temp/*.mp4 | head -5

# Find a specific task
find D:/duix_avatar_data/face2face -name "*task-1763096318*.mp4"
```

---

## Troubleshooting

### Problem: "Docker containers not running"

**Error**: `Connection refused` or `API not accessible`

**Solution**:
```bash
# Check container status
docker ps

# Start containers if needed
cd deploy
docker-compose up -d

# Check logs
docker logs duix-avatar-tts --tail 20
docker logs duix-avatar-gen-video --tail 20
```

---

### Problem: "ModuleNotFoundError: No module named 'requests'"

**Solution**:
```bash
pip install requests
```

---

### Problem: "Character encoding errors"

**Error**: `'charmap' codec can't encode character`

**Solution**: Make sure you're using `MSYS_NO_PATHCONV=1` on Windows:
```bash
MSYS_NO_PATHCONV=1 python scripts/generate_from_text.py ...
```

---

### Problem: "File not found" errors with paths

**Common causes**:
1. Using Windows paths instead of container paths
2. Files not in the mounted Docker volumes

**Solution**:
```bash
# ✓ CORRECT - File in mounted volume with container path
cp my_audio.wav D:/duix_avatar_data/face2face/temp/
MSYS_NO_PATHCONV=1 bash scripts/generate_video.sh "/code/data/temp/my_audio.wav" ...

# ✗ WRONG - File outside mounted volume
MSYS_NO_PATHCONV=1 bash scripts/generate_video.sh "C:/Users/me/audio.wav" ...
```

---

### Problem: "Video generation stuck at 20%"

This is normal! Video processing goes through phases:
- 0-20%: Audio processing and video feature extraction
- 20-80%: Video frame generation (this takes the longest)
- 80-100%: Final encoding

**Typical times**:
- 30 seconds of video: 1-2 minutes
- 1 minute of video: 2-3 minutes
- 3+ minutes of video: 5-10 minutes

---

### Problem: "TTS returns 500 error"

**Error**: `{"statusCode":500,"message":"...","error":"Internal Server Error"}`

**Common causes**:
1. Reference audio file not accessible
2. Text is too long (>2000 tokens)

**Solutions**:
```bash
# 1. Verify reference audio exists in TTS container
docker exec duix-avatar-tts ls -l /code/data/reference_audio.wav

# 2. Copy reference audio to TTS data directory
cp D:/duix_avatar_data/face2face/temp/reference_audio.wav \
   D:/duix_avatar_data/voice/data/reference_audio.wav

# 3. For long text, split into smaller chunks
```

---

### Problem: "Git Bash path conversion issues"

**Symptoms**: Paths like `/code/data` become `C:/Program Files/Git/code/data`

**Solution**: Always use `MSYS_NO_PATHCONV=1`:
```bash
MSYS_NO_PATHCONV=1 python scripts/generate_from_text.py ...
MSYS_NO_PATHCONV=1 bash scripts/generate_video.sh ...
```

---

## Advanced Usage

### Custom Voice Cloning

To use your own voice:

1. Record a reference audio (10-30 seconds of clear speech)
2. Save as WAV format
3. Transcribe the exact text spoken
4. Use in the script:

```bash
MSYS_NO_PATHCONV=1 python scripts/generate_from_text.py my_script.txt \
  "/code/data/temp/avatar.mp4" \
  "/code/data/my_voice.wav" \
  "This is the exact text I spoke in my_voice.wav"
```

---

### Custom Avatar Video

To use your own avatar:

1. Record a video of yourself (or subject) speaking
2. Place in `D:/duix_avatar_data/face2face/temp/`
3. Use the container path in the script:

```bash
MSYS_NO_PATHCONV=1 python scripts/generate_from_text.py my_script.txt \
  "/code/data/temp/my_avatar.mp4" \
  "/code/data/reference_audio.wav" \
  "呃，嗯嗯嗯嗯嗯嗯懂啊，头部梳头术，没有爱是幸福是啊黄色。"
```

---

## Performance Tips

1. **GPU Acceleration**: Ensure Docker containers have GPU access for faster processing
2. **Batch Processing**: Process multiple videos in parallel to maximize GPU utilization
3. **Text Length**: Keep individual texts under 1000 characters for best quality
4. **Audio Quality**: Use high-quality reference audio (16-bit, 44.1kHz WAV)

---

## API Reference

For detailed API documentation, see [API_USAGE.md](API_USAGE.md).

---

## Support

If you encounter issues:

1. Check Docker logs: `docker logs duix-avatar-tts --tail 50`
2. Verify API connectivity: `python scripts/test_api.py`
3. Check file paths are in mounted volumes
4. Ensure you're using container paths (not Windows paths)
5. On Windows, use `MSYS_NO_PATHCONV=1`

---

## Examples Included

This repository includes example files:

- `ml_trading_script.txt` - Example of a longer text (942 characters) about ML trading strategies
- You can use this to test the full pipeline

```bash
MSYS_NO_PATHCONV=1 python scripts/generate_from_text.py ml_trading_script.txt \
  "/code/data/temp/20251113182348159.mp4" \
  "/code/data/reference_audio.wav" \
  "呃，嗯嗯嗯嗯嗯嗯懂啊，头部梳头术，没有爱是幸福是啊黄色。"
```
