# Global Alignment Algorithm and Complete Podcast Generation Pipeline

**Date:** 2025-11-16
**Claude Model:** claude-sonnet-4-5-20250929
**Feature:** Needleman-Wunsch global alignment + ffprobe support + automated podcast generation with multi-speaker avatars and subtitles

---

## Session Metadata

**Files Modified:**
- `scripts/subtitle_utils.py:84-221` - Replaced sequential matching with Needleman-Wunsch global alignment
- `scripts/add_subtitles.py:12-15, 48-61, 231-296, 527-560` - Global alignment integration + ffprobe support with DRY principle
- `scripts/test_subtitle_matching.py` - Updated tests for global alignment
- `scripts/generate_from_text.py:1` - Minor shebang update

**Files Created (Scripts - 721 lines total):**
- `scripts/generate_podcast_segments.py` (396 lines) - Main automated podcast generation pipeline
- `scripts/concatenate_segments.py` (184 lines) - FFmpeg-based segment concatenation
- `scripts/transcribe_audio.py` (56 lines) - Whisper audio transcription utility
- `scripts/test_tts_asr.py` (85 lines) - TTS/ASR testing tool

**Files Created (Documentation - 751 lines total):**
- `documentation/ADD_SUBTITLES_GUIDE.md` (598 lines) - Comprehensive subtitle script documentation
- `AVATARS.md` (153 lines) - Avatar configuration reference with speaker profiles

**Files Created (Deployment):**
- `deploy/docker-compose-bark.yml` - Bark TTS Docker Compose configuration
- `deploy/bark-tts/` - Bark TTS deployment directory

**Total New Code:** 1,472 lines (scripts + documentation)

---

## Problem Statement

### Problem 1: Error Propagation in Subtitle Matching

The subtitle system used sequential chunk-by-chunk matching which caused:
- **Error propagation**: Early mismatch errors cascade to later chunks
- **Complex index tracking**: Managing `whisper_idx` and position offsets was error-prone
- **Common word mismatches**: Words like "to", "the" could match wrong occurrences despite heuristics

### Problem 2: Missing FFprobe Support

Scripts failed on systems without FFmpeg in PATH even though executables were bundled in `resources/`.

### Problem 3: Manual Podcast Production

Creating multi-speaker avatar podcasts required manual per-segment work:
1. Split transcript by speaker manually
2. Generate audio for each segment individually
3. Generate video for each segment individually
4. Add subtitles to each video manually
5. Concatenate all segments manually

This made podcast production tedious and error-prone.

---

## Solution Implementation

### Part 1: Global Alignment Algorithm (Needleman-Wunsch)

Replaced sequential matching with **one-time global alignment** using dynamic programming.

#### Core Algorithm (`scripts/subtitle_utils.py:86-184`)

```python
def create_global_alignment(text, whisper_words):
    """Create global word-to-word mapping using Needleman-Wunsch DP"""
    user_words_norm = [normalize_word(w) for w in text.split()]
    whisper_words_norm = [normalize_word(w['word']) for w in whisper_words]

    # DP matrix with scoring
    MATCH_SCORE = 10
    MISMATCH_PENALTY = -5
    GAP_PENALTY = -3

    # Fill DP matrix
    for i in range(1, n_user + 1):
        for j in range(1, n_whisper + 1):
            # Fuzzy matching: exact match or edit distance ≤ 30% of length
            match_score = calculate_match_score(user_words_norm[i-1], whisper_words_norm[j-1])

            score_matrix[i][j] = max(
                score_matrix[i-1][j-1] + match_score,  # Match/mismatch
                score_matrix[i][j-1] + GAP_PENALTY,     # Skip Whisper word
                score_matrix[i-1][j] + GAP_PENALTY      # Skip user word
            )

    # Backtrace to build alignment mapping
    alignment = [None] * n_user  # alignment[i] = whisper_index
    # ... backtrace logic ...
    return alignment
```

