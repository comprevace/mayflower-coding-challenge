import logging
import os
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI

from src.service.telegram_service import TelegramService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI()


@app.get("/health")
async def health_check():
    """Health-Check Endpoint für Kubernetes Probes."""
    return {"status": "ok"}

telegram_service = TelegramService(
    bot_token=os.getenv("TELEGRAM_BOT_TOKEN", "")
)

@app.get("/messages")
async def get_messages(acknowledge: bool = False):
    """Temporärer Test-Endpoint für Telegram-Nachrichten."""
    messages = await telegram_service.get_messages()

    if acknowledge and messages:
        last_update_id = messages[-1].update_id
        await telegram_service.acknowledge(last_update_id)

    return {"count": len(messages), "messages": messages}