import logging
import os
from dotenv import load_dotenv

from src.service.summarizer_service import SummarizerService

load_dotenv()

from fastapi import FastAPI

from src.service.telegram_service import TelegramService

from fastapi.responses import Response
from src.service.tts_service import TTSService

from src.service.stt_service import STTService

from src.service.twilio_service import router as twilio_router



logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI()

app.include_router(twilio_router)

@app.get("/health")
async def health_check():
    """Health-Check Endpoint für Kubernetes Probes."""
    return {"status": "ok"}

telegram_service = TelegramService(
    bot_token=os.getenv("TELEGRAM_BOT_TOKEN", "")
)

summarizer_service = SummarizerService(
    api_key=os.getenv("ANTHROPIC_API_KEY", ""),
    model=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514"),
)

tts_service = TTSService(
    voice=os.getenv("TTS_VOICE", "de-DE-ConradNeural")
)

stt_service = STTService(
    api_key=os.getenv("DEEPGRAM_API_KEY", "")
)

@app.get("/messages")
async def get_messages(acknowledge: bool = False):
    """Temporärer Test-Endpoint für Telegram-Nachrichten."""
    messages = await telegram_service.get_messages()

    if acknowledge and messages:
        last_update_id = messages[-1].update_id
        await telegram_service.acknowledge(last_update_id)

    return {"count": len(messages), "messages": messages}

@app.get("/summary")
async def get_summary():
    """Temporärer Test-Endpoint: Nachrichten abrufen und zusammenfassen."""
    messages = await telegram_service.get_messages()
    summary = await summarizer_service.summarize(messages)
    return {"count": len(messages), "summary": summary}

@app.get("/tts")
async def text_to_speech(text: str = "Hallo, dies ist ein Test."):
    """Temporärer Test-Endpoint: Text zu Sprache."""
    audio = await tts_service.synthesize(text)
    return Response(content=audio, media_type="audio/mpeg")

@app.get("/stt")
async def speech_to_text(text: str = "Hallo, dies ist ein Test."):
    """Temporärer Test-Endpoint: Text → TTS → STT → Text zurück."""
    audio = await tts_service.synthesize(text)
    transcript = await stt_service.transcribe(audio)
    return {"original": text, "transcript": transcript}
