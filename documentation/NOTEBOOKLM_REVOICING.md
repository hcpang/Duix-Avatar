# NotebookLM Video Revoicing and PIP Avatar Overlay

This guide explains how to revoice NotebookLM-generated videos with custom voice cloning and add picture-in-picture (PIP) avatar overlays.

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Workflow Steps](#workflow-steps)
4. [PIP Avatar Overlay](#pip-avatar-overlay)
5. [Complete Example](#complete-example)
6. [Troubleshooting](#troubleshooting)

---

## Overview

The NotebookLM revoicing workflow allows you to:
- Replace the original audio in a NotebookLM video with custom TTS voice cloning
- Extract slides from the video and match them to your script
- Generate word-level subtitles with accurate timing
- Add picture-in-picture avatar overlays

**Complete Pipeline:**
```
NotebookLM MP4 → Extract Slides → Transcribe → Match Slides → TTS → Regenerate Video → Add Subtitles → PIP Overlay
```

---

## Prerequisites

### 1. Docker Services Running

Ensure the required Docker services are running:

```bash
# Check Docker containers
docker ps

# You should see:
# - guiji2025/fish-speech-ziming (TTS service, port 18180)
# - guiji2025/duix.avatar (Video generation, port 8383)
```

**Note:** The scripts use faster-whisper for ASR, which runs locally without Docker.

### 2. Required Files

- **Input Video**: NotebookLM-generated MP4 (e.g., `inputs/The_Five_Tenets_of_Trading.mp4`)
- **TTS Script**: Text file with your narration (e.g., `inputs/tenets_for_trading.txt`)
- **Reference Audio**: WAV file for voice cloning (see [Reference Audio Generation](#reference-audio-generation))
- **Reference Text**: Transcription of reference audio
- **Avatar Video** (optional for PIP): Small resolution video template

### 3. Reference Audio Generation

Generate reference audio for voice cloning:

```bash
# From any audio/video file (MP4, M4A, WAV)
python scripts/generate_reference_audio.py inputs/jimmy2.m4a base

# Output:
# - Audio: D:/duix_avatar_data/voice/data/origin_audio/format_denoise_temp_extract_XXXXX.wav
# - Text: D:/duix_avatar_data/voice/data/origin_audio/format_denoise_temp_extract_XXXXX.txt
```

**Important:** After generation, manually correct the transcription text file to ensure accurate voice cloning.

---

## Workflow Steps

### Option 1: Automated Workflow (Recommended)

Use the wrapper script to run all 6 steps automatically:

```bash
python scripts/revoice_notebooklm.py \
  inputs/The_Five_Tenets_of_Trading.mp4 \
  inputs/tenets_for_trading.txt \
  --reference-audio "D:/duix_avatar_data/voice/data/origin_audio/format_denoise_temp_extract_20251117220215646.wav" \
  --reference-text "In their most recent paper, researchers at DeepMind dissect the conventional wisdom that more complex models equal better performance. The company has uncovered a previously untapped method of scaling large language models."
```

**Steps executed automatically:**
1. Extract unique slides from video
2. Transcribe original audio with faster-whisper
3. Match slides to transcription
4. Generate TTS audio with voice cloning
5. Regenerate video with slides synced to TTS
6. Add word-level subtitles

**Output files:**
- `outputs/The_Five_Tenets_of_Trading/final_video.mp4` (no subtitles)
- `outputs/The_Five_Tenets_of_Trading/final_video_subtitled.mp4` (with subtitles)
- `outputs/The_Five_Tenets_of_Trading/tts/audio.wav` (TTS audio)
- `outputs/The_Five_Tenets_of_Trading/slides/` (extracted slides)

### Option 2: Manual Step-by-Step

#### Step 1: Extract Slides

```bash
python scripts/extract_slides.py \
  inputs/The_Five_Tenets_of_Trading.mp4 \
  outputs/The_Five_Tenets_of_Trading/slides
```

**Output:** 23 unique slides with timestamps

#### Step 2: Transcribe Original Audio

```bash
python scripts/transcribe_audio.py \
  inputs/The_Five_Tenets_of_Trading.mp4 \
  base \
  outputs/The_Five_Tenets_of_Trading/asr/transcription
```

**Output:**
- `transcription.srt` (subtitle file)
- `transcription.txt` (plain text)

**Note:** Uses faster-whisper locally (model options: `tiny`, `base`, `small`, `medium`, `large`)

#### Step 3: Match Slides to Text

```bash
python scripts/match_slides_to_srt.py \
  outputs/The_Five_Tenets_of_Trading/slides/slides_timestamps.txt \
  outputs/The_Five_Tenets_of_Trading/asr/transcription.srt \
  outputs/The_Five_Tenets_of_Trading/slides/slides_with_text.txt
```

**Output:** Slide-to-text mapping file

#### Step 4: Generate TTS Audio

```bash
python scripts/generate_from_text.py \
  inputs/tenets_for_trading.txt \
  - \
  /code/data/origin_audio/format_denoise_temp_extract_20251117220215646.wav \
  "In their most recent paper, researchers at DeepMind dissect the conventional wisdom that more complex models equal better performance. The company has uncovered a previously untapped method of scaling large language models."
```

**Note:** Use `-` for video path when generating audio only.

**Output:** `D:/duix_avatar_data/face2face/temp/XXXXX.wav`

#### Step 5: Regenerate Video

```bash
python scripts/regenerate_slide_video.py \
  outputs/The_Five_Tenets_of_Trading/slides/slides_with_text.txt \
  outputs/The_Five_Tenets_of_Trading/tts/audio.wav \
  outputs/The_Five_Tenets_of_Trading/final_video.mp4
```

**Output:** Video with slides synced to new TTS audio

#### Step 6: Add Subtitles

```bash
python scripts/add_subtitles.py \
  outputs/The_Five_Tenets_of_Trading/final_video.mp4 \
  inputs/tenets_for_trading.txt \
  --audio outputs/The_Five_Tenets_of_Trading/tts/audio.wav \
  --burn \
  --font-size 24 \
  --color yellow
```

**Output:** `outputs/The_Five_Tenets_of_Trading/final_video_subtitled.mp4`

---

## PIP Avatar Overlay

Add a picture-in-picture avatar to your revoiced video.

### Step 1: Prepare Small Avatar Video

Create a reduced-resolution version of your avatar video for PIP:

```bash
# Reduce resolution to 384x288 (recommended for PIP)
python scripts/reduce_video_resolution.py \
  inputs/Jimmy2.mp4 \
  inputs/Jimmy2_pip_small.mp4 \
  384 288
```

**Result:** 1440x1080 (11.30 MB) → 384x288 (0.30 MB)

### Step 2: Generate Avatar Video from TTS Audio

```bash
python scripts/generate_avatar_from_audio.py \
  "D:/duix_avatar_data/face2face/temp/5c4b008e-fd42-4f44-9cf6-360adba26784.wav" \
  "inputs/Jimmy2_pip_small.mp4"
```

**Input:**
- TTS audio from Step 4 of revoicing workflow
- Small resolution avatar video template

**Output:** `D:/duix_avatar_data/face2face/temp/XXXXX-r.mp4` (384x288)

**Duration:** Matches TTS audio length (~2.5 minutes)

### Step 3: Overlay Avatar on Video

```bash
python scripts/overlay_avatar_pip.py \
  "outputs/The_Five_Tenets_of_Trading/final_video_subtitled.mp4" \
  "D:/duix_avatar_data/face2face/temp/346dc037-27aa-40a2-936b-64f9cdf495ca-r.mp4" \
  "outputs/The_Five_Tenets_of_Trading/final_video_pip_jimmy2.mp4"
```

**Result:**
- Base video: 1920x1080 @ 25fps (slide video with subtitles)
- Avatar overlay: 384x288 @ 30fps (positioned at top-right corner)
- Output size: ~9 MB

---

## Complete Example

### Example: "The Five Tenets of Trading" with Jimmy2 Voice

#### 1. Prepare Reference Audio

```bash
# Generate reference audio from jimmy2.m4a
python scripts/generate_reference_audio.py inputs/jimmy2.m4a base

# Output:
# Audio: D:/duix_avatar_data/voice/data/origin_audio/format_denoise_temp_extract_20251117220215646.wav
# Text: D:/duix_avatar_data/voice/data/origin_audio/format_denoise_temp_extract_20251117220215646.txt

# Manually correct the transcription:
# "In their most recent paper, researchers at DeepMind dissect the conventional
# wisdom that more complex models equal better performance. The company has
# uncovered a previously untapped method of scaling large language models."
```

#### 2. Run Automated Workflow

```bash
python scripts/revoice_notebooklm.py \
  inputs/The_Five_Tenets_of_Trading.mp4 \
  inputs/tenets_for_trading.txt \
  --reference-audio "D:/duix_avatar_data/voice/data/origin_audio/format_denoise_temp_extract_20251117220215646.wav" \
  --reference-text "In their most recent paper, researchers at DeepMind dissect the conventional wisdom that more complex models equal better performance. The company has uncovered a previously untapped method of scaling large language models."
```

**Results:**
- ✅ Step 1: Extracted 23 unique slides
- ✅ Step 2: Transcribed 377 words (faster-whisper)
- ✅ Step 3: Matched 384 words to 23 slides
- ✅ Step 4: Generated TTS audio with Jimmy2 voice (2121 characters)
- ✅ Step 5: Regenerated video (151 seconds, 97.4% word alignment)
- ✅ Step 6: Added 69 subtitle segments (98.7% word alignment)

**Output:** `outputs/The_Five_Tenets_of_Trading/final_video_subtitled.mp4`

#### 3. Add PIP Avatar Overlay

```bash
# 3a. Create small avatar video
python scripts/reduce_video_resolution.py \
  inputs/Jimmy2.mp4 \
  inputs/Jimmy2_pip_small.mp4 \
  384 288

# 3b. Generate avatar video from TTS audio
python scripts/generate_avatar_from_audio.py \
  "D:/duix_avatar_data/face2face/temp/5c4b008e-fd42-4f44-9cf6-360adba26784.wav" \
  "inputs/Jimmy2_pip_small.mp4"

# 3c. Overlay avatar on video
python scripts/overlay_avatar_pip.py \
  "outputs/The_Five_Tenets_of_Trading/final_video_subtitled.mp4" \
  "D:/duix_avatar_data/face2face/temp/346dc037-27aa-40a2-936b-64f9cdf495ca-r.mp4" \
  "outputs/The_Five_Tenets_of_Trading/final_video_pip_jimmy2.mp4"
```

**Final Output:** `outputs/The_Five_Tenets_of_Trading/final_video_pip_jimmy2.mp4`
- Duration: 2:31
- Resolution: 1920x1080 with 384x288 PIP overlay
- Size: 9.01 MB

---

## Troubleshooting

### Audio Duration Mismatch Error

**Error:** "三次获取音频时长失败" (Failed to get audio duration three times)

**Solution:** Use Windows path instead of Docker path when calling `generate_avatar_from_audio.py`:

```bash
# ✗ Wrong (Docker path)
python scripts/generate_avatar_from_audio.py \
  "/code/data/temp/audio.wav" \
  "inputs/jimmy_pip_small.mp4"

# ✓ Correct (Windows path)
python scripts/generate_avatar_from_audio.py \
  "D:/duix_avatar_data/face2face/temp/5c4b008e-fd42-4f44-9cf6-360adba26784.wav" \
  "inputs/jimmy_pip_small.mp4"
```

### Low Subtitle Alignment

If word alignment is below 95%, check:
1. TTS script matches the original video content closely
2. Reference text is accurately transcribed
3. Whisper model is appropriate (use `base` or higher)

### Video Generation Timeout

For long videos (>10 minutes), the timeout is set to 3 hours by default in `scripts/avatar_video_utils.py:18`:

```python
def generate_video(audio_path, video_path, max_wait_time=10800):  # 3 hours
```

### Docker Services Not Running

```bash
# Check running containers
docker ps

# Start TTS service
docker start <tts-container-id>

# Start video generation service
docker start <video-container-id>
```

---

## File Structure Reference

```
Duix-Avatar/
├── inputs/
│   ├── The_Five_Tenets_of_Trading.mp4    # Original NotebookLM video
│   ├── tenets_for_trading.txt             # TTS script
│   ├── Jimmy2.mp4                         # Avatar video (original)
│   └── Jimmy2_pip_small.mp4               # Avatar video (384x288)
│
├── outputs/
│   └── The_Five_Tenets_of_Trading/
│       ├── final_video.mp4                # Revoiced video (no subtitles)
│       ├── final_video_subtitled.mp4      # Revoiced video (with subtitles)
│       ├── final_video_pip_jimmy2.mp4     # Final video with PIP overlay
│       ├── slides/                        # Extracted slides
│       │   ├── slide_001.png ... slide_023.png
│       │   ├── slides_timestamps.txt
│       │   └── slides_with_text.txt
│       ├── asr/                           # Transcriptions
│       │   ├── transcription.srt
│       │   └── transcription.txt
│       └── tts/                           # TTS audio
│           └── audio.wav
│
└── scripts/
    ├── revoice_notebooklm.py              # Automated workflow wrapper
    ├── extract_slides.py                  # Step 1: Extract slides
    ├── transcribe_audio.py                # Step 2: Transcribe audio (faster-whisper)
    ├── match_slides_to_srt.py             # Step 3: Match slides to text
    ├── generate_from_text.py              # Step 4: Generate TTS
    ├── regenerate_slide_video.py          # Step 5: Regenerate video
    ├── add_subtitles.py                   # Step 6: Add subtitles
    ├── generate_reference_audio.py        # Generate reference audio
    ├── reduce_video_resolution.py         # Reduce video resolution
    ├── generate_avatar_from_audio.py      # Generate avatar video
    └── overlay_avatar_pip.py              # PIP overlay
```

---

## Related Documentation

- **Reference Audio Guide:** `documentation/REFERENCE_AUDIO_GUIDE.md`
- **Avatar Configurations:** `AVATARS.md`
- **API Usage:** `API_USAGE.md`
- **Journaling Guide:** `JOURNALING-GUIDE.md`

---

## Summary

**Complete NotebookLM Revoicing + PIP Workflow:**

1. Generate reference audio from source media
2. Correct reference transcription text
3. Run automated revoicing workflow (uses faster-whisper for ASR)
4. Create small resolution avatar video
5. Generate avatar video from TTS audio
6. Overlay avatar as PIP on final video

**Total processing time:** ~15-30 minutes for a 2.5-minute video (depending on hardware)

**Key benefits:**
- Complete control over voice and narration
- Professional subtitles with 98%+ word alignment
- Picture-in-picture avatar overlay for engagement
- Fully offline processing for privacy
- No Docker ASR service required (uses faster-whisper locally)