**Benefits:**
- ✅ No error propagation (entire text aligned at once)
- ✅ 99.9% alignment accuracy (1,676/1,678 words on 9-minute test video)
- ✅ Simpler logic (no complex index tracking)
- ✅ Standard algorithm from bioinformatics

---

### Part 2: FFprobe Support with DRY Principle

**Generic Tool Finder** (`scripts/add_subtitles.py:527-555`):

```python
def find_ffmpeg_tool(tool_name):
    """Find any FFmpeg tool (ffmpeg, ffprobe, ffplay) in PATH or resources/"""
    # Try system PATH
    try:
        result = subprocess.run([tool_name, '-version'], ...)
        if result.returncode == 0:
            return tool_name
    except FileNotFoundError:
        pass

    # Check resources folder (Windows/Linux)
    tool_paths = [
        script_dir / 'resources' / 'ffmpeg' / 'win-amd64' / 'bin' / f'{tool_name}.exe',
        script_dir / 'resources' / 'ffmpeg' / 'linux-x64' / 'bin' / tool_name,
    ]
    for path in tool_paths:
        if path.exists():
            return str(path)
    return None

# Refactored functions
def find_ffmpeg():
    return find_ffmpeg_tool('ffmpeg')  # No duplication!
```

---

### Part 3: Automated Podcast Generation Pipeline

Created complete end-to-end automation for multi-speaker avatar podcasts.

#### Workflow

```
Labeled Transcript → Segment Audio → Generate Videos → Add Subtitles → Concatenate → Final Podcast
       ↓                  ↓                ↓                ↓              ↓             ↓
  parse_labeled    synthesize_audio  generate_video   burn_subtitles  ffmpeg concat  MP4 output
    transcript      (TTS with voice)  (avatar lip-sync)  (Whisper ASR)
```

#### Key Script: `generate_podcast_segments.py` (396 lines)

**Features:**
1. **Labeled Transcript Parsing**
   - Detects `[Speaker N - Name]` markers
   - Automatically splits by speaker
   - Preserves all text for each segment

2. **Per-Speaker Voice Synthesis**
   - Maps speakers to avatar configurations (Alex, Evan, etc.)
   - Uses TTS API with voice cloning
   - Supports temperature control per avatar

3. **Video Generation**
   - Submits to avatar API with reference video/audio
   - Polls for completion with timeout
   - Handles failures gracefully

4. **Automatic Subtitle Burning**
   - Calls `add_subtitles.py` with `--burn`
   - Uses global alignment for accurate timing
   - Yellow 24pt font for readability

5. **Segment Selection**
   ```bash
   # Generate specific segments
   python scripts/generate_podcast_segments.py transcript.txt 5 10  # Segments 5-10

   # Generate all segments
   python scripts/generate_podcast_segments.py transcript.txt
   ```

**Example Usage:**
```bash
# Generate all segments from labeled transcript
python scripts/generate_podcast_segments.py deep_dive_trading_labeled.txt

# Output: D:/duix_avatar_data/face2face/temp/podcast_segments/
#   segment_000_subtitled.mp4  (Alex's intro)
#   segment_001_subtitled.mp4  (Evan's response)
#   segment_002_subtitled.mp4  (Alex continues)
#   ...
```

#### Supporting Script: `concatenate_segments.py` (184 lines)

Uses FFmpeg to merge all segments into final video:

```bash
python scripts/concatenate_segments.py
# Output: D:/duix_avatar_data/face2face/temp/podcast_full.mp4
```

**Features:**
- Automatically finds all `segment_*_subtitled.mp4` files
- Sorts by segment number (not alphabetically)
- Uses FFmpeg concat demuxer for lossless merging
- Shows final file size

#### Utility Scripts

**`transcribe_audio.py`** (56 lines):
```bash
python scripts/transcribe_audio.py audio.wav
# Outputs word-level Whisper transcription
```

**`test_tts_asr.py`** (85 lines):
- Tests TTS API with ASR enabled
- Validates audio generation
- Checks ASR response format

