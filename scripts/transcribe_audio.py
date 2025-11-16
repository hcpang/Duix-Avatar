#!/usr/bin/env python3
"""
Transcribe audio using faster-whisper (same as add_subtitles.py).
"""
import sys
import io
from faster_whisper import WhisperModel

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

if len(sys.argv) < 2:
    print("Usage: python transcribe_audio.py <audio_file>")
    sys.exit(1)

audio_path = sys.argv[1]

print(f"Loading Whisper model...")
# Reuse same model as add_subtitles.py
model = WhisperModel("tiny", device="cpu", compute_type="int8")

print(f"Transcribing: {audio_path}")
segments, info = model.transcribe(audio_path, word_timestamps=True, language="en")

# Collect all words
text_parts = []
for segment in segments:
    if hasattr(segment, 'words') and segment.words:
        for word in segment.words:
            text_parts.append(word.word.strip())

transcription = ' '.join(text_parts)

print("\n" + "="*60)
print("TRANSCRIPTION:")
print("="*60)
print(transcription)
print("="*60)
