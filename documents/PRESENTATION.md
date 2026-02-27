# Präsentation: AI-Powered Messenger-Anrufbeantworter

> Zielformat: PowerPoint / Google Slides
> Gesamtzeit: ~15 Min. Demo + ~15 Min. Besprechung

---

## Folie 1: Titelfolie

**AI-Powered Messenger-Anrufbeantworter**
Probearbeit — Robin
Februar 2026

---

## Folie 2: Das Problem

**Ausgangssituation:**
- Du bist unterwegs und hast keinen Blick aufs Handy
- Wichtige Nachrichten kommen rein — du merkst es nicht
- Jemand will dich erreichen und ruft an

**Die Idee:**
> Du rufst eine Nummer an und bekommst deine ungelesenen Nachrichten vorgelesen — mit Absender, Zeitpunkt und Inhalt. Danach kannst du Rückfragen stellen.

---

## Folie 3: Der Kern-Flow

```
Anruf eingehend
  → Begrüßung ("Du hast X ungelesene Nachrichten...")
  → Automatischer Abruf via Telegram Bot API
  → Claude fasst zusammen (Absender → Zeit → Inhalt)
  → Sprachausgabe der Zusammenfassung
  → Rückfragen per Sprache ("Erzähl mir mehr über Nachricht 3")
  → Loop bis "Tschüss"
```

**Sprechernotiz:** Den Flow einmal verbal durchgehen, betonen dass es bidirektional ist — nicht nur Vorlesen, sondern echte Konversation.

---

## Folie 4: Architektur-Überblick

```
         Anrufer (Telefon)
              │
              ▼
        ┌──────────┐
        │  Twilio   │  ← Telephony Provider
        └────┬─────┘
             │ WebSocket (bidirektionales Audio)
             ▼
     ┌───────────────────┐
     │  Application      │
     │  Server (FastAPI)  │
     │                    │
     │  ┌──────────────┐ │
     │  │   Pipeline    │ │  ← Orchestrierung
     │  └──┬───┬───┬──┘ │
     │     │   │   │     │
     │     ▼   ▼   ▼     │
     │  [STT][LLM][TTS]  │
     │     │         │    │
     └─────┼────┬────┼───┘
           │    │    │
           ▼    ▼    ▼
      Deepgram Claude edge-tts
                │
                ▼
          Telegram Bot API
```

**Sprechernotiz:** Betonen: Alle externen Services sind austauschbar. Klare Trennung durch Service-Klassen und zentralen ServiceProvider.

---

## Folie 5: Tech-Stack & Begründungen

| Komponente | Wahl | Warum? |
|---|---|---|
| **Sprache** | Python 3.13 | Async-Support, schnelle Prototyping, alle SDKs verfügbar |
| **Framework** | FastAPI | Async, WebSocket-Support, Auto-Docs, Health-Endpoints |
| **Telefonie** | Twilio | Free Trial, WebSocket Media Streams, gut dokumentiert |
| **STT** | Deepgram | Eingebautes VAD → keine separate Silero-Komponente nötig |
| **LLM** | Claude | Von Mayflower gestellt, exzellent für deutsche Zusammenfassungen |
| **TTS** | edge-tts | Kostenlos, kein API-Key, gute deutsche Stimmen |
| **Messenger** | Telegram | Empfohlen, kein OAuth, kostenlos, geringe Einstiegshürde |

**Sprechernotiz:** Bei jeder Technologie die *Abwägung* erklären, nicht nur die Wahl. Z.B.: "Deepgram statt lokalem Whisper, weil VAD eingebaut ist und ich keine separate Silero-Komponente brauchte."

---

## Folie 6: Code-Architektur

```
app/src/
├── endpoint.py              # FastAPI Routen
├── core/
│   ├── pipeline.py          # Kern-Orchestrierung
│   ├── service_provider.py  # Dependency Injection
│   ├── config.py            # Konfigurierbare Timeouts
│   └── audio_utils.py       # MP3 → mulaw Konvertierung
├── service/
│   ├── telegram_service.py  # Telegram Bot API
│   ├── llm_service.py       # Claude (Zusammenfassung + Q&A)
│   ├── tts_service.py       # edge-tts
│   ├── stt_service.py       # Deepgram Streaming
│   └── twilio_service.py    # TwiML + Media Streams
└── models/
    └── telegramMessage.py   # Datenmodell
```

**Kernprinzipien:**
- Jeder Service = eine Verantwortlichkeit
- ServiceProvider als zentraler Container
- Pipeline orchestriert den Flow
- Alle Timeouts konfigurierbar via ENV

**Sprechernotiz:** Kurz auf die Trennung eingehen. Zeigen, dass jeder Service einzeln testbar und austauschbar ist.

---

## Folie 7: Sprach-Pipeline im Detail

```
Twilio Audio (mulaw 8kHz)
    │
    ▼
Deepgram STT (WebSocket Streaming)
    │  ← VAD erkennt Sprechpausen automatisch
    ▼
Transkribierter Text
    │
    ▼
Claude API
    │  ← System-Prompt + Conversation History
    ▼
Antwort-Text
    │
    ▼
edge-tts (MP3)
    │
    ▼
audio_utils (MP3 → mulaw 8kHz)
    │
    ▼
Twilio WebSocket → Anrufer hört Antwort
```

**Sprechernotiz:** Betonen, dass das Audio-Format (mulaw 8kHz) von Twilio vorgegeben ist. Pydub + ffmpeg übernehmen die Konvertierung.

