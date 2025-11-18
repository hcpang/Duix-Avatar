#!/usr/bin/env python3
"""
Convert Portrait Video to Landscape

Crops and scales a portrait/vertical video to landscape/horizontal orientation.
Useful for converting avatar videos for picture-in-picture overlay.

Usage:
    python scripts/convert_to_landscape.py INPUT_VIDEO OUTPUT_VIDEO [WIDTH] [HEIGHT]

Examples:
    # Convert to default landscape size (512x288)
    python scripts/convert_to_landscape.py avatar_portrait.mp4 avatar_landscape.mp4

    # Custom landscape size
    python scripts/convert_to_landscape.py avatar_portrait.mp4 avatar_landscape.mp4 640 360
"""

import sys
import io
import os
import subprocess

from ffmpeg_utils import find_ffmpeg, find_ffprobe

# Handle Windows encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


def get_video_dimensions(video_path):
    """Get video width and height."""
    ffprobe = find_ffprobe()
    if not ffprobe:
        return None, None

    cmd = [
        ffprobe,
        '-v', 'quiet',
        '-print_format', 'json',
        '-show_streams',
        video_path
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return None, None

    import json
    streams = json.loads(result.stdout)['streams']
    video_stream = next((s for s in streams if s['codec_type'] == 'video'), None)

    if not video_stream:
        return None, None

    return int(video_stream['width']), int(video_stream['height'])


def main():
    if len(sys.argv) < 3:
        print("Usage: python convert_to_landscape.py INPUT_VIDEO OUTPUT_VIDEO [WIDTH] [HEIGHT]")
        print()
        print("Arguments:")
        print("  INPUT_VIDEO   Path to portrait/vertical video")
        print("  OUTPUT_VIDEO  Path to output landscape video")
        print("  WIDTH         Optional: Output width (default: 512)")
        print("  HEIGHT        Optional: Output height (default: 288)")
        print()
        print("Examples:")
        print("  python scripts/convert_to_landscape.py avatar.mp4 avatar_landscape.mp4")
        print("  python scripts/convert_to_landscape.py avatar.mp4 avatar_landscape.mp4 640 360")
        sys.exit(1)

    input_video = sys.argv[1]
    output_video = sys.argv[2]
    output_width = int(sys.argv[3]) if len(sys.argv) > 3 else 512
    output_height = int(sys.argv[4]) if len(sys.argv) > 4 else 288

    # Validate input
    if not os.path.exists(input_video):
        print(f"Error: Input video not found: {input_video}")
        sys.exit(1)

    ffmpeg = find_ffmpeg()
    if not ffmpeg:
        print("Error: ffmpeg not found")
        sys.exit(1)

    print("=" * 60)
    print("Convert Portrait Video to Landscape")
    print("=" * 60)
    print(f"Input:  {input_video}")
    print(f"Output: {output_video}")
    print(f"Target: {output_width}x{output_height}")
    print()

    # Get input dimensions
    in_width, in_height = get_video_dimensions(input_video)
    if in_width and in_height:
        print(f"Input resolution: {in_width}x{in_height}")
        print()
    else:
        in_width, in_height = 384, 512  # Default for portrait

    # Calculate crop dimensions to match target aspect ratio
    target_aspect = output_width / output_height
    input_aspect = in_width / in_height

    if input_aspect > target_aspect:
        # Input is wider, crop width
        crop_height = in_height
        crop_width = int(crop_height * target_aspect)
    else:
        # Input is taller, crop height
        crop_width = in_width
        crop_height = int(crop_width / target_aspect)

    # FFmpeg filter: crop to target aspect ratio, then scale
    filter_complex = f"crop={crop_width}:{crop_height}:(iw-{crop_width})/2:(ih-{crop_height})/2,scale={output_width}:{output_height}"

    cmd = [
        ffmpeg,
        '-i', input_video,
        '-vf', filter_complex,
        '-c:v', 'libx264',
        '-crf', '23',
        '-preset', 'medium',
        '-c:a', 'copy',
        '-y',
        output_video
    ]

    print(f"Running FFmpeg command:")
    print(f"  {' '.join(cmd)}")
    print()

    result = subprocess.run(cmd)

    if result.returncode != 0:
        print()
        print("✗ Conversion failed")
        sys.exit(1)

    # Get output file size
    output_size = os.path.getsize(output_video) / (1024 * 1024)

    print()
    print("=" * 60)
    print("✓ Video converted to landscape!")
    print("=" * 60)
    print(f"Output: {output_video}")
    print(f"Resolution: {output_width}x{output_height}")
    print(f"Size: {output_size:.2f} MB")
    print("=" * 60)


if __name__ == "__main__":
    main()
