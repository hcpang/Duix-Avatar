# Reference Audio Generation Script Documentation

**File:** `scripts/generate_reference_audio.py`

## Overview

The `generate_reference_audio.py` script processes MP4/video files or audio files to create high-quality reference audio for voice cloning in Duix Avatar's TTS (Text-to-Speech) system. It extracts audio, applies professional noise reduction, and generates accurate transcriptions using Whisper ASR.

**Key Features:**
- Accepts MP4/video files from **any location** on your filesystem
- Extracts audio and converts to optimal format (16kHz, mono, pcm_s16le)
- Professional noise reduction using **RNNoise**
- Accurate transcription using **faster-whisper ASR**
- Optional **custom output directory** for organizing files
- Generates summary JSON with all paths and transcriptions
- Output ready for immediate use with `generate_from_text.py`

---

## Installation Requirements

### Required Dependencies

```bash
# Core dependencies
pip install faster-whisper  # For ASR transcription
```

### System Requirements

1. **FFmpeg**: Required for audio extraction
   - Windows: Included in `resources/ffmpeg/win-amd64/bin/`
   - Linux: Install via package manager or place in `resources/ffmpeg/linux-amd64/`

2. **Docker**: Required for RNNoise denoising
   - The `duix-avatar-tts` container must be running
   - RNNoise binary (`rnnoise_new`) available in container

3. **Volume Mount**:
   - `d:/duix_avatar_data/voice/data/` → `/code/data/` (container)

---

## Usage

### Basic Usage

```bash
python scripts/generate_reference_audio.py <input_file> [whisper_model] [output_dir]
```

**Parameters:**
- `input_file`: Path to MP4/video/audio file (can be anywhere on your system)
- `whisper_model`: (Optional) Whisper model size - `tiny`, `base` (default), `small`, `medium`, `large`
- `output_dir`: (Optional) Copy final files to this custom directory

### Examples

#### Process MP4 from Any Location

```bash
# From Downloads folder (default output location)
python scripts/generate_reference_audio.py "C:\Users\yharm\Downloads\Evan.mp4"

# From data directory
python scripts/generate_reference_audio.py "D:/duix_avatar_data/voice/data/Alex3.mp4"

# From network drive
python scripts/generate_reference_audio.py "Z:\videos\sample.mp4"
```

#### Use Different Whisper Models

```bash
# Fast (less accurate)
python scripts/generate_reference_audio.py video.mp4 tiny

# Default (recommended)
python scripts/generate_reference_audio.py video.mp4 base

# More accurate (slower)
python scripts/generate_reference_audio.py video.mp4 medium
```

#### Custom Output Directory

```bash
# Copy files to custom location for organization
python scripts/generate_reference_audio.py \
  "C:\Users\yharm\Downloads\Evan.mp4" \
  base \
  "C:\Users\yharm\Downloads\references"
```

---

## How It Works

### Pipeline Overview

```
Input MP4/Video (any path)
    ↓
[Step 0] Extract Audio → WAV (local ffmpeg)
    ↓
[Step 1] Process Audio:
    - Format to 16kHz mono pcm_s16le (Docker ffmpeg)
    - Denoise with RNNoise (Docker rnnoise_new)
    - Re-format to pcm_s16le (Docker ffmpeg)
    ↓
[Step 2] Transcribe with faster-whisper (local)
    ↓
[Step 3] Copy to custom directory (if specified)
    ↓
Output: Processed audio + transcription + summary JSON
```

### Why This Pipeline?

This script replicates the TTS service's audio processing pipeline but runs locally to avoid API limitations:

| Feature | This Script | TTS API |
|---------|-------------|---------|
| Input location | Any path ✓ | Must be in `/code/data/` |
| Output location | Windows-accessible ✓ | `/code/sessions/` (not mounted) |
| ASR service | faster-whisper ✓ | fun-asr (often fails) |
| File safety | Temp files cleaned up ✓ | Original files deleted |
| Custom output | Supported ✓ | Not supported |
| Reliability | High ✓ | API bugs and failures |

---

## Output Files

### Default Output Location

