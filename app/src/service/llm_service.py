import logging

from anthropic import APIConnectionError, APIStatusError, APITimeoutError, AsyncAnthropic

from src.core.config import ANTHROPIC_TIMEOUT
from src.models.telegramMessage import TelegramMessage

logger = logging.getLogger(__name__)

SUMMARIZE_PROMPT = """Du bist ein Anrufbeantworter-Assistent. Der Benutzer ruft an, um seine
Telegram-Nachrichten vorgelesen zu bekommen.

Regeln:
- Beginne mit "Du hast X neue Nachrichten."
- Fasse jede Nachricht in einem kurzen Satz zusammen
- Nummeriere die Nachrichten (Nachricht 1, Nachricht 2, ...)
- Nenne Absender und ungefähre Uhrzeit
- Halte dich kurz — der Text wird per Telefon vorgelesen
- Ende mit "Möchtest du zu einer Nachricht mehr erfahren?"
"""

FOLLOWUP_PROMPT = """Du bist ein Anrufbeantworter-Assistent. Der Benutzer hat folgende
Telegram-Nachrichten:

{messages}

Der Benutzer stellt Rückfragen per Telefon. Antworte kurz und
präzise — deine Antwort wird per TTS vorgelesen.
Wenn der Benutzer "tschüss", "danke" oder ähnliches sagt,
verabschiede dich freundlich."""


class LLMService:
    """Claude-basierte Zusammenfassung und Rückfragen-Beantwortung."""

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514"):
        self.client = AsyncAnthropic(api_key=api_key, timeout=ANTHROPIC_TIMEOUT)
        self.model = model

    async def summarize(self, messages: list[TelegramMessage]) -> str:
        """Fasst Telegram-Nachrichten als sprechbaren Text zusammen."""
        if not messages:
            return "Du hast keine neuen Nachrichten."

        formatted = _format_messages(messages)

        return await self._call(
            system=SUMMARIZE_PROMPT,
            messages=[{
                "role": "user",
                "content": f"Fasse diese Nachrichten zusammen:\n\n{formatted}",
            }],
            max_tokens=500,
            fallback="Entschuldigung, ich konnte deine Nachrichten gerade nicht zusammenfassen.",
        )

    async def answer_followup(
        self,
        question: str,
        messages: list[TelegramMessage],
        conversation_history: list[dict],
    ) -> str:
        """Beantwortet eine Rückfrage im Kontext der Nachrichten."""
        system = FOLLOWUP_PROMPT.format(messages=_format_messages(messages))
        conversation_history.append({"role": "user", "content": question})

        answer = await self._call(
            system=system,
            messages=conversation_history,  # type: ignore
            max_tokens=300,
            fallback="Entschuldigung, das habe ich nicht verstanden.",
        )

        conversation_history.append({"role": "assistant", "content": answer})
        return answer

    async def _call(
        self,
        system: str,
        messages: list[dict],
        max_tokens: int,
        fallback: str,
    ) -> str:
        """Sendet eine Anfrage an Claude mit einheitlichem Error-Handling."""
        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                system=system,
                messages=messages,  # type: ignore
            )
            return response.content[0].text  # type: ignore
        except APITimeoutError:
            logger.error("Claude API timeout")
        except APIConnectionError:
            logger.error("Claude API connection error")
        except APIStatusError as e:
            logger.error(f"Claude API status error: {e.status_code} — {e.message}")
        except Exception as e:
            logger.error(f"Claude API unexpected error: {e}")

        return fallback


def _format_messages(messages: list[TelegramMessage]) -> str:
    """Formatiert Telegram-Nachrichten als lesbaren Text."""
    return "\n".join(
        f"[{m.timestamp.strftime('%H:%M')}] {m.sender}: {m.text}"
        for m in messages
    )
