import os

# Timeouts (Sekunden)
TELEGRAM_TIMEOUT = int(os.getenv("TELEGRAM_TIMEOUT", "10"))
ANTHROPIC_TIMEOUT = int(os.getenv("ANTHROPIC_TIMEOUT", "30"))
DEEPGRAM_TIMEOUT = int(os.getenv("DEEPGRAM_TIMEOUT", "30"))
TTS_TIMEOUT = int(os.getenv("TTS_TIMEOUT", "15"))
