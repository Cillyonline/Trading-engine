# Execution Modes – Klassifikation & Anwendbarkeitsregeln

Diese Seite beschreibt die **unterstützten Execution Modes** und liefert eine **deterministische Klassifikation** für Issues/Tasks. Zusätzlich wird innerhalb von **EXECUTION** ein Arbeitsmuster klassifiziert (Exploratory vs. Contract-facing), ohne neue Execution Modes einzuführen.

## Supported Execution Modes

### EXECUTION (Default)
**Zweck:** Umsetzung klar definierter Anforderungen/Tasks.

**Wann anwenden:**
- Standardmodus für Implementierungsarbeit.
- Der Task ist ausführbar und erfordert keine vorgelagerte Klärung oder Priorisierung.

**Wann nicht anwenden:**
- Wenn explizit PLANNING oder TRIAGE angefordert ist.

### PLANNING
**Zweck:** Strukturierung, Zerlegung, Aufwandsschätzung oder Planungsschritte vor der Umsetzung.

**Wann anwenden:**
- **Nur auf explizite Anforderung** (z. B. „bitte planen“, „Roadmap erstellen“).

**Wann nicht anwenden:**
- Wenn keine explizite Planungsanfrage vorliegt.

### TRIAGE
**Zweck:** Erstanalyse zur Einordnung von Problemen, insbesondere Bug-/Issue-Reproduktion und Priorisierung.

**Wann anwenden:**
- **Nur auf explizite Anforderung** (z. B. „bitte triagieren“, „Bug analysieren/reproduzieren“).

**Wann nicht anwenden:**
- Wenn keine explizite Triage-Anfrage vorliegt.

## Execution Pattern (innerhalb von EXECUTION)
**Hinweis:** Dies sind **keine zusätzlichen Execution Modes**, sondern eine Arbeitsklassifikation **innerhalb von EXECUTION**.

### Exploratory (Pattern)
**Zweck:** Erkenntnisse gewinnen, Hypothesen prüfen oder Optionen evaluieren, ohne verbindlichen Stabilitäts- oder Vertragsanspruch.

**Wann anwenden:**
- Der Task dient dem Sammeln von Informationen, Analysen oder Prototypen.
- Das Ergebnis ist **nicht** als stabiler „Contract“ gedacht.
- Änderungen/Outputs sind als vorläufig oder experimentell deklariert.

**Wann nicht anwenden:**
- Wenn ein stabiler, überprüfbarer Vertrag/Behavior dokumentiert oder festgeschrieben werden soll.
- Wenn Ergebnisse als verbindlich, reproduzierbar oder kompatibilitätskritisch kommuniziert werden.

### Contract-facing (Pattern)
**Zweck:** Stabilen, deterministischen und überprüfbaren Gebrauch/Output festhalten (z. B. Usage Contract, Snapshot-Verhalten, öffentlich dokumentierte API-Garantien).

**Wann anwenden:**
- Der Task definiert oder ändert **verbindliche** Erwartungen für Nutzung, Output oder Schnittstellen.
- Dokumentation oder Regeln sollen als **stabiler Vertrag** gelten.
- Änderungen müssen kompatibilitätsbewusst und reviewbar sein.

**Wann nicht anwenden:**
- Wenn das Ziel primär explorativ, vorläufig oder hypothesengetrieben ist.
- Wenn Ergebnisse nur als interne Notiz/Experiment gelten.

## Applicability Rules (Decision Tree)
**Reihenfolge strikt einhalten.**

### Stufe A – Execution Mode bestimmen
1. **Wenn** PLANNING ausdrücklich angefordert ist, **dann** → **PLANNING**.
2. **Sonst wenn** TRIAGE ausdrücklich angefordert ist, **dann** → **TRIAGE**.
3. **Sonst** → **EXECUTION** (Default).

### Stufe B – Execution Pattern (nur bei EXECUTION)
1. **Wenn** der Task explizit einen *Contract*, eine *Usage Contract*-Änderung, Snapshot-Verhalten, stabile API-Erwartungen oder kompatibilitätsrelevante Regeln betrifft, **dann** → **Contract-facing**.
2. **Sonst wenn** der Task als Exploration, Untersuchung, Hypothesenprüfung, Prototyp oder „vorläufig“ gekennzeichnet ist, **dann** → **Exploratory**.
3. **Sonst** → **Exploratory** (Default, solange kein stabiler Vertrag gefordert ist).

## Entry Criteria

### EXECUTION
- Keine explizite Anforderung für PLANNING oder TRIAGE.
- Task ist umsetzbar und ausreichend spezifiziert.

