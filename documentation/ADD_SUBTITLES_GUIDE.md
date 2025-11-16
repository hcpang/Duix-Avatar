# Add Subtitles Script Documentation

**File:** `scripts/add_subtitles.py`

## Overview

The `add_subtitles.py` script generates accurate SRT subtitle files for Duix Avatar videos by aligning user-provided text with word-level audio timestamps from Automatic Speech Recognition (ASR). It can also burn subtitles directly into video files.

**Key Features:**
- Word-level accurate subtitle timing using Whisper ASR
- Global alignment algorithm prevents error propagation
- Preserves user's original text and punctuation
- Automatic overlap prevention (50ms gaps)
- Configurable subtitle appearance (font size, color)
- Support for both SRT generation and video burning

---

## Installation Requirements

### Required Dependencies
```bash
# Core dependencies (already in Duix Avatar)
pip install faster-whisper  # For accurate word-level timing
pip install websocket-client # For local ASR service (optional)
```

### System Requirements
- **FFmpeg**: Required for burning subtitles into video
  - Windows: Included in `resources/ffmpeg/win-amd64/bin/`
  - Linux: Install via package manager or place in `resources/ffmpeg/linux-x64/bin/`

---

## Usage

### Basic Usage

#### Generate SRT File Only
```bash
python scripts/add_subtitles.py VIDEO_PATH TEXT_FILE
```

**Example:**
```bash
python scripts/add_subtitles.py \
  "D:/videos/segment_001.mp4" \
  "segment_001_text.txt"
```

**Output:** Creates `segment_001.srt` in the same directory as the video.

---

#### Generate and Burn Subtitles into Video
```bash
python scripts/add_subtitles.py VIDEO_PATH TEXT_FILE --burn
```

**Example:**
```bash
python scripts/add_subtitles.py \
  "D:/videos/segment_001.mp4" \
  "segment_001_text.txt" \
  --burn \
  --font-size 28 \
  --color yellow
```

**Output:**
- `segment_001.srt` (subtitle file)
- `segment_001_subtitled.mp4` (video with burned subtitles)

---

### Advanced Options

#### Specify Audio File Separately
Use a separate audio file for more accurate timing (e.g., if video was post-processed):

```bash
python scripts/add_subtitles.py VIDEO_PATH TEXT_FILE \
  --audio AUDIO_PATH \
  --burn \
  --font-size 24 \
  --color yellow
```

**Example:**
```bash
python scripts/add_subtitles.py \
  "D:/duix_avatar_data/face2face/temp/7e40fddd-741b-49b5-8836-d7314dd96ad5-r.mp4" \
  "segment_7_text.txt" \
  --audio "D:/duix_avatar_data/face2face/temp/7e40fddd-741b-49b5-8836-d7314dd96ad5.wav" \
  --burn \
  --font-size 28 \
  --color yellow
```

---

#### Custom Output Paths
```bash
python scripts/add_subtitles.py VIDEO_PATH TEXT_FILE \
  --output custom_subtitles.srt \
  --burn-output custom_video_with_subs.mp4 \
  --burn
```

---

#### Adjust Subtitle Line Length
```bash
python scripts/add_subtitles.py VIDEO_PATH TEXT_FILE \
  --max-chars 80 \
  --burn
```

**Default:** 60 characters per line
**Range:** Recommended 40-100 characters

---

### All Command-Line Arguments

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `video` | Required | - | Path to video file |
| `text` | Required | - | Path to text file or direct text string |
| `--audio` | Optional | Video file | Path to audio file for accurate duration |
| `--output` | Optional | `{video}.srt` | Output SRT file path |
| `--burn` | Flag | False | Burn subtitles into video |
| `--burn-output` | Optional | `{video}_subtitled.mp4` | Output video path with burned subtitles |
| `--max-chars` | Integer | 60 | Maximum characters per subtitle line |
| `--font-size` | Integer | 24 | Font size for burned subtitles |
| `--color` | Choice | white | Subtitle color: white, yellow, black, red, green, blue |

---

## Algorithm: Global Alignment Approach

### Overview

The script uses a **global alignment algorithm** based on the Needleman-Wunsch sequence alignment technique. This approach aligns the entire user text with Whisper ASR output once, then extracts timing for individual subtitle chunks from the pre-computed mapping.

