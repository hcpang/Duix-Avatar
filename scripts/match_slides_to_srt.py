#!/usr/bin/env python3
"""
Match slide timestamps to SRT subtitle entries.

This script reads slide timestamps and an SRT file, then matches each slide
to the text spoken during that slide's time range.
"""

import sys
import io
import os
import re
from pathlib import Path

# Handle Windows encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


def parse_srt_timestamp(timestamp_str):
    """
    Parse SRT timestamp to seconds.

    Args:
        timestamp_str: SRT timestamp like "00:00:17,000"

    Returns:
        Float seconds
    """
    # Format: HH:MM:SS,mmm
    match = re.match(r'(\d+):(\d+):(\d+),(\d+)', timestamp_str)
    if not match:
        return 0.0

    hours, minutes, seconds, millis = match.groups()
    total_seconds = int(hours) * 3600 + int(minutes) * 60 + int(seconds) + int(millis) / 1000.0
    return total_seconds


def parse_srt_file(srt_path):
    """
    Parse SRT file into list of subtitle entries.

    Args:
        srt_path: Path to SRT file

    Returns:
        List of dicts: [{'start': float, 'end': float, 'text': str}, ...]
    """
    with open(srt_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Split into subtitle blocks (separated by blank lines)
    blocks = re.split(r'\n\s*\n', content.strip())

    subtitles = []
    for block in blocks:
        lines = block.strip().split('\n')
        if len(lines) < 3:
            continue

        # Line 0: sequence number (ignore)
        # Line 1: timestamps
        # Line 2+: text

        timestamp_line = lines[1]
        match = re.match(r'([\d:,]+)\s*-->\s*([\d:,]+)', timestamp_line)
        if not match:
            continue

        start_str, end_str = match.groups()
        start_time = parse_srt_timestamp(start_str)
        end_time = parse_srt_timestamp(end_str)

        text = ' '.join(lines[2:])

        subtitles.append({
            'start': start_time,
            'end': end_time,
            'text': text
        })

    return subtitles


def read_slide_timestamps(timestamps_file):
    """
    Read slide timestamps from file.

    Args:
        timestamps_file: Path to slides_timestamps.txt

    Returns:
        List of tuples: [(slide_name, timestamp), ...]
    """
    slides = []
    with open(timestamps_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            parts = line.split()
            if len(parts) >= 2:
                slide_name = parts[0]
                timestamp = float(parts[1])
                slides.append((slide_name, timestamp))

    return slides


def match_slides_to_srt(slides, subtitles):
    """
    Match slides to subtitle text based on timestamps.

    Args:
        slides: List of (slide_name, timestamp) tuples
        subtitles: List of subtitle dicts from parse_srt_file()

    Returns:
        List of dicts: [{'slide': str, 'start': float, 'end': float, 'text': str}, ...]
    """
    results = []

    for i, (slide_name, start_time) in enumerate(slides):
        # Determine end time (next slide's start time, or last subtitle's end)
        if i + 1 < len(slides):
            end_time = slides[i + 1][1]
        else:
            # Last slide - use the end of the last subtitle
            if subtitles:
                end_time = subtitles[-1]['end']
            else:
                end_time = start_time + 10.0  # Default 10 seconds

        # Find all subtitles that overlap with this slide's time range
        slide_texts = []
        for subtitle in subtitles:
            # Check if subtitle overlaps with slide time range
            if subtitle['start'] < end_time and subtitle['end'] > start_time:
                slide_texts.append(subtitle['text'])

        combined_text = ' '.join(slide_texts).strip()

        results.append({
            'slide': slide_name,
            'start': start_time,
            'end': end_time,
            'text': combined_text,
            'word_count': len(combined_text.split()) if combined_text else 0
        })

    return results


def save_slides_with_text(results, output_file):
    """
    Save slide-text mapping to file.

    Args:
        results: List of dicts from match_slides_to_srt()
        output_file: Path to output file
    """
    with open(output_file, 'w', encoding='utf-8') as f:
        for result in results:
            # Format: slide_name|start-end|text
            f.write(f"{result['slide']}|{result['start']:.2f}-{result['end']:.2f}|{result['text']}\n")


def main():
    if len(sys.argv) < 3:
        print("Usage: python match_slides_to_srt.py TIMESTAMPS_FILE SRT_FILE [OUTPUT_FILE]")
        print()
        print("Arguments:")
        print("  TIMESTAMPS_FILE  Path to slides_timestamps.txt")
        print("  SRT_FILE         Path to SRT subtitle file")
        print("  OUTPUT_FILE      Output file (default: slides_with_text.txt)")
        print()
        print("Example:")
        print("  python match_slides_to_srt.py slides/slides_timestamps.txt video.srt")
        print()
        print("Output format (slides_with_text.txt):")
        print("  slide_001.png|0.00-17.00|Text spoken during slide 1...")
        print("  slide_002.png|17.00-47.00|Text for slide 2...")
        sys.exit(1)

    timestamps_file = sys.argv[1]
    srt_file = sys.argv[2]
    output_file = sys.argv[3] if len(sys.argv) > 3 else "slides_with_text.txt"

    print("=" * 60)
    print("Match Slides to SRT Subtitles")
    print("=" * 60)
    print(f"Timestamps: {timestamps_file}")
    print(f"SRT file: {srt_file}")
    print(f"Output: {output_file}")
    print()

    # Check files exist
    if not os.path.exists(timestamps_file):
        print(f"Error: Timestamps file not found: {timestamps_file}")
        sys.exit(1)

    if not os.path.exists(srt_file):
        print(f"Error: SRT file not found: {srt_file}")
        sys.exit(1)

    # Read slide timestamps
    print("[Step 1] Reading slide timestamps...")
    slides = read_slide_timestamps(timestamps_file)
    print(f"  ✓ Found {len(slides)} slides")

    # Parse SRT file
    print()
    print("[Step 2] Parsing SRT file...")
    subtitles = parse_srt_file(srt_file)
    print(f"  ✓ Found {len(subtitles)} subtitle entries")

    # Match slides to subtitles
    print()
    print("[Step 3] Matching slides to subtitles...")
    results = match_slides_to_srt(slides, subtitles)

    for result in results:
        print(f"  {result['slide']}: {result['word_count']} words ({result['start']:.1f}s - {result['end']:.1f}s)")
        if result['text']:
            preview = result['text'][:60] + "..." if len(result['text']) > 60 else result['text']
            print(f"    \"{preview}\"")

    # Save results
    print()
    print("[Step 4] Saving results...")
    save_slides_with_text(results, output_file)
    print(f"  ✓ Saved to: {output_file}")

    # Summary
    print()
    print("=" * 60)
    print("✓ Matching complete!")
    print("=" * 60)
    print(f"Total slides: {len(results)}")
    print(f"Total words: {sum(r['word_count'] for r in results)}")
    print(f"Output file: {output_file}")
    print("=" * 60)


if __name__ == "__main__":
    main()
