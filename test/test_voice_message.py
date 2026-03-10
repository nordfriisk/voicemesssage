#!/usr/bin/env python3
"""
VoiceMessage Bot Test Script

Tests the complete workflow: TTS generation → R2 storage → Twilio call
"""

import os
import sys
import logging
import uuid
import glob
from pathlib import Path
from datetime import datetime

# Add project to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
import boto3
from botocore.config import Config
from kokoro_onnx import Kokoro
from twilio.rest import Client
import soundfile as sf

# ============================================================================
# Test Configuration
# ============================================================================

# Test phone number (E.164 format) - loaded from .env
TO_NUMBER = None  # Will be loaded from .env

# Test message (will be spoken in English via TTS) - loaded from .env
MESSAGE = None  # Will be loaded from .env

# Kokoro voice to use for TTS - loaded from .env
VOICE = None  # Will be loaded from .env

# ============================================================================
# Logging Setup
# ============================================================================

logger = logging.getLogger(__name__)

# Setup logs directory
logs_dir = Path(__file__).parent.parent / "logs"
logs_dir.mkdir(exist_ok=True)
log_file = logs_dir / f"test_voice_message_{datetime.now().strftime('%Y-%m-%d')}.log"

# Audio directory
audio_dir = Path(__file__).parent.parent / "audio"
audio_dir.mkdir(exist_ok=True)


