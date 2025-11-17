# Reference Audio Generation Script Implementation

**Date:** 2025-11-16
**Model:** Claude Sonnet 4.5 (claude-sonnet-4-5-20250929)
**Feature:** Reference audio generation with RNNoise denoising and faster-whisper transcription

## Files Modified

- `scripts/generate_from_text.py:30,64-72,173,217-236` - Added multi-reference audio support using `|||` separator
- `scripts/add_subtitles.py:17,532-565` - Refactored to use shared `ffmpeg_utils` (removed 33 lines of duplicate code)
- `scripts/concatenate_segments.py:12,22-43` - Refactored to use shared `ffmpeg_utils` (removed 22 lines of duplicate code)

## Files Created

- `scripts/generate_reference_audio.py` - Complete pipeline for MP4/audio → denoised WAV + transcription
- `scripts/ffmpeg_utils.py` - Shared ffmpeg utility functions (eliminates duplication across 3 scripts)
- `documentation/REFERENCE_AUDIO_GUIDE.md` - Comprehensive user documentation
- `journals/2025-11-16-reference-audio-generation.md` - Development session journal

---

## Problem Statement

The user needed a script to process MP4/video files into high-quality reference audio for voice cloning in Duix Avatar's TTS system. The existing TTS API endpoint (`/v1/preprocess_and_tran`) had several issues:

1. **File path limitations**: API expects files in specific container paths
2. **Output inaccessibility**: Processed files saved to `/code/sessions/` which isn't mounted to Windows
3. **ASR failures**: The fun-asr service frequently fails with connection errors ("NoneType object has no attribute 'send'")
4. **Limited functionality**: Cannot specify custom output directories for organization

Additionally, the user wanted to use faster-whisper for ASR instead of fun-asr because fun-asr only works for Chinese language.

---

## Solution Implementation

### Core Approach

Created a standalone Python script that replicates the TTS API's audio processing pipeline locally while avoiding its limitations:

1. **Extract audio** from MP4/video using local ffmpeg (can read from any Windows path)
2. **Process audio** using Docker container:
   - Format to 16kHz mono pcm_s16le
   - Denoise with RNNoise (`rnnoise_new` command)
   - Re-format to pcm_s16le (RNNoise outputs pcm_f32le)
3. **Transcribe** using faster-whisper ASR (local Python)
4. **Optionally copy** to custom output directory

### Key Design Decisions

**1. Hybrid local/Docker approach:**
- Use local ffmpeg for initial extraction (can access any Windows path)
- Use Docker for RNNoise denoising (leverages existing container setup)
- Use local faster-whisper for transcription (more reliable than fun-asr)

**2. Custom output directory support:**
- Processing must happen in mounted directory (`D:/duix_avatar_data/voice/data/`) for Docker access
- Files can be copied to custom location after processing
- Summary JSON includes both original and custom paths
- TTS still uses container paths (required for Docker access)

**3. Refactored shared utilities:**
- Created `scripts/ffmpeg_utils.py` to centralize ffmpeg path finding logic
- Avoids code duplication between scripts
- Checks both system PATH and project resources folder

### Multi-Reference Audio Support

Enhanced `generate_from_text.py` to support multiple reference audios for better voice cloning:

```python
# Modified signature (scripts/generate_from_text.py:30)
def synthesize_audio(text, reference_audios=None, reference_texts=None):

# Join multiple references with ||| (lines 64-72)
if reference_audios and reference_texts:
    tts_params["reference_audio"] = "|||".join(reference_audios)
    tts_params["reference_text"] = "|||".join(reference_texts)
```

Usage:
```bash
python scripts/generate_from_text.py text.txt avatar.mp4 \
  "/code/data/origin_audio/ref1.wav|||/code/data/origin_audio/ref2.wav" \
  "Reference text 1|||Reference text 2"
```

### Audio Processing Pipeline

**Implementation in `scripts/generate_reference_audio.py`:**

**Step 0: Audio Extraction** (lines 144-177)
```python
def extract_audio_to_wav(input_file, output_wav):
    ffmpeg_cmd = find_ffmpeg()
    cmd = [
        ffmpeg_cmd, "-i", input_abs,
        "-vn", "-acodec", "pcm_s16le",
        "-ar", "16000", "-ac", "1", "-y", output_abs
    ]
```
- Uses local ffmpeg (can read from any Windows path)
- Outputs to mounted directory for Docker access