**Directory:** `D:/duix_avatar_data/voice/data/origin_audio/`

This location is required because it's mounted to the Docker container at `/code/data/`.

### 1. Processed Audio WAV

**Filename:** `format_denoise_<timestamp>.wav`

**Example:** `format_denoise_temp_extract_20251116204530569.wav`

**Format:**
- Sample rate: 16kHz
- Channels: Mono
- Encoding: pcm_s16le
- Denoised with RNNoise

**Use:** This is your reference audio for voice cloning.

### 2. Transcription Text File

**Filename:** `format_denoise_<timestamp>.txt`

**Example:** `format_denoise_temp_extract_20251116204530569.txt`

**Contains:** The transcribed text from the audio (UTF-8 encoded)

**Example content:**
```
Dear Coach Drollman, thank you for teaching me how to snowboard and encouraging me to go and handle. I really appreciate you teaching and guiding me to where I am now.
```

**Use:** This is your reference text that matches the reference audio.

### 3. Summary JSON

**Filename:** `reference_audio_summary.json`

**Location:** Same as audio/text files (and custom directory if specified)

**Format without custom directory:**
```json
[
  {
    "audio": "/code/data/origin_audio/format_denoise_20251116204530569.wav",
    "audio_windows": "d:\\duix_avatar_data\\voice\\data\\origin_audio\\format_denoise_20251116204530569.wav",
    "text": "Dear Coach Drollman, thank you for teaching me...",
    "text_file": "d:\\duix_avatar_data\\voice\\data\\origin_audio\\format_denoise_20251116204530569.txt"
  }
]
```

**Format with custom directory:**
```json
[
  {
    "audio": "/code/data/origin_audio/format_denoise_20251116204530569.wav",
    "audio_windows": "d:\\duix_avatar_data\\voice\\data\\origin_audio\\format_denoise_20251116204530569.wav",
    "audio_custom": "C:\\Users\\yharm\\Downloads\\references\\format_denoise_20251116204530569.wav",
    "text": "Dear Coach Drollman, thank you for teaching me...",
    "text_file": "d:\\duix_avatar_data\\voice\\data\\origin_audio\\format_denoise_20251116204530569.txt",
    "text_file_custom": "C:\\Users\\yharm\\Downloads\\references\\format_denoise_20251116204530569.txt"
  }
]
```

**Use:** Convenient reference for all generated files with all path variants.

---

## Custom Output Directory

### How It Works

When you specify a custom output directory (3rd parameter), the script:

1. **Processes files normally** in the mounted directory (required for Docker)
2. **Copies final files** to your custom location
3. **Updates summary JSON** with both locations
4. **Creates the directory** if it doesn't exist

### Benefits

- **Organization**: Group reference audios by speaker, project, etc.
- **Backup**: Keep copies outside the Docker data directory
- **Easy access**: Place files in convenient locations like Desktop, Documents, etc.
- **Still compatible**: TTS uses the container path from the original location

### Example Workflow

```bash
# Create references for different speakers
python scripts/generate_reference_audio.py speaker1_clip.mp4 base "C:/references/speaker1"
python scripts/generate_reference_audio.py speaker2_clip.mp4 base "C:/references/speaker2"

# Result:
# C:/references/
# ├── speaker1/
# │   ├── format_denoise_*.wav
# │   ├── format_denoise_*.txt
# │   └── reference_audio_summary.json
# └── speaker2/
#     ├── format_denoise_*.wav
#     ├── format_denoise_*.txt
#     └── reference_audio_summary.json
```

---

## Using Generated Reference Audio

### Single Reference Audio

After generating reference audio, use it with `generate_from_text.py`:

```bash
python scripts/generate_from_text.py \
  "Hello, this is a test of voice cloning!" \
  /code/data/temp/avatar.mp4 \
  "/code/data/origin_audio/format_denoise_20251116204530569.wav" \
  "Dear Coach Drollman, thank you for teaching me how to snowboard..."
```

**Note:** Always use the **container path** (from `audio` field in JSON) for TTS, not the custom path.

### Multiple Reference Audios

