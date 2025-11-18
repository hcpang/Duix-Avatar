#!/usr/bin/env python3
"""
Generate Avatar Video from Existing Audio

Takes existing TTS audio and generates an avatar video using a reference video template.
Skips TTS synthesis and goes straight to video generation.

Usage:
    python scripts/generate_avatar_from_audio.py AUDIO_FILE VIDEO_TEMPLATE [OUTPUT_PATH]

Examples:
    # Generate avatar video with tiny reference
    python scripts/generate_avatar_from_audio.py outputs/ML_in_Financial_Trading/tts/audio.wav /code/data/AlexReference_tiny.mp4

    # With custom output path
    python scripts/generate_avatar_from_audio.py outputs/ML_in_Financial_Trading/tts/audio.wav /code/data/AlexReference_tiny.mp4 outputs/avatar.mp4
"""

import sys
import io
import os
import shutil

from docker_path_utils import to_docker_path, ensure_docker_accessible
from avatar_video_utils import generate_video

# Handle Windows encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


def main():
    if len(sys.argv) < 3:
        print("Usage: python generate_avatar_from_audio.py AUDIO_FILE VIDEO_TEMPLATE [OUTPUT_PATH]")
        print()
        print("Arguments:")
        print("  AUDIO_FILE      Path to existing audio file (WAV format)")
        print("  VIDEO_TEMPLATE  Path to reference video template (Docker path like /code/data/xxx.mp4)")
        print("  OUTPUT_PATH     Optional: Custom output path")
        print()
        print("Examples:")
        print("  python scripts/generate_avatar_from_audio.py outputs/ML_in_Financial_Trading/tts/audio.wav /code/data/AlexReference_tiny.mp4")
        print("  python scripts/generate_avatar_from_audio.py outputs/ML_in_Financial_Trading/tts/audio.wav /code/data/Alex3.mp4 outputs/avatar.mp4")
        sys.exit(1)

    audio_file = sys.argv[1]
    video_template = sys.argv[2]
    output_path = sys.argv[3] if len(sys.argv) > 3 else None

    # Validate audio file exists
    if not os.path.exists(audio_file):
        print(f"Error: Audio file not found: {audio_file}")
        sys.exit(1)

    print("="*60)
    print("Generate Avatar Video from Existing Audio")
    print("="*60)
    print(f"Audio file:      {audio_file}")
    print(f"Video template:  {video_template}")
    if output_path:
        print(f"Output path:     {output_path}")
    print("="*60)

    # Convert audio to Docker path
    audio_docker_path = to_docker_path(audio_file)

    # Ensure video template is Docker-accessible (auto-copy if needed)
    video_docker_path = ensure_docker_accessible(video_template, service='video')

    # Generate video
    result = generate_video(audio_docker_path, video_docker_path)

    if result:
        # Copy to custom output path if specified
        if output_path:
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
            shutil.copy2(result, output_path)
            print(f"\nCopied to: {output_path}")
            final_path = output_path
        else:
            final_path = result

        print()
        print("="*60)
        print("SUCCESS! Avatar video generated!")
        print("="*60)
        print(f"Video: {final_path}")
        print("="*60)
    else:
        print()
        print("✗ Avatar video generation failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
