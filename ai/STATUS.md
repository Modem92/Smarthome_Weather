# Status
## Phase und Ziel
- Öffentliche Fassung seit 26.11.2026 auf GitHub. Funktional Stand 28.10.2026: Anzeige, Handy-Pairing, internationale Orte, Designer und Optimierung offline abgenommen (389 Tests); Pi im Livebetrieb eingerichtet.
- Ziel jetzt: offene Live- und Geräteprüfungen abschließen, dann Robustheit.

## Nächste Schritte
1. Offline-Testsuite auf diesem PC lauffähig machen und grün bekommen (Issue #8). Auf dem Windows-PC fehlt derzeit Python.
2. Freigabe-abhängige Abnahmen: Zusatzzeitreihen und Designübertragung (#1), Wiederstart live (#3), internationaler Live-Test (#4).
3. Geräteprüfungen: SSH nach Windows-Neustart (#2), Desktop-Symbol (#6), Autostart/Langzeitbetrieb (#5).
4. Aufräumen: Pi-Bibliotheken vs. requirements.txt (#9), Pi-Ziel im Updater (#10), Doku-Restverweise (#11), Doppelklick-Absturz auf anderem PC (#7).

## Offene Probleme / Fragen an mich
- Eingabetasten, Stromsparkonzept und E-Ink-Anbindung (Spec-Entwurf: ai/specs/eink.md) sind nicht entschieden.
- OpenWeather-Kontogrenze 1000/Tag nur laut Nutzerangabe, nie unabhängig geprüft.
- Sensoren (Hardware, Protokoll) und Langzeit-Datenspeicherung: Lösung nicht festgelegt.
- Ideen ohne Freigabe: automatischer Seitenwechsel (optional), Markierung auffälliger Messwerte, Datenanalyse, Cloud/ML.

## Zuletzt erledigt (max. 5 Zeilen)
- 27.11.2026: Workflow-Vorlage eingeführt, Planungsdoku nach CLAUDE.md und ai/ überführt, 11 Issues angelegt.
- 28.10.2026: Optimierung für Pi und OneDrive, Designer-Korrekturen.
