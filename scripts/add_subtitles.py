#!/usr/bin/env python3
"""
Generate SRT subtitles for Duix Avatar videos
"""

import sys
import os
import re
import wave
import subprocess
import argparse
from pathlib import Path

# Import shared subtitle utilities
from subtitle_utils import (normalize_word, edit_distance, find_best_match,
                             match_chunk_to_whisper, split_into_sentences, split_into_chunks)

# Set UTF-8 encoding for stdout on Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Try to import faster-whisper for accurate timing
try:
    from faster_whisper import WhisperModel
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False

# Try to import websocket for local ASR
try:
    import websocket
    import json as json_module
    WEBSOCKET_AVAILABLE = True
except ImportError:
    WEBSOCKET_AVAILABLE = False


def get_audio_duration(audio_path):
    """Get duration of audio file in seconds"""
    try:
        with wave.open(audio_path, 'r') as audio_file:
            frames = audio_file.getnframes()
            rate = audio_file.getframerate()
            duration = frames / float(rate)
            return duration
    except Exception as e:
        print(f"Warning: Could not read audio duration from WAV file: {e}")
        # Try using ffprobe as fallback
        try:
            result = subprocess.run(
                ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                 '-of', 'default=noprint_wrappers=1:nokey=1', audio_path],
                capture_output=True,
                text=True
            )
            return float(result.stdout.strip())
        except Exception as e2:
            print(f"Error: Could not determine audio duration: {e2}")
            return None


def split_into_sentences(text):
    """Split text into sentences using natural boundaries"""
    # Remove extra whitespace
    text = ' '.join(text.split())

    # Split on sentence endings, keeping the punctuation
    sentences = re.split(r'([.!?]+[\s]+)', text)

    # Recombine sentences with their punctuation
    result = []
    for i in range(0, len(sentences)-1, 2):
        sentence = sentences[i]
        if i+1 < len(sentences):
            sentence += sentences[i+1].strip()
        sentence = sentence.strip()
        if sentence:
            result.append(sentence)

    # Handle any remaining text
    if len(sentences) % 2 == 1 and sentences[-1].strip():
        result.append(sentences[-1].strip())

    return result if result else [text]


def chunk_text(text, max_chars=60):
    """Split long sentences into smaller chunks for subtitle display"""
    words = text.split()
    chunks = []
    current_chunk = []
    current_length = 0

    for word in words:
        word_length = len(word) + 1  # +1 for space
        if current_length + word_length > max_chars and current_chunk:
            chunks.append(' '.join(current_chunk))
            current_chunk = [word]
            current_length = word_length
        else:
            current_chunk.append(word)
            current_length += word_length

    if current_chunk:
        chunks.append(' '.join(current_chunk))

    return chunks


def get_timestamps_from_local_asr(audio_path):
    """Get word-level timestamps from local Duix ASR service via WebSocket"""
    if not WEBSOCKET_AVAILABLE:
        return None

    try:
        print("  Using local ASR service for word-level timing...")

        # Read audio file
        with open(audio_path, 'rb') as f:
            audio_data = f.read()

        # Connect to WebSocket
        ws_url = "ws://127.0.0.1:10095"
        ws = websocket.create_connection(ws_url, timeout=60)

        # Send audio data
        ws.send_binary(audio_data)

        # Signal end of audio
        ws.send('{"is_speaking": false}')

        # Receive response
        result_text = ""
        word_timings = []

        while True:
            try:
                message = ws.recv()
                if not message:
                    break

                # Parse JSON response
                result = json_module.loads(message)

                # Check if final result
                if result.get('is_final'):
                    # Extract word timestamps (in milliseconds)
                    timestamps = result.get('timestamp', [])
                    text_words = result.get('text', '').split()

                    # Convert timestamps from ms to seconds
                    for i, (start_ms, end_ms) in enumerate(timestamps):
                        if i < len(text_words):
                            word_timings.append({
                                'word': text_words[i],
                                'start': start_ms / 1000.0,
                                'end': end_ms / 1000.0
                            })

                    result_text = result.get('text', '')
                    break

            except Exception as e:
                print(f"  Warning: Error receiving from ASR: {e}")
                break

        ws.close()

        if word_timings:
            print(f"  ✓ Got {len(word_timings)} word timestamps from local ASR")
            return word_timings

        return None

    except Exception as e:
        print(f"  Warning: Local ASR failed ({e})")
        return None


