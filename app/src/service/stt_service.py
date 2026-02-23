import logging

import websockets

logger = logging.getLogger(__name__)

DEEPGRAM_STREAM_URL = "wss://api.deepgram.com/v1/listen"

STREAM_PARAMS = "&".join([
    "encoding=mulaw",
    "sample_rate=8000",
    "channels=1",
    "language=de",
    "model=nova-2",
    "punctuate=true",
    "endpointing=2000",
])


class STTService:
    """Deepgram Streaming Speech-to-Text mit integrierter VAD."""

    def __init__(self, api_key: str):
        self.api_key = api_key

    def create_stream(self):
        """Öffnet eine Streaming-Verbindung zu Deepgram mit VAD."""
        return websockets.connect(
            f"{DEEPGRAM_STREAM_URL}?{STREAM_PARAMS}",
            additional_headers={"Authorization": f"Token {self.api_key}"},
        )
