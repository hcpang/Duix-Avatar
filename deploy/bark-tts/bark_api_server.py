#!/usr/bin/env python3
"""
Bark TTS API Server using original Suno Bark library
Compatible with Fish Speech API format for Duix.Avatar integration
"""

from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
from bark import SAMPLE_RATE, generate_audio, preload_models
from bark.generation import generate_text_semantic, generate_coarse, generate_fine, codec_decode
import os
import tempfile
import uuid
import logging
import numpy as np
from scipy.io import wavfile
import nltk
from nltk.tokenize import sent_tokenize

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Preload Bark models
logger.info("Preloading Bark models...")
try:
    preload_models()
    logger.info("Bark models loaded successfully")
except Exception as e:
    logger.error(f"Failed to load Bark models: {e}")

# Data directory for voice samples
DATA_DIR = "/code/data"
os.makedirs(DATA_DIR, exist_ok=True)


@app.route('/v1/invoke', methods=['POST'])
def invoke():
    """
    TTS endpoint compatible with Fish Speech API format

    Request format:
    {
        "speaker": "unique-speaker-id",
        "text": "Text to synthesize",
        "format": "wav",
        "temperature": 0.7,
        "voice_preset": "v2/en_speaker_6",  // Optional: Bark voice preset (v2/en_speaker_0-9)
        "reference_audio": "/path/to/reference.wav",
        "reference_text": "Reference text"
    }

    Returns: WAV audio file
    """
    try:
        data = request.json
        text = data.get('text', '')
        speaker_id = data.get('speaker', str(uuid.uuid4()))
        temperature = data.get('temperature', 0.7)
        reference_audio = data.get('reference_audio')
        # Allow client to specify voice preset (default: v2/en_speaker_6)
        voice_preset = data.get('voice_preset', 'v2/en_speaker_6')

        if not text:
            return jsonify({"error": "No text provided"}), 400

        logger.info(f"Generating audio for text: {text[:100]}...")
        logger.info(f"Speaker ID: {speaker_id}")
        logger.info(f"Voice preset: {voice_preset}")
        logger.info(f"Temperature: {temperature}")
        logger.info(f"Reference audio: {reference_audio}")

        # Create temporary output file
        output_file = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
        output_path = output_file.name
        output_file.close()

        # Split into sentences using nltk for proper tokenization (as recommended by Bark docs)
        sentences = sent_tokenize(text)
        sentences = [s.strip() for s in sentences if s.strip()]

        if len(sentences) > 1:
            logger.info(f"Generating {len(sentences)} sentences with consistent voice using history_prompt")

            # Add silence between sentences (0.25 seconds as per Bark notebook)
            silence_between = np.zeros(int(0.25 * SAMPLE_RATE))
            # Add silence at the end to prevent abrupt cutoff
            silence_end = np.zeros(int(0.5 * SAMPLE_RATE))

            pieces = []
            for i, sentence in enumerate(sentences):
                logger.info(f"Generating sentence {i+1}/{len(sentences)}: {sentence[:50]}...")

                # Advanced generation pipeline with min_eos_p to prevent audio hallucinations
                # Step 1: Generate semantic tokens with early stopping
                x_semantic = generate_text_semantic(
                    text=sentence,
                    history_prompt=voice_preset,
                    temp=temperature,
                    min_eos_p=0.1  # Lower value = more aggressive stopping, prevents extra audio
                )

                # Step 2: Generate coarse audio tokens
                x_coarse = generate_coarse(
                    x_semantic,
                    history_prompt=voice_preset,
                    temp=temperature
                )

                # Step 3: Generate fine audio tokens
                x_fine = generate_fine(
                    x_coarse,
                    history_prompt=voice_preset,
                    temp=0.5
                )

                # Step 4: Decode to waveform
                audio_array = codec_decode(x_fine)

                pieces.append(audio_array)
                # Add silence between sentences (but not after the last one)
                if i < len(sentences) - 1:
                    pieces.append(silence_between.copy())

            # Add ending silence
            pieces.append(silence_end)

            # Concatenate all audio pieces
            combined_audio = np.concatenate(pieces)

            # Convert to int16 and save
            wavfile.write(output_path, SAMPLE_RATE, (combined_audio * 32767).astype(np.int16))
        else:
            # Single sentence - use advanced pipeline with min_eos_p
            x_semantic = generate_text_semantic(
                text=text,
                history_prompt=voice_preset,
                temp=temperature,
                min_eos_p=0.1
            )
            x_coarse = generate_coarse(x_semantic, history_prompt=voice_preset, temp=temperature)
            x_fine = generate_fine(x_coarse, history_prompt=voice_preset, temp=0.5)
            audio_array = codec_decode(x_fine)

            # Add ending silence to prevent abrupt cutoff
            silence_end = np.zeros(int(0.5 * SAMPLE_RATE))
            combined_audio = np.concatenate([audio_array, silence_end])

            wavfile.write(output_path, SAMPLE_RATE, (combined_audio * 32767).astype(np.int16))

        logger.info(f"Audio generated: {output_path}")

        # Send file and clean up
        response = send_file(
            output_path,
            mimetype='audio/wav',
            as_attachment=False
        )

        # Schedule cleanup (file will be deleted after response is sent)
        @response.call_on_close
        def cleanup():
            try:
                if os.path.exists(output_path):
                    os.unlink(output_path)
            except Exception as e:
                logger.error(f"Failed to cleanup temp file: {e}")

        return response

    except Exception as e:
        logger.error(f"Error generating audio: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    import torch
    return jsonify({
        "status": "ok",
        "model": "bark",
        "gpu_available": torch.cuda.is_available(),
        "gpu_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None
    })


@app.route('/voices', methods=['GET'])
def list_voices():
    """List available voice presets"""
    voices = {
        "default": "v2/en_speaker_6",
        "available": [f"v2/en_speaker_{i}" for i in range(10)],
        "description": "Bark voice presets (v2/en_speaker_0 through v2/en_speaker_9)"
    }
    return jsonify(voices)


if __name__ == '__main__':
    logger.info("Starting Bark TTS API server on 0.0.0.0:8080")
    app.run(host='0.0.0.0', port=8080, debug=False)
