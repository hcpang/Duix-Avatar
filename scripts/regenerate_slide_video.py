#!/usr/bin/env python3
"""
Regenerate slide video with new TTS audio.

This script takes slide images with their original text, transcribes new TTS audio,
matches the text to the new timing, and generates a video with slides synchronized
to the new audio.
"""

import sys
import io
import os
import subprocess
import tempfile
from pathlib import Path

# Handle Windows encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from ffmpeg_utils import find_ffmpeg
from transcribe_audio import transcribe_audio_file
from subtitle_utils import create_global_alignment, get_chunk_timing_from_alignment


def parse_slides_with_text(input_file):
    """
    Parse slides_with_text.txt file.

    Args:
        input_file: Path to slides_with_text.txt

    Returns:
        List of dicts: [{'slide': str, 'slide_dir': str, 'text': str}, ...]
    """
    slides = []
    slide_dir = os.path.dirname(input_file)

    with open(input_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            # Format: slide_name|start-end|text
            parts = line.split('|', 2)
            if len(parts) >= 3:
                slide_name = parts[0]
                text = parts[2]

                slides.append({
                    'slide': slide_name,
                    'slide_path': os.path.join(slide_dir, slide_name),
                    'text': text
                })

    return slides


def match_text_to_new_audio(slides, new_audio_path):
    """
    Match slide texts to new audio timing using alignment.

    Args:
        slides: List of slide dicts with 'text' field
        new_audio_path: Path to new TTS audio file

    Returns:
        List of dicts with added 'start' and 'end' fields, or None if failed
    """
    print("[Step 2] Transcribing new audio...")

    # Concatenate all slide texts
    full_text = ' '.join([s['text'] for s in slides if s['text']])

    if not full_text:
        print("  Error: No text found in slides")
        return None

    # Transcribe new audio
    result = transcribe_audio_file(new_audio_path, model_size="base", language="en")

    if not result:
        print("  Error: Failed to transcribe new audio")
        return None

    word_timings = result['word_timings']
    print(f"  ✓ Transcribed {len(word_timings)} words")

    # Create global alignment
    print()
    print("[Step 3] Aligning slide texts to new audio timing...")
    alignment = create_global_alignment(full_text, word_timings)

    if not alignment:
        print("  Error: Alignment failed")
        return None

    aligned_count = sum(1 for a in alignment if a is not None)
    total_words = len(alignment)
    print(f"  ✓ Aligned {aligned_count}/{total_words} words ({aligned_count/total_words*100:.1f}%)")

    # Match each slide's text to timing
    current_word_idx = 0
    updated_slides = []

    for slide in slides:
        if not slide['text']:
            # Empty slide - use minimal duration
            if updated_slides:
                prev_end = updated_slides[-1]['end']
                updated_slides.append({
                    **slide,
                    'start': prev_end,
                    'end': prev_end + 1.0
                })
            else:
                updated_slides.append({
                    **slide,
                    'start': 0.0,
                    'end': 1.0
                })
            continue

        slide_word_count = len(slide['text'].split())

        # Get timing for this slide's text
        start_time, end_time = get_chunk_timing_from_alignment(
            current_word_idx,
            slide_word_count,
            alignment,
            word_timings
        )

        if start_time is not None and end_time is not None:
            updated_slides.append({
                **slide,
                'start': start_time,
                'end': end_time,
                'duration': end_time - start_time
            })
        else:
            # Fallback: estimate duration
            if updated_slides:
                prev_end = updated_slides[-1]['end']
                estimated_duration = slide_word_count * 0.3  # ~300ms per word
                updated_slides.append({
                    **slide,
                    'start': prev_end,
                    'end': prev_end + estimated_duration,
                    'duration': estimated_duration
                })
            else:
                estimated_duration = slide_word_count * 0.3
                updated_slides.append({
                    **slide,
                    'start': 0.0,
                    'end': estimated_duration,
                    'duration': estimated_duration
                })

        current_word_idx += slide_word_count

    # Add 0.5s padding to the last slide to prevent abrupt ending
    if updated_slides:
        updated_slides[-1]['end'] += 0.5
        updated_slides[-1]['duration'] = updated_slides[-1]['end'] - updated_slides[-1]['start']

    # Display results
    print()
    for slide in updated_slides:
        print(f"  {slide['slide']}: {slide['start']:.2f}s - {slide['end']:.2f}s ({slide.get('duration', 0):.2f}s)")

    return updated_slides


def generate_video_from_slides(slides, audio_path, output_video):
    """
    Generate video from slides with synchronized audio.

    Args:
        slides: List of slide dicts with 'slide_path', 'start', 'end' fields
        audio_path: Path to audio file
        output_video: Path to output video file
    """
    print()
    print("[Step 4] Generating video...")

    ffmpeg_cmd = find_ffmpeg()
    if not ffmpeg_cmd:
        print("  Error: FFmpeg not found")
        return False

    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a video segment for each slide
        segment_files = []

        # Track cumulative frames to prevent rounding error accumulation
        fps = 25
        total_frames_so_far = 0

        for i, slide in enumerate(slides):
            segment_file = os.path.join(temp_dir, f"segment_{i:03d}.mp4")

            # Calculate target end time in frames (cumulative)
            target_end_frames = int(round(slide['end'] * fps))

            # This slide needs exactly this many frames to hit the target
            frames_for_this_slide = target_end_frames - total_frames_so_far

            if frames_for_this_slide <= 0:
                frames_for_this_slide = 1  # Minimum 1 frame

            # Actual duration this segment will have
            actual_duration = frames_for_this_slide / fps

            # Create video segment from image with exact frame count
            cmd = [
                ffmpeg_cmd,
                '-loop', '1',  # Loop the image
                '-framerate', str(fps),  # Input frame rate
                '-i', slide['slide_path'],  # Input image
                '-vframes', str(frames_for_this_slide),  # Exact frame count
                '-r', str(fps),  # Output frame rate
                '-vf', 'scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2',  # Scale and pad to 1920x1080
                '-c:v', 'libx264',
                '-pix_fmt', 'yuv420p',
                '-y',
                segment_file
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"  Error creating segment {i}: {result.stderr}")
                return False

            segment_files.append(segment_file)
            total_frames_so_far = target_end_frames
            print(f"  Created segment {i+1}/{len(slides)}: {actual_duration:.2f}s ({frames_for_this_slide} frames)")

        # Create concat file for ffmpeg
        concat_file = os.path.join(temp_dir, "concat.txt")
        with open(concat_file, 'w', encoding='utf-8') as f:
            for segment_file in segment_files:
                # FFmpeg concat requires forward slashes
                segment_path = segment_file.replace('\\', '/')
                f.write(f"file '{segment_path}'\n")

        # Concatenate all segments
        print()
        print("  Concatenating segments...")
        concat_output = os.path.join(temp_dir, "video_no_audio.mp4")

        cmd = [
            ffmpeg_cmd,
            '-f', 'concat',
            '-safe', '0',
            '-i', concat_file,
            '-c', 'copy',
            '-y',
            concat_output
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"  Error concatenating: {result.stderr}")
            return False

        print("  ✓ Video concatenated")

        # Add audio to video
        print()
        print("  Adding audio...")

        cmd = [
            ffmpeg_cmd,
            '-i', concat_output,
            '-i', audio_path,
            '-c:v', 'copy',
            '-c:a', 'aac',
            '-shortest',  # Match shortest stream (audio or video)
            '-y',
            output_video
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"  Error adding audio: {result.stderr}")
            return False

        print(f"  ✓ Audio added")

    return True


def main():
    if len(sys.argv) < 3:
        print("Usage: python regenerate_slide_video.py SLIDES_WITH_TEXT NEW_AUDIO [OUTPUT_VIDEO]")
        print()
        print("Arguments:")
        print("  SLIDES_WITH_TEXT  Path to slides_with_text.txt")
        print("  NEW_AUDIO         Path to new TTS audio file")
        print("  OUTPUT_VIDEO      Output video file (default: regenerated_video.mp4)")
        print()
        print("Example:")
        print("  python regenerate_slide_video.py slides_with_text.txt new_tts.wav output.mp4")
        sys.exit(1)

    slides_file = sys.argv[1]
    new_audio = sys.argv[2]
    output_video = sys.argv[3] if len(sys.argv) > 3 else "regenerated_video.mp4"

    print("=" * 60)
    print("Regenerate Slide Video with New Audio")
    print("=" * 60)
    print(f"Slides: {slides_file}")
    print(f"New audio: {new_audio}")
    print(f"Output: {output_video}")
    print()

    # Check files exist
    if not os.path.exists(slides_file):
        print(f"Error: Slides file not found: {slides_file}")
        sys.exit(1)

    if not os.path.exists(new_audio):
        print(f"Error: Audio file not found: {new_audio}")
        sys.exit(1)

    # Parse slides
    print("[Step 1] Reading slides...")
    slides = parse_slides_with_text(slides_file)
    print(f"  ✓ Found {len(slides)} slides")

    # Check slide images exist
    missing_slides = [s['slide'] for s in slides if not os.path.exists(s['slide_path'])]
    if missing_slides:
        print(f"  Error: Missing slide images: {', '.join(missing_slides)}")
        sys.exit(1)

    # Match text to new audio timing
    print()
    slides_with_timing = match_text_to_new_audio(slides, new_audio)

    if not slides_with_timing:
        print("\n✗ Failed to match text to audio")
        sys.exit(1)

    # Generate video
    success = generate_video_from_slides(slides_with_timing, new_audio, output_video)

    if success:
        print()
        print("=" * 60)
        print("✓ Video generation complete!")
        print("=" * 60)
        print(f"Output: {output_video}")
        print(f"Total slides: {len(slides_with_timing)}")
        total_duration = slides_with_timing[-1]['end'] if slides_with_timing else 0
        print(f"Duration: {total_duration:.1f}s")
        print("=" * 60)
    else:
        print("\n✗ Video generation failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
