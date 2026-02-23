import logging
import os

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, WebSocket
from fastapi.responses import Response

from src.core.service_provider import ServiceProvider
from src.service.llm_service import LLMService
from src.service.stt_service import STTService
from src.service.telegram_service import TelegramService
from src.service.tts_service import TTSService
from src.service.twilio_service import TwilioService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI()

# ── Services ──

services = ServiceProvider(
    telegram=TelegramService(bot_token=os.getenv("TELEGRAM_BOT_TOKEN", "")),
    llm=LLMService(
        api_key=os.getenv("ANTHROPIC_API_KEY", ""),
        model=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514"),
    ),
    tts=TTSService(voice=os.getenv("TTS_VOICE", "de-DE-ConradNeural")),
    stt=STTService(api_key=os.getenv("DEEPGRAM_API_KEY", "")),
)

twilio_service = TwilioService(services=services)


# ── Health ──

@app.get("/health")
async def health_check():
    """Health-Check Endpoint für Kubernetes Probes."""
    return {"status": "ok"}


# ── Twilio ──

@app.post("/twilio/voice")
async def handle_incoming_call():
    """Twilio ruft diesen Endpoint bei eingehendem Anruf auf."""
    twiml = twilio_service.generate_twiml()
    logger.info("Incoming call, returning TwiML with media stream")
    return Response(content=twiml, media_type="application/xml")


@app.websocket("/twilio/media-stream")
async def media_stream(ws: WebSocket):
    """Bidirektionaler WebSocket für Twilio Media Streams."""
    await twilio_service.handle_media_stream(ws)
