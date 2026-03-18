# Cilly Trading Engine – MVP v1  
Version: 1.0  
Status: Abgesegnet  
Ziel: End-to-End-Prototyp (Engine → SQLite → API → Trading Desk)

---

# 1. Ziel des MVP

Der MVP v1 implementiert eine **stabile, deterministische und modular aufgebaute Trading-Engine**, die:

1. Kursdaten aus externen Quellen lädt (Aktien & Krypto).  
2. Basisindikatoren berechnet (RSI, MACD).  
3. Zwei definierte Strategien sauber ausführt (RSI2, Turtle).  
4. Signale klar als **Setup** oder **Entry-Bestätigung** kennzeichnet.  
5. Ergebnisse dauerhaft in einer **SQLite-Datenbank** speichert.  
6. Über eine Web-API abrufbar ist.  
7. Auf der Cillyonline-Website mit einem minimalen Frontend nutzbar ist.

Der MVP bildet das **Fundament für Backtesting, Alerts, Risiko, Sentiment und spätere KI-Agenten**.

---

# 2. Zielgruppe

Primär:  
- Der Projektinhaber (Cilly / Serdar) für interne Nutzung und Validierung der Engine  
  - Screening  
  - Strategietests  
  - Papertrading  

Sekundär (nicht Teil des MVP):  
- Trading-Einsteiger  
- Website-Nutzer  
- spätere Premium-Kunden

---

# 3. Systemübersicht (Architektur)

Der MVP besteht aus fünf klar getrennten Komponenten:

1. **Engine (Backend-Tradinglogik)**  
2. **SQLite-Datenbank (Persistenz)**  
3. **Repository-Schicht (Abstraktion zwischen Engine & DB)**  
4. **Web-API (FastAPI/Flask)**  
5. **Trading Desk (Frontend auf Cillyonline)**  

**Keine Agenten im MVP.**  
Alle Logik ist rein deterministisch.

---

# 4. Engine

## 4.1 Daten-Layer

Zentrale Funktion:

```python
load_ohlcv(
    symbol: str,
    timeframe: str,
    lookback_days: int
) -> pd.DataFrame
```

Anforderungen:
- Datenquellen:
  - Yahoo Finance (Aktien)
  - Binance/CCXT (Krypto)
- Rückgabeformat: OHLCV + Datumsindex
- Fehler:
  - werden geloggt, brechen aber die Analyse nicht ab
- Unit-Tests sind verpflichtend

---

## 4.2 Indikatoren (MVP)

- **RSI(14)**
- **MACD(12/26/9)**

Regeln:
- jedes Modul in `indicators/*.py`
- keine Seiteneffekte  
- Unit-Test pro Indikator

---

## 4.3 Strategien

### Strategie 1: RSI2 (Rebound)
- Mean-Reversion
- erkennt überverkaufte Situationen
- erzeugt meist **Setup-Signale**
- Entry erst nach Bestätigung (z. B. Close über Trigger)

### Strategie 2: Turtle (Breakout)
- Trendfolge
- Setup: Annäherung an Range-Hoch
- Entry: Breakout über Trigger-Level

### Strategien müssen:

- ein gemeinsames Interface nutzen:

```python
class BaseStrategy(Protocol):
    def generate_signals(
        self,
        df: pd.DataFrame,
        config: StrategyConfig
    ) -> list[Signal]:
        ...
```

- Setup + Entry sauber trennen  
- eine klare Bestätigungsregel liefern (`confirmation_rule`)  
- optional eine Entry-Zone liefern  
- Score (0–100) vergeben  

---

## 4.4 Signalmodell

```python
Signal = {
  "symbol": str,
  "strategy": str,
  "direction": "long",
  "score": float,
  "timestamp": datetime,
  "stage": "setup" | "entry_confirmed",
  "entry_zone": {"from": float, "to": float} | None,
  "confirmation_rule": str,
  "timeframe": str,
  "market_type": str,
  "data_source": str
}
```

---

## 4.5 Engine-Funktion

```python
run_watchlist_analysis(
    symbols: list[str],
    strategies: list[BaseStrategy],
    config: EngineConfig,
) -> list[Signal]
```