### PLANNING
- **Explizite Planungsanforderung** liegt vor.
- Ziel ist Strukturierung oder Aufwandsklärung vor Umsetzung.

### TRIAGE
- **Explizite Triage-/Bug-Analyse-Anforderung** liegt vor.
- Ziel ist Einordnung, Reproduktion oder Priorisierung.

### Exploratory (Pattern)
- Task-Ziel ist Erkenntnisgewinn, Vergleich oder Validierung.
- Output ist explizit **nicht** als stabiler Vertrag deklariert.
- Es gibt keine Anforderungen an rückwärtskompatible, garantierte Ergebnisse.

### Contract-facing (Pattern)
- Task-Ziel ist ein **verbindlicher** Vertrag/Standard für Nutzung, Output oder Schnittstelle.
- Der Vertrag soll reviewbar, deterministisch und als Referenz für andere gelten.
- Änderungen sind kompatibilitätskritisch oder wirken sich auf verbindliche Erwartungen aus.

## Forbidden Transitions
Die folgenden Transitions sind **verboten** und erfordern **Reclassification** (Issue/Scope/Review-Level anpassen, bevor Arbeit fortgesetzt wird):

- **EXECUTION → PLANNING ohne explizite Anforderung**: verboten. Erst explizite Planungsanforderung einholen und reklassifizieren.
- **EXECUTION → TRIAGE ohne explizite Anforderung**: verboten. Erst explizite Triage-Anforderung einholen und reklassifizieren.
- **Exploratory → Contract-facing (innerhalb EXECUTION) ohne Reclassification**: verboten. Erst Reclassification durchführen (Issue aktualisieren, Scope/Review anpassen).
- **Contract-facing → Exploratory zur Umgehung von Stabilitäts- oder Review-Anforderungen**: verboten. Nur nach formaler Reclassification zulässig.

## Ambiguous Cases – Resolutions
1. **„Wir dokumentieren das aktuelle Verhalten, aber nennen es vorläufig.“** → **EXECUTION + Exploratory** (Vorläufigkeit dominiert; kein stabiler Vertrag).
2. **„Wir schreiben eine klare, reproduzierbare API-Beschreibung.“** → **EXECUTION + Contract-facing** (stabile Erwartung für externe Nutzung).
3. **„Wir sammeln Outputs, um später einen Vertrag zu definieren.“** → **EXECUTION + Exploratory** (Vorarbeit, kein Vertrag).
4. **„Wir korrigieren eine bestehende Contract-Doku, weil sie falsch ist.“** → **EXECUTION + Contract-facing** (Änderung eines verbindlichen Vertrags).
5. **„Wir erstellen ein Beispiel zur Orientierung, ohne Garantie.“** → **EXECUTION + Exploratory** (Hinweischarakter, keine Verbindlichkeit).

## Manual Validation Checklist
**Beispiele mit Schritt-für-Schritt Klassifikation:**

### Beispiel 1 – „Bitte plane die nächsten drei Arbeitspakete für Issue #176“
1. Stufe A: PLANNING ausdrücklich angefordert? → Ja.
2. Entscheidung → **PLANNING**.

### Beispiel 2 – „Bitte triagiere Bug #512 und liefere Repro-Schritte“
1. Stufe A: TRIAGE ausdrücklich angefordert? → Ja.
2. Entscheidung → **TRIAGE**.

### Beispiel 3 – „Aktualisiere Usage Contract für API-Response-Felder“
1. Stufe A: PLANNING/TRIAGE ausdrücklich angefordert? → Nein.
2. Entscheidung → **EXECUTION**.
3. Stufe B: Contract/Usage Contract betroffen? → Ja.
4. Entscheidung → **Contract-facing**.

### Beispiel 4 – „Untersuche, ob Snapshot-Daten ausreichend sind für Strategie X“
1. Stufe A: PLANNING/TRIAGE ausdrücklich angefordert? → Nein.
2. Entscheidung → **EXECUTION**.
3. Stufe B: Contract/Usage Contract betroffen? → Nein.
4. Exploration/Untersuchung? → Ja → **Exploratory**.

### Beispiel 5 – „Dokumentiere verbindliche Regeln für Snapshot-Validierung“
1. Stufe A: PLANNING/TRIAGE ausdrücklich angefordert? → Nein.
2. Entscheidung → **EXECUTION**.
3. Stufe B: stabile Regeln/Vertrag? → Ja.
4. Entscheidung → **Contract-facing**.
