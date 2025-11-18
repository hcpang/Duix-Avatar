# API Scripts for Text-to-Video Generation

## Header Metadata

**Date**: 2025-11-13
**Claude Model**: claude-sonnet-4-5-20250929
**Feature**: API scripts and documentation for programmatic video generation

**Files Created:**
- `scripts/generate_from_text.py:1-232` - Complete text-to-video pipeline with TTS and UTF-8 encoding fixes
- `scripts/generate_video.sh:1-88` - Bash script for video generation from audio
- `scripts/test_api.py:1-74` - API connectivity testing script
- `API_USAGE.md:1-242` - Low-level API reference documentation
- `SCRIPT_USAGE.md:1-523` - Comprehensive usage guide with examples and troubleshooting
- `JOURNALING-GUIDE.md:1-224` - Development journaling guidelines (copied from trading project)
- `ml_trading_script.txt:1-1` - Example text file demonstrating ML trading content (942 characters)
- `documentation/journals/2025-11-13-api-scripts-video-generation.md` - This journal

**Files Modified:**
None (all work was creating new files)

**Files Deleted:**
None

---

## Problem Statement

The Duix Avatar system required using a client application to generate videos, which:
1. Frequently timed out during processing
2. Provided no programmatic access for automation
3. Lacked documentation for API usage
4. Made batch processing and integration impossible

The user needed to generate avatar videos from text scripts programmatically, bypassing the unreliable client application entirely.

---

## Solution Implementation

### Technical Approach

Created a suite of Python and Bash scripts that interact directly with the Duix Avatar Docker services:

1. **TTS API Integration** (generate_from_text.py:24-88)
   - Synthesizes audio from text using voice cloning
   - Handles reference audio and text for consistent voice quality
   - Saves generated WAV files to Docker-accessible volumes

2. **Video Generation API** (generate_from_text.py:90-160, generate_video.sh:20-87)
   - Submits video generation tasks via REST API
   - Polls for completion status with progress updates
   - Handles Chinese language error messages from the API

3. **Path Translation Layer** (generate_from_text.py:221-223)
   - Translates Windows paths to Docker container paths
   - Handles both forward and backward slashes
   - Prevents Git Bash automatic path conversion on Windows

### Key Design Decisions

**Dual Implementation Strategy**: Provided both Python and Bash versions
- Python for complete text→TTS→video pipeline
- Bash for reliable video-only generation (more stable on Windows)

**UTF-8 Encoding Fixes** (generate_from_text.py:8-19)
- Wrapped stdout/stderr with UTF-8 TextIOWrapper on Windows
- Prevents 'charmap' codec errors with Unicode symbols
- Critical for displaying Chinese progress messages

**Flexible Input Handling** (generate_from_text.py:184-198)
- Accepts text files, direct text strings, or stdin
- Allows optional avatar and voice cloning parameters
- Defaults to working configuration for quick starts

### Code Examples

**TTS with Voice Cloning** (generate_from_text.py:43-64):
```python
tts_params = {
    "speaker": speaker_id,
    "text": text,
    "format": "wav",
    "topP": 0.7,
    "max_new_tokens": 2048,
    "chunk_length": 200,
    "repetition_penalty": 1.2,
    "temperature": 0.7,
    "need_asr": False,
    "streaming": False,
    "is_fixed_seed": 0,
    "is_norm": 0
}

# Add reference audio only if provided
if reference_audio and reference_text:
    tts_params["reference_audio"] = reference_audio
    tts_params["reference_text"] = reference_text
```

**Path Normalization** (generate_from_text.py:221-223):
```python
# Convert to container path (normalize Windows backslashes to forward slashes first)
audio_path_normalized = audio_path.replace("\\", "/")
audio_container_path = audio_path_normalized.replace("D:/duix_avatar_data/face2face", "/code/data")
```

---

## Technical Implementation Details

### Architecture

```
User Input (Text)
    ↓
generate_from_text.py
    ↓
TTS API (port 18180)
    ↓
Audio File (WAV)
    ↓
Video Generation API (port 8383)
    ↓
Final Video (MP4)
```

### Docker Volume Mappings

The system required understanding two separate Docker volume mappings:

**TTS Container** (duix-avatar-tts):
- Windows: `D:/duix_avatar_data/voice/data/`
- Container: `/code/data/`

**Video Container** (duix-avatar-gen-video):
- Windows: `D:/duix_avatar_data/face2face/`
- Container: `/code/data/`

### Key Integration Points

1. **Reference Audio Discovery** (via Docker logs)
   - Found existing voice cloning setup in `/code/sessions/`
   - Copied reference audio to accessible volume: `/code/data/reference_audio.wav`
   - Reference text: "呃，嗯嗯嗯嗯嗯嗯懂啊，头部梳头术，没有爱是幸福是啊黄色。"

