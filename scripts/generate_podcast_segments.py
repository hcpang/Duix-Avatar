#!/usr/bin/env python3
"""
Generate individual video segments from a labeled podcast transcript.
Each segment is generated with the appropriate avatar voice and includes burned-in subtitles.
"""

import re
import os
import sys
import io
import json
import requests
import time
import uuid
import subprocess

from docker_path_utils import to_docker_path

# Set UTF-8 encoding for stdout on Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# API endpoints
TTS_URL = "http://127.0.0.1:18180/v1/invoke"
VIDEO_SUBMIT_URL = "http://127.0.0.1:8383/easy/submit"
VIDEO_QUERY_URL = "http://127.0.0.1:8383/easy/query"

# Avatar configurations from AVATARS.md
AVATARS = {
    "Alex": {
        "reference_video": "/code/data/temp/20251115031020305.mp4",
        "reference_audio": "/code/data/origin_audio/format_denoise_20251115135836064.wav",
        "reference_text": "So they took it fun and the snowy days, and then it's got a big Christmas, and I'm going to have a Santa Claus. And then I'm going to have a wonderful day on spring, which is a check with what's my present, and then it'll be summer so I can roll, roll, roll your boat, and then fall, which is...",
        "temperature": 0.7
    },
    "Alex2": {
        "reference_video": "/code/data/temp/20251115031020305.mp4",
        "reference_audio": "/code/data/origin_audio/format_denoise_20251114215242697.wav",
        "reference_text": "这是我吗？嗯，of course， of course，我而我好想very fun。 by you妹妹哦，好好裤子trust出嗯中午。",
        "temperature": 0.7
    },
    "Evan": {
        "reference_video": "/code/data/temp/20251115000845014.mp4",
        "reference_audio": "/code/data/origin_audio/format_denoise_20251115000845014.wav",
        "reference_text": "Dear Coach George, thank you for teaching me how to snowboard and encouraging me to go on harder. I really appreciate you teaching and guiding me to where I am now.",
        "temperature": 0.95
    }
}

DATA_DIR = "D:/duix_avatar_data/face2face/temp"
OUTPUT_DIR = os.path.join(DATA_DIR, "podcast_segments")


def parse_labeled_transcript(file_path):
    """
    Parse a labeled transcript file and extract segments.

    Returns:
        List of dicts with 'speaker' and 'text' keys
    """
    segments = []
    current_speaker = None
    current_text = []

    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()

            # Check for speaker marker
            match = re.match(r'\[Speaker \d+ - (Alex|Evan)\]', line)
            if match:
                # Save previous segment if exists
                if current_speaker and current_text:
                    segments.append({
                        'speaker': current_speaker,
                        'text': ' '.join(current_text).strip()
                    })
                    current_text = []

                # Start new segment
                current_speaker = match.group(1)
            elif line and current_speaker:
                # Accumulate text for current segment
                current_text.append(line)

        # Save final segment
        if current_speaker and current_text:
            segments.append({
                'speaker': current_speaker,
                'text': ' '.join(current_text).strip()
            })

    return segments


def synthesize_audio(text, avatar_name):
    """
    Generate audio from text using TTS with avatar's voice.

    Returns:
        Path to generated audio file if successful, None otherwise
    """
    print(f"  Synthesizing audio with {avatar_name}'s voice...")
    print(f"    Text length: {len(text)} characters")

    avatar = AVATARS[avatar_name]
    speaker_id = str(uuid.uuid4())

    tts_params = {
        "speaker": speaker_id,
        "text": text,
        "format": "wav",
        "reference_audio": avatar["reference_audio"],
        "reference_text": avatar["reference_text"],
        "topP": 0.7,
        "max_new_tokens": 2048,
        "chunk_length": 200,
        "repetition_penalty": 1.2,
        "temperature": avatar["temperature"],
        "need_asr": False,
        "streaming": False,
        "is_fixed_seed": 0,
        "is_norm": 0
    }

    print(f"    Using temperature: {avatar['temperature']}")

    try:
        response = requests.post(TTS_URL, json=tts_params, timeout=600)

        if response.status_code == 200:
            audio_filename = f"{speaker_id}.wav"
            audio_path = os.path.join(DATA_DIR, audio_filename)

            with open(audio_path, 'wb') as f:
                f.write(response.content)

            print(f"    ✓ Audio synthesized: {audio_path}")
            return audio_path
        else:
            print(f"    Error: TTS returned status code {response.status_code}")
            return None
    except Exception as e:
        print(f"    Error synthesizing audio: {e}")
        return None