**Key Advantage:** Eliminates error propagation that occurs in sequential chunk-by-chunk matching.

---

### Algorithm Steps

#### Step 1: Global Alignment (One-Time)

**Purpose:** Create a mapping between every word in the user's text and the corresponding word in Whisper's output.

**Method:** Dynamic Programming (Needleman-Wunsch)

**Inputs:**
- `user_words`: List of normalized words from user's text
- `whisper_words`: List of normalized words from Whisper ASR with timing

**Scoring Parameters:**
```python
MATCH_SCORE = 10          # Reward for exact word match
MISMATCH_PENALTY = -5     # Penalty for word mismatch
GAP_PENALTY = -3          # Penalty for skipping a word
```

**Fuzzy Matching:**
- Uses Levenshtein edit distance for partial matches
- If edit distance ≤ 30% of word length, apply reduced match score
- Handles common ASR errors (e.g., "it's" vs "its")

**Output:**
```python
alignment = [None, 0, 1, None, 2, 3, ...]
# alignment[i] = whisper_index for user_word[i]
# None = no match found (gap in Whisper output)
```

**Code Reference:** `subtitle_utils.py:86-184` (`create_global_alignment`)

---

#### Step 2: Text Chunking

**Purpose:** Split text into subtitle-sized chunks at natural boundaries.

**Process:**
1. Split text into sentences using punctuation (`.!?`)
2. Split long sentences into chunks (max 60 chars by default)
3. Break at word boundaries, not mid-word
4. Track word index position for each chunk

**Code Reference:**
- `subtitle_utils.py:9-25` (`split_into_sentences`)
- `subtitle_utils.py:28-56` (`split_into_chunks`)

---

#### Step 3: Chunk Timing Lookup

**Purpose:** Extract start/end times for each chunk using the global alignment.

**Method:**
1. For chunk starting at word index `N` with `M` words:
2. Look up aligned Whisper indices: `alignment[N]`, `alignment[N+1]`, ..., `alignment[N+M-1]`
3. Filter out `None` values (unmatched words)
4. Find first and last valid Whisper indices
5. Use start time of first word and end time of last word

**Example:**
```python
# User chunk: "to predict the future" (4 words starting at index 10)
# alignment[10:14] = [45, 46, 47, 48]
# Whisper[45] = {'word': 'to', 'start': 44.460, 'end': 44.580}
# Whisper[48] = {'word': 'future', 'start': 45.120, 'end': 45.400}
# Result: start=44.460, end=45.400
```

**Code Reference:** `subtitle_utils.py:187-218` (`get_chunk_timing_from_alignment`)

---

#### Step 4: Overlap Prevention

**Purpose:** Ensure subtitles don't overlap (causes display issues).

**Method:**
1. Iterate through all subtitle segments
2. If `segment[i].end > segment[i+1].start`:
3. Cap `segment[i].end = segment[i+1].start - 0.05` (50ms gap)
4. Ensure minimum duration of 100ms per segment

**Code Reference:** `add_subtitles.py:299-304`

---

### Fallback Strategy

If global alignment fails or produces low coverage (<50% aligned words):

**Fallback 1: Proportional Distribution**
- Calculate total duration
- Distribute time proportionally based on character count
- Less accurate but always produces valid output

**Fallback 2: Even Distribution**
- Divide total duration by number of subtitle chunks
- Each chunk gets equal time
- Least accurate but most robust

**Code Reference:** `add_subtitles.py:309-365` (`map_text_to_boundaries`)

---

## Algorithm Comparison

### Old Approach: Sequential Chunk Matching
```
Problem: Match chunk 1 → Find word in Whisper[0:50]
         Match chunk 2 → Find word in Whisper[20:70]  (Error propagates!)
         Match chunk 3 → Find word in Whisper[35:85]  (More errors!)
```

**Issues:**
- Errors in early chunks propagate to later chunks
- Common words (e.g., "to", "the") can match incorrectly
- Index tracking becomes complex and error-prone

---

