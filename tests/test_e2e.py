"""Tests für den AI-Powered Messenger-Anrufbeantworter."""

import base64
from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient

from src.core.audio_utils import mulaw_to_base64_chunks
from src.core.pipeline import GOODBYE_WORDS, GREETING
from src.models.telegramMessage import TelegramMessage
from src.service.llm_service import _format_messages
from src.service.telegram_service import TelegramService


# ── Testdaten ──

SAMPLE_UPDATE = {
    "update_id": 100,
    "message": {
        "message_id": 1,
        "from": {"first_name": "Max", "last_name": "Müller"},
        "chat": {"id": 42},
        "date": 1705326600,
        "text": "Kommst du heute Abend?",
    },
}

SAMPLE_MESSAGE = TelegramMessage(
    sender="Max Müller",
    timestamp=datetime(2024, 1, 15, 14, 30, tzinfo=ZoneInfo("Europe/Berlin")),
    text="Kommst du heute Abend?",
    chat_id=42,
    message_id=1,
    update_id=100,
)


# ── Endpoints ──


class TestEndpoints:
    def test_health_returns_ok(self):
        from src.endpoint import app
        response = TestClient(app).get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_voice_returns_twiml(self):
        from src.endpoint import app
        response = TestClient(app).post("/twilio/voice")
        assert response.status_code == 200
        assert "<Response>" in response.text
        assert "<Stream" in response.text


# ── Telegram Parsing ──


class TestTelegramParsing:
    def test_parse_update(self):
        result = TelegramService._parse_update(SAMPLE_UPDATE)
        assert result is not None
        assert result.sender == "Max Müller"
        assert result.text == "Kommst du heute Abend?"
        assert result.chat_id == 42

    def test_parse_update_without_lastname(self):
        update = {
            "update_id": 1,
            "message": {
                "message_id": 1,
                "from": {"first_name": "Anna"},
                "chat": {"id": 1},
                "date": 1700000000,
                "text": "Hi",
            },
        }
        result = TelegramService._parse_update(update)
        assert result.sender == "Anna"

    def test_parse_update_without_text_returns_none(self):
        update = {"update_id": 1, "message": {"message_id": 1, "from": {"first_name": "X"}, "chat": {"id": 1}, "date": 1700000000}}
        assert TelegramService._parse_update(update) is None

    def test_parse_update_without_message_returns_none(self):
        assert TelegramService._parse_update({"update_id": 1}) is None


# ── Nachrichtenformatierung ──


class TestFormatMessages:
    def test_format_single(self):
        result = _format_messages([SAMPLE_MESSAGE])
        assert result == "[14:30] Max Müller: Kommst du heute Abend?"

    def test_format_multiple(self):
        msg2 = TelegramMessage(
            sender="Anna",
            timestamp=datetime(2024, 1, 15, 15, 0, tzinfo=ZoneInfo("Europe/Berlin")),
            text="OK",
            chat_id=1, message_id=2, update_id=101,
        )
        result = _format_messages([SAMPLE_MESSAGE, msg2])
        assert "[14:30] Max Müller" in result
        assert "[15:00] Anna: OK" in result

    def test_format_empty(self):
        assert _format_messages([]) == ""


# ── Keine Nachrichten ──


class TestNoMessages:
    async def test_summarize_empty_returns_fallback(self):
        from src.service.llm_service import LLMService
        llm = LLMService(api_key="fake")
        result = await llm.summarize([])
        assert "keine neuen Nachrichten" in result


# ── Audio ──


class TestAudioChunking:
    def test_splits_into_chunks(self):
        data = b"\x00" * 1920
        chunks = mulaw_to_base64_chunks(data, chunk_size=640)
        assert len(chunks) == 3

    def test_chunks_are_valid_base64(self):
        data = b"\x01\x02\x03\x04" * 200
        for chunk in mulaw_to_base64_chunks(data):
            base64.b64decode(chunk)  # wirft Exception bei ungültigem Base64

    def test_empty_input(self):
        assert mulaw_to_base64_chunks(b"") == []


# ── Pipeline Konstanten ──


class TestPipelineConstants:
    def test_greeting_is_german(self):
        assert "Willkommen" in GREETING

    def test_goodbye_words(self):
        assert "tschüss" in GOODBYE_WORDS
        assert "danke" in GOODBYE_WORDS
        assert "bye" in GOODBYE_WORDS

    def test_goodbye_detection(self):
        assert any(w in "okay tschüss bis bald" for w in GOODBYE_WORDS)
        assert not any(w in "erzähl mir mehr" for w in GOODBYE_WORDS)
