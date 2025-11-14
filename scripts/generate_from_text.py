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


def synthesize_audio(text, reference_audio=None, reference_text=None):
    """
    Generate audio from text using TTS

    Args:
        text: Text to synthesize
        reference_audio: (Optional) Path to reference audio for voice cloning
        reference_text: (Optional) Text content of the reference audio

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
    if reference_audio and reference_text:
        tts_params["reference_audio"] = reference_audio
        tts_params["reference_text"] = reference_text
        print(f"  Using voice cloning with reference audio")

    try:
        response = requests.post(TTS_URL, json=tts_params, timeout=120)

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


def generate_video(audio_path, video_path):
    """Generate a video using the Duix Avatar API"""

    task_code = str(uuid.uuid4())

    print(f"\nSubmitting video generation task...")
    print(f"  Audio: {audio_path}")
    print(f"  Avatar: {video_path}")
    print(f"  Task Code: {task_code}")

    submit_params = {
        "audio_url": audio_path,
        "video_url": video_path,
        "code": task_code,
        "chaofen": 0,
        "watermark_switch": 0,
        "pn": 1
    }

    try:
        response = requests.post(VIDEO_SUBMIT_URL, json=submit_params, timeout=10)
        result = response.json()
        print(f"Submit Response: {json.dumps(result, indent=2)}")

        if result.get('code') != 10000:
            print(f"Error: Failed to submit task - {result.get('msg', 'Unknown error')}")
            return None

    except Exception as e:
        print(f"Error submitting request: {e}")
        return None

    # Poll for completion
    print("\nWaiting for video generation to complete...")
    max_wait_time = 600
    poll_interval = 2
    elapsed_time = 0

    while elapsed_time < max_wait_time:
        try:
            time.sleep(poll_interval)
            elapsed_time += poll_interval

            response = requests.get(f"{VIDEO_QUERY_URL}?code={task_code}", timeout=10)
            status_result = response.json()

            if status_result.get('code') == 10000:
                data = status_result.get('data', {})
                status = data.get('status')
                progress = data.get('progress', 0)
                msg = data.get('msg', '')

                if status == 1:
                    print(f"  Progress: {progress}% - {msg}")
                elif status == 2:
                    result_path = data.get('result')
                    full_path = f"D:/duix_avatar_data/face2face/{result_path}"
                    print(f"\n✓ Video generation completed!")
                    print(f"  Output: {full_path}")
                    return full_path
                elif status == 3:
                    print(f"\n✗ Video generation failed: {msg}")
                    return None

        except Exception as e:
            print(f"Error checking status: {e}")
            continue

    print(f"\n✗ Timeout: Video generation did not complete within {max_wait_time} seconds")
    return None


def main():
    if len(sys.argv) < 2:
        print("Usage: python generate_from_text.py <text_file|text|-> [avatar_video] [reference_audio] [reference_text]")
        print("\nExamples:")
        print('  # From text file:')
        print('  python generate_from_text.py my_script.txt')
        print()
        print('  # From text directly:')
        print('  python generate_from_text.py "Hello world!"')
        print()
        print('  # From stdin:')
        print('  echo "Hello world" | python generate_from_text.py -')
        print()
        print('  # With custom avatar:')
        print('  python generate_from_text.py my_script.txt /code/data/temp/avatar.mp4')
        print("\nParameters:")
        print("  text_file: Path to text file, direct text, or '-' for stdin")
        print("  avatar_video: (Optional) Path to avatar video (default: /code/data/temp/20251113182348159.mp4)")
        print("  reference_audio: (Optional) Path to reference audio for voice cloning")
        print("  reference_text: (Optional) Text from reference audio")
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

    # Get avatar video (default or from args)
    avatar_video = sys.argv[2] if len(sys.argv) > 2 else "/code/data/temp/20251113182348159.mp4"

    # Get reference audio/text (optional)
    reference_audio = sys.argv[3] if len(sys.argv) > 3 else None
    reference_text = sys.argv[4] if len(sys.argv) > 4 else None

    # Step 1: Synthesize audio
    audio_path = synthesize_audio(text, reference_audio, reference_text)
    if not audio_path:
        print("Failed to synthesize audio")
        sys.exit(1)

    # Convert to container path (normalize Windows backslashes to forward slashes first)
    audio_path_normalized = audio_path.replace("\\", "/")
    audio_container_path = audio_path_normalized.replace("D:/duix_avatar_data/face2face", "/code/data")

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
