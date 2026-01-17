# Strategy Config Schema – MVP

## Scope & Grundsätze

Dieses Dokument beschreibt das **offizielle Strategy-Config-Schema** für den **Cilly Trading Engine – MVP**.

**Gültig für:**
- RSI2 Strategy
- Turtle Strategy

### Wichtige Regeln (verbindlich)

- Strategy-Configs sind **optional**.
- `None` oder `{}` → leere Config (`{}`).
- Fehlende Keys → bleiben **ungesetzt** (keine Defaults pro Key aus der Config-Normalisierung).
- Unbekannte Keys → werden **ignoriert** und als Warning geloggt.
- Ungültige Typen oder Werte bei bekannten Keys → **Fehler**; die Strategie wird im Engine-Lauf **übersprungen**.
- Konflikt zwischen Alias und Canonical-Key → **Fehler**; die Strategie wird im Engine-Lauf **übersprungen**.
- Ungültiger Config-Typ (kein Mapping) → Warning, es wird eine **leere Config** verwendet.

---

## Allgemeines Config-Verhalten

- Strategy-Configs werden **vor der Strategy-Ausführung normalisiert und validiert**.
- Aliases werden auf Canonical-Keys aufgelöst (siehe pro Strategie).
- Bekannte Parameter werden typisiert und gegen Min/Max geprüft.
- Die Normalisierung liefert **nur** die bekannten, validen Keys.

### Typ-Normalisierung (für implementierte Parameter)

- `int`: akzeptiert `int`, `float` mit ganzzahligem Wert (z. B. `2.0`) und numerische Strings (z. B. `"2"`).
- `float`: akzeptiert `int`, `float` und numerische Strings (z. B. `"2.5"`).

---

## Strategy: RSI2

### Beschreibung

RSI2 ist eine kurzfristige Mean-Reversion-Strategie basierend auf einem sehr kurzen RSI-Indikator.

### Konfigurations-Keys

| Key | Typ | Alias | Beschreibung | Constraints |
|---|---|---|---|---|
| `rsi_period` | int | – | RSI-Periode | `>= 1` |
| `oversold_threshold` | float | `oversold` | Oversold-Schwelle | `0.0 .. 100.0` |
| `min_score` | float | – | Mindest-Score | `0.0 .. 100.0` |

### Minimal-Beispiel

```json
{ "oversold": 5, "min_score": 40 }
```

---

## Strategy: Turtle

### Beschreibung

Turtle ist eine klassische Breakout-Trendfolge-Strategie.

### Konfigurations-Keys

| Key | Typ | Alias | Beschreibung | Constraints |
|---|---|---|---|---|
| `breakout_lookback` | int | `entry_lookback` | Breakout-Lookback | `>= 1` |
| `proximity_threshold_pct` | float | `proximity_threshold` | Nähe zum Breakout-Level (Prozent) | `0.0 .. 1.0` |
| `min_score` | float | – | Mindest-Score | `0.0 .. 100.0` |

### Minimal-Beispiel

```json
{ "entry_lookback": 55, "proximity_threshold": 0.2 }
```

---

## Kompatibilität

- Nur die oben gelisteten Keys sind implementiert.
- Unbekannte Keys werden ignoriert; bekannte Keys werden strikt validiert.
- Es gibt keine stillen Defaults oder Fallbacks in der Config-Normalisierung.
