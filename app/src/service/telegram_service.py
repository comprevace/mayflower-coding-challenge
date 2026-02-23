import logging
from datetime import datetime, timezone

import httpx

from src.core.config import TELEGRAM_TIMEOUT
from src.models.telegramMessage import TelegramMessage

logger = logging.getLogger(__name__)

TELEGRAM_API_BASE = "https://api.telegram.org/bot{token}"


class TelegramService:
    def __init__(self, bot_token: str):
        self.bot_token = bot_token
        self.base_url = TELEGRAM_API_BASE.format(token=bot_token)
        self.client = httpx.AsyncClient(timeout=TELEGRAM_TIMEOUT)

    async def get_messages(self, limit: int = 20) -> list[TelegramMessage]:
        """Ruft die letzten Nachrichten via getUpdates ab."""
        url = f"{self.base_url}/getUpdates"
        params = {"limit": limit, "allowed_updates": '["message"]'}

        try:
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
        except httpx.TimeoutException:
            logger.error("Telegram API timeout — API nicht erreichbar")
            return []
        except httpx.ConnectError:
            logger.error("Telegram API connection error — keine Verbindung")
            return []
        except httpx.HTTPError as e:
            logger.error(f"Telegram API error: {e}")
            return []

        if not data.get("ok"):
            logger.error(f"Telegram API returned error: {data}")
            return []

        messages = []
        for update in data.get("result", []):
            msg = update.get("message")
            if not msg or not msg.get("text"):
                continue

            sender = msg["from"].get("first_name", "Unbekannt")
            if last_name := msg["from"].get("last_name"):
                sender = f"{sender} {last_name}"

            messages.append(
                TelegramMessage(
                    sender=sender,
                    timestamp=datetime.fromtimestamp(
                        msg["date"], tz=timezone.utc
                    ),
                    text=msg["text"],
                    chat_id=msg["chat"]["id"],
                    message_id=msg["message_id"],
                    update_id=update["update_id"],
                )
            )

        logger.info(f"Retrieved {len(messages)} messages from Telegram")
        return messages
    
    async def acknowledge(self, last_update_id: int):
        """Markiert Updates bis einschließlich last_update_id als gelesen."""
        url = f"{self.base_url}/getUpdates"
        params = {"offset": last_update_id + 1, "limit": 0}
        await self.client.get(url, params=params)
        logger.info(f"Acknowledged updates up to {last_update_id}")

    async def close(self):
        """HTTP Client schließen."""
        await self.client.aclose()