2. **API Status Polling** (generate_from_text.py:128-159)
   - Status 1: Processing (shows progress percentage)
   - Status 2: Success (returns result path)
   - Status 3: Failed (shows error message)
   - 2-second poll interval, 10-minute timeout

---

## Testing/Validation

### API Connectivity Test

Created `test_api.py` to verify both APIs are accessible:
```bash
$ python test_api.py
============================================================
Duix Avatar API Test
============================================================
Testing Video Generation API...
  ✓ Video API is accessible

Testing TTS API...
  ✓ TTS API is accessible
```

### End-to-End Test

Generated a complete video from the ML trading script (942 characters):

```bash
$ MSYS_NO_PATHCONV=1 python generate_from_text.py ml_trading_script.txt \
  "/code/data/temp/20251113182348159.mp4" \
  "/code/data/reference_audio.wav" \
  "呃，嗯嗯嗯嗯嗯嗯懂啊，头部梳头术，没有爱是幸福是啊黄色。"
```

**Results**:
- Audio generated: `144fd900-40e1-4ef3-a6bc-77c5b799a280.wav` (4.9 MB)
- Video generated: `task-1763096318-r.mp4` (46 MB)
- Processing time: ~2-3 minutes
- Video quality: High-definition with synchronized lip movements

### Performance Verification

Tested with Bash script for reliability comparison:
```bash
$ MSYS_NO_PATHCONV=1 bash generate_video.sh \
  "/code/data/temp/144fd900-40e1-4ef3-a6bc-77c5b799a280.wav" \
  "/code/data/temp/20251113182348159.mp4"

Progress: 20% - 视频特征提取完成
Progress: 80% - 视频处理完成
Progress: 100% - 视频处理完成
✓ Video generation completed!
```

---

## Development Learnings

### 1. Creating New Scripts Instead of Reusing Existing Ones

**Mistake**: Started creating a new script `generate_ml_video.py` for generating the ML trading video instead of making the existing script flexible.

**Your Feedback**: "why are you creating a new script each time? can't you have a script that takes in the text input from a file or something like that?"

**Correction**: Modified `generate_from_text.py` to accept multiple input types (file, direct text, or stdin) with optional parameters instead of creating specialized scripts for each use case.

**Next time**: When asked to generate content with slightly different inputs, first consider making existing scripts more flexible with optional parameters rather than creating new specialized scripts.

### 2. Using Windows Paths Instead of Container Paths

**Mistake**: Initially used Windows path format `D:/duix_avatar_data/...` when calling APIs, which failed because the Docker containers expect container paths.

**Your Feedback**: "why can't you use the same as before when you run the test?"

**Correction**: Standardized on container path format `/code/data/...` for all API calls and added path translation logic in generate_from_text.py:221-223 to convert Windows paths to container paths.

**Next time**: When working with Docker-based services, always use container paths in API calls and translate Windows paths to container paths programmatically rather than passing Windows paths directly.

### 3. Not Investigating Existing Voice Cloning Setup

**Mistake**: Tried to generate audio without reference audio parameters, which caused TTS API to return 500 errors.

**Your Feedback**: "can you look at the logs from docker how it's done? i believe voice cloning is already set up for this avatar"

**Correction**: Checked Docker logs (`docker logs duix-avatar-tts`) and found existing reference audio configuration in `/code/sessions/` directory, then copied it to an accessible location for reuse.

**Next time**: When encountering API errors with optional parameters, check service logs and existing usage patterns before attempting workarounds. The infrastructure may already have the required configuration that just needs to be discovered and referenced correctly.

---

## Implementation Status

### Completed Items

- [x] Created API connectivity test script
- [x] Implemented complete text-to-video pipeline (Python)
- [x] Created video-only generation script (Bash)
- [x] Added UTF-8 encoding fixes for Windows
- [x] Implemented flexible input handling (file/text/stdin)
- [x] Added path translation for Windows/Docker compatibility
- [x] Created comprehensive API documentation
- [x] Created detailed usage guide with examples
- [x] Successfully generated test video (46MB, ML trading content)
- [x] Verified end-to-end workflow functionality

### Current State

All scripts are fully functional and tested. The system can:
- Generate videos from text files, direct text input, or stdin
- Use custom avatars and voice cloning
- Process long-form content (tested with 942-character script)
- Handle Windows path conversions automatically
- Provide progress updates during generation
- Return final video paths for downstream processing

### Known Limitations

1. **Git Bash Path Conversion**: Requires `MSYS_NO_PATHCONV=1` environment variable on Windows
2. **Output Buffering**: Python script may not show real-time output due to buffering; Bash version is more reliable for status updates
3. **Volume Mapping Dependency**: Files must be in Docker-mounted volumes (`D:/duix_avatar_data/`)
4. **Processing Time**: 2-5 minutes per video depending on text length and system resources