def get_word_timestamps(audio_path, text):
    """Get timing from Whisper and map user's original text with accurate start times"""
    if not WHISPER_AVAILABLE:
        return None

    try:
        print("  Using Whisper for accurate word-level timing...")
        # Use tiny model for speed (can use 'base' or 'small' for better accuracy)
        model = WhisperModel("tiny", device="cpu", compute_type="int8")

        # Transcribe to get word-level timestamps
        segments, info = model.transcribe(
            audio_path,
            word_timestamps=True,
            language="en"
        )

        # Extract word-level timestamps
        word_timings = []
        for segment in segments:
            if hasattr(segment, 'words') and segment.words:
                for word in segment.words:
                    word_timings.append({
                        'word': word.word.strip(),
                        'start': word.start,
                        'end': word.end
                    })

        if word_timings:
            print(f"  ✓ Got {len(word_timings)} word timestamps from Whisper")
            # Map user's original text to these word timings
            print(f"  ✓ Mapping your original text with accurate start times...")
            aligned_segments = map_text_to_word_timings(text, word_timings, max_chars=60)
            if aligned_segments:
                print(f"  ✓ Created {len(aligned_segments)} subtitle segments with accurate timing")
                return aligned_segments

        return None

    except Exception as e:
        print(f"  Warning: Whisper failed ({e}), falling back to even distribution")
        return None


def map_text_to_word_timings(text, word_timings, max_chars=60):
    """Map user's original text to Whisper word timings with accurate start times"""

    # Split text into sentences
    full_sentences = split_into_sentences(text)
    if not full_sentences:
        return None

    # Normalize all Whisper words for matching
    whisper_words_normalized = [normalize_word(w['word']) for w in word_timings]

    # Calculate total duration
    total_duration = word_timings[-1]['end'] - word_timings[0]['start']
    total_chars = sum(len(s) for s in full_sentences)

    subtitle_segments = []
    whisper_idx = 0
    chars_processed = 0
    prev_chunk_word_count = 0  # Track previous chunk's word count for position estimation

    for sentence in full_sentences:
        # Split sentence into chunks if it exceeds max_chars
        chunks = split_into_chunks(sentence, max_chars)

        # For each chunk, find accurate start time
        for chunk in chunks:
            # Try to match chunk to Whisper words
            chunk_start, whisper_idx, match_found, current_chunk_word_count = match_chunk_to_whisper(
                chunk, word_timings, whisper_words_normalized, whisper_idx, prev_chunk_word_count
            )

            # Update prev_chunk_word_count for next iteration
            prev_chunk_word_count = current_chunk_word_count

            if not match_found:
                # No match found for any of the first 5 words, use proportional positioning
                # Calculate where we are in the text (percentage)
                progress = chars_processed / total_chars if total_chars > 0 else 0
                # Estimate position in audio based on text progress
                estimated_time = word_timings[0]['start'] + (progress * total_duration)

                # Find closest Whisper word to this estimated time
                closest_idx = whisper_idx
                min_time_diff = abs(word_timings[closest_idx]['start'] - estimated_time)

                for idx in range(whisper_idx, len(word_timings)):
                    time_diff = abs(word_timings[idx]['start'] - estimated_time)
                    if time_diff < min_time_diff:
                        min_time_diff = time_diff
                        closest_idx = idx
                    elif time_diff > min_time_diff:
                        # Times are getting further, stop searching
                        break

                chunk_start = word_timings[closest_idx]['start']
                whisper_idx = closest_idx + 1

            # Calculate end time based on character proportion
            chunk_duration = (len(chunk) / total_chars) * total_duration
            chunk_end = chunk_start + chunk_duration

            # Make sure end time doesn't exceed total duration
            if chunk_end > word_timings[-1]['end']:
                chunk_end = word_timings[-1]['end']

            subtitle_segments.append({
                'text': chunk,
                'start': chunk_start,
                'end': chunk_end
            })

            chars_processed += len(chunk)

    # Fix overlapping segments - ensure each segment ends before the next starts
    for i in range(len(subtitle_segments) - 1):
        next_start = subtitle_segments[i + 1]['start']
        if subtitle_segments[i]['end'] > next_start:
            # Cap the end time to just before the next segment starts (with 50ms gap)
            subtitle_segments[i]['end'] = max(subtitle_segments[i]['start'] + 0.1, next_start - 0.05)

    return subtitle_segments if subtitle_segments else None