**Step 1: Audio Processing** (lines 38-109)
```python
def process_audio_with_rnnoise(input_wav):
    # 1. Format: 16kHz mono pcm_s16le
    subprocess.run(["docker", "exec", "duix-avatar-tts", "sh", "-c",
        f"ffmpeg -i {container_path} -ar 16000 -ac 1 -c:a pcm_s16le -y {format1_container}"])

    # 2. Denoise with RNNoise
    subprocess.run(["docker", "exec", "duix-avatar-tts",
        "rnnoise_new", format1_container, denoise_container])

    # 3. Re-format (RNNoise outputs pcm_f32le)
    subprocess.run(["docker", "exec", "duix-avatar-tts", "sh", "-c",
        f"ffmpeg -i {denoise_container} -ar 16000 -ac 1 -c:a pcm_s16le -y {final_container}"])
```

**Step 2: Transcription** (lines 110-141)
```python
def transcribe_audio(audio_path, model_size="base"):
    from faster_whisper import WhisperModel
    model = WhisperModel(model_size, device="cpu", compute_type="int8")
    segments, info = model.transcribe(audio_path, language=None)
    text = " ".join([segment.text for segment in segments])
```

**Step 3: Custom Output Directory** (lines 277-319)
```python
if custom_output_dir:
    os.makedirs(custom_output_dir, exist_ok=True)
    shutil.copy2(audio_file, custom_audio)
    shutil.copy2(txt_file, custom_txt)
    # Update summary JSON with custom paths
```

### Additional Refactoring: Eliminating Code Duplication

After initial implementation, user identified that `add_subtitles.py` and `concatenate_segments.py` still had duplicated ffmpeg finding logic. Refactored both scripts to use shared `ffmpeg_utils.py`:

**`scripts/add_subtitles.py:17,532-565`**
- Added import: `from ffmpeg_utils import find_ffmpeg`
- Removed duplicate `find_ffmpeg_tool()` and `find_ffmpeg()` functions (33 lines)

**`scripts/concatenate_segments.py:12,22-43`**
- Added import: `from ffmpeg_utils import find_ffmpeg`
- Removed duplicate `find_ffmpeg()` function (22 lines)

**Result:** All three scripts (`add_subtitles.py`, `concatenate_segments.py`, `generate_reference_audio.py`) now use the shared utility, eliminating 55 lines of duplicate code.

### Investigation: Why API Failed

Through analyzing Docker logs and API code, discovered:

1. **API processing succeeded**: The pipeline (extract → format → denoise → re-format) completed successfully
2. **Real issue**: fun-asr connection failure
   ```
   ERROR - 建立funasr连接异常：[Errno -2] Name or service not known
   ERROR - 'NoneType' object has no attribute 'send'
   ```
3. **File location**: Processed files saved to `/code/sessions/` (not mounted to Windows)
4. **RNNoise works perfectly**: No file destruction issues - the API's `format_wav()` only deletes after successful conversion

---

## Testing/Validation

### Test 1: Basic Processing from Downloads Folder
```bash
python scripts/generate_reference_audio.py "C:\Users\yharm\Downloads\Evan.mp4"
```

**Results:**
- ✓ Extracted audio from arbitrary Windows path
- ✓ Processed with RNNoise (format → denoise → re-format)
- ✓ Transcribed: "Dear Coach Drollman, thank you for teaching me how to snowboard..."
- ✓ Output: `D:/duix_avatar_data/voice/data/origin_audio/format_denoise_temp_extract_20251116203042270.wav`

### Test 2: TTS with Generated Reference Audio
```bash
python scripts/generate_from_text.py \
  "Hello everyone, this is a test of the text to speech system." \
  /code/data/temp/20251113182348159.mp4 \
  "/code/data/origin_audio/format_denoise_temp_extract_20251116203042270.wav" \
  "Dear Coach Drollman, thank you for teaching me..."
```

**Results:**
- ✓ Audio synthesized with Evan's voice cloning
- ✓ Generated: `D:/duix_avatar_data/face2face/temp/186c66e4-8808-462e-9624-7d5163bb5e1b.wav`

