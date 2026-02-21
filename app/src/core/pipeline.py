import asyncio
import json
import logging

from fastapi import WebSocket

from src.core.audio_utils import mp3_to_mulaw, mulaw_to_base64_chunks
from src.service.telegram_service import TelegramService
from src.service.summarizer_service import SummarizerService
from src.service.tts_service import TTSService

logger = logging.getLogger(__name__)


class Pipeline:
    def __init__(
        self,
        ws: WebSocket,
        stream_sid: str,
        telegram_service: TelegramService,
        summarizer_service: SummarizerService,
        tts_service: TTSService,
    ):
        self.ws = ws
        self.stream_sid = stream_sid
        self.telegram_service = telegram_service
        self.summarizer_service = summarizer_service
        self.tts_service = tts_service

    async def run(self):
        """Kern-Flow: Nachrichten abrufen → zusammenfassen → vorlesen."""
        try:
            # 1. Telegram-Nachrichten abrufen
            logger.info("Fetching Telegram messages...")
            messages = await self.telegram_service.get_messages()

            # 2. Claude-Zusammenfassung
            logger.info("Summarizing messages with Claude...")
            summary = await self.summarizer_service.summarize(messages)
            logger.info(f"Summary: {summary}")

            # 3. Text → MP3 → mulaw → an Twilio senden
            logger.info("Converting summary to speech...")
            await self.speak(summary)

            # 4. Nachrichten als gelesen markieren
            if messages:
                last_update_id = messages[-1].update_id
                await self.telegram_service.acknowledge(last_update_id)

        except Exception as e:
            logger.error(f"Pipeline error: {e}")
            await self.speak("Es tut mir leid, es ist ein Fehler aufgetreten.")

    async def speak(self, text: str):
        """Wandelt Text in Sprache und sendet es über den Twilio WebSocket."""
        mp3_bytes = await self.tts_service.synthesize(text)
        if not mp3_bytes:
            return

        mulaw_bytes = mp3_to_mulaw(mp3_bytes)
        if not mulaw_bytes:
            return

        chunks = mulaw_to_base64_chunks(mulaw_bytes)
        logger.info(f"Sending {len(chunks)} audio chunks to Twilio")

        for chunk in chunks:
            await self.ws.send_json({
                "event": "media",
                "streamSid": self.stream_sid,
                "media": {"payload": chunk},
            })

        await asyncio.sleep(0.1)
