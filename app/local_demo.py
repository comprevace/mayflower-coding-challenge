"""
Lokale Demo: Ersetzt Twilio durch Mikrofon + Lautsprecher.

Nutzung: uv run python app/local_demo.py

Verwendet alle bestehenden Services (Telegram, Claude, Deepgram, edge-tts)
und ersetzt nur die Twilio-Transportschicht durch lokale Audio-I/O.
"""

import asyncio
import audioop
import io
import json
import logging
import os
import sys
from pathlib import Path

# Damit 'from src...' funktioniert (wie in app.py)
sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
import sounddevice as sd
import websockets
from dotenv import load_dotenv
from pydub import AudioSegment

load_dotenv()

from src.core.pipeline import ERROR_MSG, GOODBYE_MSG, GOODBYE_WORDS, GREETING
from src.core.service_provider import ServiceProvider
from src.service.llm_service import LLMService
from src.service.stt_service import STTService
from src.service.telegram_service import TelegramService
from src.service.tts_service import TTSService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


# ── Konsolen-Ausgabe ──


def status(msg: str):
    """Gibt eine formatierte Statusmeldung auf der Konsole aus."""
    print(f"\n{'='*60}")
    print(f"  {msg}")
    print(f"{'='*60}\n")


# ── Audio-Ausgabe (TTS → Lautsprecher) ──


async def play_mp3(mp3_bytes: bytes):
    """Spielt MP3-Audio über die Lautsprecher ab."""
    if not mp3_bytes:
        return

    audio = AudioSegment.from_mp3(io.BytesIO(mp3_bytes))
    audio = audio.set_channels(1)

    samples = np.array(audio.get_array_of_samples(), dtype=np.float32)
    samples /= 2 ** (audio.sample_width * 8 - 1)

    loop = asyncio.get_event_loop()
    await loop.run_in_executor(
        None,
        lambda: sd.play(samples, samplerate=audio.frame_rate, blocking=True),
    )


async def speak(text: str, tts: TTSService):
    """Wandelt Text in Sprache und spielt es über die Lautsprecher ab."""
    status(f"[TTS] {text[:80]}{'...' if len(text) > 80 else ''}")
    mp3_bytes = await tts.synthesize(text)
    await play_mp3(mp3_bytes)


# ── Audio-Eingabe (Mikrofon → Deepgram STT) ──


async def listen_for_utterance(stt: STTService) -> str:
    """Nimmt Sprache über das Mikrofon auf und transkribiert via Deepgram."""
    status("[MIC] Hoere zu... (Sprechen Sie jetzt)")
    transcript_parts: list[str] = []

    try:
        dg_ctx = stt.create_stream()
    except Exception as e:
        logger.error(f"Failed to create Deepgram stream: {e}")
        return ""

    try:
        async with dg_ctx as dg_ws:
            logger.info("Deepgram streaming connection established")
            await _stream_and_transcribe(dg_ws, transcript_parts)
    except websockets.exceptions.WebSocketException as e:
        logger.error(f"Deepgram WebSocket error: {e}")
    except Exception as e:
        logger.error(f"listen_for_utterance error: {e}", exc_info=True)

    result = " ".join(transcript_parts)
    if result:
        print(f'  [STT] Erkannt: "{result}"')
    return result


async def _stream_and_transcribe(dg_ws, transcript_parts: list[str]):
    """Startet Mikrofon-Forwarding und Receive-Tasks parallel."""
    forward_task = asyncio.create_task(_forward_mic_audio(dg_ws))
    receive_task = asyncio.create_task(
        _receive_transcript(dg_ws, transcript_parts)
    )

    _, pending = await asyncio.wait(
        [forward_task, receive_task],
        return_when=asyncio.FIRST_COMPLETED,
    )
    for task in pending:
        task.cancel()


