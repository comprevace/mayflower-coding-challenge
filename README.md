# AI-Powered Messenger-Anrufbeantworter

Sprachgesteuerter Anrufbeantworter, der ungelesene Telegram-Nachrichten per Telefon zusammenfasst und Rückfragen im Dialog beantwortet.

## Ablauf

```
Anruf → Twilio → WebSocket → Telegram-Nachrichten abrufen
                                      ↓
                              Claude Zusammenfassung
                                      ↓
                              edge-tts → mulaw → Anrufer hört Zusammenfassung
                                      ↓
                              Anrufer spricht → Deepgram STT → Claude Antwort → TTS → Anrufer hört Antwort
                                      ↓
                              (Loop bis "Tschüss")
```

## Architektur

```
app/
├── app.py                          # Uvicorn Entrypoint
└── src/
    ├── endpoint.py                 # FastAPI Routen (/health, /twilio/*)
    ├── core/
    │   ├── config.py               # Konfigurierbare Timeouts (env)
    │   ├── pipeline.py             # Anruf-Orchestrierung (Kern-Flow)
    │   ├── service_provider.py     # Zentraler Service-Container
    │   └── audio_utils.py          # MP3 → mulaw Konvertierung
    ├── service/
    │   ├── telegram_service.py     # Telegram Bot API
    │   ├── llm_service.py          # Claude API (Zusammenfassung + Rückfragen)
    │   ├── tts_service.py          # edge-tts Text-to-Speech
    │   ├── stt_service.py          # Deepgram Streaming STT
    │   └── twilio_service.py       # TwiML + Media Stream Handling
    └── models/
        └── telegramMessage.py      # TelegramMessage Dataclass
k8s/                                # Kubernetes Manifeste
```

## Tech-Stack

| Komponente | Technologie |
|---|---|
| Framework | FastAPI + Uvicorn |
| Telefonie | Twilio Media Streams (WebSocket) |
| Nachrichten | Telegram Bot API |
| LLM | Anthropic Claude (claude-sonnet) |
| TTS | edge-tts (de-DE-ConradNeural) |
| STT | Deepgram Streaming (nova-2, VAD) |
| Audio | pydub + audioop-lts (MP3 → mulaw 8kHz) |
| Container | Docker (multi-stage mit uv) |
| Orchestrierung | Kubernetes |

## Setup

### Voraussetzungen

- Python 3.13+
- [uv](https://docs.astral.sh/uv/) (Package Manager)
- ffmpeg (für pydub)
- ngrok oder öffentliche URL (für Twilio Webhook)

### Installation

```bash
git clone https://github.com/comprevace/mayflower-coding-challenge.git
cd mayflower-coding-challenge

cp .env.example .env
# .env mit echten API-Keys befüllen

uv sync
```

### Lokal starten

```bash
# Terminal 1: Server
uv run python app/app.py

# Terminal 2: ngrok
ngrok http 8000
```

Twilio Webhook auf `https://<ngrok-url>/twilio/voice` setzen.

### Docker

```bash
docker compose up --build
```

### Kubernetes

```bash
# Secret erstellen
kubectl create secret generic messenger-ab-secrets --from-env-file=.env

# Deployen
kubectl apply -k k8s/
```

## Konfiguration

Alle Werte werden über Umgebungsvariablen gesetzt (siehe `.env.example`):

| Variable | Beschreibung | Default |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | Telegram Bot Token | - |
| `ANTHROPIC_API_KEY` | Anthropic API Key | - |
| `DEEPGRAM_API_KEY` | Deepgram API Key | - |
| `TWILIO_ACCOUNT_SID` | Twilio Account SID | - |
| `TWILIO_AUTH_TOKEN` | Twilio Auth Token | - |
| `TWILIO_PHONE_NUMBER` | Twilio Telefonnummer | - |
| `PUBLIC_URL` | Öffentliche URL (ngrok) | localhost:8000 |
| `TTS_VOICE` | edge-tts Stimme | de-DE-ConradNeural |
| `ANTHROPIC_MODEL` | Claude Modell | claude-sonnet-4-20250514 |
| `TELEGRAM_TIMEOUT` | Telegram Timeout (s) | 10 |
| `ANTHROPIC_TIMEOUT` | Claude Timeout (s) | 30 |
| `DEEPGRAM_TIMEOUT` | Deepgram Timeout (s) | 30 |
| `TTS_TIMEOUT` | TTS Timeout (s) | 15 |
