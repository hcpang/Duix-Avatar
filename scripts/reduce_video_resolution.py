#!/usr/bin/env python3
"""
Reduce Video Resolution

Creates a lower-resolution version of a video file for picture-in-picture (PIP) overlay.
Useful for reducing file size and processing time when the video will be displayed small.

Usage:
    python scripts/reduce_video_resolution.py INPUT_VIDEO [OUTPUT_VIDEO] [WIDTH] [HEIGHT]

Examples:
    # Create 384x512 version (default for PIP)
    python scripts/reduce_video_resolution.py inputs/AlexReference.mp4

    # Custom output path
    python scripts/reduce_video_resolution.py inputs/AlexReference.mp4 inputs/AlexReference_small.mp4

    # Custom resolution
    python scripts/reduce_video_resolution.py inputs/AlexReference.mp4 inputs/AlexReference_small.mp4 640 480
"""

import sys
import io
import os
import subprocess
from pathlib import Path

from ffmpeg_utils import find_ffmpeg, find_ffprobe

# Handle Windows encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


def get_video_info(video_path):
    """
    Get video resolution and duration.

    Args:
        video_path: Path to video file

    Returns:
        dict with width, height, duration
    """
    ffprobe = find_ffprobe()
    if not ffprobe:
        print("Error: ffprobe not found")
        return None

    cmd = [
        ffprobe,
        '-v', 'quiet',
        '-print_format', 'json',
        '-show_streams',
        video_path
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error getting video info: {result.stderr}")
        return None

    import json
    streams = json.loads(result.stdout)['streams']
    video_stream = next((s for s in streams if s['codec_type'] == 'video'), None)

    if not video_stream:
        print("Error: No video stream found")
        return None

    return {
        'width': int(video_stream['width']),
        'height': int(video_stream['height']),
        'duration': float(video_stream.get('duration', 0))
    }


def reduce_video_resolution(input_video, output_video, target_width, target_height):
    """
    Create a lower-resolution version of a video.

    Args:
        input_video: Path to input video
        output_video: Path to output video
        target_width: Target width in pixels
        target_height: Target height in pixels

    Returns:
        True if successful, False otherwise
    """
    ffmpeg = find_ffmpeg()
    if not ffmpeg:
        print("Error: ffmpeg not found")
        return False

    # Scale video maintaining aspect ratio and padding if needed
    # This ensures the output is exactly target_width x target_height
    scale_filter = f"scale={target_width}:{target_height}:force_original_aspect_ratio=decrease,pad={target_width}:{target_height}:(ow-iw)/2:(oh-ih)/2"

    cmd = [
        ffmpeg,
        '-i', input_video,
        '-vf', scale_filter,
        '-c:v', 'libx264',
        '-crf', '23',  # Quality (lower = better, 18-28 is good range)
        '-preset', 'medium',
        '-c:a', 'aac',
        '-b:a', '128k',
        '-y',  # Overwrite output file
        output_video
    ]

    print(f"Running FFmpeg command:")
    print(f"  {' '.join(cmd)}")
    print()

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"Error reducing video resolution:")
        print(result.stderr)
        return False

    return True


def main():
    if len(sys.argv) < 2:
        print("Usage: python reduce_video_resolution.py INPUT_VIDEO [OUTPUT_VIDEO] [WIDTH] [HEIGHT]")
        print()
        print("Arguments:")
        print("  INPUT_VIDEO   Path to input video file")
        print("  OUTPUT_VIDEO  Path to output video file (default: INPUT_small.mp4)")
        print("  WIDTH         Target width in pixels (default: 384)")
        print("  HEIGHT        Target height in pixels (default: 512)")
        print()
        print("Examples:")
        print("  python scripts/reduce_video_resolution.py inputs/AlexReference.mp4")
        print("  python scripts/reduce_video_resolution.py inputs/AlexReference.mp4 inputs/AlexReference_small.mp4")
        print("  python scripts/reduce_video_resolution.py inputs/AlexReference.mp4 inputs/AlexReference_small.mp4 640 480")
        sys.exit(1)

    input_video = sys.argv[1]

    # Default output path
    if len(sys.argv) > 2:
        output_video = sys.argv[2]
    else:
        input_path = Path(input_video)
        output_video = str(input_path.parent / f"{input_path.stem}_small{input_path.suffix}")

    # Default resolution (optimized for PIP overlay)
    target_width = int(sys.argv[3]) if len(sys.argv) > 3 else 384
    target_height = int(sys.argv[4]) if len(sys.argv) > 4 else 512

    # Validate input
    if not os.path.exists(input_video):
        print(f"Error: Input video not found: {input_video}")
        sys.exit(1)

    print("=" * 60)
    print("Reduce Video Resolution")
    print("=" * 60)
    print(f"Input:  {input_video}")
    print(f"Output: {output_video}")
    print(f"Target: {target_width}x{target_height}")
    print()

    # Get input video info
    print("Analyzing input video...")
    video_info = get_video_info(input_video)

    if not video_info:
        print("Failed to get video information")
        sys.exit(1)

    print(f"  Original resolution: {video_info['width']}x{video_info['height']}")
    print(f"  Duration: {video_info['duration']:.2f}s")
    print()

    # Calculate size reduction
    original_pixels = video_info['width'] * video_info['height']
    target_pixels = target_width * target_height
    reduction = (1 - target_pixels / original_pixels) * 100

    print(f"  Pixel reduction: {reduction:.1f}%")
    print()

    # Reduce resolution
    print("Reducing resolution...")
    success = reduce_video_resolution(input_video, output_video, target_width, target_height)

    if success:
        # Get output file size
        input_size = os.path.getsize(input_video) / (1024 * 1024)  # MB
        output_size = os.path.getsize(output_video) / (1024 * 1024)  # MB
        size_reduction = (1 - output_size / input_size) * 100

        print()
        print("=" * 60)
        print("✓ Resolution reduction complete!")
        print("=" * 60)
        print(f"Output: {output_video}")
        print(f"Resolution: {target_width}x{target_height}")
        print(f"File size: {input_size:.2f} MB → {output_size:.2f} MB ({size_reduction:.1f}% reduction)")
        print("=" * 60)
    else:
        print()
        print("✗ Resolution reduction failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
