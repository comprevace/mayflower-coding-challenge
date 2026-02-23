from src.service.llm_service import LLMService
from src.service.stt_service import STTService
from src.service.telegram_service import TelegramService
from src.service.tts_service import TTSService


class ServiceProvider:
    """Zentraler Container für alle Service-Instanzen."""

    def __init__(
        self,
        telegram: TelegramService,
        llm: LLMService,
        tts: TTSService,
        stt: STTService,
    ):
        self.telegram = telegram
        self.llm = llm
        self.tts = tts
        self.stt = stt