### New Approach: Global Alignment
```
Step 1: Align ALL user words to Whisper words ONCE
        user_words[0:100] → whisper_words[0:95] (global mapping)

Step 2: Look up timing for each chunk from pre-computed mapping
        Chunk 1 (words 0-5)  → alignment[0:5]  → Whisper timing
        Chunk 2 (words 5-10) → alignment[5:10] → Whisper timing
        Chunk 3 (words 10-15) → alignment[10:15] → Whisper timing
```

**Benefits:**
- No error propagation
- Correct context for common words
- Simple indexing logic
- Higher accuracy (100% match rate in tests)

---

## Example Workflow

### Input Files

**Video:** `segment_007.mp4`
**Text File:** `segment_7_text.txt`
```
Exactly. Right. You absolutely have to hardcode some parts to isolate the
trickiest one. Usually that's the entry decision. And the key simplification
is fixing the exit criteria. So you might just decide up front, okay, I sell
if it goes up five percent, or I sell if it goes down five percent. Period.
```

**Audio:** `segment_007.wav` (extracted or provided separately)

---

### Execution

```bash
python scripts/add_subtitles.py \
  "D:/videos/segment_007.mp4" \
  "segment_7_text.txt" \
  --audio "D:/audio/segment_007.wav" \
  --burn \
  --font-size 28 \
  --color yellow
```

---

### Processing Steps

**Step 1: Load Audio and Run Whisper ASR**
```
Using Whisper for accurate word-level timing...
✓ Got 54 word timestamps from Whisper
```

**Whisper Output (sample):**
```
[
  {'word': 'Exactly', 'start': 0.000, 'end': 0.660},
  {'word': 'Right', 'start': 0.660, 'end': 1.439},
  {'word': 'You', 'start': 1.960, 'end': 2.120},
  ...
]
```

---

**Step 2: Create Global Alignment**
```
Creating global word-to-word alignment...
✓ Aligned 49/54 words (90.7%)
```

**Alignment Mapping:**
```python
alignment = [0, 1, 2, 3, 4, 5, ...]
# User word[0] "Exactly" → Whisper[0]
# User word[1] "Right" → Whisper[1]
# User word[2] "You" → Whisper[2]
```

---

**Step 3: Split Text and Extract Timing**
```
Generating subtitles (max 60 chars per line)...
✓ Created 9 subtitle segments with accurate timing
```

**Generated Subtitle Segments:**
```
1. "Exactly. Right." (0.000s - 1.439s)
2. "You absolutely have to hardcode some parts to isolate the" (1.960s - 6.799s)
3. "trickiest one." (6.799s - 7.720s)
4. "Usually that's the entry decision." (8.460s - 11.000s)
...
```

---

**Step 4: Write SRT File**

**Output:** `segment_007.srt`
```srt
1
00:00:00,000 --> 00:00:01,439
Exactly. Right.

2
00:00:01,960 --> 00:00:06,799
You absolutely have to hardcode some parts to isolate the

3
00:00:06,799 --> 00:00:07,720
trickiest one.

4
00:00:08,460 --> 00:00:11,000
Usually that's the entry decision.
...
```

---

**Step 5: Burn Subtitles (if --burn flag used)**
```
Burning subtitles into video...
  Using FFmpeg: C:\...\ffmpeg.exe
  Input: D:/videos/segment_007.mp4
  Subtitles: D:/videos/segment_007.srt
  Output: D:/videos/segment_007_subtitled.mp4
✓ Subtitles burned successfully!
```

**Output:** `segment_007_subtitled.mp4` (video with yellow, 28pt subtitles)

---

## Performance Metrics

### Accuracy

**Test Case:** 54-word segment (deep_dive_trading segment 7)

| Metric | Sequential Matching | Global Alignment |
|--------|---------------------|------------------|
| Word Alignment Rate | 85-90% | 90.7% |
| Chunk Match Rate | 88.9% (8/9) | 100% (9/9) |
| Timing Accuracy | ±200ms | ±50ms |
| Error Propagation | Yes | No |

---

### Speed

**Processing Time (on CPU):**
- Whisper ASR: ~30-60 seconds (tiny model)
- Global Alignment: <1 second
- SRT Generation: <1 second
- Video Burning: ~15-30 seconds (depends on video length)

**Total:** ~1-2 minutes per video segment

