import asyncio
import logging
import os

from fastapi import WebSocket, WebSocketDisconnect

from src.core.pipeline import Pipeline
from src.service.telegram_service import TelegramService
from src.service.summarizer_service import SummarizerService
from src.service.tts_service import TTSService
from src.service.stt_service import STTService

logger = logging.getLogger(__name__)

PUBLIC_URL = os.getenv("PUBLIC_URL", "localhost:8000")


class TwilioService:
    """Kapselt die Twilio-Logik: TwiML-Generierung und Media-Stream-Handling."""

    def __init__(
        self,
        telegram_service: TelegramService,
        summarizer_service: SummarizerService,
        tts_service: TTSService,
        stt_service: STTService,
    ):
        self.telegram_service = telegram_service
        self.summarizer_service = summarizer_service
        self.tts_service = tts_service
        self.stt_service = stt_service

    def generate_twiml(self) -> str:
        """Erzeugt TwiML-Response für eingehende Anrufe."""
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="Polly.Vicki" language="de-DE">
        Willkommen beim intelligenten Anrufbeantworter.
        Einen Moment, ich prüfe deine Nachrichten.
    </Say>
    <Connect>
        <Stream url="wss://{PUBLIC_URL}/twilio/media-stream" />
    </Connect>
</Response>"""

    async def handle_media_stream(self, ws: WebSocket):
        """Verarbeitet den bidirektionalen Twilio Media Stream."""
        await ws.accept()
        logger.info("Twilio WebSocket connected")

        stream_sid = None
        pipeline = None
        pipeline_task = None

        try:
            async for message in ws.iter_json():
                event = message.get("event")

                if event == "connected":
                    logger.info("Twilio media stream connected")

                elif event == "start":
                    stream_sid = message["start"]["streamSid"]
                    logger.info(f"Stream started: {stream_sid}")

                    pipeline = Pipeline(
                        ws=ws,
                        stream_sid=stream_sid,
                        telegram_service=self.telegram_service,
                        summarizer_service=self.summarizer_service,
                        tts_service=self.tts_service,
                        stt_service=self.stt_service,
                    )

                    pipeline_task = asyncio.create_task(pipeline.run())

                elif event == "media":
                    if pipeline:
                        payload = message["media"]["payload"]
                        pipeline.feed_audio(payload)

                elif event == "stop":
                    logger.info(f"Stream stopped: {stream_sid}")
                    if pipeline:
                        pipeline.audio_queue.put_nowait(None)
                    break

        except WebSocketDisconnect:
            logger.info("Twilio WebSocket disconnected")
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
        finally:
            if pipeline_task and not pipeline_task.done():
                pipeline_task.cancel()
            logger.info(f"WebSocket session ended: {stream_sid}")