For better voice cloning quality, combine multiple reference audios using `|||` separator:

```bash
python scripts/generate_from_text.py \
  "Your text here" \
  /code/data/temp/avatar.mp4 \
  "/code/data/origin_audio/ref1.wav|||/code/data/origin_audio/ref2.wav" \
  "Reference text 1|||Reference text 2"
```

### Workflow Example

```bash
# Step 1: Generate 2 reference audios from different clips
python scripts/generate_reference_audio.py clip1.mp4
# Output: /code/data/origin_audio/format_denoise_xxx1.wav

python scripts/generate_reference_audio.py clip2.mp4
# Output: /code/data/origin_audio/format_denoise_xxx2.wav

# Step 2: Use both for better voice cloning
python scripts/generate_from_text.py \
  "New synthesized speech" \
  /code/data/temp/avatar.mp4 \
  "/code/data/origin_audio/format_denoise_xxx1.wav|||/code/data/origin_audio/format_denoise_xxx2.wav" \
  "Text from clip1|||Text from clip2"
```

---

## Technical Details

### Audio Processing Pipeline

#### Step 0: Audio Extraction (if MP4/video)

**Tool:** Local ffmpeg
**Input:** MP4/video from any path
**Output:** 16kHz mono pcm_s16le WAV in `D:/duix_avatar_data/voice/data/`

**Command:**
```bash
ffmpeg -i <input_file> -vn -acodec pcm_s16le -ar 16000 -ac 1 -y <output_wav>
```

**Why local ffmpeg?**
- Can read files from any Windows path
- Doesn't require Docker access
- Writes to mounted directory for next steps

#### Step 1.1: Format Conversion

**Tool:** ffmpeg in Docker container
**Input:** Extracted WAV
**Output:** 16kHz mono pcm_s16le WAV

**Container command:**
```bash
docker exec duix-avatar-tts sh -c \
  "ffmpeg -i /code/data/temp.wav -ar 16000 -ac 1 -c:a pcm_s16le -y /code/data/origin_audio/format_temp.wav"
```

**Purpose:**
- Ensure exact format (some videos have different sample rates)
- Prepare for RNNoise (requires specific format)

#### Step 1.2: Noise Reduction

**Tool:** RNNoise (`rnnoise_new` in Docker container)
**Input:** Formatted WAV (pcm_s16le)
**Output:** Denoised WAV (pcm_f32le)

**Container command:**
```bash
docker exec duix-avatar-tts rnnoise_new \
  /code/data/origin_audio/format_temp.wav \
  /code/data/origin_audio/denoise_temp.wav
```

**About RNNoise:**
- Professional-grade noise reduction
- Uses deep learning (Recurrent Neural Network)
- Specifically designed for speech
- Changes output format to pcm_f32le (requires re-formatting)

#### Step 1.3: Re-format

**Tool:** ffmpeg in Docker container
**Input:** Denoised WAV (pcm_f32le)
**Output:** Final WAV (pcm_s16le)

**Container command:**
```bash
docker exec duix-avatar-tts sh -c \
  "ffmpeg -i /code/data/origin_audio/denoise_temp.wav -ar 16000 -ac 1 -c:a pcm_s16le -y /code/data/origin_audio/format_denoise_temp.wav"
```

**Purpose:**
- Convert back to pcm_s16le (required by TTS)
- Ensure consistent format for all reference audios

#### Step 2: Transcription

**Tool:** faster-whisper (local Python)
**Input:** Final processed WAV
**Output:** Transcribed text

**Code:**
```python
from faster_whisper import WhisperModel

model = WhisperModel(model_size, device="cpu", compute_type="int8")
segments, info = model.transcribe(audio_path, language=None)
text = " ".join([segment.text for segment in segments])
```

**Whisper Models:**

| Model | Speed | Accuracy | RAM | Best For |
|-------|-------|----------|-----|----------|
| tiny  | Fastest | Lowest | ~1GB | Quick testing |
| base  | Fast | Good | ~1.5GB | **Default/Recommended** |
| small | Medium | Better | ~2GB | High quality |
| medium | Slow | Great | ~5GB | Best quality |
| large | Slowest | Best | ~10GB | Critical accuracy |

