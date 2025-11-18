#!/usr/bin/env python3
"""
Revoice NotebookLM Videos

Replace the AI-generated voice in NotebookLM slideshow videos with your own TTS voice.

Orchestrates the 6-step workflow:
1. Extract slides from NotebookLM video
2. Transcribe original audio with Whisper ASR
3. Match slides to transcribed text
4. Generate TTS audio from clean user-provided text (with optional voice cloning)
5. Regenerate video with slides synchronized to new TTS audio
6. Add word-level subtitles to the final video

All outputs organized in outputs/{video_name}/ directory.
"""

import sys
import io
import os
import argparse
import subprocess
import shutil
import re
from pathlib import Path

from docker_path_utils import convert_reference_audio_path

# Handle Windows encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


def run_command(cmd, description):
    """Run a command and handle errors."""
    print(f"\n{'='*60}")
    print(f"{description}")
    print(f"{'='*60}")
    print(f"Command: {' '.join(cmd)}")
    print()

    result = subprocess.run(cmd, capture_output=True, text=True)

    # Print stdout
    if result.stdout:
        print(result.stdout)

    # Print stderr if there's an error
    if result.returncode != 0:
        print(f"\nError: Command failed with return code {result.returncode}")
        if result.stderr:
            print(result.stderr)
        sys.exit(1)

    return result.stdout


def extract_audio_path_from_output(output):
    """Extract the generated audio path from generate_from_text.py output."""
    # Look for: D:/duix_avatar_data/face2face/temp/{uuid}.wav (handles mixed slashes)
    match = re.search(r'(D:/duix_avatar_data/face2face/temp[/\\][a-f0-9\-]+\.wav)', output)
    if match:
        return match.group(1)
    return None