Anforderungen:

- lädt Daten  
- berechnet Indikatoren  
- führt Strategien aus  
- speichert Signale in SQLite  
- gibt Signale für API/Frontend zurück  
- Unit-Tests vorhanden  

---

# 5. Persistenz (SQLite)

File: **`cilly_trading.db`**

SQLite ist im MVP das zentrale Speicherformat.  
Keine CSV als Kernspeicher.

## 5.1 Tabelle `signals`

Felder:

- `id` (PK)
- `symbol`
- `strategy`
- `direction`
- `score`
- `timestamp`
- `stage`
- `entry_zone_from`
- `entry_zone_to`
- `confirmation_rule`
- `timeframe`
- `market_type`
- `data_source`

---

## 5.2 Tabelle `trades`

Felder:

- `id` (PK)
- `symbol`
- `strategy`
- `stage`
- `entry_price`
- `entry_date`
- `exit_price`
- `exit_date`
- `reason_entry`
- `reason_exit`
- `notes`
- `timeframe`
- `market_type`
- `data_source`

---

## 5.3 Repositories

```python
class SignalRepository(Protocol):
    def save_signals(self, signals: list[Signal]) -> None: ...
    def list_signals(self, filter: SignalFilter | None = None) -> list[Signal]: ...

class TradeRepository(Protocol):
    def save_trade(self, trade: Trade) -> None: ...
    def list_trades(self, filter: TradeFilter | None = None) -> list[Trade]: ...
```

Implementierung im MVP:

- `SqliteSignalRepository`
- `SqliteTradeRepository`

---

# 6. Screener (MVP)

Ein Screener:

## „US Momentum Screener“

- erzeugt eine dynamische Watchlist  
- gibt nur **Kandidaten** zurück  
- kein Entry, nur Vorauswahl  
- Grundlage für die Engine-Strategien  

---

# 7. Web-API (MVP)

FastAPI oder Flask.

## `GET /health`
Antwort:
```json
{ "status": "ok" }
```

## `POST /screener/basic`
Output:
- dynamische Watchlist

## `POST /strategy/analyze`
Output:
- Score  
- Setup/Entry  
- Bestätigungsregel  
- Entry-Zone  

---

# 8. Trading Desk (Cillyonline)

Minimaler Funktionsumfang:

1. Button: „US Momentum Screener starten“  
2. Einzelanalyse: Symbol + Strategie  
3. Ausgabe der Signale  

Umsetzung via:

- Elementor HTML Widget  
- fetch() API-Requests  

---

# 9. Backtesting (Version 2)

Nicht Teil des MVP.

Phase 2 umfasst:

- `run_backtest()`  
- Bar-by-Bar-Simulation  
- Nutzung der Engine-Strategien  
- Speicherung in SQLite  
- Erzeugung von:
  - Trefferquote  
  - Drawdown  
  - Equity-Kurve  
  - PnL  

---

# 10. Nicht-Ziele des MVP

- keine Agenten  
- kein Backtesting  
- kein Live-Trading  
- keine Alerts  
- kein Risikomodul  
- keine Portfolio-Simulation  
- keine Chart-Visualisierung  
- keine Benutzeraccounts  

---

# 11. Erfolgskriterien

Erfolgreich ist der MVP, wenn:

1. Engine erzeugt reproduzierbare Signale.  
2. SQLite speichert Daten korrekt.  
3. API antwortet stabil & korrekt.  
4. Trading Desk zeigt Ergebnisse sauber an.  
5. End-to-End-Kette funktioniert.  

---

# 12. Vorbereitung für Version 2

Der MVP ermöglicht:

- Backtesting  
- Risiko & Portfolio  
- Alerts  
- PostgreSQL-Migration  
- KI-Agenten (Supervisor, DailyRunner, ReportAgent)  

---

# 13. Zusammenfassung

MVP v1 liefert eine **professionell strukturierte Trading-Engine** mit:

- deterministischer Logik  
- modularer Architektur  
- SQLite-Persistenz  
- API-Anbindung  
- Website-Frontend  

Es ist das stabile Fundament für alle zukünftigen Trading-Features.
