import asyncio
import logging
import os

from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import Response

from src.core.pipeline import Pipeline

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/twilio")

PUBLIC_URL = os.getenv("PUBLIC_URL", "localhost:8000")


@router.post("/voice")
async def handle_incoming_call(request: Request):
    """Twilio ruft diesen Endpoint bei eingehendem Anruf auf."""
    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="Polly.Vicki" language="de-DE">
        Willkommen beim intelligenten Anrufbeantworter.
        Einen Moment, ich prüfe deine Nachrichten.
    </Say>
    <Connect>
        <Stream url="wss://{PUBLIC_URL}/twilio/media-stream" />
    </Connect>
</Response>"""

    logger.info("Incoming call, returning TwiML with media stream")
    return Response(content=twiml, media_type="application/xml")


@router.websocket("/media-stream")
async def media_stream(ws: WebSocket):
    """Bidirektionaler WebSocket für Twilio Media Streams."""
    await ws.accept()
    logger.info("Twilio WebSocket connected")

    stream_sid = None
    pipeline_task = None

    try:
        async for message in ws.iter_json():
            event = message.get("event")

            if event == "connected":
                logger.info("Twilio media stream connected")

            elif event == "start":
                stream_sid = message["start"]["streamSid"]
                logger.info(f"Stream started: {stream_sid}")

                from src.endpoint import (
                    telegram_service,
                    summarizer_service,
                    tts_service,
                )

                pipeline = Pipeline(
                    ws=ws,
                    stream_sid=stream_sid,
                    telegram_service=telegram_service,
                    summarizer_service=summarizer_service,
                    tts_service=tts_service,
                )

                pipeline_task = asyncio.create_task(pipeline.run())

            elif event == "media":
                pass  # Wird in Ticket 8 für STT genutzt

            elif event == "stop":
                logger.info(f"Stream stopped: {stream_sid}")
                break

    except WebSocketDisconnect:
        logger.info("Twilio WebSocket disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        if pipeline_task and not pipeline_task.done():
            pipeline_task.cancel()
        logger.info(f"WebSocket session ended: {stream_sid}")
