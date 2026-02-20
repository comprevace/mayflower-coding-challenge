# AI-Powered Messenger-Anrufbeantworter

Ein sprachgesteuerter Anrufbeantworter, der eingehende Telefonanrufe entgegennimmt, ungelesene Nachrichten aus Telegram abruft, diese per LLM zusammenfasst und dem Anrufer als Sprache zurückgibt.

## Architektur-Übersicht

```
Anrufer
  │
  ▼
Twilio (Telephony)
  │  WebSocket (bidirektionaler Audio-Stream)
  ▼
Application Server
  ├── Deepgram STT (Speech-to-Text, inkl. VAD/Endpointing)
  ├── Claude API (LLM-Zusammenfassung & Konversation)
  ├── edge-tts (Text-to-Speech)
  └── Telegram Bot API (Messenger-Integration)
```

### Kern-Flow

1. Anruf geht bei Twilio ein → WebSocket-Verbindung zum Application Server
2. Begrüßung wird per TTS generiert und an den Anrufer gestreamt
3. Ungelesene Nachrichten werden via Telegram Bot API abgerufen
4. Claude fasst die Nachrichten zusammen (Absender → Zeitpunkt → Inhalt)
5. Zusammenfassung wird per TTS als Sprache an den Anrufer ausgegeben
6. Anrufer kann per Sprache Rückfragen stellen (bidirektionale Konversation)

## Tech-Stack

| Komponente | Technologie | Kosten |
|---|---|---|
| Telephony | Twilio (Free Trial) | Kostenlos ($15 Guthaben) |
| Speech-to-Text | Deepgram (WebSocket API, inkl. VAD) | Kostenlos ($200 Credit) |
| LLM | Claude API (Anthropic) | Key von Mayflower gestellt |
| Text-to-Speech | edge-tts (Microsoft Edge TTS) | Kostenlos, kein API Key nötig |
| Messenger | Telegram Bot API | Kostenlos |

### Begründung der Technologie-Entscheidungen

- **Deepgram** statt lokales Whisper: Bietet eingebautes VAD/Endpointing über WebSocket-Streaming, sodass keine separate VAD-Komponente (z.B. Silero) nötig ist. Reduziert Komplexität erheblich.
- **edge-tts** statt ElevenLabs/Google TTS: Komplett kostenlos, kein API Key nötig, gute deutsche Stimmen verfügbar. Für einen Prototyp ideal.
- **Twilio** für Telephony: Free Trial reicht für die Demo. Bietet WebSocket Media Streams für bidirektionales Audio-Streaming.
- **Telegram Bot API**: Empfohlen in der Aufgabenstellung. Geringe Einstiegshürde, kein OAuth, kostenlos, gut dokumentiert.

## Containerisierung & Deployment

- Dockerfile für den Application Server
- Kubernetes Deployment-Manifest (YAML)
- Lokales Cluster via Kind oder K3s
- Konfiguration über Umgebungsvariablen (API Keys, Tokens)
- Health-Check / Readiness-Probe

## Setup

> TODO: Setup-Anleitung folgt

## Abweichungen Prototyp vs. Produktivsystem

> TODO: Dokumentation pragmatischer Abkürzungen und was in Produktion anders wäre

## Tickets

 - Erstelle Tickets um Überblick zu erhalten und um die Aufgabenstellungen systematisch abarbeiten zu können