def generate_video(audio_path, avatar_name):
    """
    Generate a video using the Duix Avatar API.

    Returns:
        Path to generated video if successful, None otherwise
    """
    avatar = AVATARS[avatar_name]
    task_code = str(uuid.uuid4())

    print(f"  Submitting video generation...")

    # Convert to container path
    audio_container_path = to_docker_path(audio_path)

    submit_params = {
        "audio_url": audio_container_path,
        "video_url": avatar["reference_video"],
        "code": task_code,
        "chaofen": 0,
        "watermark_switch": 0,
        "pn": 1
    }

    # Retry submission indefinitely if service is busy
    submit_retry_delay = 15  # seconds
    attempt = 0

    while True:
        try:
            response = requests.post(VIDEO_SUBMIT_URL, json=submit_params, timeout=10)
            result = response.json()

            if result.get('code') == 10000:
                # Successfully submitted
                print(f"    ✓ Task submitted")
                break
            elif '忙碌' in str(result.get('msg', '')):
                # Service is busy, wait and retry
                attempt += 1
                print(f"    Service busy, waiting {submit_retry_delay}s... (attempt {attempt})")
                time.sleep(submit_retry_delay)
                continue
            else:
                print(f"    Error: Failed to submit task - {result.get('msg', 'Unknown error')}")
                return None

        except Exception as e:
            attempt += 1
            print(f"    Error submitting request: {e}, retrying in {submit_retry_delay}s... (attempt {attempt})")
            time.sleep(submit_retry_delay)
            continue

    # Poll for completion
    print(f"    Waiting for video generation...")
    max_wait_time = 600
    poll_interval = 2
    elapsed_time = 0

    try:
        while elapsed_time < max_wait_time:
            time.sleep(poll_interval)
            elapsed_time += poll_interval

            response = requests.get(f"{VIDEO_QUERY_URL}?code={task_code}", timeout=10)
            status_result = response.json()

            if status_result.get('code') == 10000:
                data = status_result.get('data', {})
                status = data.get('status')
                progress = data.get('progress', 0)

                if status == 1:
                    if progress % 20 == 0:  # Print every 20%
                        print(f"      Progress: {progress}%")
                elif status == 2:
                    result_path = data.get('result')
                    print(f"    DEBUG: API returned result_path = '{result_path}'")
                    # Strip leading slash and add /temp/ prefix
                    result_path = result_path.lstrip('/')
                    full_path = os.path.normpath(f"D:/duix_avatar_data/face2face/temp/{result_path}")
                    print(f"    ✓ Video generated: {full_path}")
                    return full_path
                elif status == 3:
                    print(f"    ✗ Video generation failed")
                    return None

        print(f"    ✗ Timeout")
        return None

    except Exception as e:
        print(f"    Error: {e}")
        return None


