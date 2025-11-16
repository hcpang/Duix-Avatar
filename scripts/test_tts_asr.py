#!/usr/bin/env python3
"""
Test Fish TTS API with ASR enabled to see what it returns.
"""
import sys
import io
import json
import requests
import uuid

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Read segment 3 text
with open('deep_dive_trading_labeled.txt', 'r', encoding='utf-8') as f:
    content = f.read()

# Extract segment 3 text (Evan's segment)
import re
segments = []
current_speaker = None
current_text = []

for line in content.split('\n'):
    line = line.strip()
    match = re.match(r'\[Speaker \d+ - (Alex|Evan)\]', line)
    if match:
        if current_speaker and current_text:
            segments.append({
                'speaker': current_speaker,
                'text': ' '.join(current_text).strip()
            })
            current_text = []
        current_speaker = match.group(1)
    elif line and current_speaker:
        current_text.append(line)

if current_speaker and current_text:
    segments.append({
        'speaker': current_speaker,
        'text': ' '.join(current_text).strip()
    })

segment_3 = segments[3]
print(f"Segment 3 speaker: {segment_3['speaker']}")
print(f"Segment 3 text preview: {segment_3['text'][:100]}...")

# Evan's avatar config
EVAN_CONFIG = {
    "reference_audio": "/code/data/origin_audio/format_denoise_20251115000845014.wav",
    "reference_text": "Dear Coach George, thank you for teaching me how to snowboard and encouraging me to go on harder. I really appreciate you teaching and guiding me to where I am now."
}

# Call TTS API with need_asr=True
TTS_URL = "http://127.0.0.1:18180/v1/invoke"
speaker_id = str(uuid.uuid4())

tts_params = {
    "speaker": speaker_id,
    "text": segment_3['text'],
    "format": "wav",
    "reference_audio": EVAN_CONFIG["reference_audio"],
    "reference_text": EVAN_CONFIG["reference_text"],
    "topP": 0.7,
    "max_new_tokens": 2048,
    "chunk_length": 200,
    "repetition_penalty": 1.2,
    "temperature": 0.7,
    "need_asr": True,  # Enable ASR
    "streaming": False,
    "is_fixed_seed": 0,
    "is_norm": 0
}

print("\nCalling TTS API with need_asr=True...")
print(f"Request params: {json.dumps({k: v for k, v in tts_params.items() if k not in ['text']}, indent=2)}")

response = requests.post(TTS_URL, json=tts_params, timeout=600)

print(f"\nResponse status: {response.status_code}")
print(f"Response headers: {dict(response.headers)}")

# Check if response is JSON or binary
content_type = response.headers.get('Content-Type', '')
if 'json' in content_type.lower():
    print(f"\nResponse JSON:")
    print(json.dumps(response.json(), indent=2))
elif 'audio' in content_type.lower() or response.content[:4] == b'RIFF':
    print(f"\nResponse is audio (WAV file)")
    print(f"Audio size: {len(response.content)} bytes")

    # Save audio
    audio_path = f"D:/duix_avatar_data/face2face/temp/test_asr_{speaker_id}.wav"
    with open(audio_path, 'wb') as f:
        f.write(response.content)
    print(f"Audio saved to: {audio_path}")
else:
    print(f"\nResponse content (first 1000 chars):")
    try:
        print(response.text[:1000])
    except:
        print(response.content[:1000])
