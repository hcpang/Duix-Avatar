#!/usr/bin/env python3
"""
Extract unique slides from a video (e.g., NotebookLM generated slideshows).

This script extracts frames from a video at regular intervals and saves only
the unique slides by detecting significant visual changes between frames.
"""

import sys
import io
import os
import subprocess
import tempfile
import shutil
from PIL import Image
import numpy as np
from pathlib import Path

# Handle Windows encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from ffmpeg_utils import find_ffmpeg


def extract_frames(video_path, output_dir, fps=1):
    """
    Extract frames from video at specified FPS.

    Args:
        video_path: Path to input video
        output_dir: Directory to save frames
        fps: Frames per second to extract (default: 1 frame per second)
    """
    ffmpeg_cmd = find_ffmpeg()

    # Create output directory
    os.makedirs(output_dir, exist_ok=True)

    # Extract frames at specified FPS
    output_pattern = os.path.join(output_dir, "frame_%05d.png")

    cmd = [
        ffmpeg_cmd,
        "-i", video_path,
        "-vf", f"fps={fps}",
        "-q:v", "2",  # High quality
        output_pattern
    ]

    print(f"  Extracting frames at {fps} FPS...")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        raise Exception(f"Failed to extract frames: {result.stderr}")

    # Get list of extracted frames
    frames = sorted([f for f in os.listdir(output_dir) if f.startswith("frame_")])
    print(f"  ✓ Extracted {len(frames)} frames")

    return [os.path.join(output_dir, f) for f in frames]


def compare_images(img1_path, img2_path, threshold=0.02):
    """
    Compare two images and return True if they are significantly different.

    Args:
        img1_path: Path to first image
        img2_path: Path to second image
        threshold: Difference threshold (0-1, lower = more similar required)

    Returns:
        True if images are different, False if similar
    """
    # Load images
    img1 = Image.open(img1_path).convert('RGB')
    img2 = Image.open(img2_path).convert('RGB')

    # Resize to same size if needed
    if img1.size != img2.size:
        img2 = img2.resize(img1.size)

    # Convert to numpy arrays
    arr1 = np.array(img1, dtype=np.float32)
    arr2 = np.array(img2, dtype=np.float32)

    # Calculate mean absolute difference
    diff = np.abs(arr1 - arr2) / 255.0
    mean_diff = np.mean(diff)

    return mean_diff > threshold


def extract_unique_slides(video_path, output_dir, fps=1, threshold=0.02):
    """
    Extract unique slides from a video with timestamps.

    Args:
        video_path: Path to input video
        output_dir: Directory to save unique slides
        fps: Frames per second to sample (default: 1)
        threshold: Difference threshold for detecting slide changes (default: 0.02)

    Returns:
        List of tuples: [(slide_path, timestamp), ...]
    """
    print("=" * 60)
    print("Unique Slide Extraction")
    print("=" * 60)
    print(f"Input: {video_path}")
    print(f"Output: {output_dir}")
    print(f"Sampling: {fps} FPS")
    print(f"Threshold: {threshold}")
    print()

    # Create temp directory for all frames
    with tempfile.TemporaryDirectory() as temp_dir:
        print("[Step 1] Extracting frames from video...")
        frames = extract_frames(video_path, temp_dir, fps)

        if not frames:
            print("No frames extracted!")
            return []

        print()
        print("[Step 2] Detecting unique slides...")

        # Create output directory
        os.makedirs(output_dir, exist_ok=True)

        # Always save first frame as first slide
        unique_slides = []
        slide_num = 1

        # Extract frame number from filename (frame_00001.png -> 1)
        first_frame_num = int(os.path.basename(frames[0]).split('_')[1].split('.')[0])
        first_timestamp = (first_frame_num - 1) / fps  # Convert to seconds

        first_slide_path = os.path.join(output_dir, f"slide_{slide_num:03d}.png")
        shutil.copy2(frames[0], first_slide_path)
        unique_slides.append((first_slide_path, first_timestamp))
        print(f"  Slide {slide_num}: {os.path.basename(frames[0])} at {first_timestamp:.2f}s")

        # Compare each frame with the last unique slide
        last_unique_frame = frames[0]

        for i, frame in enumerate(frames[1:], start=1):
            if compare_images(last_unique_frame, frame, threshold):
                # Found a new unique slide
                slide_num += 1

                # Calculate timestamp from frame number
                frame_num = int(os.path.basename(frame).split('_')[1].split('.')[0])
                timestamp = (frame_num - 1) / fps

                slide_path = os.path.join(output_dir, f"slide_{slide_num:03d}.png")
                shutil.copy2(frame, slide_path)
                unique_slides.append((slide_path, timestamp))
                last_unique_frame = frame
                print(f"  Slide {slide_num}: {os.path.basename(frame)} at {timestamp:.2f}s")

        print()
        print("=" * 60)
        print(f"✓ Extracted {len(unique_slides)} unique slides")
        print("=" * 60)

        return unique_slides


def main():
    if len(sys.argv) < 2:
        print("Usage: python extract_slides.py VIDEO_PATH [OUTPUT_DIR] [FPS] [THRESHOLD]")
        print()
        print("Arguments:")
        print("  VIDEO_PATH    Path to input video file")
        print("  OUTPUT_DIR    Directory to save slides (default: video_name_slides/)")
        print("  FPS           Sampling rate in frames per second (default: 1)")
        print("  THRESHOLD     Change detection threshold 0-1 (default: 0.02)")
        print()
        print("Example:")
        print("  python extract_slides.py inputs/video.mp4 outputs/slides 1 0.02")
        sys.exit(1)

    video_path = sys.argv[1]

    # Default output directory based on video name
    video_name = Path(video_path).stem
    default_output = f"{video_name}_slides"

    output_dir = sys.argv[2] if len(sys.argv) > 2 else default_output
    fps = float(sys.argv[3]) if len(sys.argv) > 3 else 1.0
    threshold = float(sys.argv[4]) if len(sys.argv) > 4 else 0.02

    if not os.path.exists(video_path):
        print(f"Error: Video file not found: {video_path}")
        sys.exit(1)

    unique_slides = extract_unique_slides(video_path, output_dir, fps, threshold)

    # Save timestamps to file
    timestamps_file = os.path.join(output_dir, "slides_timestamps.txt")
    with open(timestamps_file, 'w', encoding='utf-8') as f:
        for slide_path, timestamp in unique_slides:
            slide_name = os.path.basename(slide_path)
            f.write(f"{slide_name} {timestamp:.2f}\n")

    print()
    print("=" * 60)
    print("Output files:")
    print("=" * 60)
    print(f"Slides directory: {output_dir}")
    print(f"Timestamps file: {timestamps_file}")
    print()
    print("Slides with timestamps:")
    for slide_path, timestamp in unique_slides:
        print(f"  {os.path.basename(slide_path)}: {timestamp:.2f}s")
    print("=" * 60)


if __name__ == "__main__":
    main()