def main():
    parser = argparse.ArgumentParser(
        description='Replace NotebookLM AI voice with your own TTS voice',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage (default TTS voice):
  python scripts/revoice_notebooklm.py \\
    inputs/notebooklm_video.mp4 \\
    inputs/script.txt

  # With voice cloning (use your own voice):
  python scripts/revoice_notebooklm.py \\
    inputs/notebooklm_video.mp4 \\
    inputs/script.txt \\
    --reference-audio inputs/my_voice.wav \\
    --reference-text "Sample of my voice reading text"

  # With multiple reference audios (for better voice quality):
  python scripts/revoice_notebooklm.py \\
    inputs/notebooklm_video.mp4 \\
    inputs/script.txt \\
    --reference-audio "inputs/voice1.wav|||inputs/voice2.wav" \\
    --reference-text "First sample text|||Second sample text"

Output structure:
  outputs/{video_name}/
  ├── slides/                  # Extracted slides
  │   ├── slide_001.png
  │   ├── slides_timestamps.txt
  │   └── slides_with_text.txt
  ├── asr/                     # ASR transcription
  │   ├── transcription.txt
  │   └── transcription.srt
  ├── tts/                     # TTS audio
  │   └── audio.wav
  ├── final_video.mp4          # Final output (no subtitles)
  └── final_video_subtitled.mp4  # Final output (with subtitles)
"""
    )

    parser.add_argument('input_video', help='Path to NotebookLM video file')
    parser.add_argument('tts_text_file', help='Clean script text for TTS (improves quality over ASR)')
    parser.add_argument('--reference-audio', help='Your voice sample for cloning (||| separated for multiple)')
    parser.add_argument('--reference-text', help='Transcription of your voice sample (||| separated for multiple)')
    parser.add_argument('--whisper-model', default='base', help='Whisper ASR model size (default: base)')
    parser.add_argument('--output-name', help='Custom output directory name (default: based on video filename)')

    args = parser.parse_args()

    # Validate input files
    if not os.path.exists(args.input_video):
        print(f"Error: Input video not found: {args.input_video}")
        sys.exit(1)

    if not os.path.exists(args.tts_text_file):
        print(f"Error: TTS text file not found: {args.tts_text_file}")
        sys.exit(1)

    # Set up paths
    input_video_path = os.path.abspath(args.input_video)
    tts_text_path = os.path.abspath(args.tts_text_file)

    # Determine output name
    if args.output_name:
        output_name = args.output_name
    else:
        output_name = Path(args.input_video).stem

    # Create output directory structure
    output_dir = os.path.join('outputs', output_name)
    slides_dir = os.path.join(output_dir, 'slides')
    asr_dir = os.path.join(output_dir, 'asr')
    tts_dir = os.path.join(output_dir, 'tts')

    os.makedirs(slides_dir, exist_ok=True)
    os.makedirs(asr_dir, exist_ok=True)
    os.makedirs(tts_dir, exist_ok=True)

    print("="*60)
    print("REVOICE NOTEBOOKLM VIDEO")
    print("="*60)
    print(f"Input video:    {input_video_path}")
    print(f"TTS text:       {tts_text_path}")
    print(f"Output dir:     {output_dir}")
    print(f"Whisper model:  {args.whisper_model}")
    if args.reference_audio:
        print(f"Reference audio: {args.reference_audio}")
    print("="*60)

    # Step 1: Extract slides
    run_command(
        ['python', 'scripts/extract_slides.py', input_video_path, slides_dir],
        "STEP 1: Extracting slides from video"
    )

    # Step 2: Transcribe video audio
    asr_prefix = os.path.join(asr_dir, 'transcription')
    run_command(
        ['python', 'scripts/transcribe_audio.py', input_video_path, args.whisper_model, asr_prefix],
        "STEP 2: Transcribing video audio with Whisper ASR"
    )

    # Step 3: Match slides to transcription
    timestamps_file = os.path.join(slides_dir, 'slides_timestamps.txt')
    srt_file = f"{asr_prefix}.srt"
    slides_with_text_file = os.path.join(slides_dir, 'slides_with_text.txt')

    run_command(
        ['python', 'scripts/match_slides_to_srt.py', timestamps_file, srt_file, slides_with_text_file],
        "STEP 3: Matching slides to transcribed text"
    )

    # Preprocess TTS text for better pronunciation
    with open(tts_text_path, 'r', encoding='utf-8') as f:
        tts_text = f.read()

    # Replace symbols that cause TTS issues
    tts_text_processed = tts_text.replace('%', ' per cent')
    tts_text_processed = tts_text_processed.replace('-', ' ')

    # Save preprocessed text to temp file
    tts_text_processed_path = os.path.join(tts_dir, 'tts_text_processed.txt')
    with open(tts_text_processed_path, 'w', encoding='utf-8') as f:
        f.write(tts_text_processed)

    # Step 4: Generate TTS audio
    tts_cmd = ['python', 'scripts/generate_from_text.py', tts_text_processed_path, '-']

    if args.reference_audio:
        # Convert Windows path to Docker path for TTS server
        docker_ref_audio = convert_reference_audio_path(args.reference_audio)
        tts_cmd.append(docker_ref_audio)

    if args.reference_text:
        tts_cmd.append(args.reference_text)

    tts_output = run_command(tts_cmd, "STEP 4: Generating TTS audio from clean text")

    # Extract audio path from output
    temp_audio_path = extract_audio_path_from_output(tts_output)
    if not temp_audio_path:
        print("Error: Could not find generated audio path in output")
        sys.exit(1)

    # Copy TTS audio to output directory
    final_audio_path = os.path.join(tts_dir, 'audio.wav')
    shutil.copy2(temp_audio_path, final_audio_path)
    print(f"\nCopied TTS audio to: {final_audio_path}")

    # Step 5: Regenerate video with TTS audio
    final_video_path = os.path.join(output_dir, 'final_video.mp4')

    run_command(
        ['python', 'scripts/regenerate_slide_video.py', slides_with_text_file, final_audio_path, final_video_path],
        "STEP 5: Regenerating video with TTS audio"
    )

    # Step 6: Add subtitles to video
    subtitled_video_path = os.path.join(output_dir, 'final_video_subtitled.mp4')

    run_command(
        ['python', 'scripts/add_subtitles.py', final_video_path, tts_text_path, '--audio', final_audio_path, '--burn', '--font-size', '24', '--color', 'yellow'],
        "STEP 6: Adding subtitles to video"
    )

    # Print final summary
    print("\n" + "="*60)
    print("SUCCESS! NotebookLM video revoiced with subtitles!")
    print("="*60)
    print(f"Project:        {output_name}")
    print(f"Output dir:     {output_dir}")
    print()
    print(f"Videos:")
    print(f"  No subtitles: {final_video_path}")
    print(f"  With subs:    {subtitled_video_path}")
    print()
    print(f"TTS audio:      {final_audio_path}")
    print(f"Slides:         {slides_dir}")
    print(f"ASR:            {asr_dir}")
    print("="*60)
    print()
    print(f"Watch your revoiced videos:")
    print(f"  No subtitles: {final_video_path}")
    print(f"  With subs:    {subtitled_video_path}")
    print("="*60)


if __name__ == "__main__":
    main()
