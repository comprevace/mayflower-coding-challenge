# Tickets – AI-Powered Messenger-Anrufbeantworter

## Übersicht

```
Ticket 1: Projekt-Setup
   │
Ticket 2: Telegram Bot Integration
   │
Ticket 3: LLM-Zusammenfassung (Claude)
   │
Ticket 4: Text-to-Speech (edge-tts)
   │
Ticket 5: Speech-to-Text (Deepgram)
   │
Ticket 6: Twilio Telephony – Basis
   │
Ticket 7: Audio-Pipeline (End-to-End)
   │
Ticket 8: Bidirektionale Konversation
   │
Ticket 9: Fehlerbehandlung & Logging
   │
Ticket 10: Containerisierung (Docker)
   │
Ticket 11: Kubernetes Deployment
   │
Ticket 12: Dokumentation & Cleanup
   │
Ticket 13: Tests
```

---

## Ticket 1: Projekt-Setup
**Ziel:** Grundgerüst des Projekts aufsetzen  
**Tasks:**
- Repository initialisieren
- Programmiersprache & Framework festlegen (z.B. Python + FastAPI)
- Projektstruktur anlegen (Modulare Trennung der Komponenten)
- Dependency Management (requirements.txt / pyproject.toml)
- .env-Template für API Keys und Tokens
- .gitignore

**Testbar:** Projekt startet ohne Fehler, Health-Endpoint erreichbar

---

## Ticket 2: Telegram Bot Integration
**Ziel:** Ungelesene Nachrichten aus Telegram abrufen können  
**Tasks:**
- Telegram Bot über BotFather erstellen
- Telegram Bot API anbinden (getUpdates oder Webhook)
- Ungelesene Nachrichten abrufen mit Metadaten (Absender, Timestamp, Text)
- Nachrichten-Modell definieren (Datenstruktur)
- Fehlerbehandlung (keine Nachrichten, API nicht erreichbar, Rate Limits)

**Testbar:** API-Call gibt Liste ungelesener Nachrichten als strukturierte Daten zurück

---

## Ticket 3: LLM-Zusammenfassung (Claude)
**Ziel:** Nachrichten per Claude API zusammenfassen  
**Tasks:**
- Claude API (Anthropic SDK) anbinden
- Prompt-Design für strukturierte Zusammenfassung
  - Format: Absender → Zeitpunkt → Kerninhalt
  - Umgang mit mehreren Nachrichten (Gruppierung/Priorisierung)
- Prompt für natürliche Sprachausgabe optimieren (wird vorgelesen!)
- Fehlerbehandlung (API-Fehler, leere Nachrichten)

**Testbar:** Übergabe von Beispiel-Nachrichten → Claude gibt sprechbare Zusammenfassung zurück

---

## Ticket 4: Text-to-Speech (edge-tts)
**Ziel:** Text in Audio-Daten umwandeln  
**Tasks:**
- edge-tts integrieren
- Deutsche Stimme auswählen und konfigurieren
- Text → Audio-Bytes Pipeline
- Audio-Format passend für Twilio (mulaw 8kHz) sicherstellen
- Streaming-fähig machen (falls möglich)

**Testbar:** Text-Input → Audio-Datei wird erzeugt und ist abspielbar

---

## Ticket 5: Speech-to-Text (Deepgram)
**Ziel:** Audio-Stream in Text umwandeln  
**Tasks:**
- Deepgram Account + API Key
- WebSocket-Verbindung zu Deepgram Streaming API
- Audio-Chunks entgegennehmen und weiterleiten
- VAD/Endpointing konfigurieren (erkennt Sprechende)
- Interim- vs. Final-Transkripte verarbeiten
- Deutsche Sprache konfigurieren

**Testbar:** Audio-Datei → korrektes deutsches Transkript

---

## Ticket 6: Twilio Telephony – Basis
**Ziel:** Eingehenden Anruf entgegennehmen und Audio streamen  
**Tasks:**
- Twilio Account + Telefonnummer einrichten
- Webhook-Endpoint für eingehende Anrufe (TwiML)
- WebSocket Media Stream aufsetzen (bidirektional)
- Audio-Format verstehen (mulaw, 8kHz, base64-encoded)
- Ngrok oder ähnliches für lokale Entwicklung
- Einfacher Test: Anruf → statische Begrüßung abspielen

**Testbar:** Anruf auf Twilio-Nummer → Begrüßung wird abgespielt

---

## Ticket 7: Audio-Pipeline (End-to-End)
**Ziel:** Alle Komponenten zum Kern-Flow verbinden  
**Tasks:**
- Anruf eingehend → Begrüßung per TTS
- Telegram-Nachrichten abrufen
- Claude-Zusammenfassung generieren
- Zusammenfassung per TTS an Anrufer streamen
- Audio-Formate zwischen Twilio ↔ Deepgram ↔ edge-tts konvertieren
- Latenz optimieren

**Testbar:** Kompletter Kern-Flow funktioniert: Anruf → Begrüßung → Zusammenfassung hören

---

