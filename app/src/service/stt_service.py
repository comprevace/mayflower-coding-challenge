import logging

import httpx
import websockets

from src.core.config import DEEPGRAM_TIMEOUT

logger = logging.getLogger(__name__)

DEEPGRAM_URL = "https://api.deepgram.com/v1/listen"
DEEPGRAM_STREAM_URL = "wss://api.deepgram.com/v1/listen"

class STTService:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = httpx.AsyncClient(timeout=DEEPGRAM_TIMEOUT)

    async def transcribe(self, audio_bytes: bytes, content_type: str = "audio/mpeg") -> str:
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
                    "Content-Type": content_type,
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
        except httpx.TimeoutException:
            logger.error("Deepgram API timeout — Transkription dauerte zu lange")
            return ""
        except httpx.ConnectError:
            logger.error("Deepgram API connection error — keine Verbindung")
            return ""
        except httpx.HTTPStatusError as e:
            logger.error(f"Deepgram API HTTP error: {e.response.status_code}")
            return ""
        except Exception as e:
            logger.error(f"STT unexpected error: {e}")
            return ""
        
    def create_stream(self):
        """Öffnet eine Streaming-Verbindung zu Deepgram mit VAD."""
        params = "&".join([
            "encoding=mulaw",
            "sample_rate=8000",
            "channels=1",
            "language=de",
            "model=nova-2",
            "punctuate=true",
            "endpointing=2000",
        ])
        return websockets.connect(
            f"{DEEPGRAM_STREAM_URL}?{params}",
            additional_headers={"Authorization": f"Token {self.api_key}"},
        )
        

    async def close(self):
        await self.client.aclose()
