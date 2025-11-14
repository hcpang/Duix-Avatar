# Subtitle Word Matching and Code Refactoring

## Session Metadata

**Date**: 2025-11-14
**Model**: Claude Sonnet 4.5 (claude-sonnet-4-5-20250929)
**Feature**: Whisper word-level subtitle matching with temporal position estimation

**Files Modified:**
- `scripts/add_subtitles.py:228-284` - Replaced sentence/chunk splitting with shared utility calls, updated to use refactored `match_chunk_to_whisper()` with word-based position tracking
- `scripts/add_subtitles.py:306-325` - Added subtitle overlap prevention (50ms gap insertion)

**Files Created:**
- `scripts/test_subtitle_matching.py` - Unit test for subtitle matching with 100% match rate validation (26/26 chunks), moved to scripts/ directory for proper organization
- `scripts/subtitle_utils.py` - Shared utilities for subtitle generation including:
  - `split_into_sentences()` - Sentence splitting by punctuation
  - `split_into_chunks()` - Chunk splitting at natural breaks
  - `normalize_word()` - Word normalization for fuzzy matching
  - `edit_distance()` - Levenshtein distance calculation
  - `find_best_match()` - Fuzzy word matching within search window
  - `match_chunk_to_whisper()` - Complete chunk matching with word-based position estimation

## Problem Statement

The subtitle generation system had multiple issues:

1. **Overlapping subtitle segments**: End times were calculated independently from start times of subsequent segments, causing subtitles to overlap and display simultaneously (confusing for viewers)

2. **Incorrect timing for common words**: Sequential word matching caused common words like "to" to match the first occurrence instead of the contextually correct one. For example, "to predict every tiny reason..." was matching the "to" from "want **to** bring" (41.600s) instead of "model **to** predict" (44.460s)

3. **Code duplication**: Identical logic was duplicated between `scripts/add_subtitles.py` and `test_subtitle_matching.py` for:
   - Word normalization and fuzzy matching
   - Sentence and chunk splitting
   - Multi-word fallback matching
   - Search positioning logic

## Solution Implementation

### 1. Fixed Overlapping Subtitles

Added post-processing to cap each segment's end time 50ms before the next segment starts:

```python
# scripts/add_subtitles.py:306-312
# Fix overlapping segments - ensure each segment ends before the next starts
for i in range(len(subtitle_segments) - 1):
    next_start = subtitle_segments[i + 1]['start']
    if subtitle_segments[i]['end'] > next_start:
        subtitle_segments[i]['end'] = max(subtitle_segments[i]['start'] + 0.1, next_start - 0.05)
```

### 2. Implemented Multi-Word Fallback Matching

When the first word of a chunk doesn't match, try up to 5 words. If word N matches, use the timing of word N-1:

```python
# scripts/subtitle_utils.py:95-119
for word_offset in range(min(5, len(chunk_words))):
    target_word = chunk_words[word_offset].split('-')[0]
    target_word_normalized = normalize_word(target_word)

    match_idx, distance = find_best_match(
        target_word_normalized,
        whisper_words_normalized,
        min_search_idx,
        search_window=20
    )

    if match_idx is not None and distance <= 2:
        if word_offset > 0 and match_idx > 0:
            # We matched 2nd+ word, use the word before it as start time
            chunk_start = whisper_words[match_idx - 1]['start']
        else:
            chunk_start = whisper_words[match_idx]['start']
        new_whisper_idx = match_idx + 1
        return chunk_start, new_whisper_idx, True, len(chunk_words)
```

### 3. Word-Based Position Estimation

After matching a chunk with N words, the next chunk starts searching at `whisper_idx + N/2` to prevent matching common words too early:

```python
# scripts/subtitle_utils.py:89-93
# Calculate minimum search position based on PREVIOUS chunk's word count
# If we just matched a chunk with N words, the next chunk should be at least N/2 words ahead
# This prevents matching common words too early (like matching the wrong "to")
min_words_ahead = prev_chunk_word_count // 2
min_search_idx = whisper_idx + min_words_ahead
```

The function signature was updated to track and return word counts:

```python
def match_chunk_to_whisper(chunk, whisper_words, whisper_words_normalized,
                          whisper_idx, prev_chunk_word_count=0):
    # ...
    return chunk_start, new_whisper_idx, True, len(chunk_words)
```