---

## Folie 8: Containerisierung & Deployment

**Dockerfile** (Multi-Stage Build):
- Build: `python:3.13-slim` + `uv` für Dependencies
- Runtime: Schlankes Image mit ffmpeg
- Health-Check eingebaut

**Kubernetes:**
- Deployment mit Resource Requests/Limits
- Liveness + Readiness Probes auf `/health`
- Secrets via K8s Secrets (aus `.env`)
- Kustomize für Orchestrierung
- LoadBalancer Service

**Sprechernotiz:** Zeigen, dass das Deployment production-ready vorbereitet ist — nicht nur ein Dockerfile, sondern echte K8s-Manifeste mit Probes und Ressourcen-Limits.

---

## Folie 9: Was in Production anders wäre

| Bereich | Prototyp | Production |
|---|---|---|
| TTS | edge-tts (kostenlos, inoffiziell) | Google Cloud TTS / Amazon Polly |
| Secrets | `.env` + K8s Secrets | HashiCorp Vault |
| Skalierung | 1 Replica | HPA basierend auf WebSocket-Connections |
| Queue | In-Memory asyncio.Queue | Redis |
| Monitoring | Logs | Prometheus + Grafana |
| TLS | ngrok | NGINX Ingress + Let's Encrypt |
| CI/CD | Manuell | GitHub Actions → K8s |

**Sprechernotiz:** Zeigt, dass pragmatische Abkürzungen bewusst getroffen wurden — und du weißt, was in Produktion anders sein müsste.

---

## Folie 10: Live-Demo

**Jetzt zeige ich es in Aktion!**

Lokale Demo per Mikrofon + Lautsprecher (gleiche Pipeline, ohne Twilio):

```bash
uv run python app/local_demo.py
```

1. Terminal zeigen → Skript startet
2. Begrüßung kommt über Lautsprecher
3. Telegram-Nachrichten werden abgerufen + zusammengefasst
4. Zusammenfassung hörbar
5. Rückfrage ins Mikrofon stellen (z.B. "Was war nochmal mit dem Meeting?")
6. Claude antwortet über Lautsprecher
7. "Tschüss" sagen → Demo endet

**Sprechernotiz:** Erklären: "Die einzige Komponente die hier simuliert wird ist die Twilio-Telefonie. Deepgram STT, Claude, edge-tts und Telegram laufen identisch zum Produktionscode. Laut Aufgabenstellung liegt der Fokus auf Architektur, Messenger-Integration, LLM-Zusammenfassung und Sprach-Ein-/Ausgabe — nicht auf der Telefonie-Infrastruktur."

---

## Folie 11: Zusammenfassung

- Funktionaler Prototyp mit bidirektionaler Sprachinteraktion
- Saubere Architektur mit austauschbaren Services
- Container-ready mit Kubernetes-Deployment
- Bewusste Tech-Entscheidungen mit dokumentierten Trade-offs
- Production-Verbesserungen dokumentiert

**Fragen?**

---

# Demo-Checkliste

## Einen Tag vorher

- [ ] API-Keys prüfen (Telegram, Deepgram, Anthropic)
- [ ] `uv sync` ausführen (installiert sounddevice + numpy)
- [ ] `uv run python app/local_demo.py` testen — Begrüßung hörbar?
- [ ] Mikrofon testen: Rückfrage stellen, Antwort prüfen
- [ ] Telegram-Bot testen: Nachrichten senden und abrufen

## 30 Minuten vor der Demo

- [ ] `.env` Datei prüfen — Telegram, Deepgram, Anthropic Keys korrekt?
- [ ] Mikrofon + Lautsprecher des Laptops testen
- [ ] Lautstärke hoch genug für Zuschauer?
- [ ] Einmal `uv run python app/local_demo.py` komplett durchlaufen lassen

## Demo-Nachrichten vorbereiten

Sende 3-4 verschiedene Nachrichten an den Telegram-Bot, die gut klingen:

**Beispiel-Nachrichten:**
1. "Hey, kannst du heute Abend zum Essen kommen? Wir treffen uns um 19 Uhr bei Luigi's."
2. "Das Meeting morgen wurde auf 10:30 verschoben. Bitte bring die Quartalsberichte mit."
3. "Dein Paket wurde geliefert und steht vor der Tür."
4. "Kurze Erinnerung: Zahnarzttermin am Donnerstag um 14 Uhr."

> Tipp: Verschiedene Themen und Längen wirken natürlicher.

## Während der Demo

- [ ] Terminal sichtbar (zeigt Status-Meldungen + Logs)
- [ ] `uv run python app/local_demo.py` starten
- [ ] Begrüßung abwarten → Zusammenfassung hören
- [ ] Eine Rückfrage ins Mikrofon stellen (z.B. "Was war nochmal mit dem Meeting?")
- [ ] Claude-Antwort abwarten
- [ ] Mit "Tschüss" verabschieden

## Backup-Plan

Falls etwas schiefgeht:
- **Kein Audio?** → ffmpeg installiert? `ffmpeg -version` prüfen
- **Mikrofon geht nicht?** → Windows Einstellungen → Datenschutz → Mikrofon → Zugriff erlauben
- **Deepgram-Fehler?** → API-Key prüfen, Deepgram-Guthaben checken
- **edge-tts Fehler?** → Internetverbindung prüfen (braucht Microsoft-Server)
- **Keine Telegram-Nachrichten?** → Nachrichten an Bot senden, dann nochmal starten