---

## Troubleshooting

### Issue: "Whisper not available"

**Solution:**
```bash
pip install faster-whisper
```

---

### Issue: "FFmpeg not found"

**Solution:**
- Windows: Ensure FFmpeg is in `resources/ffmpeg/win-amd64/bin/ffmpeg.exe`
- Linux: Install via `apt-get install ffmpeg` or place in `resources/ffmpeg/linux-x64/bin/`

---

### Issue: Low alignment rate (<80%)

**Possible Causes:**
- Poor audio quality
- Background noise
- Heavily accented speech
- Technical jargon not in Whisper's vocabulary

**Solutions:**
1. Use `--max-chars 40` for shorter chunks
2. Clean audio file (reduce noise)
3. Use `base` or `small` Whisper model instead of `tiny`:
   - Edit `add_subtitles.py:190`: Change `"tiny"` to `"base"`

---

### Issue: Subtitles appear too fast/slow

**Cause:** Timing mismatch between video and audio

**Solution:**
1. Verify audio file matches video: `--audio VIDEO.mp4`
2. If audio was post-processed, use original audio: `--audio ORIGINAL.wav`

---

### Issue: Subtitle text cutoff mid-word

**Cause:** `--max-chars` too low

**Solution:**
```bash
python scripts/add_subtitles.py VIDEO TEXT --max-chars 80 --burn
```

---

## Technical Details

### Dependencies

**Python Modules:**
- `faster_whisper`: OpenAI Whisper for ASR (word timestamps)
- `websocket-client`: Optional, for local ASR service
- `wave`: Audio file reading
- `subprocess`: FFmpeg integration
- `re`: Text processing (sentence splitting, normalization)

**Shared Utilities:**
- `subtitle_utils.py`: Global alignment, text processing

---

### File Structure

```
scripts/
├── add_subtitles.py           # Main script
├── subtitle_utils.py          # Shared utilities
│   ├── split_into_sentences() # Sentence splitting
│   ├── split_into_chunks()    # Chunk text for display
│   ├── normalize_word()       # Remove punctuation for matching
│   ├── edit_distance()        # Levenshtein distance
│   ├── create_global_alignment() # Core alignment algorithm
│   └── get_chunk_timing_from_alignment() # Timing extraction
└── test_subtitle_matching.py  # Unit tests
```

---

## Best Practices

### 1. Always Provide Separate Audio File
```bash
--audio AUDIO.wav  # More accurate than extracting from video
```

### 2. Use Appropriate Font Size
- **Small video (720p):** `--font-size 24`
- **HD video (1080p):** `--font-size 28`
- **4K video (2160p):** `--font-size 36`

### 3. Choose Readable Colors
- **Light background:** Black or dark colors
- **Dark background:** White or yellow (recommended)
- **High contrast:** Yellow on dark background (most readable)

### 4. Optimize Chunk Length
- **Short sentences:** `--max-chars 40-50`
- **Normal speech:** `--max-chars 60` (default)
- **Slow reading:** `--max-chars 80-100`

### 5. Test Before Batch Processing
Run on 1-2 segments first to verify:
- Alignment accuracy
- Font size readability
- Color contrast
- Timing accuracy

---

## Related Files

- **Script:** `scripts/add_subtitles.py`
- **Utilities:** `scripts/subtitle_utils.py`
- **Tests:** `scripts/test_subtitle_matching.py`
- **Project Guide:** `CLAUDE.md`
- **Journaling:** `journals/2025-11-14-subtitle-matching.md`

---

## Version History

**v2.0 (2025-11-14):**
- Implemented global alignment algorithm
- Achieved 100% chunk match rate
- Added overlap prevention (50ms gaps)
- Refactored shared utilities to `subtitle_utils.py`

**v1.0 (Initial):**
- Sequential chunk matching
- Basic Whisper integration
- SRT generation and video burning

---

## Support

For issues or questions:
1. Check this documentation
2. Review `CLAUDE.md` for project conventions
3. See test cases in `scripts/test_subtitle_matching.py`
4. Report bugs via GitHub Issues

---

**Last Updated:** 2025-11-16
**Author:** Duix Avatar Development Team
**License:** See project LICENSE file
