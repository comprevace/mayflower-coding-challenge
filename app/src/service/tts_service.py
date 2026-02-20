import io
import logging

import edge_tts

logger = logging.getLogger(__name__)


class TTSService:
    def __init__(self, voice: str = "de-DE-ConradNeural"):
        self.voice = voice

    async def synthesize(self, text: str) -> bytes:
        """Wandelt Text in Audio-Bytes um (MP3)."""
        if not text:
            return b""

        try:
            communicate = edge_tts.Communicate(text, self.voice)
            buffer = io.BytesIO()

            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    buffer.write(chunk["data"])  # type: ignore

            logger.info(f"TTS generated {buffer.tell()} bytes for {len(text)} chars")
            return buffer.getvalue()
        except Exception as e:
            logger.error(f"TTS error: {e}")
            return b""