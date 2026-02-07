# Engine Runtime Ownership & Lifetime Model

## Zweck
Dieses Dokument definiert eindeutig, wo die Engine-Runtime lebt,
wem sie gehört und wie ihr Lebenszyklus gesteuert wird.
Es beschreibt bewusst keine Implementierungsdetails.

## Runtime-Instanzmodell
- Es existiert genau EINE Engine-Runtime-Instanz pro Prozess.
- Die Runtime ist ein langlebiges, zustandsbehaftetes Objekt.
- Es gibt keine kurzlebigen oder mehrfachen Runtime-Instanzen.

## Ownership
- Die Runtime gehört der Engine-Schicht.
- Die Engine ist allein verantwortlich für:
  - Erzeugung der Runtime
  - Halten der Runtime
  - Geordnetes Beenden der Runtime
- Externe Komponenten (z. B. API-Schicht) besitzen die Runtime NICHT.

## Kontrolle vs. Sichtbarkeit
- Die API-Schicht darf die Runtime:
  - nutzen
  - ansprechen
  - Status abfragen
- Die API-Schicht darf die Runtime NICHT:
  - erzeugen
  - ersetzen
  - neu starten
  - direkt beenden

## Lifetime-Regeln
- Die Runtime wird beim Start der Engine initialisiert.
- Die Runtime existiert für die gesamte Lebensdauer der Engine.
- Die Runtime wird exakt einmal sauber heruntergefahren:
  - ausgelöst durch die Engine
  - als Teil des Engine-Shutdowns

## Verbotene Annahmen
- Keine Lazy-Initialisierung durch API-Zugriffe
- Kein implizites Neustarten der Runtime
- Keine Ownership-Übergabe an andere Schichten

## Scope-Hinweis
Dieses Dokument trifft keine Aussagen zu:
- technischer Umsetzung
- Threading oder Concurrency
- Dependency Injection
- konkreten Klassen oder Funktionen
