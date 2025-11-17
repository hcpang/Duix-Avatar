#!/usr/bin/env python3
"""
Generate reference audio from MP4/audio files with denoising and FastWhisper ASR.

This script:
1. Calls the TTS service /v1/preprocess_and_tran endpoint for audio processing
   (extraction, denoising, formatting, optional splitting)
2. Transcribes the resulting audio(s) using FastWhisper ASR

Output:
- Processed audio files (already in origin_audio directory from API)
- Transcription text file(s)
- Summary JSON with audio paths and transcriptions
"""

import subprocess
import sys
import os
import io
import json
import datetime
import shutil
from ffmpeg_utils import find_ffmpeg

# Set UTF-8 encoding for stdout on Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Default paths
OUTPUT_DIR = "D:/duix_avatar_data/voice/data/origin_audio"
TEMP_DIR = "D:/duix_avatar_data/voice/data"  # For temporary extraction


def process_audio_with_rnnoise(input_wav):
    """
    Process audio using rnnoise in Docker container (replicating API pipeline).

    Pipeline: format → denoise → re-format

    Args:
        input_wav: Path to input WAV file (Windows path in d:/duix_avatar_data/voice/data/)

    Returns:
        Path to processed audio file (Windows path) or None if failed
    """
    print("\n[Step 1] Processing audio (format, denoise, re-format)...")
    print(f"  Input: {input_wav}")

    # Convert to container path (handle both D: and d:)
    container_path = input_wav.replace('\\', '/')
    container_path = container_path.replace('D:/duix_avatar_data/voice/data/', '/code/data/')
    container_path = container_path.replace('d:/duix_avatar_data/voice/data/', '/code/data/')

    # Generate output paths
    basename = os.path.basename(input_wav)
    format1_container = f"/code/data/origin_audio/format_{basename}"
    denoise_container = f"/code/data/origin_audio/denoise_{basename}"
    final_container = f"/code/data/origin_audio/format_denoise_{basename}"

    try:
        # Step 1: Format to 16kHz mono pcm_s16le
        print(f"  [1/3] Formatting to 16kHz mono pcm_s16le...")
        cmd = f"ffmpeg -i {container_path} -ar 16000 -ac 1 -c:a pcm_s16le -y {format1_container}"
        result = subprocess.run(
            ["docker", "exec", "duix-avatar-tts", "sh", "-c", cmd],
            capture_output=True, text=True, timeout=60
        )
        if result.returncode != 0:
            print(f"    Error formatting: {result.stderr}")
            return None
        print(f"    ✓ Formatted")

        # Step 2: Denoise with rnnoise_new
        print(f"  [2/3] Denoising with rnnoise...")
        result = subprocess.run(
            ["docker", "exec", "duix-avatar-tts", "rnnoise_new", format1_container, denoise_container],
            capture_output=True, text=True, timeout=60
        )
        if result.returncode != 0:
            print(f"    Error denoising: {result.stderr}")
            return None
        print(f"    ✓ Denoised")

        # Step 3: Re-format to pcm_s16le (rnnoise outputs pcm_f32le)
        print(f"  [3/3] Re-formatting to pcm_s16le...")
        cmd = f"ffmpeg -i {denoise_container} -ar 16000 -ac 1 -c:a pcm_s16le -y {final_container}"
        result = subprocess.run(
            ["docker", "exec", "duix-avatar-tts", "sh", "-c", cmd],
            capture_output=True, text=True, timeout=60
        )
        if result.returncode != 0:
            print(f"    Error re-formatting: {result.stderr}")
            return None
        print(f"    ✓ Re-formatted")

        # Convert container path back to Windows path
        windows_path = final_container.replace('/code/data/', 'd:/duix_avatar_data/voice/data/').replace('/', '\\')

        print(f"  ✓ Audio processing complete: {os.path.basename(windows_path)}")
        return windows_path

    except subprocess.TimeoutExpired:
        print(f"    Error: Processing timeout")
        return None
    except Exception as e:
        print(f"    Error: {e}")
        return None