def add_subtitles(video_path, audio_path, text, segment_num):
    """
    Add burned-in subtitles to a video segment.

    Args:
        video_path: Path to the video file
        audio_path: Path to the audio file
        text: Text content for subtitles
        segment_num: Segment number for naming temp files

    Returns:
        Path to subtitled video if successful, None otherwise
    """
    print(f"  Adding subtitles...")

    # Create temporary text file for this segment
    text_file = os.path.join(OUTPUT_DIR, f"segment_{segment_num:03d}_text.txt")
    with open(text_file, 'w', encoding='utf-8') as f:
        f.write(text)

    try:
        cmd = [
            "python", "scripts/add_subtitles.py",
            video_path,
            text_file,
            "--audio", audio_path,
            "--burn",
            "--font-size", "24",
            "--color", "yellow"
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300, encoding='utf-8')

        # Log any errors from the subprocess
        if result.returncode != 0:
            print(f"    Error: add_subtitles.py failed with return code {result.returncode}")
            if result.stdout:
                print(f"    STDOUT: {result.stdout}")
            if result.stderr:
                print(f"    STDERR: {result.stderr}")
            return None

        # The subtitled video should be at video_path.replace(".mp4", "_subtitled.mp4")
        subtitled_path = video_path.replace(".mp4", "_subtitled.mp4")

        if os.path.exists(subtitled_path):
            print(f"    ✓ Subtitles added: {subtitled_path}")

            # Clean up temp text file
            os.remove(text_file)

            return subtitled_path
        else:
            print(f"    Error: Subtitled video not found at {subtitled_path}")
            print(f"    STDOUT: {result.stdout}")
            print(f"    STDERR: {result.stderr}")
            return None

    except Exception as e:
        print(f"    Error adding subtitles: {e}")
        return None


def main():
    if len(sys.argv) < 2:
        print("Usage: python generate_podcast_segments.py <labeled_transcript_file> [start_segment] [end_segment]")
        print("\nExample:")
        print("  python generate_podcast_segments.py deep_dive_trading_labeled.txt")
        print("  python generate_podcast_segments.py deep_dive_trading_labeled.txt 0 5  # Generate first 5 segments")
        sys.exit(1)

    transcript_file = sys.argv[1]
    start_segment = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    end_segment = int(sys.argv[3]) if len(sys.argv) > 3 else None

    # Create output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Parse transcript
    print(f"Parsing transcript: {transcript_file}")
    segments = parse_labeled_transcript(transcript_file)
    print(f"Found {len(segments)} segments")

    # Apply segment range filter
    if end_segment is not None:
        segments = segments[start_segment:end_segment]
    else:
        segments = segments[start_segment:]

    print(f"Generating {len(segments)} segments (starting from segment {start_segment})\n")

    # Generate each segment
    results = []
    for i, segment in enumerate(segments):
        segment_num = start_segment + i
        speaker = segment['speaker']
        text = segment['text']

        print(f"[{segment_num + 1}/{len(segments) + start_segment}] Generating segment with {speaker}")
        print(f"  Text preview: {text[:100]}...")

        # Step 1: Synthesize audio
        audio_path = synthesize_audio(text, speaker)
        if not audio_path:
            print(f"  ✗ Failed to synthesize audio, skipping segment")
            continue

        # Step 2: Generate video
        video_path = generate_video(audio_path, speaker)
        if not video_path:
            print(f"  ✗ Failed to generate video, skipping segment")
            continue

        # Step 3: Add subtitles
        subtitled_path = add_subtitles(video_path, audio_path, text, segment_num)
        if not subtitled_path:
            print(f"  ✗ Failed to add subtitles, skipping segment")
            continue

        # Move to output directory with numbered filename
        final_filename = f"segment_{segment_num:03d}_{speaker.lower()}_subtitled.mp4"
        final_path = os.path.join(OUTPUT_DIR, final_filename)

        # Copy the file (keep original in temp as well)
        import shutil
        shutil.copy2(subtitled_path, final_path)

        print(f"  ✓ Segment complete: {final_path}\n")

        results.append({
            'segment_num': segment_num,
            'speaker': speaker,
            'audio': audio_path,
            'video': video_path,
            'subtitled': final_path
        })

    # Print summary
    print(f"\n{'='*60}")
    print(f"Generation Complete!")
    print(f"  Total segments: {len(results)}")
    print(f"  Output directory: {OUTPUT_DIR}")
    print(f"{'='*60}\n")

    # Save manifest
    manifest_path = os.path.join(OUTPUT_DIR, "manifest.json")
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"Manifest saved: {manifest_path}")


if __name__ == "__main__":
    main()