async def _forward_mic_audio(dg_ws):
    """Streamt Mikrofon-Audio an Deepgram als mulaw 8kHz."""
    SAMPLE_RATE = 8000
    CHANNELS = 1
    BLOCK_SIZE = 640  # 80ms Chunks bei 8kHz

    audio_queue: asyncio.Queue[bytes | None] = asyncio.Queue()
    loop = asyncio.get_event_loop()

    def callback(indata, frames, time_info, status_flags):
        if status_flags:
            logger.warning(f"Sounddevice status: {status_flags}")
        pcm_bytes = indata.tobytes()
        mulaw_bytes = audioop.lin2ulaw(pcm_bytes, 2)
        loop.call_soon_threadsafe(audio_queue.put_nowait, mulaw_bytes)

    stream = sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        dtype="int16",
        blocksize=BLOCK_SIZE,
        callback=callback,
    )

    chunks_sent = 0
    try:
        stream.start()
        while True:
            chunk = await asyncio.wait_for(audio_queue.get(), timeout=15.0)
            if chunk is None:
                break
            await dg_ws.send(chunk)
            chunks_sent += 1
            if chunks_sent % 50 == 0:
                logger.info(f"Forwarded {chunks_sent} mic chunks to Deepgram")
    except (asyncio.TimeoutError, asyncio.CancelledError):
        pass
    finally:
        stream.stop()
        stream.close()
        logger.info(f"Mic forward done. Total: {chunks_sent}")
        try:
            await dg_ws.send(json.dumps({"type": "CloseStream"}))
        except Exception:
            pass


async def _receive_transcript(dg_ws, transcript_parts: list[str]):
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


# ── Haupt-Flow ──


async def run_demo():
    """Haupt-Flow: Begrüßung → Nachrichten → Zusammenfassung → Rückfragen."""
    services = ServiceProvider(
        telegram=TelegramService(bot_token=os.getenv("TELEGRAM_BOT_TOKEN", "")),
        llm=LLMService(
            api_key=os.getenv("ANTHROPIC_API_KEY", ""),
            model=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514"),
        ),
        tts=TTSService(voice=os.getenv("TTS_VOICE", "de-DE-ConradNeural")),
        stt=STTService(api_key=os.getenv("DEEPGRAM_API_KEY", "")),
    )

    conversation_history: list[dict] = []

    try:
        # 1. Begruessung
        status("[START] Demo gestartet!")
        await speak(GREETING, services.tts)

        # 2. Telegram-Nachrichten abrufen
        status("[TELEGRAM] Rufe Nachrichten ab...")
        messages = await services.telegram.get_messages()
        logger.info(f"Retrieved {len(messages)} messages")

        if not messages:
            await speak(
                "Du hast keine neuen Nachrichten. Auf Wiedersehen!", services.tts
            )
            return

        # 3. Claude-Zusammenfassung
        status("[LLM] Claude fasst Nachrichten zusammen...")
        summary = await services.llm.summarize(messages)
        logger.info(f"Summary: {summary}")

        # 4. Zusammenfassung vorlesen
        await speak(summary, services.tts)

        # 5. Nachrichten als gelesen markieren
        last_update_id = messages[-1].update_id
        try:
            await services.telegram.acknowledge(last_update_id)
        except Exception as e:
            logger.warning(f"Failed to acknowledge messages: {e}")

        # 6. Rückfragen-Loop
        status("[Q&A] Rueckfragen-Modus (sag 'Tschuess' zum Beenden)")
        while True:
            transcript = await listen_for_utterance(services.stt)
            if not transcript:
                continue

            logger.info(f"User said: {transcript}")

            if any(word in transcript.lower() for word in GOODBYE_WORDS):
                await speak(GOODBYE_MSG, services.tts)
                break

            status("[LLM] Claude denkt nach...")
            answer = await services.llm.answer_followup(
                question=transcript,
                messages=messages,
                conversation_history=conversation_history,
            )
            logger.info(f"Claude answer: {answer}")
            await speak(answer, services.tts)

    except KeyboardInterrupt:
        print("\nDemo beendet.")
    except Exception as e:
        logger.error(f"Demo error: {e}", exc_info=True)
        try:
            await speak(ERROR_MSG, services.tts)
        except Exception:
            logger.error("Failed to speak error message")

    status("[ENDE] Demo beendet. Auf Wiedersehen!")


# ── Einstiegspunkt ──

if __name__ == "__main__":
    status("AI-Powered Messenger-Anrufbeantworter -- Lokale Demo")
    print("  Mikrofon + Lautsprecher statt Telefon.")
    print("  Alle Services identisch (Telegram, Claude, Deepgram, edge-tts).")
    print("  Druecke Ctrl+C zum Beenden.\n")

    try:
        asyncio.run(run_demo())
    except KeyboardInterrupt:
        print("\nDemo beendet.")
