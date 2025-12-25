# Strategy Config Schema – MVP

## Scope & Grundsätze

Dieses Dokument beschreibt das **offizielle Strategy-Config-Schema** für den **Cilly Trading Engine – MVP**.

**Gültig für:**
- RSI2 Strategy
- Turtle Strategy

### Wichtige Regeln (verbindlich)

- Alle Strategy-Configs sind **optional**
- `None` oder `{}` → es werden **vollständige Defaults** verwendet
- Fehlende Keys → **Default pro Key**
- Ungültige Typen oder Werte → **deterministischer Fallback auf Default**
- Unbekannte Keys → **werden ignoriert**
- Das Verhalten ist **backward compatible**
- Strategy-Configs dürfen **niemals** einen Engine-Crash verursachen

---

## Allgemeines Config-Verhalten

- Strategy-Configs werden **vor der Strategy-Ausführung normalisiert**
- Jede Strategie arbeitet intern immer mit einer:
  - vollständigen
  - typsicheren
  - validierten Konfiguration
- Strategien enthalten **keine I/O-Logik** und **keine eigene Config-Validierung**

---

## Strategy: RSI2

### Beschreibung

RSI2 ist eine kurzfristige Mean-Reversion-Strategie basierend auf einem sehr kurzen RSI-Indikator, optional kombiniert mit einem Trendfilter.

### Konfigurations-Keys

| Key | Typ | Default | Beschreibung | Constraints |
|---|---|---:|---|---|
| rsi_period | int | 2 | RSI-Periode | >= 2 |
| oversold | float | 10.0 | Buy-Trigger | 0 ≤ oversold < overbought ≤ 100 |
| overbought | float | 70.0 | Exit-Trigger | 0 ≤ oversold < overbought ≤ 100 |
| trend_filter | bool | true | Trendfilter aktiv | – |
| trend_ma_period | int | 200 | MA-Periode | >= 1 |
| trend_filter_mode | str | price_above_ma | Trendfilter-Modus | intern definiert |
| min_bars | int | 250 | Mindestanzahl Bars | >= max(rsi, ma) |

### Minimal-Beispiel

```json
{ "oversold": 5, "overbought": 80 }
```

---

## Strategy: Turtle

### Beschreibung

Turtle ist eine klassische Breakout-Trendfolge-Strategie auf Basis von Donchian-Kanälen.

### Konfigurations-Keys

| Key | Typ | Default | Beschreibung | Constraints |
|---|---|---:|---|---|
| entry_lookback | int | 20 | Entry-Lookback | >= 2 |
| exit_lookback | int | 10 | Exit-Lookback | >= 2 |
| atr_period | int | 20 | ATR-Periode | >= 2 |
| stop_atr_mult | float | 2.0 | Stop-Distanz | > 0 |
| risk_per_trade | float | 0.01 | Risiko pro Trade | 0 < v ≤ 0.05 |
| max_units | int | 4 | Max Units | >= 1 |
| unit_add_atr | float | 0.5 | Unit-Abstand | > 0 |
| allow_short | bool | false | Shorts erlaubt | – |
| min_bars | int | 60 | Mindestanzahl Bars | >= max(entry, exit, atr) |

### Minimal-Beispiel

```json
{ "entry_lookback": 55, "exit_lookback": 20, "allow_short": true }
```

---

## Kompatibilität

- Alle Keys optional
- Fehlende / ungültige Werte werden ersetzt
- Unbekannte Keys werden ignoriert
- Vollständig backward compatible