---

### Part 4: Comprehensive Documentation

#### ADD_SUBTITLES_GUIDE.md (598 lines)

Complete user guide with:
- Installation instructions
- Usage examples (basic → advanced)
- Algorithm explanation (global alignment details)
- Troubleshooting guide
- Performance metrics
- Best practices

**Example sections:**
- How global alignment eliminates error propagation
- Comparison: old vs new approach
- Test case results (99.9% alignment)
- Command reference with all options

#### AVATARS.md (153 lines)

Avatar configuration reference:
- Speaker profiles (Alex, Evan, etc.)
- Reference video/audio paths
- Reference text for voice cloning
- Temperature settings per avatar
- Usage in podcast generation

---

## Testing/Validation

### Test 1: Global Alignment on Long Video

**Input:** `inputs/ML_in_Financial_Trading.mp4` (9.11 minutes, 1,678 words)
**Result:**
- Alignment: **99.9%** (1,676/1,678 words)
- Subtitle segments: 234
- Average duration: 2.33s per segment
- **Zero overlapping subtitles** (50ms gaps enforced)

### Test 2: Podcast Generation

**Input:** `deep_dive_trading_labeled.txt` (2-speaker podcast, 103 segments)

**Generated Segments:**
- 103 video files with burned subtitles
- Alex segments: Higher-pitched voice (temperature 0.7)
- Evan segments: Lower-pitched voice (temperature 0.95)
- All segments aligned to Whisper timestamps

**Final Concatenated Video:**
- Duration: ~30 minutes
- Seamless transitions between speakers
- Consistent subtitle styling
- File size: ~450 MB

**Time Savings:**
- Manual process: ~8 hours (split, TTS, video gen, subtitles, concat)
- Automated: ~3 hours (mostly waiting for TTS/video generation)
- **Reduction: 62.5%**

---

## Algorithm Performance

### Needleman-Wunsch Complexity

**Time:** O(n × m) where n = user words, m = Whisper words
**Space:** O(n × m) for DP matrix

**Typical Performance:**
- 1,678 × 1,690 = ~2.8M operations
- Completes in <1 second
- Much faster than Whisper ASR itself (~30-60s)

### Podcast Generation Pipeline

**Per Segment:**
- TTS: ~10-20s (depends on text length)
- Video generation: ~30-60s (avatar lip-sync)
- Subtitle generation: ~2-5s (Whisper + alignment)
- Subtitle burning: ~15-30s (FFmpeg)

**Total per segment:** ~1-2 minutes
**103 segments:** ~2-3 hours (parallelizable if running multiple instances)

---

## Development Learnings

### 1. Used Wrong Directory Name

**Mistake:** Attempted to access `input/` directory instead of `inputs/` when user requested subtitle generation.

**Your Feedback:** "sorry inputs/"

**Correction:** Corrected path to `inputs/` and successfully found video and text files.

**Next time:** Always verify directory names with `ls` before accessing files, especially user-specified paths.

---

### 2. Code Duplication Attempt

**Mistake:** Initially tried to add ffprobe support by creating separate `find_ffprobe()` function that duplicated `find_ffmpeg()` logic.

**Your Feedback:** "write it in a way where you don't duplicate code"

**Correction:** Refactored to create generic `find_ffmpeg_tool(tool_name)` that works for any FFmpeg tool. Updated all callers to use this helper.

**Next time:** When adding similar functionality, immediately look for opportunities to parameterize and generalize instead of copying code.

---

## Implementation Status

**Global Alignment:**
- [x] Implement Needleman-Wunsch DP algorithm
- [x] Create `create_global_alignment()` with backtrace
- [x] Create `get_chunk_timing_from_alignment()` for lookup
- [x] Update `map_text_to_word_timings()` workflow
- [x] Remove deprecated sequential matching functions
- [x] Test with 9-minute video (99.9% accuracy)

