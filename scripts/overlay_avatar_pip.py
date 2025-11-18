#!/usr/bin/env python3
"""
Overlay Avatar Video with Picture-in-Picture (PIP)

Usage:
    python scripts/overlay_avatar_pip.py SLIDE_VIDEO AVATAR_VIDEO OUTPUT [WIDTH] [HEIGHT]

Examples:
    python scripts/overlay_avatar_pip.py slides.mp4 avatar.mp4 output.mp4
    python scripts/overlay_avatar_pip.py slides.mp4 avatar.mp4 output.mp4 384 512
"""

import sys
import io
import os
import subprocess

from ffmpeg_utils import find_ffmpeg

# Handle Windows encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


def main():
    if len(sys.argv) < 4:
        print("Usage: python overlay_avatar_pip.py SLIDE_VIDEO AVATAR_VIDEO OUTPUT [WIDTH] [HEIGHT]")
        print()
        print("Arguments:")
        print("  SLIDE_VIDEO   Path to slide/main video")
        print("  AVATAR_VIDEO  Path to avatar video to overlay")
        print("  OUTPUT        Output path")
        print("  WIDTH         Optional: Avatar width (default: 288)")
        print("  HEIGHT        Optional: Avatar height (default: 384)")
        print()
        print("Examples:")
        print("  python scripts/overlay_avatar_pip.py slides.mp4 avatar.mp4 output.mp4")
        print("  python scripts/overlay_avatar_pip.py slides.mp4 avatar.mp4 output.mp4 384 512")
        sys.exit(1)

    slide_video = sys.argv[1]
    avatar_video = sys.argv[2]
    output_path = sys.argv[3]
    avatar_width = int(sys.argv[4]) if len(sys.argv) > 4 else 288
    avatar_height = int(sys.argv[5]) if len(sys.argv) > 5 else 384

    # Validate inputs
    if not os.path.exists(slide_video):
        print(f"Error: Slide video not found: {slide_video}")
        sys.exit(1)

    if not os.path.exists(avatar_video):
        print(f"Error: Avatar video not found: {avatar_video}")
        sys.exit(1)

    ffmpeg = find_ffmpeg()
    if not ffmpeg:
        print("Error: ffmpeg not found")
        sys.exit(1)

    print("=" * 60)
    print("Overlay Avatar Video (Picture-in-Picture)")
    print("=" * 60)
    print(f"Slide video:  {slide_video}")
    print(f"Avatar video: {avatar_video}")
    print(f"Output:       {output_path}")
    print(f"Avatar size:  {avatar_width}x{avatar_height}")
    print("=" * 60)
    print()

    # FFmpeg overlay filter: overlay avatar as-is (no scaling to preserve aspect ratio)
    filter_complex = "[0:v][1:v]overlay=W-w-20:20"

    cmd = [
        ffmpeg,
        '-i', slide_video,
        '-i', avatar_video,
        '-filter_complex', filter_complex,
        '-c:a', 'copy',
        '-y',
        output_path
    ]

    print(f"Running FFmpeg command:")
    print(f"  {' '.join(cmd)}")
    print()

    result = subprocess.run(cmd)

    if result.returncode != 0:
        print()
        print("✗ Overlay failed")
        sys.exit(1)

    output_size = os.path.getsize(output_path) / (1024 * 1024)
    print()
    print("=" * 60)
    print("✓ Picture-in-picture overlay complete!")
    print("=" * 60)
    print(f"Output: {output_path}")
    print(f"Size: {output_size:.2f} MB")
    print("=" * 60)


if __name__ == "__main__":
    main()
