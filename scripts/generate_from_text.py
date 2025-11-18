#!/usr/bin/env python3
"""
Complete Duix Avatar Video Generation from Text
1. Synthesizes audio from text using TTS
2. Generates video with the avatar speaking
"""

import requests
import time
import uuid
import sys
import json
import os
import io

from docker_path_utils import to_docker_path
from avatar_video_utils import generate_video

# Set UTF-8 encoding for stdout on Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# API endpoints
TTS_URL = "http://127.0.0.1:18180/v1/invoke"
VIDEO_SUBMIT_URL = "http://127.0.0.1:8383/easy/submit"
VIDEO_QUERY_URL = "http://127.0.0.1:8383/easy/query"

# Default paths
DATA_DIR = "D:/duix_avatar_data/face2face/temp"


def synthesize_audio(text, reference_audios=None, reference_texts=None):
    """
    Generate audio from text using TTS

    Args:
        text: Text to synthesize
        reference_audios: (Optional) List of paths to reference audios for voice cloning
        reference_texts: (Optional) List of text contents of the reference audios

    Returns:
        Path to generated audio file if successful, None otherwise
    """
    print(f"Synthesizing audio from text...")
    print(f"  Text length: {len(text)} characters")
    if len(text) > 100:
        print(f"  Preview: {text[:100]}...")
    else:
        print(f"  Text: {text}")

    speaker_id = str(uuid.uuid4())

    tts_params = {
        "speaker": speaker_id,
        "text": text,
        "format": "wav",
        "topP": 0.7,
        "max_new_tokens": 2048,
        "chunk_length": 200,
        "repetition_penalty": 1.2,
        "temperature": 0.7,
        "need_asr": False,
        "streaming": False,
        "is_fixed_seed": 0,
        "is_norm": 0
    }

    # Add reference audio only if provided
    if reference_audios and reference_texts:
        # Join multiple reference audios/texts with |||
        tts_params["reference_audio"] = "|||".join(reference_audios)
        tts_params["reference_text"] = "|||".join(reference_texts)
        print(f"  Using voice cloning with {len(reference_audios)} reference audio(s)")
        for i, audio in enumerate(reference_audios, 1):
            print(f"    {i}. {audio}")

    try:
        response = requests.post(TTS_URL, json=tts_params, timeout=10800)  # 3 hours for long texts

        # The response should be the audio file
        if response.status_code == 200:
            # Save the audio file
            audio_filename = f"{speaker_id}.wav"
            audio_path = os.path.join(DATA_DIR, audio_filename)

            with open(audio_path, 'wb') as f:
                f.write(response.content)

            print(f"✓ Audio synthesized: {audio_path}")
            return audio_path
        else:
            print(f"Error: TTS returned status code {response.status_code}")
            print(f"Response: {response.text}")
            return None

    except Exception as e:
        print(f"Error synthesizing audio: {e}")
        return None


# generate_video function now imported from avatar_video_utils


def main():
    if len(sys.argv) < 2:
        print("Usage: python generate_from_text.py <text_file|text|-> [avatar_video] [ref_audio1|||ref_audio2|||...] [ref_text1|||ref_text2|||...]")
        print("\nExamples:")
        print('  # From text file:')
        print('  python generate_from_text.py my_script.txt')
        print()
        print('  # From text directly:')
        print('  python generate_from_text.py "Hello world!"')
        print()
        print('  # With single reference audio:')
        print('  python generate_from_text.py my_script.txt /code/data/temp/avatar.mp4 \\')
        print('    /code/data/origin_audio/ref.wav "Reference text"')
        print()
        print('  # With multiple reference audios (||| separated):')
        print('  python generate_from_text.py my_script.txt /code/data/temp/avatar.mp4 \\')
        print('    "/code/data/origin_audio/ref1.wav|||/code/data/origin_audio/ref2.wav" \\')
        print('    "Reference text 1|||Reference text 2"')
        print()
        print('  # TTS only (no video generation):')
        print('  python generate_from_text.py my_script.txt - \\')
        print('    /code/data/origin_audio/ref.wav "Reference text"')
        print("\nParameters:")
        print("  text_file: Path to text file, direct text, or '-' for stdin")
        print("  avatar_video: (Optional) Path to avatar video, or '-'/'none' to skip video generation")
        print("  reference_audios: (Optional) ||| separated paths to reference audios for voice cloning")
        print("  reference_texts: (Optional) ||| separated texts from reference audios")
        sys.exit(1)

    # Get text input
    text_input = sys.argv[1]
    if text_input == "-":
        # Read from stdin
        text = sys.stdin.read().strip()
        print("Reading text from stdin...")
    elif os.path.isfile(text_input):
        # Read from file
        with open(text_input, 'r', encoding='utf-8') as f:
            text = f.read().strip()
        print(f"Reading text from file: {text_input}")
    else:
        # Direct text
        text = text_input
        print("Using direct text input")

    print(f"Text length: {len(text)} characters")

    # Get avatar video (optional)
    avatar_video = sys.argv[2] if len(sys.argv) > 2 else None

    # Check if user wants to skip video generation
    if avatar_video and avatar_video.lower() in ['-', 'none']:
        avatar_video = None

    # Get reference audio/text (optional, ||| separated)
    reference_audios = None
    reference_texts = None

    if len(sys.argv) > 3:
        # Split ||| separated reference audios
        reference_audios = [a.strip() for a in sys.argv[3].split('|||')]

    if len(sys.argv) > 4:
        # Split ||| separated reference texts
        reference_texts = [t.strip() for t in sys.argv[4].split('|||')]

    # Validate that audio and text counts match
    if reference_audios and reference_texts:
        if len(reference_audios) != len(reference_texts):
            print(f"Error: Number of reference audios ({len(reference_audios)}) must match number of reference texts ({len(reference_texts)})")
            sys.exit(1)

    # Step 1: Synthesize audio
    audio_path = synthesize_audio(text, reference_audios, reference_texts)
    if not audio_path:
        print("Failed to synthesize audio")
        sys.exit(1)

    # If no avatar video specified, exit after TTS
    if not avatar_video:
        print(f"\n{'='*60}")
        print(f"SUCCESS! TTS audio generated:")
        print(f"  {audio_path}")
        print(f"{'='*60}")
        sys.exit(0)

    # Convert to container path
    audio_container_path = to_docker_path(audio_path)

    # Step 2: Generate video
    video_path = generate_video(audio_container_path, avatar_video)
    if video_path:
        print(f"\n{'='*60}")
        print(f"SUCCESS! Your video is ready:")
        print(f"  {video_path}")
        print(f"{'='*60}")
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
