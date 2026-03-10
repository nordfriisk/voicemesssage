# Test Directory

Test scripts for the VoiceMessage Bot.

## Test Files

### test_voice_message.py

Demonstrates the complete workflow:
1. TTS Generation (Kokoro Onnx)
2. Upload to Cloudflare R2
3. Twilio VoIP Call

## Configuration

The following settings are loaded from the `.env` file:

### Required Variables

- **PHONE_NUMBER**: Destination phone number in E.164 format (e.g., `+41789402218`)
- **MESSAGE**: Text to be spoken by the voice message (will be spoken in English)
- **DEFAULT_VOICE**: Kokoro voice name (default: `bf_emma`, British female voice)

### Available Voices

- `af_heart`, `af_bella`, `af_nicole` - American female voices
- `am_adam`, `am_michael` - American male voices
- `bf_emma`, `bf_isabella` - British female voices
- `bm_george`, `bm_lewis` - British male voices

## Usage

### 1. Configure .env File

```bash
# Copy .env.example to .env
cp .env.example .env

# Edit .env with your settings
# Update PHONE_NUMBER, MESSAGE, DEFAULT_VOICE
```

### 2. Run Test

```bash
cd /home/aimy/Projects/VoiceMessage/test
python test_voice_message.py
```

## Notes

- The `.env` file must exist in the test directory for the script to work
- Voice messages are always spoken in English
- Trial accounts can only call verified numbers (add your number in Twilio Console > Verified Caller IDs)
- Ensure all system requirements are met (Python 3.11+, Twilio credentials, R2 configuration)

## Example

```bash
# Setup
cd test
cp .env.example .env

# Edit .env - customize your settings
# PHONE_NUMBER="+41987654321"
# MESSAGE="Your custom message here"
# DEFAULT_VOICE="bf_emma"

# Run test
python test_voice_message.py
```