"""Kokoro TTS wrapper — converts text to a WAV file using a local ONNX model."""

import sys
import uuid
import logging
from pathlib import Path
from datetime import datetime

import numpy as np
import soundfile as sf

# Logging configuration
logger = logging.getLogger(__name__)

# Audio directory for temporary files
AUDIO_DIR = Path(__file__).parent.parent / "audio"
AUDIO_DIR.mkdir(parents=True, exist_ok=True)

# Model directory for ONNX model and voice embeddings
MODEL_DIR = Path(__file__).parent.parent / "models"
MODEL_DIR.mkdir(parents=True, exist_ok=True)

_kokoro = None


def _get_kokoro(voice: str):
    """Lazy-load the Kokoro model on first use."""
    global _kokoro
    if _kokoro is None:
        logger.info("Loading Kokoro TTS Model (first run may download ~85MB)...")
        try:
            # Import kokoro from kokoro_onnx
            from kokoro_onnx import Kokoro
            # Find model files in models directory
            kokoro_onnx_path = MODEL_DIR / "kokoro-v1.0.onnx"
            voices_bin_path = MODEL_DIR / "voices.bin"

            _kokoro = Kokoro(
                str(kokoro_onnx_path),
                str(voices_bin_path)
            )
            logger.info("✅ Kokoro TTS model loaded!")
        except ImportError as e:
            logger.error(f"❌ Import error: {e}")
            logger.error("Please run 'pip install kokoro-onnx'")
            sys.exit(1)
    return _kokoro


def synthesize(text: str, voice: str = "bf_emma") -> Path:
    """
    Synthesize text to speech and return the path to the generated WAV file.

    Args:
        text: Text to speak
        voice: Voice name (e.g. bf_emma, bf_isabella, af_heart, etc.)

    Returns:
        Path to the WAV file (stored in audio/ directory)
    """
    kokoro = _get_kokoro(voice)

    # Delete all existing WAV files in audio directory
    deleted_count = 0
    for audio_file in AUDIO_DIR.glob("*.wav"):
        audio_file.unlink()
        deleted_count += 1

    if deleted_count > 0:
        logger.info(f"🗑️  Deleted {deleted_count} old WAV file(s) from audio/ directory")

    logger.info(f"🎤 Generating TTS audio with voice '{voice}'...")
    logger.info(f"📝 Text: {text}")

    # Generate audio (always English for all voices)
    samples, sample_rate = kokoro.create(text, voice=voice, speed=1.0, lang="en-gb")

    # Save file using audio directory with timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    unique_id = uuid.uuid4().hex[:8]

    out_path = AUDIO_DIR / f"{timestamp}_{unique_id}_{voice}.wav"

    logger.info(f"💾 Saving TTS audio to: {out_path}")
    sf.write(str(out_path), samples, sample_rate)

    logger.info(f"✅ Audio successfully created ({samples.shape[0] / sample_rate:.2f}s audio)")

    return out_path


if __name__ == "__main__":
    # Test TTS
    import sys

    # Enable logging
    log_file = Path(__file__).parent.parent / "logs" / f"tts_{datetime.now().strftime('%Y-%m-%d')}.log"

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stderr)
        ]
    )

    logger.info("="*60)
    logger.info("TTS Test Run")
    logger.info("="*60)

    # Test synthesis
    try:
        test_text = "Hello! This is a test from your VoiceMessage Bot."
        audio_path = synthesize(test_text, voice="bf_emma")

        logger.info(f"✅ Test successful! Audio: {audio_path}")

    except Exception as e:
        logger.error(f"❌ Test failed: {e}")

    logger.info("="*60 + "\n")