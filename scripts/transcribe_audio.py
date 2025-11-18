#!/usr/bin/env python3
"""
Transcribe audio using faster-whisper with word-level timestamps.

This is the SINGLE source of truth for Whisper transcription in the codebase.
Can be used as a script or imported as a module.

Outputs:
- SRT file with word-level timestamps
- TXT file with plain transcription text

Used by: add_subtitles.py, generate_reference_audio.py, and other scripts
"""
import sys
import io
import os
from pathlib import Path

try:
    from faster_whisper import WhisperModel
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False


def format_srt_timestamp(seconds):
    """Format seconds into SRT timestamp format: HH:MM:SS,mmm"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def transcribe_audio_file(audio_path, model_size="base", language="en"):
    """
    Transcribe audio file using Whisper with word-level timestamps.

    Args:
        audio_path: Path to audio file
        model_size: Whisper model (tiny, base, small, medium, large)
        language: Language code (default: "en", None for auto-detect)

    Returns:
        dict with:
            'word_timings': List of {'word': str, 'start': float, 'end': float}
            'transcription': Full text as string
            'language': Detected/specified language
    """
    if not WHISPER_AVAILABLE:
        print("Error: faster-whisper not installed. Install with: pip install faster-whisper")
        return None

    try:
        print(f"  Loading Whisper model ({model_size})...")
        model = WhisperModel(model_size, device="cpu", compute_type="int8")

        print(f"  Transcribing audio...")
        segments, info = model.transcribe(audio_path, word_timestamps=True, language=language)

        # Collect word-level timestamps
        word_timings = []
        text_parts = []

        for segment in segments:
            if hasattr(segment, 'words') and segment.words:
                for word in segment.words:
                    word_text = word.word.strip()
                    word_timings.append({
                        'word': word_text,
                        'start': word.start,
                        'end': word.end
                    })
                    text_parts.append(word_text)

        transcription = ' '.join(text_parts)

        print(f"  ✓ Transcribed {len(word_timings)} words")

        return {
            'word_timings': word_timings,
            'transcription': transcription,
            'language': info.language if hasattr(info, 'language') else language
        }

    except Exception as e:
        print(f"Error during transcription: {e}")
        return None


def save_srt_file(word_timings, output_path):
    """
    Save word timings as SRT file.

    Args:
        word_timings: List of {'word': str, 'start': float, 'end': float}
        output_path: Path to output SRT file
    """
    srt_content = []
    for i, word_timing in enumerate(word_timings, 1):
        srt_content.append(f"{i}")
        srt_content.append(
            f"{format_srt_timestamp(word_timing['start'])} --> {format_srt_timestamp(word_timing['end'])}"
        )
        srt_content.append(word_timing['word'])
        srt_content.append("")  # Empty line between entries

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(srt_content))

    print(f"  ✓ SRT saved to: {output_path}")


def save_txt_file(transcription, output_path):
    """Save plain transcription text to file."""
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(transcription)

    print(f"  ✓ TXT saved to: {output_path}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python transcribe_audio.py AUDIO_FILE [MODEL_SIZE] [OUTPUT_PREFIX]")
        print()
        print("Arguments:")
        print("  AUDIO_FILE     Path to audio/video file")
        print("  MODEL_SIZE     Whisper model: tiny, base, small, medium, large (default: base)")
        print("  OUTPUT_PREFIX  Output file prefix (default: same as audio file)")
        print()
        print("Outputs:")
        print("  - PREFIX.srt   SRT file with word-level timestamps")
        print("  - PREFIX.txt   Plain text transcription")
        print()
        print("Example:")
        print("  python transcribe_audio.py audio.wav base output")
        print("  → Creates: output.srt, output.txt")
        sys.exit(1)

    audio_path = sys.argv[1]
    model_size = sys.argv[2] if len(sys.argv) > 2 else "base"
    output_prefix = sys.argv[3] if len(sys.argv) > 3 else str(Path(audio_path).with_suffix(''))

    print("=" * 60)
    print("Audio Transcription with Whisper")
    print("=" * 60)
    print(f"Input: {audio_path}")
    print(f"Model: {model_size}")
    print(f"Output prefix: {output_prefix}")
    print()

    # Transcribe
    result = transcribe_audio_file(audio_path, model_size=model_size)

    if not result:
        print("\n✗ Transcription failed")
        sys.exit(1)

    # Save SRT file
    srt_path = f"{output_prefix}.srt"
    save_srt_file(result['word_timings'], srt_path)

    # Save TXT file
    txt_path = f"{output_prefix}.txt"
    save_txt_file(result['transcription'], txt_path)

    # Display results
    print()
    print("=" * 60)
    print("TRANSCRIPTION:")
    print("=" * 60)
    print(result['transcription'])
    print("=" * 60)
    print()
    print(f"✓ Transcription complete!")
    print(f"  Language: {result['language']}")
    print(f"  Word count: {len(result['word_timings'])}")
    print(f"  SRT file: {srt_path}")
    print(f"  TXT file: {txt_path}")
    print("=" * 60)


if __name__ == "__main__":
    # Set UTF-8 encoding for Windows (only when run as main script)
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

    main()
