<!-- TEIL A: Arbeitsweise. In allen Repos identisch. Änderungen nur über die Vorlage. -->
# Arbeitsweise

## Sprache
- Antworte auf Deutsch. Code, Kommentare, Commit-Messages und Branch-Namen auf Englisch, außer das Repo macht es anders.

## Grundprinzip
- Arbeite so selbstständig wie möglich: Doku pflegen, organisieren, delegieren, prüfen, committen. Frag mich nur bei Entscheidungen, die das Ergebnis wesentlich ändern oder schwer rückgängig zu machen sind.
- Frag nichts, was in dieser Datei oder in ai/ steht.
- IMPORTANT: Jede Entscheidung, Korrektur und nicht offensichtliche Änderung bekommt ein kurzes Warum (siehe „Projektgedächtnis“). Künftige Sessions wissen nur, was aufgeschrieben ist.

## Sessionstart
- Lautet mein Auftrag „weiter“ oder fehlt ein konkreter Auftrag: obersten offenen Punkt aus ai/STATUS.md nehmen (inkl. verlinkter Spec bzw. Issue), in einem Satz nennen und loslegen. Ist dort nichts offen: offene GitHub-Issues abfragen und das wichtigste vorschlagen.
- Hat mein Auftrag nichts mit offenen Punkten zu tun: offenen Punkt in einem Satz erwähnen, dann den Auftrag erledigen.
- Nennt mein Auftrag ein Issue („Setze Issue #12 um“): nur daran arbeiten. Es laufen evtl. andere Sessions parallel, also in ai/STATUS.md nur diesen Punkt aktualisieren.

## Vorgehen
- Unklarer Ansatz oder mehrere Dateien betroffen: erst erkunden, dann kurzen Plan mit Done-Kriterium, dann umsetzen. Lässt sich der Diff in einem Satz beschreiben: direkt umsetzen.
- Größeres Feature: erst mich interviewen (AskUserQuestion, nur die schwierigen Fragen), dann ai/specs/<feature>.md schreiben (Ziel, betroffene Dateien, außerhalb des Scopes, Teilschritte mit Done-Kriterium, End-to-End-Prüfung), Teilschritte als GitHub-Issues anlegen (Abhängigkeiten als „blockiert durch #…“ im Issue), in ai/STATUS.md eintragen, per PR nach main bringen. Dann sagen, welche Issues parallel laufen können, und fragen, ob ich sofort umsetzen lassen will.
- Große Aufgaben in kleine Schritte zerlegen. Ein Schritt = ein Commit.
- Bestehenden Mustern folgen, siehe „Referenzbeispiele“ unten.
- Fehlt eine Information, die das Ergebnis wesentlich ändert: fragen statt raten.
- Nach zwei gescheiterten Versuchen am selben Problem: anhalten, Erkenntnisse in ai/STATUS.md festhalten, neuen Ansatz vorschlagen.

## Delegieren und Modelle
- Du koordinierst, Subagents erledigen abgeschlossene Arbeit in frischem Kontext:
  - Breite Suche über viele Dateien → `researcher`
  - Tests/Builds mit langer Ausgabe → `test-runner`
  - Prüfung vor dem Abschluss → `/code-review`, sonst `reviewer`
  - Feature mit mehreren Teilschritten: jeden Teilschritt an einen eigenen Subagent geben (Spec-Pfad, Issue-Nr. und Done-Kriterium mitgeben), Ergebnis prüfen, committen, ai/STATUS.md aktualisieren, dann der nächste.
  - Kleine, gezielte Änderungen und Arbeit mit viel Rückfragen: selbst erledigen.
- Modell pro Subagent selbst wählen: haiku für Mechanisches (Tests ausführen, Umbenennen), sonnet für normale Umsetzung und Suche, opus für Architektur, knifflige Fehler und Reviews. Kein fable.
- Das Modell der Hauptsession nicht wechseln. Lohnt sich für die nächste Session ein anderes, sag es im 80/20.

## Qualität
- Nichts ist fertig ohne Prüfung: Tests, Build und Linter ausführen und Befehl + Ergebnis zeigen.
- Neue Logik bekommt Tests. Ursachen beheben, Fehler nicht unterdrücken.
- IMPORTANT: Tests nie abschwächen, überspringen oder löschen, um sie grün zu bekommen.
- Vor jedem Pull Request, der mehr als eine Kleinigkeit ändert: `/code-review` auf den Diff ausführen (klappt das nicht: Subagent `reviewer`). Funde zu Korrektheit und Anforderungen beheben, Stilfragen ignorieren.

## Kontext und Kosten
- Gezielt lesen: erst suchen (Grep/Glob), dann nur die relevanten Dateien oder Abschnitte.
- GitHub lokal über die `gh` CLI. In Cloud-Sessions die eingebauten GitHub-Werkzeuge oder `gh api` (REST) nutzen, weil `gh pr` und `gh issue` dort blockiert sind. Was über die Session hinausgeht, wird ein Issue.
- Jedes neue Issue sofort in ai/STATUS.md unter „Nächste Schritte“ oder „Offene Probleme“ mit Nummer eintragen. Neue Sessions sehen nur, was dort steht. Geschlossene Issues dort entfernen.
- Knapp antworten: keinen Code wiederholen, den ich schon gesehen habe, keine Zusammenfassung jedes Zwischenschritts.
- Beim Kompaktieren erhalten: aktuelle Aufgabe mit Done-Kriterium, geänderte Dateien, Testbefehle, offene Probleme.
- Neue Session und `/compact` kann nur ich auslösen. Ist eine Aufgabe abgeschlossen: ai/STATUS.md aktualisieren, committen und im 80/20 eine neue Session empfehlen. Ist der Kontext mitten in einer Aufgabe voll mit Erledigtem: `/compact` mit passendem Fokus empfehlen.

## Projektgedächtnis (selbstständig pflegen, ohne zu fragen)
- CLAUDE.md enthält nur Stabiles (Zweck, Stack, Befehle, Konventionen, Regeln, Leitentscheidungen) und bleibt unter 150 Zeilen.
- ai/STATUS.md enthält den veränderlichen Stand. Direkt nach jedem abgeschlossenen Schritt, jeder Entscheidung und jedem neuen Problem aktualisieren. Erledigtes löschen oder auf eine Zeile kürzen. Max. ca. 30 Zeilen.
- ai/DECISIONS.md: jede Entscheidung als Eintrag mit Datum, Entscheidung, Warum und verworfenen Alternativen, neueste oben. Ersetzte Entscheidungen als „ersetzt durch …“ markieren statt löschen. Vor Änderungen an Architektur oder früheren Entscheidungen dort suchen.
- Neue dauerhafte Anforderung von mir (z. B. „muss ressourcenschonend sein“, Zielgerät, Datenschutz): sofort unter „Anforderungen“ eintragen, mit Warum, falls ich eins nenne (sonst nachfragen). Ab dann bei jeder Arbeit berücksichtigen und im 80/20 erwähnen. Widerspricht sie bestehendem Code oder früheren Entscheidungen: Konflikt nennen und als Issue anlegen.
- Korrektur von mir, die wieder passieren kann: als einzeilige Regel mit Warum in Klammern unter „Regeln“ eintragen und im 80/20 erwähnen.
- Commits: Betreff = was, Text = warum (1–3 Zeilen).
- Nicht offensichtlicher Code: kurzer Kommentar zum Warum, nicht zum Was.
- Überholtes und Widersprüchliches in CLAUDE.md und ai/STATUS.md entfernen.
- Fehlen Dateien in ai/: nach dieser Vorlage anlegen.

## Werkzeuge erweitern
- Wiederholt sich ein mehrstufiger Ablauf: Skill vorschlagen. Muss etwas immer passieren, oder wird eine Regel trotzdem verletzt: Hook vorschlagen. Jeweils mit Warum; anlegen nach meinem OK (.claude/ ist geschützt).

## Git
- Vor jedem neuen Branch main aktualisieren (git pull), denn parallele Sessions mergen laufend.
- Eigener Branch (feat/…, fix/…). Selbstständig in kleinen Schritten committen, CLAUDE.md und ai/ immer mit.
- Fertige Arbeit: Pull Request mit „Closes #…“ in der Beschreibung, damit das Issue automatisch schließt. Auf grüne CI warten (falls vorhanden), Fehler beheben, dann nach main mergen.
- Merge-Konflikte in ai/STATUS.md und ai/DECISIONS.md selbst auflösen: beide Stände zusammenführen, nichts verwerfen.
- Nie direkt auf main pushen, nie force-push.

## Abschluss
Nur am Ende einer abgeschlossenen Aufgabe (nicht bei Zwischenantworten), unter `---`:
## 80/20
🟢/🟡/🔴 Phase und Stand in einem Satz (🟢 nichts zu tun, 🟡 du musst etwas tun, 🔴 blockiert).
👉 Was du tun musst: nummerierte Schritte, Aktionen fett. Weglassen, wenn nichts zu tun ist.
💡 Ratschlag: nur wenn er wirklich hilft.

<!-- TEIL B: Projekt. Nur Projektspezifisches. Nichts, was Claude aus dem Code lesen kann. -->
# Projekt: Wetterstation (`wetterstation`)
- Zweck: Passive Wetteranzeige (Uhr, Wetter, Vorhersage, Regenkarte) für Raspberry Pi und Windows aus einer gemeinsamen Codebasis; Einstellungen und Widget-Anordnung per Handy im Heimnetz, Gestaltung im Qt-Designer am PC.
- Stack: Python ≥3.11 mit Tkinter, Pillow, cryptography, tzdata; PySide6 nur im PC-Designer. Tests mit unittest, Browserprüfungen mit Node/Playwright. Kein Linter, keine CI.
- Zielgerät: Raspberry Pi 3 Model A Plus, Debian 12 Bookworm, Python 3.11.2 (aarch64), Display 1024×600. Öffentliche Fassung mit Beispielort Potsdam.

## Befehle
- Starten: `python -m wetterstation` (live, nur mit Freigabe) · Demo: `python -m wetterstation --widget-demo` · Designer: `python -m wetterstation.designer.app --workspace <temp-ordner>`
- Einzelnen Test: `python tools/offline_tests.py test_widgets.WidgetModelTests`   Alle Tests: `python tools/offline_tests.py --report build/checks/offline-tests.txt`
- Visuell: `python tests/display_visual_check.py`, `python tests/designer_scale_check.py` (Ausgaben unter `build/checks/`)
- Browser: `python tests/widget_demo.py` starten, dann `node tests/widget_browser_check.cjs` bzw. `pairing_`/`designer_phone_`/`international_browser_check.cjs`
- Designer-Abnahme mit Pi-Paketbau: `python tools/designer_acceptance.py` · Workspace-Wartung (Prüfmodus): `python tools/workspace_maintenance.py`
- Pi-Update: `windows/Pi aktualisieren.cmd` (nur mit Freigabe; Ablauf in docs/UPDATE.md)

## Struktur (nur Einstiegspunkte)
- `wetterstation/ui/`: Tk-Anzeige (`app.py`), `dashboard.py` zeichnet, `widgets.py` Widgettypen (`CATALOG`) und Standardlayout
- `wetterstation/weather/`: Geocodierung, Abrufe, Ortszeit · `maps/`: DE-Karte (BKG/DWD), international (OSM/RainViewer), Regenzug
- `wetterstation/storage/`: Einstellungen, Schlüssel, `openweather_budget.py` · `paths.py`: einziger Ort für Projekt-/Privatpfade
- `wetterstation/mobile/`: HTTPS-Server, Pairing, Layout-API; Browsercode in `web/` · `designer/`: Qt-Designer (`app.py`, `model.py`, `render.py`, `runtime.py`)
- `tools/pi/update.py`: Pi-Paket und -Installation (nur Standardbibliothek) · `windows/`, `raspberry_pi/`: Starter. Rootdateien (`app.py`, `pi_update.py`, `start_*`) sind nur Kompatibilitätseinstiege.
- Menschen-Doku: README.md, docs/UPDATE.md, docs/DESIGNER.md, docs/STRUCTURE.md, docs/OPTIMIZATION.md

## Referenzbeispiele
- Test wie `tests/test_widgets.py` (unittest, temporärer Speicher, Dummy-Schlüssel), Widgettyp wie die Einträge in `CATALOG` (`wetterstation/ui/widgets.py`), Pi-relevante Datei wie die Einträge in `FILES` (`tools/pi/update.py`)

## Konventionen (nur Abweichungen vom Standard)
- Doku und UI-Texte auf Deutsch; Code, Kommentare und Commit-Messages Englisch.
- Jede Datei, die auf den Pi muss, steht in `FILES` in `tools/pi/update.py`; entfernte Pi-Dateien kommen in `RETIRED_FILES` (sonst bricht der Paketbau bzw. bleiben Altdateien liegen).
- Private Daten (Einstellungen, Schlüssel, Zertifikate, Caches, Zähler, Layouts) nur unter `private/`, Pfade über `paths.py`.

## Regeln (aus Korrekturen, mit Warum)
- Eine notierte Idee ist keine Freigabe: neue Features, Liveabrufe, Pi-Übertragung, Sensoren, Konten, Cloud-Dienste und Veröffentlichung nur nach konkreter Freigabe (Nutzer gibt Umfang jeweils ausdrücklich frei).
- Entwicklung und Tests nur mit gekennzeichneten Beispieldaten, Dummy-Schlüsseln und temporärem Speicher (echte Einstellungen und Budgetzähler dürfen nie verändert werden).
- API-Schlüssel nie in Code, Doku, Logs, Screenshots oder HTTP-Antworten (öffentliches Repo; Schlüssel liegt unverschlüsselt in `private/`).
- PC-Live und Pi-Live nie gleichzeitig mit derselben Budgetidentität (getrennte Kopien haben keine gemeinsame Sperre).
- `.pi-update-in-progress.json` nie löschen; Wiederherstellung nach docs/UPDATE.md (Marker schützt vor halbem Update).
- Nichts automatisch installieren, keine Firewall-/Router-/Zertifikatsvertrauensänderungen (Pi-Bibliotheken kommen aus Debian, Nutzer will volle Kontrolle).
- Tk-Objekte und -Bilder nur im Tk-Hauptthread anlegen/freigeben (sonst Abstürze und Ruckler am Pi).
- Bestehende Layouts und Gestaltungsdaten bei Änderungen an Display oder Handy-Editor erhalten; bei Wetter-, Karten- oder Budgetänderungen Ortswechsel, Hintergrundarbeit, Cache-Zuordnung und Tageswechsel isoliert testen.
- Abschlussbericht trennt: was der Code kann, was geprüft wurde, welche Live-/Geräteprüfung aussteht (Offline-Abnahme ersetzt keine Geräteprüfung).

## Leitentscheidungen (max. 10, Details in ai/DECISIONS.md)
- Ein gemeinsamer Kern für PC und Pi; `paths.py` hält den bisherigen `private/`-Pfad stabil (Einstellungen und Budgetidentität dürfen nicht wandern).
- Passive Anzeige, Bedienung nur per Handy mit Einmalcode-Pairing über HTTPS im Heimnetz (keine lokalen Dialoge am Display).
- Ein Wetterort (Ort + ISO-Land) steuert Wetter, Ortszeit und Karte (gleichnamige Orte dürfen keine Daten teilen).
- Budgetschutz: Reservierung vor HTTP, max. 1000/Tag (Berlin und UTC), 3 Anfragen alle 5 Minuten haben Vorrang; Zusatzreihen nur per Gerätefreigabe.
- Fehlende Radarabdeckung nie als „trocken“ darstellen; Quellenangaben auf internationalen Karten immer sichtbar.
- Designformat 4, ältere Formate lesbar; Qt nur am PC, Tk auf dem Pi.
- Pi-Updates nur manuell, mit Sicherung, Offline-Prüfung und Wiederstart nur des vorher laufenden Modus.
- Öffentliches Repo ohne Gerätedaten, private Daten und alte Git-Historie.

## Aktueller Stand
@ai/STATUS.md
