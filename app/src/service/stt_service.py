import logging

import httpx

logger = logging.getLogger(__name__)

DEEPGRAM_URL = "https://api.deepgram.com/v1/listen"


class STTService:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = httpx.AsyncClient(timeout=30.0)

    async def transcribe(self, audio_bytes: bytes) -> str:
        """Wandelt Audio-Bytes in Text um."""
        if not audio_bytes:
            return ""

        try:
            response = await self.client.post(
                DEEPGRAM_URL,
                params={
                    "model": "nova-2",
                    "language": "de",
                    "smart_format": "true",
                    "punctuate": "true",
                },
                headers={
                    "Authorization": f"Token {self.api_key}",
                    "Content-Type": "audio/mpeg",
                },
                content=audio_bytes,
            )
            response.raise_for_status()
            data = response.json()

            transcript = (
                data["results"]["channels"][0]["alternatives"][0]["transcript"]
            )
            logger.info(f"STT transcribed: {transcript}")
            return transcript
        except Exception as e:
            logger.error(f"STT error: {e}")
            return ""

    async def close(self):
        await self.client.aclose()
