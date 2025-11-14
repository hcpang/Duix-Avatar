#!/usr/bin/env python3
"""
Shared utilities for subtitle text matching and timing
"""

import re


def split_into_sentences(text):
    """Split text into sentences using natural boundaries

    Args:
        text: The text to split

    Returns:
        List of sentences with punctuation attached
    """
    sentences = re.split(r'([.!?。！？]+)', text)
    full_sentences = []
    for i in range(0, len(sentences) - 1, 2):
        if i + 1 < len(sentences):
            full_sentences.append((sentences[i] + sentences[i + 1]).strip())
        elif sentences[i].strip():
            full_sentences.append(sentences[i].strip())
    return full_sentences


def split_into_chunks(sentence, max_chars=60):
    """Split a long sentence into chunks at natural break points

    Args:
        sentence: The sentence to split
        max_chars: Maximum characters per chunk

    Returns:
        List of chunks
    """
    if len(sentence) <= max_chars:
        return [sentence]

    words = sentence.split()
    chunks = []
    current_chunk = []

    for word in words:
        test_chunk = ' '.join(current_chunk + [word])
        if len(test_chunk) > max_chars and current_chunk:
            chunks.append(' '.join(current_chunk))
            current_chunk = [word]
        else:
            current_chunk.append(word)

    if current_chunk:
        chunks.append(' '.join(current_chunk))

    return chunks


def normalize_word(word):
    """Remove punctuation and lowercase for comparison"""
    return re.sub(r'[^\w\s]', '', word.lower())


def edit_distance(s1, s2):
    """Calculate Levenshtein distance between two strings"""
    if len(s1) < len(s2):
        return edit_distance(s2, s1)
    if len(s2) == 0:
        return len(s1)

    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]


def find_best_match(target_word, whisper_words_norm, start_idx, search_window=20):
    """Find best matching word within search window using fuzzy matching

    Args:
        target_word: Normalized word from user's text to match
        whisper_words_norm: List of normalized Whisper words
        start_idx: Index to start searching from
        search_window: How many words ahead to search

    Returns:
        Tuple of (best_match_index, edit_distance) or (None, inf) if no match
    """
    if not target_word:
        return None, float('inf')

    end_idx = min(start_idx + search_window, len(whisper_words_norm))
    best_idx = None
    best_distance = float('inf')

    for idx in range(start_idx, end_idx):
        whisper_word = whisper_words_norm[idx]

        # Try exact match first
        if whisper_word == target_word:
            return idx, 0

        # Calculate edit distance for fuzzy match
        dist = edit_distance(target_word, whisper_word)

        # Only consider as match if distance is small relative to word length
        max_dist = max(2, len(target_word) // 3)  # Allow up to 1/3 of chars different
        if dist < best_distance and dist <= max_dist:
            best_distance = dist
            best_idx = idx

    return best_idx, best_distance


def match_chunk_to_whisper(chunk, whisper_words, whisper_words_normalized, whisper_idx, prev_chunk_word_count=0):
    """Match a text chunk to Whisper word timings

    Args:
        chunk: Text chunk to match
        whisper_words: List of word timing dicts with 'word', 'start', 'end'
        whisper_words_normalized: List of normalized Whisper words
        whisper_idx: Current position in whisper_words
        prev_chunk_word_count: Number of words in the previous chunk (for position estimation)

    Returns:
        Tuple of (chunk_start_time, new_whisper_idx, match_found, current_chunk_word_count) or (None, whisper_idx, False, 0)
    """
    chunk_words = chunk.split()
    if not chunk_words:
        return None, whisper_idx, False, 0

    # Calculate minimum search position based on PREVIOUS chunk's word count
    # If we just matched a chunk with N words, the next chunk should be at least N/2 words ahead
    # This prevents matching common words too early (like matching the wrong "to")
    min_words_ahead = prev_chunk_word_count // 2
    min_search_idx = whisper_idx + min_words_ahead

    # Try to match first word, then fallback to next words (up to 5)
    for word_offset in range(min(5, len(chunk_words))):
        # Handle hyphenated words by taking first part
        target_word = chunk_words[word_offset].split('-')[0]
        target_word_normalized = normalize_word(target_word)

        # Try fuzzy matching with search window, starting from estimated position
        match_idx, distance = find_best_match(
            target_word_normalized,
            whisper_words_normalized,
            min_search_idx,
            search_window=20
        )

        if match_idx is not None and distance <= 2:
            # Found a match!
            if word_offset > 0 and match_idx > 0:
                # We matched 2nd+ word, use the word before it as start time
                chunk_start = whisper_words[match_idx - 1]['start']
            else:
                # We matched the first word, use it directly
                chunk_start = whisper_words[match_idx]['start']

            new_whisper_idx = match_idx + 1
            return chunk_start, new_whisper_idx, True, len(chunk_words)

    return None, whisper_idx, False, len(chunk_words)
