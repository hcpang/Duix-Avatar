# CLAUDE.md - Duix.Avatar Development Guide

## Project Overview

**Duix.Avatar** is an open-source AI avatar toolkit for offline video generation and digital human cloning. The project enables users to:
- Clone appearance and voice to create realistic digital avatars
- Generate videos driven by text or voice input
- Add accurate word-level subtitles with Whisper ASR
- Operate completely offline to protect privacy

**Core Technologies:**
- Voice cloning and TTS (Text-to-Speech)
- Automatic Speech Recognition (Whisper ASR)
- Computer vision for facial recognition and lip-sync
- Docker-based microservices architecture

**Official Website:** [www.duix.com](http://www.duix.com)

---

## Project Structure

```
Duix-Avatar/
├── scripts/                           # Python utility scripts
│   ├── add_subtitles.py              # Subtitle generation with Whisper ASR
│   ├── subtitle_utils.py             # Shared subtitle utilities
│   ├── generate_from_text.py         # End-to-end video generation from text
│   ├── generate_reference_audio.py   # Reference audio generation for voice cloning
│   ├── revoice_notebooklm.py         # NotebookLM video revoicing workflow
│   ├── extract_slides.py             # Extract slides from video
│   ├── regenerate_slide_video.py     # Regenerate video with new audio
│   ├── overlay_avatar_pip.py         # PIP avatar overlay
│   ├── ffmpeg_utils.py               # Shared FFmpeg utilities
│   └── test_api.py                   # API testing utilities
├── journals/                          # Development session documentation
│   └── YYYY-MM-DD-{feature}.md
├── documentation/                     # Additional docs
│   ├── REFERENCE_AUDIO_GUIDE.md      # Reference audio generation guide
│   └── NOTEBOOKLM_REVOICING.md       # NotebookLM revoicing workflow
├── inputs/                            # Input files (videos, scripts, audio)
├── outputs/                           # Generated output files
├── AVATARS.md                         # Avatar configurations
├── JOURNALING-GUIDE.md               # Journal writing requirements
└── API_USAGE.md                      # API documentation
```

---

## Key Files and Their Purposes

### Python Scripts (`scripts/`)

#### `add_subtitles.py`
Generates accurate word-level subtitles using Whisper ASR.

**Key Features:**
- Word-level timestamp matching with user's original text
- Multi-word fallback matching (tries up to 5 words)
- Word-based position estimation to prevent matching common words too early
- Subtitle overlap prevention (50ms gaps)
- Fuzzy matching with Levenshtein distance

**Usage:**
```bash
python scripts/add_subtitles.py VIDEO_PATH TEXT_FILE \
  --audio AUDIO_PATH \
  --burn \
  --font-size 28 \
  --color yellow
```

#### `subtitle_utils.py`
Shared utilities for subtitle generation (created 2025-11-14, updated 2025-11-16).

**Functions:**
- `split_into_sentences(text)` - Sentence splitting by punctuation
- `split_into_chunks(sentence, max_chars=60)` - Chunk splitting at natural breaks
- Global alignment with Needleman-Wunsch algorithm for accurate word matching

**Critical Implementation Detail:**
Uses global alignment (Needleman-Wunsch) to match user's original text with Whisper transcription, achieving 98%+ word alignment accuracy.

#### `generate_from_text.py`
End-to-end pipeline for generating avatar videos from text.

**Workflow:**
1. Synthesize audio from text using TTS API
2. Submit video generation job
3. Poll for completion
4. Return video path

**API Endpoints:**
- TTS: `http://127.0.0.1:18180/v1/invoke`
- Video Submit: `http://127.0.0.1:8383/easy/submit`
- Video Query: `http://127.0.0.1:8383/easy/query`

#### `generate_reference_audio.py`
Complete pipeline for creating reference audio from MP4/video files for voice cloning (created 2025-11-16).

**Key Features:**
- Accepts MP4/video from any Windows path
- Extracts and processes audio with RNNoise denoising
- Transcribes with faster-whisper ASR
- Optional custom output directory

**Workflow:**
1. Extract audio to WAV (local ffmpeg)
2. Process audio: format → denoise (RNNoise) → re-format (Docker)
3. Transcribe with faster-whisper
4. Optionally copy to custom directory

**Usage:**
```bash
python scripts/generate_reference_audio.py input.mp4 [whisper_model] [output_dir]
```

**See:** `documentation/REFERENCE_AUDIO_GUIDE.md` for complete documentation

#### `ffmpeg_utils.py`
Shared utilities for FFmpeg tools (created 2025-11-16).

**Functions:**
- `find_ffmpeg_tool(tool_name)` - Find any FFmpeg tool (ffmpeg, ffprobe, etc.)
- `find_ffmpeg()` - Find ffmpeg executable
- `find_ffprobe()` - Find ffprobe executable

**Used by:** `add_subtitles.py`, `concatenate_segments.py`, `generate_reference_audio.py`

**Purpose:** Eliminates code duplication by centralizing FFmpeg path finding logic. Checks both system PATH and project resources folder.

---

## Development Conventions

### File Organization

1. **Test files belong in `scripts/`** alongside the code they test
   - Example: `scripts/test_subtitle_matching.py`, `scripts/test_api.py`
   - DO NOT place test files in the root directory

2. **Shared utilities go in dedicated modules**
   - Example: `scripts/subtitle_utils.py` eliminates code duplication
   - Import from same directory when co-located

3. **Data storage location**
   - Default: `D:/duix_avatar_data/face2face/temp/`
   - Videos, audio files, SRT subtitles stored here

### Code Quality Standards

1. **Zero Code Duplication**
   - Proactively refactor shared logic into utility modules
   - Check both production code AND test files for duplication
   - Don't wait for user to ask - refactor immediately

   **Best Practice Workflow:**
   ```bash
   # Step 1: When creating new utility code, first check for existing similar code
   grep -r "def function_name" scripts/

   # Step 2: If duplication exists, create shared utility module
   # Example: scripts/ffmpeg_utils.py, scripts/subtitle_utils.py

   # Step 3: Search for ALL instances of the duplicated pattern
   grep -r "def find_ffmpeg" scripts/

   # Step 4: Refactor ALL scripts that have the duplication
   # Don't just refactor the new script - update all existing ones too

   # Step 5: Verify no duplication remains
   grep -r "def find_ffmpeg" scripts/
   # Should only show the utility module
   ```

   **Example:** When creating `ffmpeg_utils.py` (2025-11-16):
   - Found `add_subtitles.py`, `concatenate_segments.py` both had `find_ffmpeg()`
   - Refactored all 3 scripts to use shared utility
   - Eliminated 55 lines of duplicate code

2. **Complete Refactoring**
   - When refactoring, extract ALL duplicated logic, not just obvious parts
   - Includes: text processing, data structures, utility functions
   - **Search the entire codebase** - use grep to find all instances
   - Update imports in all affected files
   - Verify with grep that no duplication remains

3. **UTF-8 Encoding**
   All Python scripts must handle Windows encoding properly:
   ```python
   import sys
   import io

   if sys.platform == 'win32':
       sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
       sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
   ```

### Journaling Requirements

Every development session MUST produce a journal in `journals/YYYY-MM-DD-{feature}.md`.

**Required Sections:**
1. **Session Metadata** - Date, model, files modified/created (with line numbers)
2. **Problem Statement** - What needed to be solved and why
3. **Solution Implementation** - Technical approach with code examples
4. **Testing/Validation** - How solution was verified
5. **Development Learnings** - ONLY mistakes corrected by user (with quotes)

**See:** `JOURNALING-GUIDE.md` for complete requirements.

**Critical Rule:** Development Learnings section documents ONLY mistakes that were corrected by the user during the session. Do NOT include general patterns, things that went well, or architectural insights.

---

## Docker Services

The project uses two main Docker containers:

1. **TTS Service** - `guiji2025/fish-speech-ziming`
   - Text-to-Speech with voice cloning
   - Port: 18180

2. **Video Generation** - `guiji2025/duix.avatar`
   - Avatar video synthesis
   - Port: 8383

**Note:** ASR uses faster-whisper locally (no Docker container needed)

---

## Common Workflows

### Generate Video from Text

```bash
python scripts/generate_from_text.py script.txt [video_template] [reference_audio] [reference_text]
```

### Add Subtitles to Video

```bash
python scripts/add_subtitles.py video.mp4 script.txt --audio audio.wav --burn --font-size 28 --color yellow
```

### Revoice NotebookLM Video

```bash
python scripts/revoice_notebooklm.py video.mp4 script.txt \
  --reference-audio "path/to/reference.wav" \
  --reference-text "reference transcription"
```

**See:** `documentation/NOTEBOOKLM_REVOICING.md` for complete workflow

---

## Critical Implementation Patterns

### Subtitle Word Matching Algorithm

**Problem:** Need accurate word-level timestamp matching between user's text and Whisper transcription.

**Solution:** Global alignment using Needleman-Wunsch algorithm
- Matches user's original text word-by-word with Whisper's transcription
- Handles insertions, deletions, and substitutions
- Achieves 98%+ word alignment accuracy
- Prevents common word mismatches through global optimization

**Implementation:** See `scripts/add_subtitles.py` and `scripts/subtitle_utils.py`

### Subtitle Overlap Prevention

**Problem:** End times calculated independently cause overlapping subtitles.

**Solution:** Post-process to cap each segment 50ms before next segment starts
```python
for i in range(len(subtitle_segments) - 1):
    next_start = subtitle_segments[i + 1]['start']
    if subtitle_segments[i]['end'] > next_start:
        subtitle_segments[i]['end'] = max(
            subtitle_segments[i]['start'] + 0.1,
            next_start - 0.05
        )
```

---

## Testing

### Running Tests

Tests are located in `scripts/` alongside the code they test.

**API Testing:**
- File: `scripts/test_api.py`
- Tests TTS and video generation APIs

---

## Common Pitfalls

### 1. Code Duplication
**Mistake:** Leaving duplicated logic between production code and tests.
**Fix:** Extract to shared utility modules immediately.

### 2. Incomplete Refactoring
**Mistake:** Only refactoring obvious logic, missing text processing/utilities.
**Fix:** Search for ALL instances of duplication, not just main logic.

### 3. Improper File Organization
**Mistake:** Placing test files in root instead of scripts/.
**Fix:** Check existing project structure (e.g., `scripts/test_api.py`) before creating files.

### 4. Low Subtitle Alignment
**Mistake:** Poor word alignment between user text and Whisper transcription.
**Fix:** Use global alignment (Needleman-Wunsch) for accurate word matching. Achieves 98%+ alignment.

---

## Git Commit Conventions

**Commit Message Format:**
```
Brief imperative title

- Bullet points describing changes
- Reference file paths and line numbers for key changes
- Include testing/validation results

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

**Example:**
```
Refactor subtitle matching with word-level position estimation

- Created scripts/subtitle_utils.py with shared utilities
- Implemented word-based position estimation (skip N/2 words)
- Added subtitle overlap prevention (50ms gaps)
- Achieved 100% match rate validation (26/26 chunks)

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

---

## Hardware Requirements

**Recommended:**
- CPU: 13th Gen Intel Core i5-13400F or better
- RAM: 32GB
- GPU: NVIDIA RTX 4070 or better
- Storage:
  - C Drive: 100GB+ for Docker images
  - D Drive: 30GB+ for data

**Software:**
- Windows 10 19042.1526 or higher / Ubuntu 22.04
- Docker with WSL2 (Windows)
- Node.js 18
- NVIDIA drivers for GPU acceleration

---

## API Reference

See `API_USAGE.md` for detailed API documentation.

**Quick Reference:**
- TTS: POST to `http://127.0.0.1:18180/v1/invoke`
- Video Submit: POST to `http://127.0.0.1:8383/easy/submit`
- Video Query: GET `http://127.0.0.1:8383/easy/query?task_id={id}`

---

## Support

- GitHub Issues: Report bugs and feature requests
- Official Website: [www.duix.com](http://www.duix.com)
- License: See `LICENSE` file

---

## For Claude Sessions

**Before Starting Work:**
1. Read relevant journal entries in `journals/` to understand recent changes
2. Check `JOURNALING-GUIDE.md` for documentation requirements
3. Review this CLAUDE.md for project conventions

**During Development:**
1. Follow file organization conventions (tests in scripts/)
2. Proactively refactor duplicate code - don't wait to be asked
3. Use established patterns (UTF-8 encoding, word-based matching, etc.)
4. Reference specific file paths and line numbers in communications

**After Completion:**
1. Write journal in `journals/YYYY-MM-DD-{feature}.md`
2. Include only user-corrected mistakes in Development Learnings
3. Create git commit with proper format
4. Update this CLAUDE.md if new conventions were established
