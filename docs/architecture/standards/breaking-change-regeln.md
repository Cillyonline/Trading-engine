# Breaking-Change-Regeln für versionierte Schemas

Diese Regeln definieren, was als Breaking Change für versionierte Schemas gilt und wann ein Major-Version-Bump erforderlich ist.

## Was ist ein Breaking Change?

Ein Breaking Change liegt vor, wenn eine der folgenden Änderungen an einem versionierten Schema vorgenommen wird:

- **Feld entfernt**: Ein bestehendes Feld ist im neuen Schema nicht mehr vorhanden.
- **Typ geändert**: Der Datentyp eines bestehenden Feldes wird geändert.
- **Requiredness geändert**: Ein Feld wechselt zwischen `required` und `optional`.

## Wann ist ein Major-Version-Bump erforderlich?

Wenn ein Breaking Change erkannt wird, muss die **Major-Version** des Schemas erhöht werden. Ein Breaking Change ohne Major-Version-Bump ist nicht zulässig.

## Testbasierte Durchsetzung

Die Tests simulieren Breaking Changes, indem sie ein Feld entfernen, den Typ ändern oder die Requiredness ändern, ohne die Major-Version zu erhöhen. Der Fehlerfall wird per erwarteter Assertion geprüft und muss eine Fehlermeldung liefern, die:

- die verletzte Regel (z. B. „Field removed“),
- den betroffenen Feldpfad (z. B. `$.signal.score`),
- und den Hinweis „Major version bump required“

enthält.