#### Step 3: Copy to Custom Directory (Optional)

**Tool:** Python shutil
**Action:** Copy audio + text + summary JSON to custom location

**Code:**
```python
shutil.copy2(audio_file, custom_audio)
shutil.copy2(txt_file, custom_txt)
```

---

## Path Handling

### Input Paths

**MP4/Video can be anywhere:**
- `C:\Users\...\Downloads\video.mp4`
- `D:\videos\sample.mp4`
- `\\network\share\video.mp4`

### Processing Paths

**Temporary extraction:** `D:/duix_avatar_data/voice/data/temp_extract_<timestamp>.wav`
- Automatically cleaned up after processing

**Intermediate files (in container):**
- Format: `/code/data/origin_audio/format_<timestamp>.wav`
- Denoise: `/code/data/origin_audio/denoise_<timestamp>.wav`

### Output Paths

**Default location:** `D:/duix_avatar_data/voice/data/origin_audio/`
- Accessible from both Windows and Docker container

**Custom location:** Anywhere you specify (3rd parameter)
- Files are copied here after processing
- Original files remain in default location (required for TTS)

### Path Conversions

The script automatically handles path conversions:

**Windows → Container:**
```
D:/duix_avatar_data/voice/data/file.wav → /code/data/file.wav
d:\duix_avatar_data\voice\data\file.wav → /code/data/file.wav
```

**Container → Windows:**
```
/code/data/origin_audio/file.wav → D:\duix_avatar_data\voice\data\origin_audio\file.wav
```

---

## Troubleshooting

### Error: FFmpeg not found

**Symptom:**
```
Error: FFmpeg not found in PATH or resources folder
```

**Cause:** FFmpeg not in PATH or resources folder

**Solution:**
1. Check if FFmpeg exists in `resources/ffmpeg/win-amd64/bin/ffmpeg.exe`
2. Or install FFmpeg system-wide and add to PATH
3. Or download FFmpeg and place in resources folder

### Error: faster-whisper not installed

**Symptom:**
```
Error: faster-whisper not installed. Install with: pip install faster-whisper
```

**Cause:** faster-whisper package not installed

**Solution:**
```bash
pip install faster-whisper
```

### Error: Docker container not accessible

**Symptom:**
```
Error formatting: ... connection refused
```

**Cause:** `duix-avatar-tts` container not running

**Solution:**
```bash
# Check if container is running
docker ps | grep duix-avatar-tts

# Start container if needed
docker start duix-avatar-tts
```

### Error: rnnoise_new command not found

**Symptom:**
```
Error denoising: rnnoise_new: not found
```

**Cause:** RNNoise not installed in container or wrong container

**Solution:**
- Ensure using the correct `duix-avatar-tts` container
- RNNoise is pre-installed in `guiji2025/fish-speech-ziming` image
- Check container image: `docker inspect duix-avatar-tts | grep Image`

### Error: Permission denied on output directory

**Symptom:**
```
PermissionError: [Errno 13] Permission denied
```

**Cause:** Output directory doesn't exist or no write permissions

**Solution:**
```bash
# Create directory manually with proper permissions
mkdir -p D:/duix_avatar_data/voice/data/origin_audio

# On Windows: Right-click folder → Properties → Security → ensure write permissions
```

### Transcription is inaccurate

**Issue:** Whisper transcription has errors

**Solutions:**
1. Use a larger Whisper model: `medium` or `large`
2. Ensure audio quality is good (clear speech, minimal background noise)
3. Manually edit the `.txt` file to correct errors
4. Use longer audio clips (20-30 seconds) for better context

**Note:** Always verify transcription accuracy before using as reference text!

---

## Performance

### Processing Time Estimates

For a **30-second video**:
- Audio extraction: ~1 second
- Format conversion: ~0.5 seconds
- RNNoise denoising: ~1 second
- Re-format: ~0.5 seconds
- Transcription (base model): ~5-10 seconds
- Copy to custom dir: <1 second
- **Total: ~10-15 seconds**

### Optimization Tips

