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




def create_global_alignment(text, whisper_words):
    """Create global alignment between all user text words and Whisper words

    This does ONE Needleman-Wunsch alignment of the entire text, creating a mapping
    from user word positions to Whisper word positions. This is more robust than
    sequential chunk matching because errors don't propagate.

    Args:
        text: Full user text to align
        whisper_words: List of word timing dicts with 'word', 'start', 'end'

    Returns:
        List where alignment[i] = whisper_index for user_word[i], or None if no match
    """
    user_words = text.split()
    if not user_words or not whisper_words:
        return []

    user_words_norm = [normalize_word(w) for w in user_words]
    whisper_words_norm = [normalize_word(w['word']) for w in whisper_words]

    n_user = len(user_words_norm)
    n_whisper = len(whisper_words_norm)

    # Scoring parameters
    MATCH_SCORE = 10
    MISMATCH_PENALTY = -5
    GAP_PENALTY = -3

    # Initialize DP matrix
    score_matrix = [[0] * (n_whisper + 1) for _ in range(n_user + 1)]

    # Initialize first row and column (gaps)
    for i in range(1, n_user + 1):
        score_matrix[i][0] = i * GAP_PENALTY
    for j in range(1, n_whisper + 1):
        score_matrix[0][j] = j * GAP_PENALTY

    # Fill DP matrix
    for i in range(1, n_user + 1):
        user_word = user_words_norm[i - 1]
        for j in range(1, n_whisper + 1):
            whisper_word = whisper_words_norm[j - 1]

            # Calculate match/mismatch score
            if user_word == whisper_word:
                match_score = MATCH_SCORE
            else:
                # Use edit distance for partial matches
                dist = edit_distance(user_word, whisper_word)
                max_len = max(len(user_word), len(whisper_word))
                if max_len > 0 and dist <= max_len * 0.3:
                    match_score = MATCH_SCORE - dist
                else:
                    match_score = MISMATCH_PENALTY

            diagonal = score_matrix[i - 1][j - 1] + match_score
            left = score_matrix[i][j - 1] + GAP_PENALTY  # Gap in user (skip whisper word)
            up = score_matrix[i - 1][j] + GAP_PENALTY  # Gap in whisper (skip user word)

            score_matrix[i][j] = max(diagonal, left, up)

    # Backtrace to build alignment mapping
    alignment = [None] * n_user  # alignment[i] = whisper_index for user_word[i]
    i, j = n_user, n_whisper

    while i > 0 and j > 0:
        current_score = score_matrix[i][j]
        diagonal_score = score_matrix[i - 1][j - 1]
        left_score = score_matrix[i][j - 1]
        up_score = score_matrix[i - 1][j]

        user_word = user_words_norm[i - 1]
        whisper_word = whisper_words_norm[j - 1]

        # Calculate expected match score
        if user_word == whisper_word:
            expected_match = MATCH_SCORE
        else:
            dist = edit_distance(user_word, whisper_word)
            max_len = max(len(user_word), len(whisper_word))
            if max_len > 0 and dist <= max_len * 0.3:
                expected_match = MATCH_SCORE - dist
            else:
                expected_match = MISMATCH_PENALTY

        if current_score == diagonal_score + expected_match:
            # Match/mismatch - record mapping
            alignment[i - 1] = j - 1
            i -= 1
            j -= 1
        elif current_score == left_score + GAP_PENALTY:
            # Gap in user text (skip whisper word)
            j -= 1
        else:
            # Gap in whisper (skip user word, leave as None)
            i -= 1

    return alignment


def get_chunk_timing_from_alignment(chunk_start_word_idx, chunk_word_count, alignment, whisper_words):
    """Get timing for a chunk using pre-computed global alignment

    Args:
        chunk_start_word_idx: Starting word index of chunk in original text
        chunk_word_count: Number of words in the chunk
        alignment: Global alignment list from create_global_alignment()
        whisper_words: List of word timing dicts

    Returns:
        Tuple of (start_time, end_time) or (None, None) if no alignment found
    """
    if not alignment or chunk_word_count == 0:
        return None, None

    # Find first and last aligned Whisper words for this chunk
    whisper_indices = []
    for i in range(chunk_start_word_idx, min(chunk_start_word_idx + chunk_word_count, len(alignment))):
        if alignment[i] is not None:
            whisper_indices.append(alignment[i])

    if not whisper_indices:
        return None, None

    # Get timing from first and last aligned Whisper words
    first_whisper_idx = min(whisper_indices)
    last_whisper_idx = max(whisper_indices)

    start_time = whisper_words[first_whisper_idx]['start']
    end_time = whisper_words[last_whisper_idx]['end']

    return start_time, end_time


