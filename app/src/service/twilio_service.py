import logging
import os

from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import Response

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

    try:
        async for message in ws.iter_json():
            event = message.get("event")

            if event == "connected":
                logger.info("Twilio media stream connected")

            elif event == "start":
                stream_sid = message["start"]["streamSid"]
                logger.info(f"Stream started: {stream_sid}")

            elif event == "media":
                # Audio-Daten vom Anrufer (base64-kodiertes mulaw)
                # Hier wird später die Pipeline angebunden
                pass

            elif event == "stop":
                logger.info(f"Stream stopped: {stream_sid}")
                break

    except WebSocketDisconnect:
        logger.info("Twilio WebSocket disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        logger.info(f"WebSocket session ended: {stream_sid}")
