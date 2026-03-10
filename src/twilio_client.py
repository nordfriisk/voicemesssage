"""Twilio outbound call client."""

import os
import logging
from pathlib import Path
from datetime import datetime

from twilio.rest import Client

# Logging
logger = logging.getLogger(__name__)


def make_call(to: str, audio_url: str) -> dict:
    """
    Place an outbound call that plays an audio file.

    Args:
        to: Destination phone number in E.164 format (e.g. +49XXXXXXXXXX)
        audio_url: Publicly accessible URL of the WAV file to play

    Returns:
        dict with call_sid and status

    Raises:
        Exception: If call fails
    """
    logger.info("📞 Initializing Twilio Call...")

    client = Client(os.environ["TWILIO_ACCOUNT_SID"], os.environ["TWILIO_AUTH_TOKEN"])
    from_number = os.environ["TWILIO_FROM_NUMBER"]

    logger.info(f"📱 From: {from_number}")
    logger.info(f"📱 To: {to}")
    logger.info(f"🔗 Audio URL: {audio_url}")

    # Create TwiML
    twiml = f"<Response><Play>{audio_url}</Play></Response>"

    try:
        call = client.calls.create(
            to=to,
            from_=from_number,
            twiml=twiml,
        )

        result = {"call_sid": call.sid, "status": call.status}

        logger.info("✅ Call initiated!")
        logger.info(f"   📞 Call SID: {call.sid}")
        logger.info(f"   📊 Status: {call.status}")

        return result

    except Exception as e:
        logger.error(f"❌ Call failed: {e}")
        raise


if __name__ == "__main__":
    # Enable logging for testing
    import sys
    log_file = Path(__file__).parent.parent / "logs" / f"twilio_client_{datetime.now().strftime('%Y-%m-%d')}.log"

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stderr)
        ]
    )

    logger.info("="*60)
    logger.info("Twilio Client Test Run")
    logger.info("="*60)

    # Test call
    try:
        # audio_url = "https://pub-xxxxxxxxxxxxxxx.r2.dev/audio/test.wav"
        # result = make_call("+41789402218", audio_url)
        # logger.info(f"✅ Test complete! Call SID: {result['call_sid']}")
        logger.info("⚠️ Test call commented out")
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")

    logger.info("="*60 + "\n")