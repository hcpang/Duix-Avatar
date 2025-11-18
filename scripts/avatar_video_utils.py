#!/usr/bin/env python3
"""
Avatar Video Generation Utilities

Shared utilities for generating avatar videos using the Duix Avatar API.
Extracted from generate_from_text.py to eliminate code duplication.
"""

import requests
import time
import uuid

# API endpoints
VIDEO_SUBMIT_URL = "http://127.0.0.1:8383/easy/submit"
VIDEO_QUERY_URL = "http://127.0.0.1:8383/easy/query"


def generate_video(audio_path, video_path, max_wait_time=10800):
    """
    Generate a video using the Duix Avatar API.

    Args:
        audio_path: Path to audio file (Docker container path)
        video_path: Path to avatar video template (Docker container path)
        max_wait_time: Maximum time to wait for completion in seconds (default: 10800 = 3 hours)

    Returns:
        Path to generated video file, or None if failed
    """
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

        # Pretty print for debugging
        import json
        print(f"Submit Response: {json.dumps(result, indent=2)}")

        if result.get('code') != 10000:
            print(f"Error: Failed to submit task - {result.get('msg', 'Unknown error')}")
            return None

    except Exception as e:
        print(f"Error submitting request: {e}")
        return None

    # Poll for completion
    print("\nWaiting for video generation to complete...")
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
