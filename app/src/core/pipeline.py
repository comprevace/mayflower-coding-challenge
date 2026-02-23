import asyncio
import base64
import json
import logging

import websockets
from fastapi import WebSocket

from src.core.audio_utils import mp3_to_mulaw, mulaw_to_base64_chunks
from src.service.stt_service import STTService
from src.service.llm_service import LLMService
from src.service.telegram_service import TelegramService
from src.service.tts_service import TTSService

logger = logging.getLogger(__name__)

GOODBYE_WORDS = ["tschüss", "danke", "auf wiedersehen", "bye", "ciao", "Ende"]


class Pipeline:
    def __init__(
        self,
        ws: WebSocket,
        stream_sid: str,
        telegram_service: TelegramService,
        llm_service: LLMService,
        tts_service: TTSService,
        stt_service: STTService,
    ):
        self.ws = ws
        self.stream_sid = stream_sid
        self.telegram_service = telegram_service
        self.llm_service = llm_service
        self.tts_service = tts_service
        self.stt_service = stt_service

        self.audio_queue: asyncio.Queue[bytes | None] = asyncio.Queue()
        self.conversation_history: list[dict] = []
        self.messages = []

    def feed_audio(self, payload: str):
        """Empfängt Base64-kodierten mulaw-Audio vom WebSocket."""
        audio_bytes = base64.b64decode(payload)
        self.audio_queue.put_nowait(audio_bytes)

    async def run(self):
        """Kern-Flow: Nachrichten abrufen → zusammenfassen → vorlesen → Fragen beantworten."""
        try:
            # 1. Telegram-Nachrichten abrufen
            logger.info("Fetching Telegram messages...")
            self.messages = await self.telegram_service.get_messages()

            # 2. Claude-Zusammenfassung
            logger.info("Summarizing messages with Claude...")
            summary = await self.llm_service.summarize(self.messages)
            logger.info(f"Summary: {summary}")

            # 3. Zusammenfassung vorlesen
            logger.info("Converting summary to speech...")
            await self.speak(summary)

            # 4. Nachrichten als gelesen markieren
            if self.messages:
                last_update_id = self.messages[-1].update_id
                try:
                    await self.telegram_service.acknowledge(last_update_id)
                except Exception as e:
                    logger.warning(f"Failed to acknowledge messages: {e}")

            # 5. Hör-Loop für Rückfragen
            await self.listen_loop()

        except asyncio.CancelledError:
            logger.info("Pipeline cancelled (call ended)")
        except Exception as e:
            logger.error(f"Pipeline error: {e}", exc_info=True)
            try:
                await self.speak("Es tut mir leid, es ist ein Fehler aufgetreten.")
            except Exception:
                logger.error("Failed to speak error message")

    async def listen_loop(self):
        """Hört auf Anrufer-Fragen und beantwortet sie per Claude."""
        logger.info("Entering listen loop for follow-up questions...")

        while True:
            # Audio sammeln bis Stille erkannt wird
            transcript = await self.listen_for_utterance()
            if not transcript:
                logger.info("No speech detected, ending listen loop")
                continue

            logger.info(f"Caller said: {transcript}")

            # Abschied erkennen
            if any(word in transcript.lower() for word in GOODBYE_WORDS):
                await self.speak("Auf Wiedersehen! Ich wünsche dir einen schönen Tag.")
                break

            # Claude-Antwort generieren
            answer = await self.llm_service.answer_followup(
                question=transcript,
                messages=self.messages,
                conversation_history=self.conversation_history,
            )
            logger.info(f"Claude answer: {answer}")

            # Antwort vorlesen
            await self.speak(answer)

    async def listen_for_utterance(self) -> str:
        """Streamt Audio an Deepgram und wartet auf eine vollständige Äußerung."""
        # Queue leeren (stale Audio von Wiedergabe)
        while not self.audio_queue.empty():
            try:
                self.audio_queue.get_nowait()
            except asyncio.QueueEmpty:
                break

        transcript_parts = []

        try:
            dg_ctx = self.stt_service.create_stream()
        except Exception as e:
            logger.error(f"Failed to create Deepgram stream: {e}")
            return ""

        try:
            async with dg_ctx as dg_ws:
                logger.info("Deepgram streaming connection established")

                async def forward_audio():
                    chunks_sent = 0
                    try:
                        while True:
                            chunk = await asyncio.wait_for(
                                self.audio_queue.get(), timeout=15.0
                            )
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

                async def receive_results():
                    async for msg in dg_ws:
                        data = json.loads(msg)
                        if data.get("type") == "Results":
                            alt = data.get("channel", {}).get("alternatives", [{}])[0]
                            text = alt.get("transcript", "")
                            is_final = data.get("is_final", False)
                            speech_final = data.get("speech_final", False)

                            logger.info(
                                f"DG: is_final={is_final}, speech_final={speech_final}, text='{text}'"
                            )

                            if is_final and text.strip():
                                transcript_parts.append(text.strip())

                            if (speech_final or is_final) and transcript_parts:
                                return

                        elif data.get("type") == "UtteranceEnd":
                            if transcript_parts:
                                return

                forward_task = asyncio.create_task(forward_audio())
                receive_task = asyncio.create_task(receive_results())

                done, pending = await asyncio.wait(
                    [forward_task, receive_task],
                    return_when=asyncio.FIRST_COMPLETED,
                )
                for task in pending:
                    task.cancel()

        except websockets.exceptions.WebSocketException as e:
            logger.error(f"Deepgram WebSocket error: {e}")
        except Exception as e:
            logger.error(f"listen_for_utterance error: {e}", exc_info=True)

        return " ".join(transcript_parts)


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
