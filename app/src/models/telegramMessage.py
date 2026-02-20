from dataclasses import dataclass
from datetime import datetime


@dataclass
class TelegramMessage:
    sender: str
    timestamp: datetime
    text: str
    chat_id: int
    message_id: int
    update_id: int