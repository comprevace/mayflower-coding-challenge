import logging

from anthropic import AsyncAnthropic

from src.models.telegramMessage import TelegramMessage

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Du bist ein Anrufbeantworter-Assistent. Der Benutzer ruft an, um seine
Telegram-Nachrichten vorgelesen zu bekommen.

Regeln:
- Beginne mit "Du hast X neue Nachrichten."
- Fasse jede Nachricht in einem kurzen Satz zusammen
- Nummeriere die Nachrichten (Nachricht 1, Nachricht 2, ...)
- Nenne Absender und ungefähre Uhrzeit
- Halte dich kurz — der Text wird per Telefon vorgelesen
- Ende mit "Möchtest du zu einer Nachricht mehr erfahren?"
"""


class SummarizerService:
    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514"):
        self.client = AsyncAnthropic(api_key=api_key)
        self.model = model

    async def summarize(self, messages: list[TelegramMessage]) -> str:
        """Fasst Telegram-Nachrichten als sprechbaren Text zusammen."""
        if not messages:
            return "Du hast keine neuen Nachrichten."

        formatted = "\n".join(
            f"[{m.timestamp.strftime('%H:%M')}] {m.sender}: {m.text}"
            for m in messages
        )

        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=500,
                system=SYSTEM_PROMPT,
                messages=[{
                    "role": "user",
                    "content": f"Fasse diese Nachrichten zusammen:\n\n{formatted}"
                }],
            )
            return response.content[0].text # type: ignore
        except Exception as e:
            logger.error(f"Claude API error: {e}")
            return "Entschuldigung, ich konnte deine Nachrichten gerade nicht zusammenfassen."
