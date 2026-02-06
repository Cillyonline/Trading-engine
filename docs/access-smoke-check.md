# Access Smoke Check (Owner)

## Purpose

Der Owner verifiziert **direkt nach dem Startup**, dass die Anwendung lokal erreichbar ist (Access vorhanden).

## Prerequisites

- Lokale Umgebung mit installiertem `curl`
- API wurde bereits lokal gestartet (z. B. per `PYTHONPATH=src uvicorn api.main:app --reload`)
- Kein externer Dienst erforderlich

## Manual Execution

1. Führe den Access-Check gegen den lokalen Health-Endpoint aus:

```bash
curl -sS -m 3 -i http://127.0.0.1:8000/health
```

2. Prüfe die Ausgabe auf:
   - Statuszeile enthält: `HTTP/1.1 200 OK` (oder äquivalent `HTTP/1.0 200 OK`)

Optional kann der Response-Body angezeigt werden (z. B. `{"status":"ok"}`), ist aber nicht bindend für die Bewertung.

## Success Signal

Der Smoke Check ist erfolgreich, wenn der HTTP-Status `200` ist.

## Failure Signal

Der Smoke Check ist fehlgeschlagen, wenn **eine** der folgenden Bedingungen auftritt:

- `curl` meldet Verbindungsfehler (z. B. `Connection refused`)
- `curl` läuft in Timeout (z. B. durch `-m 3`)
- HTTP-Status ist ungleich `200`

## Troubleshooting (deterministisch, lokal)

1. Prüfe, ob der API-Prozess läuft (Terminal mit `uvicorn` darf nicht beendet sein).
2. Prüfe den Port lokal:

```bash
ss -ltn | grep ':8000'
```

Erwartung: Ein LISTEN-Socket auf `127.0.0.1:8000` oder `0.0.0.0:8000`.

3. Wiederhole den Check mit Headern:

```bash
curl -sS -m 3 -i http://127.0.0.1:8000/health
```

Wenn weiterhin kein `HTTP 200` zurückkommt, ist Access nicht bestätigt.

## Determinism & Non-External Dependency

Dieser Smoke Check ist deterministisch und nutzt **ausschließlich lokale Ressourcen**:

- Endpoint: `http://127.0.0.1:8000/health`
- Keine Internet-Abhängigkeit
- Keine externen APIs oder Services
- Kein Trading-/Daten-Validierungsumfang
