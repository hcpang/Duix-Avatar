#!/usr/bin/env python3
"""
Test Duix Avatar API endpoints
"""

import requests
import json
import sys
import io

# Set UTF-8 encoding for stdout on Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

def test_video_api():
    """Test video generation API"""
    print("Testing Video Generation API...")
    try:
        response = requests.get("http://127.0.0.1:8383/easy/query?code=test", timeout=5)
        print(f"  ✓ Video API is accessible")
        print(f"  Response: {json.dumps(response.json(), indent=2)}")
        return True
    except Exception as e:
        print(f"  ✗ Video API error: {e}")
        return False


def test_tts_api():
    """Test TTS API with a minimal request"""
    print("\nTesting TTS API...")
    try:
        # Simple test payload
        test_params = {
            "speaker": "test",
            "text": "Hello",
            "format": "wav",
            "topP": 0.7,
            "max_new_tokens": 1024,
            "chunk_length": 100,
            "repetition_penalty": 1.2,
            "temperature": 0.7,
            "need_asr": False,
            "streaming": False,
            "is_fixed_seed": 0,
            "is_norm": 0
        }
        response = requests.post("http://127.0.0.1:18180/v1/invoke",
                               json=test_params, timeout=5)

        if response.status_code == 200:
            print(f"  ✓ TTS API is accessible")
            print(f"  Response type: {response.headers.get('content-type')}")
            print(f"  Response size: {len(response.content)} bytes")
        else:
            print(f"  ✓ TTS API is accessible (status: {response.status_code})")
            print(f"  Note: This may require reference audio for voice cloning")
        return True
    except Exception as e:
        print(f"  ✗ TTS API error: {e}")
        return False


def main():
    print("="*60)
    print("Duix Avatar API Test")
    print("="*60)

    video_ok = test_video_api()
    tts_ok = test_tts_api()

    print("\n" + "="*60)
    print("Test Summary:")
    print(f"  Video API: {'✓ OK' if video_ok else '✗ Failed'}")
    print(f"  TTS API: {'✓ OK' if tts_ok else '✗ Failed'}")
    print("="*60)


if __name__ == "__main__":
    main()