### Test 3: Custom Output Directory
```bash
python scripts/generate_reference_audio.py \
  "C:\Users\yharm\Downloads\Evan.mp4" \
  base \
  "C:\Users\yharm\Downloads\references"
```

**Results:**
- ✓ Processing completed in mounted directory
- ✓ Files copied to custom location:
  - `format_denoise_temp_extract_20251116204530569.wav` (441KB)
  - `format_denoise_temp_extract_20251116204530569.txt` (169 bytes)
  - `reference_audio_summary.json` (768 bytes)
- ✓ Summary JSON includes both original and custom paths

---

## Development Learnings

### 1. Don't Duplicate Code - Refactor into Shared Utilities

**Mistake**: Was about to duplicate the ffmpeg path finding logic from `add_subtitles.py` into `generate_reference_audio.py`.

**Your Feedback**: "why are you duplicating code! check how you get the ffmpg in existing scripts, and reuse that functionality or refactor it into a common util"

**Correction**: Created `scripts/ffmpeg_utils.py` with shared functions `find_ffmpeg_tool()`, `find_ffmpeg()`, and `find_ffprobe()`. Updated `generate_reference_audio.py` to import and use this utility.

**Next time**: Before implementing utility functions, always check existing scripts for similar functionality and refactor into a shared module if found. Proactively avoid code duplication.

### 2. Check Existing Dependencies Before Installing New Ones

**Mistake**: Attempted to install `openai-whisper` package when the codebase already uses `faster-whisper`.

**Your Feedback**: "look at the other scripts. we are already using whisper"

**Correction**: Checked `add_subtitles.py` and found it uses `faster-whisper`. Updated `generate_reference_audio.py` to use `WhisperModel` from `faster_whisper` instead of `whisper.load_model()` from `openai-whisper`.

**Next time**: Before installing new dependencies, grep the codebase to check if similar functionality already exists with established packages. Use the same libraries for consistency.

### 3. Don't Create Unnecessary Intermediate Files

**Mistake**: Tried to echo test text to a file before calling `generate_from_text.py` when the script accepts direct text input.

**Your Feedback**: "why do you need to pipe it to a file? just call the script with the text?"

**Correction**: Called the script directly with the text as a command-line argument instead of creating a temporary file.

**Next time**: Review script usage documentation before creating test workflows. Many scripts accept direct input and don't require intermediate files.

### 4. Complete Refactoring Thoroughly - Check All Scripts

**Mistake**: Created `ffmpeg_utils.py` to eliminate duplication, but only refactored `generate_reference_audio.py` while leaving `add_subtitles.py` and `concatenate_segments.py` with the same duplicated code.

**Your Feedback**: "ffmpeg_utils.py - you factored out the logic. but is all the scripts using it. or are they duplicating code?"

**Correction**: Searched for all scripts with `find_ffmpeg` definitions, found `add_subtitles.py` and `concatenate_segments.py` still had duplicates. Refactored both to import from `ffmpeg_utils.py`, removing 55 total lines of duplicate code.

**Next time**: When refactoring to eliminate duplication, search the entire codebase for all instances of the duplicated pattern and refactor them all at once. Use grep to find all occurrences, not just the ones you're immediately aware of.

---

## Implementation Status

✓ **Completed:**
- Created `generate_reference_audio.py` with complete audio processing pipeline
- Supports MP4/video/audio from any Windows path
- RNNoise denoising integration via Docker
- faster-whisper transcription (any Whisper model: tiny, base, small, medium, large)
- Custom output directory support with path tracking
- Multi-reference audio support in `generate_from_text.py`
- Created `ffmpeg_utils.py` for shared utilities and eliminated all code duplication
- Refactored `add_subtitles.py` and `concatenate_segments.py` to use shared utilities (removed 55 lines of duplicate code)
- Comprehensive documentation in `REFERENCE_AUDIO_GUIDE.md`
- Tested end-to-end pipeline with multiple test cases

✓ **Output Files:**
- Processed audio WAV (16kHz mono pcm_s16le, denoised)
- Transcription text file (UTF-8 encoded)
- Summary JSON with container paths, Windows paths, and custom paths

✓ **Validated:**
- Input files can be anywhere on filesystem
- Processing works correctly with Docker RNNoise
- Transcription accuracy with faster-whisper
- TTS voice cloning with generated reference audio
- Custom output directory functionality
