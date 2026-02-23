import asyncio
import io
import logging

import edge_tts

from src.core.config import TTS_TIMEOUT

logger = logging.getLogger(__name__)


class TTSService:
    def __init__(self, voice: str = "de-DE-ConradNeural"):
        self.voice = voice

    async def synthesize(self, text: str) -> bytes:
        """Wandelt Text in Audio-Bytes um (MP3)."""
        if not text:
            return b""

        try:
            return await asyncio.wait_for(
                self._do_synthesize(text), timeout=TTS_TIMEOUT
            )
        except asyncio.TimeoutError:
            logger.error(f"TTS timeout nach {TTS_TIMEOUT}s für {len(text)} Zeichen")
            return b""
        except ConnectionError as e:
            logger.error(f"TTS connection error: {e}")
            return b""
        except Exception as e:
            logger.error(f"TTS unexpected error: {e}")
            return b""

    async def _do_synthesize(self, text: str) -> bytes:
        """Interne TTS-Synthese ohne Timeout-Wrapper."""
        communicate = edge_tts.Communicate(text, self.voice)
        buffer = io.BytesIO()

        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                buffer.write(chunk["data"])  # type: ignore

        logger.info(f"TTS generated {buffer.tell()} bytes for {len(text)} chars")
        return buffer.getvalue()