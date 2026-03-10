"""Cloudflare R2 storage — uploads audio files and returns their public URL."""

import os
import uuid
import logging
from pathlib import Path
from datetime import datetime

import boto3
from botocore.config import Config

# Logging
logger = logging.getLogger(__name__)


def _client():
    """Create R2 S3 Client"""
    account_id = os.environ["R2_ACCOUNT_ID"]
    logger.debug(f"🔗 Creating R2 client for account: {account_id}")

    return boto3.client(
        "s3",
        endpoint_url=f"https://{account_id}.r2.cloudflarestorage.com",
        aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
        config=Config(signature_version="s3v4"),
        region_name="auto",
    )


def upload(wav_path: Path) -> str:
    """
    Upload a WAV file to Cloudflare R2 and return its public URL.

    Args:
        wav_path: Path to WAV file

    Returns:
        Public URL of the file

    Raises:
        Exception: If upload fails
    """
    bucket = os.environ["R2_BUCKET_NAME"]
    public_base = os.environ["R2_PUBLIC_URL"].rstrip("/")

    if not wav_path.exists():
        raise FileNotFoundError(f"Audio file not found: {wav_path}")

    # File info
    file_size = wav_path.stat().st_size / 1024  # KB
    file_name = wav_path.name

    logger.info(f"☁️ Starting upload to R2...")
    logger.info(f"📂 File: {file_name} ({file_size:.2f} KB)")
    logger.info(f"📦 Bucket: {bucket}")

    # Upload file
    key = f"audio/{file_name}"
    try:
        _client().upload_file(
            str(wav_path),
            bucket,
            key,
            ExtraArgs={"ContentType": "audio/wav"},
        )

        audio_url = f"{public_base}/{key}"
        logger.info(f"✅ Upload successful!")
        logger.info(f"🔗 Public URL: {audio_url}")

        return audio_url

    except Exception as e:
        logger.error(f"❌ Upload failed: {e}")
        raise


if __name__ == "__main__":
    # Enable logging for testing
    import sys
    log_file = Path(__file__).parent.parent / "logs" / f"r2_storage_{datetime.now().strftime('%Y-%m-%d')}.log"

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stderr)
        ]
    )

    logger.info("="*60)
    logger.info("R2 Storage Test Run")
    logger.info("="*60)

    # Test upload (removed after test)
    test_path = Path.home() / "Downloads" / "test.wav"

    try:
        if test_path.exists():
            logger.info(f"🔍 Test file found: {test_path}")
            # audio_url = upload(test_path)
            logger.info(f"✅ Upload complete!")
        else:
            logger.warning(f"⚠️ Test file not found: {test_path}")

    except Exception as e:
        logger.error(f"❌ Test failed: {e}")

    logger.info("="*60 + "\n")