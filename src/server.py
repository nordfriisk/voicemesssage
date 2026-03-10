"""VoiceMessage MCP Server — send voice messages via Twilio with local Kokoro TTS."""

import os
import re
import sys
import logging
import uuid
from pathlib import Path
from datetime import datetime

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

# Logging configuration
logger = logging.getLogger(__name__)

# Load environment
dotenv_path = Path(__file__).parent.parent / ".env"
if dotenv_path.exists():
    load_dotenv(dotenv_path)

mcp = FastMCP("voicemessage")

E164_RE = re.compile(r"^\+[1-9]\d{6,14}$")


@mcp.tool()
def send_voice_message(
    phone_number: str,
    message: str,
    voice: str = "",
) -> dict:
    """
    Send a voice message to a phone number using text-to-speech.

    Args:
        phone_number: Destination phone number in E.164 format (e.g. +49XXXXXXXXXX).
        message: The text to speak (will be spoken in English).
        voice: Kokoro voice name. Defaults to bf_emma (British female, English).
                Available: af_heart, af_bella, af_nicole (American female),
                           am_adam, am_michael (American male),
                           bf_emma, bf_isabella (British female),
                           bm_george, bm_lewis (British male)

    Returns:
        dict with call_sid and status from Twilio.
    """
    if not E164_RE.match(phone_number):
        error_msg = f"Invalid phone number '{phone_number}'. Must be E.164 format, e.g. +49XXXXXXXXXX"
        logger.error(error_msg)
        raise ValueError(error_msg)

    if not message.strip():
        error_msg = "Message must not be empty."
        logger.error(error_msg)
        raise ValueError(error_msg)

    selected_voice = voice or os.environ.get("DEFAULT_VOICE", "bf_emma")

    from src import r2_storage, tts, twilio_client

    wav_path = None
    session_id = uuid.uuid4().hex[:8]

    logger.info("="*60)
    logger.info(f"🎤 Voice Message Request [Session: {session_id}]")
    logger.info("="*60)
    logger.info(f"📱 To: {phone_number}")
    logger.info(f"📝 Message: {message[:50]}...")
    logger.info(f"🎤 Voice: {selected_voice}")

    try:
        # 1️⃣ TTS Generation
        logger.info("\n[1/3] Generating TTS audio...")
        wav_path = tts.synthesize(message, voice=selected_voice)
        logger.info(f"✅ TTS generated: {wav_path.name}")

        # 2️⃣ Upload to Cloudflare R2
        logger.info("\n[2/3] Uploading to Cloudflare R2...")
        audio_url = r2_storage.upload(wav_path)
        logger.info(f"✅ Audio uploaded")

        # 3️⃣ Twilio Call
        logger.info(f"\n[3/3] Placing call to {phone_number}...")
        result = twilio_client.make_call(to=phone_number, audio_url=audio_url)

        logger.info(f"✅ Call initiated: {result['call_sid']}")
        logger.info(f"📊 Status: {result['status']}")

        # Summary
        logger.info(f"\n{'='*60}")
        logger.info(f"✅ VOICE MESSAGE SENT [Session: {session_id}]")
        logger.info(f"{'='*60}")
        logger.info(f"📞 Call SID: {result['call_sid']}")
        logger.info(f"📡 Audio URL: {audio_url}")
        logger.info(f"📱 To: {phone_number}")
        logger.info(f"🎤 Voice: {selected_voice}")
        logger.info(f"{'='*60}\n")

        return result

    except Exception as e:
        logger.error(f"\n❌ Voice message failed: {e}")
        logger.info(f"{'='*60}\n")
        raise

    finally:
        # Cleanup: delete temporary audio file
        if wav_path and wav_path.exists():
            logger.info(f"🗑️  Deleting temporary file: {wav_path.name}")
            wav_path.unlink()


def main():
    # Logging configuration for server
    log_file = Path(__file__).parent.parent / "logs" / f"server_{datetime.now().strftime('%Y-%m-%d')}.log"

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stderr)
        ]
    )

    logger.info("="*60)
    logger.info("VoiceMessage MCP Server started")
    logger.info("="*60)
    logger.info(f"📂 Log file: {log_file}")

    mcp.run()


if __name__ == "__main__":
    main()