def setup_logging():
    """Configure logging to file and console"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stderr)
        ]
    )

    logger.info("="*60)
    logger.info("VoiceMessage Test Run")
    logger.info("="*60)
    logger.info(f"📂 Log file: {log_file}")
    logger.info(f"🎬 Audio directory: {audio_dir}")


def load_test_config():
    """Load test configuration from .env file"""
    logger.info("\n📤 Loading test configuration from .env file...")

    # Load .env from test directory
    dotenv_path = Path(__file__).parent / ".env"
    load_dotenv(dotenv_path)

    global TO_NUMBER, MESSAGE, VOICE

    TO_NUMBER = os.getenv("PHONE_NUMBER")
    MESSAGE = os.getenv("MESSAGE")
    VOICE = os.getenv("DEFAULT_VOICE", "bf_emma")

    # Validation
    if not TO_NUMBER:
        raise ValueError("PHONE_NUMBER not found in .env file - please set it in your .env")

    if not MESSAGE:
        raise ValueError("MESSAGE not found in .env file - please add it in your .env")

    logger.info(f"📱 Phone Number: {TO_NUMBER}")
    logger.info(f"📝 Message: {MESSAGE[:50]}...")
    logger.info(f"🎤 Voice: {VOICE}")
    logger.info("✅ Configuration loaded successfully\n")


def cleanup_old_audio_files():
    """Delete old WAV files from audio directory before test"""
    logger.info("🧹 Starting cleanup: removing old audio files")

    try:
        # Find old WAV files and delete them
        wav_files = glob.glob(str(audio_dir / "*.wav"))

        if wav_files:
            logger.info(f"🗑️  Found {len(wav_files)} old audio file(s):")
            for file_path in wav_files:
                logger.info(f"   - {Path(file_path).name}")
                Path(file_path).unlink()
            logger.info(f"✅ Cleanup completed")
        else:
            logger.info("✅ No old files to delete")

        return len(wav_files)

    except Exception as e:
        logger.warning(f"⚠️ Cleanup error (non-critical): {e}")
        return 0


def generate_tts(text: str, voice: str = "bf_emma") -> str:
    """
    Generate TTS audio file

    Args:
        text: Text to speak (will be spoken in English)
        voice: Kokoro voice name

    Returns:
        Path to the generated WAV file
    """
    logger.info("[1/3] Generating TTS audio...")

    # Kokoro initialization
    logger.info(f"🎤 Voice: '{voice}'")
    logger.info(f"🌐 Language: English (en-gb)")
    logger.info(f"📝 Text: {text}")

    try:
        # Load Kokoro TTS model
        logger.info("⏳ Loading Kokoro TTS Model...")
        project_root = Path(__file__).parent.parent

        kokoro = Kokoro(
            str(project_root / "models" / "kokoro-v1.0.onnx"),
            str(project_root / "models" / "voices.bin")
        )
        logger.info("✅ TTS Model loaded!")

        # Generate audio (always English for all voices)
        samples, sample_rate = kokoro.create(
            text=text,
            voice=voice,
            speed=1.0,
            lang="en-gb"
        )

        # Save file with timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        unique_id = uuid.uuid4().hex[:8]

        output_path = audio_dir / f"{timestamp}_{unique_id}_{voice}.wav"
        sf.write(str(output_path), samples, sample_rate)

        logger.info(f"✅ Audio saved: {output_path}")
        logger.info(f"📊 Duration: {samples.shape[0] / sample_rate:.2f}s\n")

        return str(output_path)

    except Exception as e:
        logger.error(f"❌ TTS generation failed: {e}")
        raise


def upload_to_r2(file_path: str) -> str:
    """Upload audio file to Cloudflare R2"""
    logger.info("[2/3] Uploading to Cloudflare R2...")

    # Load environment
    dotenv_path = Path(__file__).parent.parent / ".env"
    if dotenv_path.exists():
        load_dotenv(dotenv_path)

    account_id = os.getenv("R2_ACCOUNT_ID")
    bucket_name = os.getenv("R2_BUCKET_NAME")
    public_url = os.getenv("R2_PUBLIC_URL").rstrip("/")

    try:
        # Create R2 client
        client = boto3.client(
            "s3",
            endpoint_url=f"https://{account_id}.r2.cloudflarestorage.com",
            aws_access_key_id=os.getenv("R2_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("R2_SECRET_ACCESS_KEY"),
            config=Config(signature_version="s3v4"),
            region_name="auto"
        )

        # Upload file
        file_name = Path(file_path).name
        key = f"audio/{file_name}"

        logger.info(f"📂 File: {file_name}")
        logger.info(f"📦 Bucket: {bucket_name}")

        client.upload_file(
            file_path,
            bucket_name,
            key,
            ExtraArgs={"ContentType": "audio/wav"}
        )

        audio_url = f"{public_url}/{key}"
        logger.info(f"✅ Audio uploaded: {audio_url}\n")

        return audio_url

    except Exception as e:
        logger.error(f"❌ Upload failed: {e}")
        raise


def send_twilio_call(to_number: str, audio_url: str) -> dict:
    """Initiate Twilio outbound call"""
    logger.info(f"[3/3] Placing call to {to_number}...")

    try:
        # Twilio client
        client = Client(
            os.getenv("TWILIO_ACCOUNT_SID"),
            os.getenv("TWILIO_AUTH_TOKEN")
        )

        from_number = os.getenv("TWILIO_FROM_NUMBER")
        logger.info(f"📱 From: {from_number}")
        logger.info(f"📱 To: {to_number}")
        logger.info(f"🔗 Audio URL: {audio_url}")

        # Create TwiML
        twiml = f"<Response><Play>{audio_url}</Play></Response>"

        # Create call
        call = client.calls.create(
            to=to_number,
            from_=from_number,
            twiml=twiml
        )

        result = {"call_sid": call.sid, "status": call.status}

        logger.info("✅ Call initiated!")
        logger.info(f"   📞 Call SID: {call.sid}")
        logger.info(f"   📊 Status: {call.status}\n")

        return result

    except Exception as e:
        logger.error(f"❌ Call failed: {e}")
        raise


def main():
    """Main test function"""
    # Try to load .env file
    dotenv_path = Path(__file__).parent / ".env"
    if dotenv_path.exists():
        load_dotenv(dotenv_path)
        logger.info("✅ .env file found and loaded")
    else:
        logger.warning("⚠️ No .env file found - will use system environment variables if available")

    setup_logging()

    # Load configuration
    load_test_config()

    # Start cleanup - remove old audio files
    logger.info("🧹 Starting cleanup before call...")
    old_files = cleanup_old_audio_files()
    if old_files == 0:
        logger.info("✅ No old files found")

    try:
        # 1️⃣ TTS Generation
        logger.info("\n" + "="*60)
        logger.info("STEP 1: TTS GENERATION")
        logger.info("="*60)
        audio_path = generate_tts(MESSAGE, voice=VOICE)
        logger.info(f"✅ TTS audio generated")

        # 2️⃣ Upload to R2
        logger.info("\n" + "="*60)
        logger.info("STEP 2: R2 UPLOAD")
        logger.info("="*60)
        audio_url = upload_to_r2(audio_path)
        logger.info(f"✅ Audio uploaded to R2")

        # 3️⃣ Twilio Call
        logger.info("\n" + "="*60)
        logger.info("STEP 3: TWILIO CALL")
        logger.info("="*60)
        twilio_result = send_twilio_call(TO_NUMBER, audio_url)

        # Success summary
        logger.info("\n" + "="*60)
        logger.info("✅ TEST COMPLETED SUCCESSFULLY")
        logger.info("="*60)
        logger.info(f"📱 Sent to: {TO_NUMBER}")
        logger.info(f"🎤 Voice: {VOICE} ({'British' if 'b' in VOICE else 'American'})")
        logger.info(f"📤 Audio URL: {audio_url}")
        logger.info(f"📞 Call SID: {twilio_result['call_sid']}")
        logger.info(f"📊 Status: {twilio_result['status']}")
        logger.info("="*60 + "\n")

        return True

    except Exception as e:
        logger.error(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)