def map_text_to_boundaries(text, segment_boundaries, max_chars=60):
    """Map user's original text to Whisper timing boundaries proportionally"""

    # Split text into sentences
    full_sentences = split_into_sentences(text)
    if not full_sentences:
        return None

    # Calculate total duration
    total_duration = segment_boundaries[-1]['end'] - segment_boundaries[0]['start']

    # Assign timing to each sentence based on character proportion
    total_chars = sum(len(s) for s in full_sentences)
    current_time = segment_boundaries[0]['start']

    subtitle_segments = []
    for sentence in full_sentences:
        # Calculate duration for this sentence based on character proportion
        sentence_chars = len(sentence)
        sentence_duration = (sentence_chars / total_chars) * total_duration

        # Split sentence into chunks if it exceeds max_chars
        if len(sentence) <= max_chars:
            subtitle_segments.append({
                'text': sentence,
                'start': current_time,
                'end': current_time + sentence_duration
            })
            current_time += sentence_duration
        else:
            # Split long sentence at natural break points
            words = sentence.split()
            chunks = []
            current_chunk = []

            for word in words:
                test_chunk = ' '.join(current_chunk + [word])
                if len(test_chunk) > max_chars and current_chunk:
                    chunks.append(' '.join(current_chunk))
                    current_chunk = [word]
                else:
                    current_chunk.append(word)

            if current_chunk:
                chunks.append(' '.join(current_chunk))

            # Distribute duration across chunks
            chunk_duration = sentence_duration / len(chunks)
            for chunk in chunks:
                subtitle_segments.append({
                    'text': chunk,
                    'start': current_time,
                    'end': current_time + chunk_duration
                })
                current_time += chunk_duration

    return subtitle_segments if subtitle_segments else None


def align_text_to_timestamps(text, word_timings, max_chars=60):
    """Align user's original text to ASR word timestamps preserving punctuation"""

    def normalize_word(word):
        """Remove punctuation and lowercase for comparison"""
        return re.sub(r'[^\w\s]', '', word.lower())

    # Extract words from original text (keeping punctuation)
    user_words_with_punct = re.findall(r'\S+', text)
    user_words_normalized = [normalize_word(w) for w in user_words_with_punct]

    # Normalize ASR words for comparison
    asr_words_normalized = [normalize_word(w['word']) for w in word_timings]

    # Align words
    aligned_chunks = []
    current_words_original = []
    current_start = None
    current_end = None
    over_max = False  # Track if we've exceeded max length

    asr_idx = 0
    for user_idx, user_word_norm in enumerate(user_words_normalized):
        if not user_word_norm:  # Skip empty words
            continue

        # Find matching ASR word
        matched = False
        while asr_idx < len(asr_words_normalized):
            asr_word_norm = asr_words_normalized[asr_idx]

            # Check if words match (fuzzy matching for small differences)
            if user_word_norm == asr_word_norm or \
               user_word_norm in asr_word_norm or \
               asr_word_norm in user_word_norm:

                timing = word_timings[asr_idx]

                if current_start is None:
                    current_start = timing['start']
                current_end = timing['end']

                # Add original word with punctuation
                current_words_original.append(user_words_with_punct[user_idx])

                # Check if we should break into new subtitle
                chunk_text = ' '.join(current_words_original)
                user_word_original = user_words_with_punct[user_idx]

                # Update over_max flag
                if len(chunk_text) > max_chars:
                    over_max = True

                # Determine if this is a natural break point
                is_sentence_end = user_word_original.rstrip().endswith(('.', '!', '?', '。', '！', '？'))
                is_pause_point = user_word_original.rstrip().endswith((',', ';', ':', '.', '!', '?', '。', '！', '？'))

                # Break logic:
                # 1. Always break at sentence end
                # 2. If we've exceeded max, break at next pause point (comma, period, etc.)
                # 3. If way over max (1.8x), force break
                should_break = (
                    is_sentence_end or
                    (over_max and is_pause_point) or
                    len(chunk_text) > max_chars * 1.8
                )

                if should_break and current_words_original:
                    aligned_chunks.append({
                        'text': chunk_text,
                        'start': current_start,
                        'end': current_end
                    })
                    current_words_original = []
                    current_start = None
                    current_end = None
                    over_max = False  # Reset flag

                asr_idx += 1
                matched = True
                break

            asr_idx += 1

        # If no match found for this word, skip it (might be filler words or ASR missed it)
        if not matched and current_words_original:
            # Still add the word to current chunk if we have context
            current_words_original.append(user_words_with_punct[user_idx])

    # Add remaining chunk
    if current_words_original and current_start is not None:
        aligned_chunks.append({
            'text': ' '.join(current_words_original),
            'start': current_start,
            'end': current_end if current_end else current_start + 2.0
        })

    return aligned_chunks if aligned_chunks else None


