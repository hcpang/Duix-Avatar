#!/usr/bin/env python3
"""
Unit test for subtitle text-to-timing matching
Tests the alignment between original text and Whisper word timings
"""

import re
import sys

try:
    from faster_whisper import WhisperModel
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False
    print("Error: faster-whisper not installed")
    sys.exit(1)

# Import shared utilities (same directory)
from subtitle_utils import (normalize_word, edit_distance, find_best_match,
                             match_chunk_to_whisper, split_into_sentences, split_into_chunks)

def test_matching(text_file, audio_file):
    """Test the text matching against Whisper output"""

    print("=" * 70)
    print("SUBTITLE TEXT MATCHING TEST")
    print("=" * 70)

    # Read original text
    with open(text_file, 'r', encoding='utf-8') as f:
        original_text = f.read().strip()

    print(f"\nOriginal text length: {len(original_text)} characters")
    print(f"Original text: {original_text[:100]}...")

    # Get Whisper word timings
    print("\nRunning Whisper ASR...")
    model = WhisperModel("tiny", device="cpu", compute_type="int8")
    segments, info = model.transcribe(audio_file, word_timestamps=True, language="en")

    # Extract word timings
    whisper_words = []
    for segment in segments:
        if hasattr(segment, 'words') and segment.words:
            for word in segment.words:
                whisper_words.append({
                    'word': word.word.strip(),
                    'start': word.start,
                    'end': word.end
                })

    print(f"Whisper found {len(whisper_words)} words")
    print(f"\nFirst 10 Whisper words:")
    for i, w in enumerate(whisper_words[:10]):
        print(f"  {i}: '{w['word']}' @ {w['start']:.2f}s")

    # Split original text into sentences
    full_sentences = split_into_sentences(original_text)
    print(f"\nSplit into {len(full_sentences)} sentences")

    # Now test matching for each sentence
    print("\n" + "=" * 70)
    print("MATCHING RESULTS")
    print("=" * 70)

    whisper_words_normalized = [normalize_word(w['word']) for w in whisper_words]
    whisper_idx = 0

    total_chunks = 0
    matched_chunks = 0

    # Track character progress for temporal positioning
    chars_processed = 0
    total_chars = len(original_text)
    total_duration = whisper_words[-1]['end'] if whisper_words else 0
    prev_chunk_word_count = 0  # Track previous chunk's word count for position estimation

    for sent_num, sentence in enumerate(full_sentences, 1):
        print(f"\n--- Sentence {sent_num} ---")
        print(f"Text: {sentence[:80]}{'...' if len(sentence) > 80 else ''}")

        # Split into chunks (max 60 chars)
        chunks = split_into_chunks(sentence, max_chars=60)

        for chunk_num, chunk in enumerate(chunks, 1):
            total_chunks += 1

            # Try to match chunk to Whisper words using shared function
            chunk_start_time, new_whisper_idx, match_found, current_chunk_word_count = match_chunk_to_whisper(
                chunk, whisper_words, whisper_words_normalized, whisper_idx, prev_chunk_word_count
            )

            # Update prev_chunk_word_count for next iteration
            prev_chunk_word_count = current_chunk_word_count

            if match_found:
                matched_chunks += 1
                # Update whisper_idx for next iteration
                match_idx = new_whisper_idx - 1  # The matched word index
                whisper_idx = new_whisper_idx

            # Update character progress
            chars_processed += len(chunk) + 1  # +1 for space

            status = "[MATCH]" if match_found else "[NO MATCH]"
            print(f"\n  Chunk {chunk_num}: {chunk[:50]}{'...' if len(chunk) > 50 else ''}")

            if match_found:
                print(f"  {status} at index {match_idx}")
                print(f"    Whisper word: '{whisper_words[match_idx]['word']}'")
                print(f"    Start time: {chunk_start_time:.3f}s")
            else:
                chunk_words = chunk.split()
                first_word = chunk_words[0] if chunk_words else ""
                print(f"  First word: '{first_word}'")
                print(f"  {status}")

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Total chunks: {total_chunks}")
    print(f"Matched chunks: {matched_chunks}")
    print(f"Unmatched chunks: {total_chunks - matched_chunks}")
    print(f"Match rate: {matched_chunks / total_chunks * 100:.1f}%")

    if matched_chunks < total_chunks:
        print("\n[WARNING] Some chunks did not match. Consider:")
        print("  - Wider search window (look ahead/behind)")
        print("  - Better fuzzy matching (edit distance)")
        print("  - Handling contractions and filler words")

if __name__ == "__main__":
    text_file = "deep_dive_trading.txt"
    audio_file = "D:/duix_avatar_data/face2face/temp/aeef7485-34c2-422c-9f17-aeeac99bc830.wav"

    test_matching(text_file, audio_file)
