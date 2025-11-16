#!/usr/bin/env python3
"""
Unit test for subtitle text-to-timing matching
Tests the alignment between original text and Whisper word timings
"""

import re
import sys
import io

# Set UTF-8 encoding for stdout on Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

try:
    from faster_whisper import WhisperModel
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False
    print("Error: faster-whisper not installed")
    sys.exit(1)

# Import shared utilities (same directory)
from subtitle_utils import (normalize_word, split_into_sentences, split_into_chunks,
                             create_global_alignment, get_chunk_timing_from_alignment)

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

    # Now test NEW global alignment approach
    print("\n" + "=" * 70)
    print("GLOBAL ALIGNMENT APPROACH")
    print("=" * 70)

    # Step 1: Create global alignment once for entire text
    print("\nStep 1: Creating global word-to-word alignment...")
    alignment = create_global_alignment(original_text, whisper_words)

    if not alignment:
        print("ERROR: Global alignment failed!")
        return

    # Count alignment statistics
    aligned_count = sum(1 for a in alignment if a is not None)
    total_words = len(alignment)
    print(f"✓ Aligned {aligned_count}/{total_words} words ({aligned_count/total_words*100:.1f}%)")

    # Step 2: Test matching for each chunk using global alignment
    print("\n" + "=" * 70)
    print("CHUNK MATCHING RESULTS")
    print("=" * 70)

    total_chunks = 0
    matched_chunks = 0
    current_word_idx = 0  # Track position in original text word array

    for sent_num, sentence in enumerate(full_sentences, 1):
        print(f"\n--- Sentence {sent_num} ---")
        print(f"Text: {sentence[:80]}{'...' if len(sentence) > 80 else ''}")

        # Split into chunks (max 60 chars)
        chunks = split_into_chunks(sentence, max_chars=60)

        for chunk_num, chunk in enumerate(chunks, 1):
            total_chunks += 1
            chunk_word_count = len(chunk.split())

            # Step 3: Get timing from global alignment
            start_time, end_time = get_chunk_timing_from_alignment(
                current_word_idx,
                chunk_word_count,
                alignment,
                whisper_words
            )

            match_found = (start_time is not None and end_time is not None)

            if match_found:
                matched_chunks += 1

            status = "[MATCH]" if match_found else "[NO MATCH]"
            print(f"\n  Chunk {chunk_num}: {chunk[:50]}{'...' if len(chunk) > 50 else ''}")

            if match_found:
                # Find which Whisper words were aligned for this chunk
                whisper_indices = []
                for i in range(current_word_idx, min(current_word_idx + chunk_word_count, len(alignment))):
                    if alignment[i] is not None:
                        whisper_indices.append(alignment[i])

                if whisper_indices:
                    match_start = min(whisper_indices)
                    match_end = max(whisper_indices) + 1
                    matched_whisper_words = whisper_words[match_start:match_end]

                    print(f"  {status} at Whisper indices [{match_start}:{match_end}]")
                    print(f"    Start time: {start_time:.3f}s")
                    print(f"    End time: {end_time:.3f}s")
                    print(f"    Duration: {end_time - start_time:.3f}s")
                    print(f"    Chunk words ({len(chunk.split())}): {chunk.split()}")
                    print(f"    Whisper words ({len(matched_whisper_words)}): {[w['word'] for w in matched_whisper_words]}")

                    # Show word-by-word alignment from global mapping
                    print(f"    Word alignment (from global mapping):")
                    chunk_words_list = chunk.split()
                    for i, word in enumerate(chunk_words_list):
                        word_idx = current_word_idx + i
                        if word_idx < len(alignment) and alignment[word_idx] is not None:
                            whisper_idx = alignment[word_idx]
                            whisper_word = whisper_words[whisper_idx]['word']
                            match_symbol = "[OK]" if normalize_word(word) == normalize_word(whisper_word) else "[~]"
                            print(f"      {word:<20} -> {whisper_word:<20} {match_symbol}")
                        else:
                            print(f"      {word:<20} -> [none]               [GAP]")
            else:
                print(f"  {status}")

            # Move word index forward
            current_word_idx += chunk_word_count

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
    # Default: deep_dive_trading.txt
    # text_file = "deep_dive_trading.txt"
    # audio_file = "D:/duix_avatar_data/face2face/temp/aeef7485-34c2-422c-9f17-aeeac99bc830.wav"

    # Test on segment 7
    text_file = "segment_7_text.txt"
    audio_file = "D:/duix_avatar_data/face2face/temp/bd427605-4529-4f35-b6db-8f0fc2a18cab.wav"

    test_matching(text_file, audio_file)