def format_timestamp(seconds):
    """Format seconds into SRT timestamp format: HH:MM:SS,mmm"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def generate_srt(text, duration, max_chars=60, word_timings=None):
    """Generate SRT subtitle content from text and duration

    Args:
        text: The text to create subtitles for
        duration: Total duration in seconds
        max_chars: Maximum characters per subtitle line
        word_timings: Optional timed segments from ASR (Whisper segments)
    """
    # Use timed segments if available (from Whisper or ASR)
    if word_timings:
        srt_content = []
        for i, segment in enumerate(word_timings):
            srt_content.append(f"{i + 1}")
            srt_content.append(f"{format_timestamp(segment['start'])} --> {format_timestamp(segment['end'])}")
            srt_content.append(segment['text'])
            srt_content.append("")  # Empty line between entries

        return '\n'.join(srt_content)

    # Fall back to even distribution
    # Split text into sentences
    sentences = split_into_sentences(text)

    # Further split into display chunks
    all_chunks = []
    for sentence in sentences:
        chunks = chunk_text(sentence, max_chars)
        all_chunks.extend(chunks)

    if not all_chunks:
        return ""

    # Calculate timing for each chunk
    time_per_chunk = duration / len(all_chunks)

    # Generate SRT content
    srt_content = []
    for i, chunk in enumerate(all_chunks):
        start_time = i * time_per_chunk
        end_time = (i + 1) * time_per_chunk

        srt_content.append(f"{i + 1}")
        srt_content.append(f"{format_timestamp(start_time)} --> {format_timestamp(end_time)}")
        srt_content.append(chunk)
        srt_content.append("")  # Empty line between entries

    return '\n'.join(srt_content)


def find_ffmpeg():
    """Find ffmpeg executable, checking PATH and resources folder"""
    # Try system PATH first
    try:
        result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True)
        if result.returncode == 0:
            return 'ffmpeg'
    except FileNotFoundError:
        pass

    # Check resources folder
    script_dir = Path(__file__).parent.parent
    ffmpeg_paths = [
        script_dir / 'resources' / 'ffmpeg' / 'win-amd64' / 'bin' / 'ffmpeg.exe',
        script_dir / 'resources' / 'ffmpeg' / 'linux-x64' / 'bin' / 'ffmpeg',
    ]

    for ffmpeg_path in ffmpeg_paths:
        if ffmpeg_path.exists():
            return str(ffmpeg_path)

    return None


def burn_subtitles(video_path, srt_path, output_path, font_size=24, font_color="white"):
    """Burn subtitles into video using FFmpeg"""
    print(f"\nBurning subtitles into video...")
    print(f"  Input: {video_path}")
    print(f"  Subtitles: {srt_path}")
    print(f"  Output: {output_path}")

    # Find FFmpeg
    ffmpeg_cmd = find_ffmpeg()
    if not ffmpeg_cmd:
        print("Error: FFmpeg not found. Please ensure FFmpeg is installed and in your PATH.")
        print("Tip: FFmpeg binaries should be in resources/ffmpeg/win-amd64/bin/")
        return False

    print(f"  Using FFmpeg: {ffmpeg_cmd}")

    # Normalize paths for FFmpeg subtitle filter (needs forward slashes and escaping)
    # For Windows, FFmpeg needs the path in the subtitle filter to use forward slashes and be escaped
    srt_path_for_filter = str(Path(srt_path).absolute()).replace('\\', '/').replace(':', '\\:')

    # FFmpeg subtitle filter
    subtitles_filter = f"subtitles='{srt_path_for_filter}':force_style='FontSize={font_size},PrimaryColour=&H{get_color_hex(font_color)}&'"

    try:
        result = subprocess.run(
            [
                ffmpeg_cmd, '-i', str(Path(video_path).absolute()),
                '-vf', subtitles_filter,
                '-c:a', 'copy',  # Copy audio without re-encoding
                '-y',  # Overwrite output file
                str(Path(output_path).absolute())
            ],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace'
        )

        if result.returncode == 0:
            print(f"✓ Subtitles burned successfully!")
            return True
        else:
            print(f"Error burning subtitles: {result.stderr}")
            return False
    except FileNotFoundError:
        print("Error: FFmpeg not found. Please ensure FFmpeg is installed and in your PATH.")
        print("Tip: FFmpeg binaries are in resources/ffmpeg/win-amd64/bin/")
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False


def get_color_hex(color_name):
    """Convert color name to hex for FFmpeg (BGR format)"""
    colors = {
        'white': 'FFFFFF',
        'yellow': '00FFFF',
        'black': '000000',
        'red': '0000FF',
        'green': '00FF00',
        'blue': 'FF0000',
    }
    return colors.get(color_name.lower(), 'FFFFFF')


def main():
    parser = argparse.ArgumentParser(
        description='Generate SRT subtitles for Duix Avatar videos',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate SRT file only
  python add_subtitles.py video.mp4 script.txt

  # Generate SRT and burn into video
  python add_subtitles.py video.mp4 script.txt --burn

  # Customize subtitle appearance
  python add_subtitles.py video.mp4 script.txt --burn --font-size 28 --color yellow

  # Specify audio file for accurate timing
  python add_subtitles.py video.mp4 script.txt --audio audio.wav
        """
    )

    parser.add_argument('video', help='Path to video file')
    parser.add_argument('text', help='Path to text file or direct text string')
    parser.add_argument('--audio', help='Path to audio file (for accurate duration). If not provided, extracts from video.')
    parser.add_argument('--output', help='Output SRT file path (default: same as video with .srt extension)')
    parser.add_argument('--burn', action='store_true', help='Burn subtitles into video')
    parser.add_argument('--burn-output', help='Output video path with burned subtitles (default: video_subtitled.mp4)')
    parser.add_argument('--max-chars', type=int, default=60, help='Maximum characters per subtitle line (default: 60)')
    parser.add_argument('--font-size', type=int, default=24, help='Font size for burned subtitles (default: 24)')
    parser.add_argument('--color', default='white', choices=['white', 'yellow', 'black', 'red', 'green', 'blue'],
                        help='Subtitle color for burned subtitles (default: white)')

    args = parser.parse_args()

    print("="*60)
    print("Duix Avatar Subtitle Generator")
    print("="*60)

    # Read text content
    if os.path.isfile(args.text):
        print(f"\nReading text from: {args.text}")
        with open(args.text, 'r', encoding='utf-8') as f:
            text = f.read().strip()
    else:
        text = args.text

    print(f"Text length: {len(text)} characters")

    # Determine audio source for duration
    audio_path = args.audio if args.audio else args.video
    print(f"\nGetting duration from: {audio_path}")

    duration = get_audio_duration(audio_path)
    if duration is None:
        print("Error: Could not determine audio duration")
        return 1

    print(f"Duration: {duration:.2f} seconds ({duration/60:.2f} minutes)")

    # Try to get word-level timestamps from audio
    word_timings = None
    print(f"\nGetting word-level timestamps...")

    # Try local ASR first (fastest, already running)
    if WEBSOCKET_AVAILABLE:
        word_timings = get_timestamps_from_local_asr(audio_path)

    # Fall back to Whisper if local ASR didn't work
    if not word_timings and WHISPER_AVAILABLE:
        word_timings = get_word_timestamps(audio_path, text)

    # Status message
    if word_timings:
        print(f"  ✓ Using accurate word-level timing for {len(word_timings)} words")
    else:
        print("  ⚠ Using even distribution (less accurate)")
        if not WEBSOCKET_AVAILABLE and not WHISPER_AVAILABLE:
            print("  Tip: Install 'websocket-client' or 'faster-whisper' for accurate timing")

    # Generate SRT content
    print(f"\nGenerating subtitles (max {args.max_chars} chars per line)...")
    srt_content = generate_srt(text, duration, args.max_chars, word_timings=word_timings)

    if not srt_content:
        print("Error: Failed to generate subtitle content")
        return 1

    # Determine output SRT path
    if args.output:
        srt_path = args.output
    else:
        video_path = Path(args.video)
        srt_path = video_path.with_suffix('.srt')

    # Write SRT file
    print(f"\nWriting subtitles to: {srt_path}")
    with open(srt_path, 'w', encoding='utf-8') as f:
        f.write(srt_content)

    print(f"✓ SRT file created successfully!")

    # Count subtitle entries
    num_entries = srt_content.count('\n\n') + 1
    print(f"  Subtitle entries: {num_entries}")
    print(f"  Average duration per entry: {duration/num_entries:.2f}s")

    # Burn subtitles if requested
    if args.burn:
        if args.burn_output:
            burn_output = args.burn_output
        else:
            video_path = Path(args.video)
            burn_output = video_path.parent / f"{video_path.stem}_subtitled{video_path.suffix}"

        success = burn_subtitles(
            args.video,
            srt_path,
            str(burn_output),
            font_size=args.font_size,
            font_color=args.color
        )

        if success:
            print(f"\n✓ Video with burned subtitles: {burn_output}")

    print("\n" + "="*60)
    print("SUCCESS!")
    print(f"  SRT file: {srt_path}")
    if args.burn:
        print(f"  Video with subtitles: {burn_output}")
    print("="*60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