## Ticket 8: Bidirektionale Konversation
**Ziel:** Anrufer kann Rückfragen stellen  
**Tasks:**
- Nach Zusammenfassung auf Spracheingabe warten
- Deepgram STT für Rückfragen nutzen
- Claude Conversation-Kontext aufbauen (Nachrichten + bisherige Konversation)
- Rückfragen verarbeiten ("Erzähl mir mehr über Nachricht 3")
- Antwort per TTS zurückgeben
- Loop bis Anrufer auflegt oder "Tschüss" sagt
- Fehlerbehandlung bei unverständlichen Eingaben

**Testbar:** Anrufer hört Zusammenfassung, stellt Rückfrage, bekommt sinnvolle Antwort

---

## Ticket 9: Fehlerbehandlung & Logging
**Ziel:** Robustes Error Handling und nachvollziehbares Logging  
**Tasks:**
- Strukturiertes Logging (z.B. structlog oder logging mit JSON)
- Fehlerbehandlung pro Komponente absichern
  - Telegram API nicht erreichbar
  - Claude API Timeout/Fehler
  - Deepgram WebSocket Disconnect
  - Twilio Stream Abbruch
- Graceful Degradation (z.B. "Entschuldigung, ich konnte deine Nachrichten gerade nicht abrufen")
- Timeouts konfigurieren

**Testbar:** Fehlerszenarien durchspielen → System reagiert sinnvoll statt zu crashen

---

## Ticket 10: Containerisierung (Docker)
**Ziel:** Anwendung als Docker Container lauffähig  
**Tasks:**
- Dockerfile erstellen (Multi-Stage Build falls sinnvoll)
- .dockerignore
- Umgebungsvariablen für alle API Keys / Tokens
- Container lokal bauen und testen
- Health-Check Endpoint im Dockerfile

**Testbar:** `docker build` + `docker run` → Service startet und ist erreichbar

---

## Ticket 11: Kubernetes Deployment
**Ziel:** Deployment auf lokalem K8s Cluster  
**Tasks:**
- Lokales Cluster aufsetzen (Kind oder K3s)
- Kubernetes Deployment Manifest
- Service Manifest
- ConfigMap / Secret für Umgebungsvariablen
- Readiness-Probe / Liveness-Probe
- Deployment testen

**Testbar:** `kubectl apply` → Pod läuft, Probes sind green, Service erreichbar

---

## Ticket 12: Dokumentation & Cleanup
**Ziel:** Alles für die Abgabe vorbereiten  
**Tasks:**
- README finalisieren
  - Setup-Anleitung (Schritt für Schritt)
  - Architektur-Übersicht mit Diagramm
  - Umgebungsvariablen dokumentieren
- Abschnitt "Prototyp vs. Produktion" schreiben
- Code aufräumen, tote Imports entfernen
- Commit-History prüfen (nachvollziehbare Schritte)
- Demo vorbereiten (Talking Points, Architektur-Entscheidungen)

**Testbar:** Jemand anderes kann das Projekt nur mit der README aufsetzen

---

## Ticket 13: Tests
**Ziel:** Unit Tests für alle Service-Klassen und Hilfsfunktionen
**Tasks:**
- Test-Framework aufsetzen (pytest + pytest-asyncio)
- **TelegramService**: `_parse_update()` mit verschiedenen Update-Formaten, `fetch_unread_messages()` mit gemockter HTTP-Response, `acknowledge()`
- **LLMService**: `_format_messages()` mit verschiedenen Nachrichtensets, `summarize()` und `answer_followup()` mit gemocktem Anthropic Client, Fallback bei API-Fehlern
- **TTSService**: `synthesize()` mit gemocktem edge-tts, mulaw-Konvertierung prüfen
- **STTService**: `create_stream()` URL und Header korrekt
- **TwilioService**: `generate_twiml()` gibt valides TwiML zurück
- **Pipeline**: `_flush_audio_queue()`, Goodbye-Erkennung
- **audio_utils**: `mp3_to_mulaw()` Konvertierung
- **config**: Timeout-Werte aus Umgebungsvariablen

**Testbar:** `pytest` läuft durch, alle Tests grün

---

## Zeitschätzung (grob)

| Ticket | Aufwand |
|---|---|
| 1: Projekt-Setup | 0.5 Tage |
| 2: Telegram Integration | 0.5 Tage |
| 3: LLM-Zusammenfassung | 0.5 Tage |
| 4: TTS (edge-tts) | 0.5 Tage |
| 5: STT (Deepgram) | 0.5 Tage |
| 6: Twilio Basis | 1 Tag |
| 7: Audio-Pipeline E2E | 1-2 Tage |
| 8: Bidirektionale Konversation | 1 Tag |
| 9: Fehlerbehandlung & Logging | 0.5 Tage |
| 10: Docker | 0.5 Tage |
| 11: Kubernetes | 0.5 Tage |
| 12: Dokumentation | 0.5 Tage |
| 13: Tests | 1 Tag |
| **Gesamt** | **~8-9 Tage** |

> Puffer einplanen für unerwartete Probleme, besonders bei der Audio-Pipeline (Ticket 7).