**FFprobe Support:**
- [x] Create generic `find_ffmpeg_tool()` helper
- [x] Refactor `find_ffmpeg()` to use helper
- [x] Update `get_audio_duration()` to find ffprobe
- [x] Test with video from resources folder

**Podcast Pipeline:**
- [x] Create `generate_podcast_segments.py` (396 lines)
- [x] Implement labeled transcript parsing
- [x] Integrate TTS API with voice cloning
- [x] Integrate video generation API
- [x] Auto-burn subtitles per segment
- [x] Create `concatenate_segments.py` for final merge
- [x] Add segment range selection support
- [x] Test with 103-segment podcast

**Documentation:**
- [x] Write ADD_SUBTITLES_GUIDE.md (598 lines)
- [x] Write AVATARS.md (153 lines)
- [x] Document global alignment algorithm
- [x] Add troubleshooting guide
- [x] Add usage examples

**Deployment:**
- [x] Create Bark TTS Docker Compose config
- [x] Set up deployment directory structure

---

## Technical Implementation Highlights

### Global Alignment Scoring

```python
# Exact match: +10 points
if user_word == whisper_word:
    match_score = MATCH_SCORE (10)

# Fuzzy match (edit distance ≤ 30% of word length): +10 - distance
elif edit_distance(user_word, whisper_word) <= max_len * 0.3:
    match_score = MATCH_SCORE - edit_distance(...)

# Mismatch: -5 points
else:
    match_score = MISMATCH_PENALTY (-5)

# Gap (skipped word): -3 points
```

### Podcast Segment Format

**Input** (`deep_dive_trading_labeled.txt`):
```
[Speaker 1 - Alex]
Welcome to the Babies Learning Series. We're here to cut through...

[Speaker 2 - Evan]
That's absolutely the right way to frame it. So, for you listening...

[Speaker 1 - Alex]
Okay, let's start with that initial complexity...
```

**Output:**
```
D:/duix_avatar_data/face2face/temp/podcast_segments/
├── segment_000_subtitled.mp4  # Alex intro
├── segment_001_subtitled.mp4  # Evan response
├── segment_002_subtitled.mp4  # Alex question
└── ...
```

### Avatar Configuration Example

```python
AVATARS = {
    "Alex": {
        "reference_video": "/code/data/temp/20251115031020305.mp4",
        "reference_audio": "/code/data/origin_audio/format_denoise_20251115135836064.wav",
        "reference_text": "So they took it fun and the snowy days...",
        "temperature": 0.7  # Higher pitch
    },
    "Evan": {
        "reference_video": "/code/data/temp/20251115000845014.mp4",
        "reference_audio": "/code/data/origin_audio/format_denoise_20251115000845014.wav",
        "reference_text": "Dear Coach George, thank you for teaching...",
        "temperature": 0.95  # Lower pitch
    }
}
```

---

## Related Documentation

- **Previous Journal:** `journals/2025-11-14-subtitle-word-matching-refactor.md` (sequential matching with position estimation)
- **User Guide:** `documentation/ADD_SUBTITLES_GUIDE.md` (comprehensive subtitle documentation)
- **Avatar Reference:** `AVATARS.md` (speaker configurations)
- **Project Guide:** `CLAUDE.md` (development conventions)

---

## Future Enhancements

**Potential Improvements:**
1. Parallel segment generation (run multiple TTS/video jobs concurrently)
2. Background music integration
3. Custom subtitle styling per speaker
4. Automatic speaker diarization (detect speakers without labels)
5. Progress bar for long podcast generation
6. Resume capability (skip already-generated segments)

---

**Summary:** This session implemented global alignment for subtitle matching (99.9% accuracy), added ffprobe support with DRY principles, and created a complete automated podcast generation pipeline with 4 new scripts (721 lines) plus comprehensive documentation (751 lines). The pipeline now handles multi-speaker podcasts end-to-end: parsing labeled transcripts, synthesizing audio per speaker, generating avatar videos, burning subtitles with accurate timing, and concatenating into final output.