### 4. Complete Code Refactoring

All shared logic was moved to `scripts/subtitle_utils.py`:

**Text Processing:**
- `split_into_sentences(text)` - Splits text by punctuation marks
- `split_into_chunks(sentence, max_chars=60)` - Splits long sentences at word boundaries

**Word Matching:**
- `normalize_word(word)` - Removes punctuation and lowercases
- `edit_distance(s1, s2)` - Levenshtein distance for fuzzy matching
- `find_best_match(target_word, whisper_words_norm, start_idx, search_window=20)` - Finds best word match within window
- `match_chunk_to_whisper(...)` - Complete matching logic with multi-word fallback and position estimation

Both `scripts/add_subtitles.py` and `test_subtitle_matching.py` now import and use these shared functions.

## Testing/Validation

Ran unit test against reference audio with 26 subtitle chunks:

```
Match rate: 100.0%
Total chunks: 26
Matched chunks: 26
```

**Critical timing verification:**
```
Chunk: "to predict every tiny reason for a defect, would y..."
  Matched at index 117
  Whisper word: 'to'
  Start time: 44.460s  ✓ (correct - "model to predict")
```

Previously this was incorrectly matching at 41.600s (the "to" from "want to bring").

**Overlap verification:**
All subtitle segments now have 50ms gaps between them - no overlapping timestamps.

## Development Learnings

### 1. Incomplete Code Refactoring

**Mistake**: Initially only refactored the word matching logic into `subtitle_utils.py`, but left sentence splitting and chunk splitting duplicated between `scripts/add_subtitles.py` and `test_subtitle_matching.py`.

**Your Feedback**: "are you sure you properly refactored the code? how come there's still duplication"

**Correction**: Added `split_into_sentences()` and `split_into_chunks()` to `subtitle_utils.py` and updated both files to import and use these shared functions. Eliminated all code duplication.

**Next time**: When refactoring duplicated code, proactively search for ALL instances of duplication across files, not just the most obvious logic. Check for duplicated text processing, data structure creation, and utility functions.

### 2. Not Refactoring Code Proactively

**Mistake**: Did not identify and refactor code duplication until explicitly asked by the user.

**Your Feedback**: "also, are there duplicated code between the unit test and the actual script? if so can you factor them?"

**Correction**: Created comprehensive `subtitle_utils.py` module and moved all shared logic there.

**Next time**: After implementing functionality in both production code and tests, immediately check for code duplication and proactively refactor into shared modules before the user has to ask.

### 3. Improper File Organization

**Mistake**: Initially placed `test_subtitle_matching.py` in the root directory instead of following the project's existing convention of placing test files in the `scripts/` directory alongside the code they test.

**Your Feedback**: "why is @test_subtitle_matching.py not in /scripts?"

**Correction**: Moved `test_subtitle_matching.py` to `scripts/test_subtitle_matching.py` and updated the import statement to remove the `sys.path.insert(0, 'scripts')` hack since the test is now in the same directory as `subtitle_utils.py`.

**Next time**: Before creating new files, check the existing project structure to understand file organization conventions. Look for similar files (like `scripts/test_api.py`) to understand where new files should be placed. Follow the established patterns to maintain consistency.

## Implementation Status

**Completed:**
- ✅ Fixed overlapping subtitle segments (50ms gaps)
- ✅ Implemented multi-word fallback matching (tries up to 5 words)
- ✅ Implemented word-based position estimation (skip N/2 words after matching N-word chunk)
- ✅ Achieved 100% match rate on test data
- ✅ Fixed incorrect timing for "to predict" chunk (41.600s → 44.460s)
- ✅ Refactored all duplicate code into `scripts/subtitle_utils.py`
- ✅ Updated both main script and test to use shared utilities
- ✅ Moved test file to `scripts/` directory for proper organization
- ✅ Generated final video with accurate word-level subtitle timing

**Final Output:**
- Video: `D:/duix_avatar_data/face2face/temp/deep_dive_final.mp4`
- SRT: `D:\duix_avatar_data\face2face\temp\0c5bcf91-2b40-459a-8026-881fbd173958-r.srt`
- 26 subtitle segments with accurate word-level timing
- No overlapping segments
- Zero code duplication
