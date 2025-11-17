#!/usr/bin/env python3
"""
Concatenate all podcast segments into a single MP4 file.
"""
import os
import sys
import io
import subprocess
import glob
import re
from pathlib import Path
from ffmpeg_utils import find_ffmpeg

# Set UTF-8 encoding for stdout on Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

SEGMENTS_DIR = "D:/duix_avatar_data/face2face/temp/podcast_segments"
OUTPUT_FILE = "D:/duix_avatar_data/face2face/temp/podcast_full.mp4"


def find_segments():
    """Find all segment files and sort them by number."""
    pattern = os.path.join(SEGMENTS_DIR, "segment_*_subtitled.mp4")
    files = glob.glob(pattern)

    # Sort by segment number
    def get_segment_num(filepath):
        match = re.search(r'segment_(\d+)_', filepath)
        return int(match.group(1)) if match else 0

    files.sort(key=get_segment_num)
    return files


def create_concat_file(segments):
    """Create ffmpeg concat file."""
    concat_file = os.path.join(SEGMENTS_DIR, "concat_list.txt")

    with open(concat_file, 'w', encoding='utf-8') as f:
        for segment in segments:
            # Convert to forward slashes for ffmpeg
            segment_path = segment.replace('\\', '/')
            f.write(f"file '{segment_path}'\n")

    return concat_file


def concatenate_videos(concat_file, output_file, ffmpeg_cmd):
    """Use ffmpeg to concatenate videos."""
    print(f"Concatenating {len(open(concat_file).readlines())} segments...")

    cmd = [
        ffmpeg_cmd,
        '-f', 'concat',
        '-safe', '0',
        '-i', concat_file,
        '-c', 'copy',
        '-y',  # Overwrite output file
        output_file
    ]

    print(f"Running: {' '.join(cmd)}")

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"Error: {result.stderr}")
        return False

    print(f"✓ Successfully created: {output_file}")
    return True


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Concatenate podcast segments into a single video')
    parser.add_argument('--input-dir', default=SEGMENTS_DIR,
                        help='Directory containing segment files (default: %(default)s)')
    parser.add_argument('--output', default=OUTPUT_FILE,
                        help='Output file path (default: %(default)s)')

    args = parser.parse_args()

    segments_dir = args.input_dir
    output_file = args.output

    print("=" * 60)
    print("PODCAST SEGMENT CONCATENATION")
    print("=" * 60)

    # Find ffmpeg
    ffmpeg_cmd = find_ffmpeg()
    if not ffmpeg_cmd:
        print("\nError: FFmpeg not found!")
        print("Please install FFmpeg or place it in resources/ffmpeg/win-amd64/bin/")
        return 1

    print(f"\nUsing FFmpeg: {ffmpeg_cmd}")
    print(f"Input directory: {segments_dir}")
    print(f"Output file: {output_file}")

    # Find segments using custom directory
    pattern = os.path.join(segments_dir, "segment_*_subtitled.mp4")
    files = glob.glob(pattern)

    # Sort by segment number
    def get_segment_num(filepath):
        match = re.search(r'segment_(\d+)_', filepath)
        return int(match.group(1)) if match else 0

    files.sort(key=get_segment_num)
    segments = files

    if not segments:
        print(f"Error: No segments found in {segments_dir}")
        return 1

    print(f"\nFound {len(segments)} segments:")
    for i, seg in enumerate(segments[:5]):
        print(f"  {i}: {os.path.basename(seg)}")
    if len(segments) > 5:
        print(f"  ... and {len(segments) - 5} more")

    # Create concat file in output directory
    output_dir = os.path.dirname(output_file)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    concat_file_dir = output_dir if output_dir else segments_dir
    concat_file = os.path.join(concat_file_dir, "concat_list.txt")

    with open(concat_file, 'w', encoding='utf-8') as f:
        for segment in segments:
            # Convert to forward slashes for ffmpeg
            segment_path = segment.replace('\\', '/')
            f.write(f"file '{segment_path}'\n")

    print(f"\nCreated concat list: {concat_file}")

    # Concatenate
    success = concatenate_videos(concat_file, output_file, ffmpeg_cmd)

    # Cleanup
    if os.path.exists(concat_file):
        os.remove(concat_file)

    if success:
        file_size = os.path.getsize(output_file) / (1024 * 1024)
        print(f"\nFinal video size: {file_size:.2f} MB")
        print(f"Output: {output_file}")
        return 0
    else:
        return 1


if __name__ == "__main__":
    sys.exit(main())
