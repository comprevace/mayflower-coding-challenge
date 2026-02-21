import audioop
import base64
import io
import logging

from pydub import AudioSegment

logger = logging.getLogger(__name__)


def mp3_to_mulaw(mp3_bytes: bytes) -> bytes:
    """Konvertiert MP3-Audio zu mulaw 8kHz (Twilio-Format)."""
    try:
        audio = AudioSegment.from_mp3(io.BytesIO(mp3_bytes))
        audio = audio.set_frame_rate(8000).set_channels(1).set_sample_width(2)
        mulaw = audioop.lin2ulaw(audio.raw_data, 2)
        logger.info(f"Converted {len(mp3_bytes)} MP3 bytes to {len(mulaw)} mulaw bytes")
        return mulaw
    except Exception as e:
        logger.error(f"Audio conversion error: {e}")
        return b""


def mulaw_to_base64_chunks(mulaw_bytes: bytes, chunk_size: int = 640) -> list[str]:
    """Teilt mulaw-Audio in Base64-kodierte Chunks für Twilio."""
    chunks = []
    for i in range(0, len(mulaw_bytes), chunk_size):
        chunk = mulaw_bytes[i : i + chunk_size]
        chunks.append(base64.b64encode(chunk).decode("ascii"))
    return chunks
