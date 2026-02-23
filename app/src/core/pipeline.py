import asyncio
import base64
import json
import logging

import websockets
from fastapi import WebSocket

from src.core.audio_utils import mp3_to_mulaw, mulaw_to_base64_chunks
from src.core.service_provider import ServiceProvider

logger = logging.getLogger(__name__)

GREETING = (
    "Willkommen beim intelligenten Anrufbeantworter. "
    "Einen Moment, ich prüfe deine Nachrichten."
)
GOODBYE_MSG = "Auf Wiedersehen! Ich wünsche dir einen schönen Tag."
ERROR_MSG = "Es tut mir leid, es ist ein Fehler aufgetreten."
GOODBYE_WORDS = ["tschüss", "danke", "auf wiedersehen", "bye", "ciao", "ende"]


class Pipeline:
    """Orchestriert den Anruf-Flow: Begrüßung → Zusammenfassung → Rückfragen."""

    def __init__(self, ws: WebSocket, stream_sid: str, services: ServiceProvider):
        self.ws = ws
        self.stream_sid = stream_sid
        self.services = services

        self.audio_queue: asyncio.Queue[bytes | None] = asyncio.Queue()
        self.conversation_history: list[dict] = []
        self.messages = []

    def feed_audio(self, payload: str):
        """Empfängt Base64-kodierten mulaw-Audio vom WebSocket."""
        self.audio_queue.put_nowait(base64.b64decode(payload))

    # ── Haupt-Flow ──

    async def run(self):
        """Kern-Flow: Begrüßung → Nachrichten → Zusammenfassung → Rückfragen."""
        try:
            await self.speak(GREETING)

            logger.info("Fetching Telegram messages...")
            self.messages = await self.services.telegram.get_messages()

            logger.info("Summarizing messages with Claude...")
            summary = await self.services.llm.summarize(self.messages)
            logger.info(f"Summary: {summary}")

            await self.speak(summary)

            if self.messages:
                last_update_id = self.messages[-1].update_id
                try:
                    await self.services.telegram.acknowledge(last_update_id)
                except Exception as e:
                    logger.warning(f"Failed to acknowledge messages: {e}")

            await self._listen_loop()

        except asyncio.CancelledError:
            logger.info("Pipeline cancelled (call ended)")
        except Exception as e:
            logger.error(f"Pipeline error: {e}", exc_info=True)
            try:
                await self.speak(ERROR_MSG)
            except Exception:
                logger.error("Failed to speak error message")

    async def _listen_loop(self):
        """Hört auf Anrufer-Fragen und beantwortet sie per Claude."""
        logger.info("Entering listen loop for follow-up questions...")

        while True:
            transcript = await self._listen_for_utterance()
            if not transcript:
                continue

            logger.info(f"Caller said: {transcript}")

            if any(word in transcript.lower() for word in GOODBYE_WORDS):
                await self.speak(GOODBYE_MSG)
                break

            answer = await self.services.llm.answer_followup(
                question=transcript,
                messages=self.messages,
                conversation_history=self.conversation_history,
            )
            logger.info(f"Claude answer: {answer}")
            await self.speak(answer)

    # ── STT (Deepgram Streaming) ──

    async def _listen_for_utterance(self) -> str:
        """Streamt Audio an Deepgram und wartet auf eine vollständige Äußerung."""
        self._flush_audio_queue()
        transcript_parts: list[str] = []

        try:
            dg_ctx = self.services.stt.create_stream()
        except Exception as e:
            logger.error(f"Failed to create Deepgram stream: {e}")
            return ""

        try:
            async with dg_ctx as dg_ws:
                logger.info("Deepgram streaming connection established")
                await self._stream_and_transcribe(dg_ws, transcript_parts)
        except websockets.exceptions.WebSocketException as e:
            logger.error(f"Deepgram WebSocket error: {e}")
        except Exception as e:
            logger.error(f"listen_for_utterance error: {e}", exc_info=True)

        return " ".join(transcript_parts)

    async def _stream_and_transcribe(self, dg_ws, transcript_parts: list[str]):
        """Startet Forward- und Receive-Tasks parallel, wartet auf erstes Ergebnis."""
        forward_task = asyncio.create_task(self._forward_audio(dg_ws))
        receive_task = asyncio.create_task(
            self._receive_transcript(dg_ws, transcript_parts)
        )

        _, pending = await asyncio.wait(
            [forward_task, receive_task],
            return_when=asyncio.FIRST_COMPLETED,
        )
        for task in pending:
            task.cancel()

    async def _forward_audio(self, dg_ws):
        """Leitet Audio-Chunks aus der Queue an Deepgram weiter."""
        chunks_sent = 0
        try:
            while True:
                chunk = await asyncio.wait_for(self.audio_queue.get(), timeout=15.0)
                if chunk is None:
                    break
                await dg_ws.send(chunk)
                chunks_sent += 1
                if chunks_sent % 50 == 0:
                    logger.info(f"Forwarded {chunks_sent} chunks to Deepgram")
        except (asyncio.TimeoutError, asyncio.CancelledError):
            pass
        finally:
            logger.info(f"Forward audio done. Total: {chunks_sent}")
            try:
                await dg_ws.send(json.dumps({"type": "CloseStream"}))
            except Exception:
                pass

    async def _receive_transcript(self, dg_ws, transcript_parts: list[str]):
        """Empfängt Deepgram-Ergebnisse und sammelt finale Transkripte."""
        async for msg in dg_ws:
            data = json.loads(msg)

            if data.get("type") == "Results":
                alt = data.get("channel", {}).get("alternatives", [{}])[0]
                text = alt.get("transcript", "")
                is_final = data.get("is_final", False)
                speech_final = data.get("speech_final", False)

                logger.info(
                    f"DG: is_final={is_final}, speech_final={speech_final}, "
                    f"text='{text}'"
                )

                if is_final and text.strip():
                    transcript_parts.append(text.strip())

                if (speech_final or is_final) and transcript_parts:
                    return

            elif data.get("type") == "UtteranceEnd":
                if transcript_parts:
                    return

    # ── TTS + Audio-Ausgabe ──

    async def speak(self, text: str):
        """Wandelt Text in Sprache und sendet es über den Twilio WebSocket."""
        mp3_bytes = await self.services.tts.synthesize(text)
        if not mp3_bytes:
            return

        mulaw_bytes = mp3_to_mulaw(mp3_bytes)
        if not mulaw_bytes:
            return

        await self._send_audio(mulaw_bytes)

    async def _send_audio(self, mulaw_bytes: bytes):
        """Sendet mulaw-Audio in Chunks über den Twilio WebSocket."""
        chunks = mulaw_to_base64_chunks(mulaw_bytes)
        logger.info(f"Sending {len(chunks)} audio chunks to Twilio")

        for chunk in chunks:
            await self.ws.send_json({
                "event": "media",
                "streamSid": self.stream_sid,
                "media": {"payload": chunk},
            })

        await asyncio.sleep(0.1)

    # ── Helpers ──

    def _flush_audio_queue(self):
        """Leert die Audio-Queue (stale Audio von vorheriger Wiedergabe)."""
        while not self.audio_queue.empty():
            try:
                self.audio_queue.get_nowait()
            except asyncio.QueueEmpty:
                break