def transcribe_audio(audio_path, model_size="base"):
    """
    Transcribe audio using faster-whisper.

    Args:
        audio_path: Path to audio file (Windows path)
        model_size: Whisper model size (tiny, base, small, medium, large)

    Returns:
        Transcription text or None if failed
    """
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        print("    Error: faster-whisper not installed. Install with: pip install faster-whisper")
        return None

    try:
        # Load model (cached after first load)
        model = WhisperModel(model_size, device="cpu", compute_type="int8")

        # Transcribe
        segments, info = model.transcribe(audio_path, language=None)

        # Collect all text from segments
        text = " ".join([segment.text for segment in segments])

        return text.strip()

    except Exception as e:
        print(f"    Error transcribing: {e}")
        return None


def extract_audio_to_wav(input_file, output_wav):
    """Extract audio from video to WAV using ffmpeg"""
    print(f"  Extracting audio to WAV...")

    # Find ffmpeg
    ffmpeg_cmd = find_ffmpeg()
    if not ffmpeg_cmd:
        print(f"    Error: FFmpeg not found in PATH or resources folder")
        print(f"    Tip: FFmpeg binaries should be in resources/ffmpeg/win-amd64/bin/")
        return False

    try:
        # Convert to absolute paths
        input_abs = os.path.abspath(input_file)
        output_abs = os.path.abspath(output_wav)

        cmd = [
            ffmpeg_cmd, "-i", input_abs,
            "-vn",  # No video
            "-acodec", "pcm_s16le",
            "-ar", "16000",
            "-ac", "1",
            "-y",
            output_abs
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            print(f"    Error: {result.stderr}")
            return False
        print(f"    ✓ Audio extracted: {output_wav}")
        return True
    except Exception as e:
        print(f"    Error: {e}")
        return False


def main():
    if len(sys.argv) < 2:
        print("Usage: python generate_reference_audio.py <input_file> [whisper_model] [output_dir]")
        print("\nExamples:")
        print("  python generate_reference_audio.py video.mp4")
        print("  python generate_reference_audio.py audio.wav small")
        print("  python generate_reference_audio.py video.mp4 base C:/my_references")
        print("\nParameters:")
        print("  input_file:    MP4/video/audio file (can be anywhere)")
        print("  whisper_model: (Optional) tiny, base (default), small, medium, large")
        print("  output_dir:    (Optional) Copy final files to this directory")
        print("\nWhisper models (larger = more accurate but slower):")
        print("  tiny, base (default), small, medium, large")
        print("\nThis script will:")
        print("  1. Extract audio to WAV (if input is video)")
        print("  2. Process audio (format, denoise, re-format)")
        print("  3. Transcribe using faster-whisper ASR")
        print("  4. Save transcriptions as .txt files")
        print("  5. Optionally copy to custom output directory")
        print("\nNote: Processing happens in D:/duix_avatar_data/voice/data/origin_audio/")
        print("      (required for Docker container access)")
        sys.exit(1)

    input_file = sys.argv[1]
    whisper_model = sys.argv[2] if len(sys.argv) > 2 else "base"
    custom_output_dir = sys.argv[3] if len(sys.argv) > 3 else None

    print(f"\n{'='*60}")
    print(f"Reference Audio Generation with FastWhisper")
    print(f"{'='*60}")
    print(f"Input: {input_file}")
    print(f"Whisper Model: {whisper_model}")
    if custom_output_dir:
        print(f"Custom Output: {custom_output_dir}")

    # Step 0: If input is video (MP4, etc.), extract audio to WAV first
    processing_file = input_file
    temp_wav = None

    if not input_file.lower().endswith('.wav'):
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S%f")[:-3]
        temp_wav = os.path.join(TEMP_DIR, f"temp_extract_{timestamp}.wav")

        print(f"\n[Step 0] Extracting audio from video...")
        if not extract_audio_to_wav(input_file, temp_wav):
            print("\n✗ Failed to extract audio")
            sys.exit(1)

        processing_file = temp_wav

    # Step 1: Process audio with rnnoise (format, denoise, re-format)
    processed_audio = process_audio_with_rnnoise(processing_file)
    if not processed_audio:
        print("\n✗ Failed to process audio")
        sys.exit(1)

    audio_files = [processed_audio]

    # Step 2: Transcribe each audio file with FastWhisper
    print(f"\n[Step 2] Transcribing with FastWhisper (model: {whisper_model})...")
    print("  Loading Whisper model (this may take a moment)...")

    results = []
    for i, audio_file in enumerate(audio_files, 1):
        print(f"\n  [{i}/{len(audio_files)}] Transcribing: {os.path.basename(audio_file)}")

        transcription = transcribe_audio(audio_file, whisper_model)

        if transcription:
            print(f"    ✓ Transcription: {transcription}")

            # Save transcription to .txt file
            txt_file = audio_file.replace('.wav', '.txt')
            with open(txt_file, 'w', encoding='utf-8') as f:
                f.write(transcription)
            print(f"    ✓ Saved to: {txt_file}")

            # Convert back to container path for the result
            container_audio = audio_file.replace('d:\\duix_avatar_data\\voice\\data\\', '/code/data/')
            container_audio = container_audio.replace('\\', '/')

            results.append({
                "audio": container_audio,
                "audio_windows": audio_file,
                "text": transcription,
                "text_file": txt_file
            })
        else:
            print(f"    ✗ Failed to transcribe")

    # Save summary and clean up
    if results:
        summary_file = os.path.join(OUTPUT_DIR, "reference_audio_summary.json")
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        # Copy to custom output directory if specified
        if custom_output_dir:
            print(f"\n[Step 3] Copying files to custom output directory...")
            print(f"  Target: {custom_output_dir}")

            # Create directory if needed
            os.makedirs(custom_output_dir, exist_ok=True)

            custom_results = []
            for result in results:
                audio_file = result['audio_windows']
                txt_file = result['text_file']

                # Copy audio file
                audio_basename = os.path.basename(audio_file)
                custom_audio = os.path.join(custom_output_dir, audio_basename)
                shutil.copy2(audio_file, custom_audio)
                print(f"    ✓ Copied: {audio_basename}")

                # Copy text file
                txt_basename = os.path.basename(txt_file)
                custom_txt = os.path.join(custom_output_dir, txt_basename)
                shutil.copy2(txt_file, custom_txt)
                print(f"    ✓ Copied: {txt_basename}")

                # Update paths for custom location
                custom_results.append({
                    "audio": result['audio'],  # Keep container path for TTS
                    "audio_windows": audio_file,  # Original location
                    "audio_custom": custom_audio,  # Custom location
                    "text": result['text'],
                    "text_file": txt_file,  # Original location
                    "text_file_custom": custom_txt  # Custom location
                })

            # Save custom summary
            custom_summary = os.path.join(custom_output_dir, "reference_audio_summary.json")
            with open(custom_summary, 'w', encoding='utf-8') as f:
                json.dump(custom_results, f, indent=2, ensure_ascii=False)
            print(f"    ✓ Summary saved to: {custom_summary}")

            # Update results for display
            results = custom_results

        # Clean up temp WAV file
        if temp_wav and os.path.exists(temp_wav):
            try:
                os.remove(temp_wav)
                print(f"  Cleaned up temp file: {temp_wav}")
            except:
                pass

        # Success!
        print(f"\n{'='*60}")
        print(f"✓ Reference Audio Generation Complete!")
        print(f"{'='*60}")
        print(f"Generated {len(results)} reference audio(s):\n")

        for i, result in enumerate(results, 1):
            print(f"{i}. Audio: {result['audio']}")
            print(f"   Text:  {result['text']}")
            print()

        print(f"Summary saved to: {summary_file}")
        print(f"\nYou can now use these in generate_from_text.py:")
        if len(results) == 1:
            print(f"  python scripts/generate_from_text.py text.txt avatar.mp4 \\")
            print(f"    \"{results[0]['audio']}\" \\")
            print(f"    \"{results[0]['text']}\"")
        else:
            audio_paths = "|||".join([r['audio'] for r in results])
            texts = "|||".join([r['text'] for r in results])
            print(f"  python scripts/generate_from_text.py text.txt avatar.mp4 \\")
            print(f"    \"{audio_paths}\" \\")
            print(f"    \"{texts}\"")

        print(f"{'='*60}\n")
    else:
        # Clean up temp WAV file on failure too
        if temp_wav and os.path.exists(temp_wav):
            try:
                os.remove(temp_wav)
            except:
                pass

        print("\n✗ No audio files were transcribed successfully")
        sys.exit(1)


if __name__ == "__main__":
    main()