1. **Use appropriate Whisper model:**
   - Testing: `tiny` (~2-3 seconds)
   - Production: `base` (~5-10 seconds) - **recommended**
   - High quality: `medium` (~15-30 seconds)

2. **Batch processing:**
   - Process multiple files sequentially
   - Whisper model loads once and caches

3. **Storage:**
   - Processed WAV: ~441KB for 30 seconds
   - Original files in mounted directory count toward disk quota
   - Custom copies don't affect Docker storage

---

## Best Practices

### Recording Quality

- **Clear audio**: Minimal background noise (RNNoise helps but isn't magic)
- **Consistent voice**: Same speaking style, volume, tone
- **Duration**: 20-30 seconds ideal (not too short, not too long)
- **Content**: Natural speech, complete sentences, avoid music/effects

### Reference Audio Selection

- **Use 2-3 diverse samples** for better voice cloning
- Include different **tones/emotions** if needed in final output
- Ensure **good audio quality** (denoising improves but can't fix extremely bad audio)
- Use **multiple clips** from same speaker for consistency

### Transcription Verification

- **Always review** the generated `.txt` file
- **Fix any errors** before using as reference text
- Accurate reference text **significantly improves** TTS quality
- Keep punctuation natural

### Organization

- Use **custom output directories** to organize by:
  - Speaker: `C:/references/speaker_name/`
  - Project: `C:/projects/project_name/references/`
  - Date: `C:/references/2025-11/`
- Keep **summary JSON** files for easy reference
- **Name source files** descriptively before processing

---

## Common Workflows

### Workflow 1: Single Speaker, Single Reference

```bash
# Generate reference audio
python scripts/generate_reference_audio.py \
  "C:\Downloads\speaker_sample.mp4" \
  base \
  "C:\references\john"

# Use for TTS
python scripts/generate_from_text.py \
  "New text to synthesize" \
  /code/data/temp/avatar.mp4 \
  "/code/data/origin_audio/format_denoise_xxx.wav" \
  "Original transcribed text"
```

### Workflow 2: Single Speaker, Multiple References

```bash
# Generate multiple reference audios
python scripts/generate_reference_audio.py clip1.mp4 base "C:\references\john"
python scripts/generate_reference_audio.py clip2.mp4 base "C:\references\john"

# Combine for better quality
python scripts/generate_from_text.py \
  "New text" \
  /code/data/temp/avatar.mp4 \
  "/code/data/origin_audio/ref1.wav|||/code/data/origin_audio/ref2.wav" \
  "Text from clip1|||Text from clip2"
```

### Workflow 3: Multiple Speakers

```bash
# Process each speaker separately
python scripts/generate_reference_audio.py alice.mp4 base "C:\refs\alice"
python scripts/generate_reference_audio.py bob.mp4 base "C:\refs\bob"

# Use appropriate reference for each generation
python scripts/generate_from_text.py "Alice text" avatar.mp4 alice_ref.wav "Alice ref text"
python scripts/generate_from_text.py "Bob text" avatar.mp4 bob_ref.wav "Bob ref text"
```

### Workflow 4: Batch Processing

```bash
# Windows PowerShell
Get-ChildItem "C:\Videos\*.mp4" | ForEach-Object {
    python scripts/generate_reference_audio.py $_.FullName base "C:\references"
}

# Linux/Git Bash
for file in /c/Videos/*.mp4; do
    python scripts/generate_reference_audio.py "$file" base "C:/references"
done
```

---

## Summary

The `generate_reference_audio.py` script provides a robust, reliable way to create reference audio for voice cloning:

✓ **Simple**: One command to process any MP4/video
✓ **Flexible**: Input files can be anywhere, output to custom locations
✓ **Reliable**: Avoids API bugs and failures
✓ **Professional**: RNNoise denoising for clean audio
✓ **Accurate**: faster-whisper ASR for quality transcriptions
✓ **Complete**: Audio + transcription + summary in one step
✓ **Ready to use**: Output immediately compatible with TTS

For questions or issues, check the troubleshooting section or review the script source code at `scripts/generate_reference_audio.py`.
