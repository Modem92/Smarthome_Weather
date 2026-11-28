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
- Fertige Arbeit: Pull Request mit „Closes #…“ in der Beschreibung, damit das Issue automatisch schließt. Auf grüne CI warten, Fehler beheben, dann selbst nach main mergen (`gh pr merge --squash --delete-branch`, in der Cloud per GitHub-Werkzeug bzw. `gh api`). Dafür hast du die Freigabe.
- Gibt es noch keine CI: einen GitHub-Actions-Workflow anlegen, der bei jedem PR Tests, Build und Linter ausführt, und das in DECISIONS.md begründen.
- Merge-Konflikte in ai/STATUS.md und ai/DECISIONS.md selbst auflösen: beide Stände zusammenführen, nichts verwerfen.
- Nie direkt auf main pushen, nie force-push.

## Abschluss
Nur am Ende einer abgeschlossenen Aufgabe (nicht bei Zwischenantworten), unter `---`:
## 80/20
🟢/🟡/🔴 Phase und Stand in einem Satz (🟢 nichts zu tun, 🟡 du musst etwas tun, 🔴 blockiert).
👉 Was du tun musst: nummerierte Schritte, Aktionen fett. Weglassen, wenn nichts zu tun ist.
💡 Ratschlag: nur wenn er wirklich hilft.

<!-- TEIL B: Projekt. Nur Projektspezifisches. Nichts, was Claude aus dem Code lesen kann. -->
# Projekt: Weather station (`wetterstation`)
<!-- Section headings stay German because part A refers to them by name; content is English. -->
- Purpose: passive weather display (clock, weather, forecast, rain map) for Raspberry Pi and Windows from one shared codebase; settings and widget arrangement via phone on the home network, visual design in the Qt designer on the PC.
- Stack: Python ≥3.11 with Tkinter, Pillow, cryptography, tzdata; PySide6 only in the PC designer. Tests with unittest, browser checks with Node/Playwright. No linter, no CI.
- Target device: Raspberry Pi 3 Model A Plus, Debian 12 Bookworm, Python 3.11.2 (aarch64), display 1024×600. The public version uses Potsdam as the sample location.

## Befehle
- Run: `python -m wetterstation` (live, only with approval) · Demo: `python -m wetterstation --widget-demo` · Designer: `python -m wetterstation.designer.app --workspace <temp-dir>`
- Single test: `python tools/offline_tests.py test_widgets.WidgetModelTests`   All tests: `python tools/offline_tests.py --report build/checks/offline-tests.txt`
- Visual: `python tests/display_visual_check.py`, `python tests/designer_scale_check.py` (output under `build/checks/`)
- Browser: start `python tests/widget_demo.py`, then `node tests/widget_browser_check.cjs` or `pairing_`/`designer_phone_`/`international_browser_check.cjs`
- Designer acceptance incl. Pi package build: `python tools/designer_acceptance.py` · Workspace maintenance (check mode): `python tools/workspace_maintenance.py`
- Leak guard: once per clone `git config core.hooksPath tools/git-hooks` (pre-commit runs `tools/check_private_leaks.py`); audit with `--tracked` / `--history`
- Pi update: `windows/Update Pi.cmd` (only with approval; procedure in docs/UPDATE.md)

## Struktur (nur Einstiegspunkte)
- `wetterstation/ui/`: Tk display (`app.py`), `dashboard.py` draws, `widgets.py` widget types (`CATALOG`) and default layout
- `wetterstation/weather/`: geocoding, requests, local time · `maps/`: German map (BKG/DWD), international (OSM/RainViewer), rain movement
- `wetterstation/storage/`: settings, keys, `openweather_budget.py` · `paths.py`: the only place for project/private paths
- `wetterstation/mobile/`: HTTPS server, pairing, layout API; browser code in `web/` · `designer/`: Qt designer (`app.py`, `model.py`, `render.py`, `runtime.py`)
- `tools/pi/update.py`: Pi package and installation (standard library only) · `windows/`, `raspberry_pi/`: starters. Root files (`app.py`, `pi_update.py`, `start_*`) are compatibility entry points only.
- Human docs: README.md, docs/UPDATE.md, docs/DESIGNER.md, docs/STRUCTURE.md, docs/OPTIMIZATION.md

## Referenzbeispiele
- Test like `tests/test_widgets.py` (unittest, temporary storage, dummy key), widget type like the entries in `CATALOG` (`wetterstation/ui/widgets.py`), Pi-relevant file like the entries in `FILES` (`tools/pi/update.py`)

## Anforderungen (gelten für jede Änderung, mit Warum)
- The user keeps full control of the device: nothing is installed automatically, no firewall/router/certificate-trust changes (Pi libraries come from Debian).
- Existing layouts and design data survive every change to display or phone editor.
- E-Ink panel (Waveshare 7.3inch e-Paper HAT (E)): at least 3 minutes between two refreshes, at least one refresh every 24 h, full refresh only, sleep/power-off after every refresh (otherwise permanent panel damage; user's requirement of 28 Nov 2026).
- UI texts (display, phone, designer, messages) stay German; docs, ai/, issues, code, comments and commits are English (user's language decision of 27 Nov 2026).

## Konventionen (nur Abweichungen vom Standard)
- Every file the Pi needs is listed in `FILES` in `tools/pi/update.py`; removed Pi files go into `RETIRED_FILES` (otherwise the package build fails or stale files remain).
- Private data (settings, keys, certificates, caches, counters, layouts) only under `private/`, paths via `paths.py`.
- Real device/location facts live in gitignored `CLAUDE.local.md`; the denylist for the leak guard in gitignored `private/leak-denylist.txt`. Public files use Potsdam and placeholders; never bypass the hook (`--no-verify`).

## Regeln (aus Korrekturen, mit Warum)
- A noted idea is not an approval: new features, live requests, Pi transfer, sensors, accounts, cloud services and publishing only after concrete approval (the user approves each scope explicitly).
- Development and tests only with labelled sample data, dummy keys and temporary storage (real settings and budget counters must never change).
- Never put API keys in code, docs, logs, screenshots or HTTP responses (public repo; the key is stored unencrypted in `private/`).
- Never run PC live and Pi live at the same time with the same budget identity (separate copies share no lock).
- Never delete `.pi-update-in-progress.json`; recover as described in docs/UPDATE.md (the marker protects against a half-applied update).
- Create/release Tk objects and images only in the Tk main thread (otherwise crashes and stutter on the Pi).
- For weather, map or budget changes, test location change, background work, cache assignment and day rollover in isolation.
- The final report separates what the code can do, what was checked, and which live/device check is still open (offline acceptance does not replace a device check).

## Leitentscheidungen (max. 10, Details in ai/DECISIONS.md)
- One shared core for PC and Pi; `paths.py` keeps the existing `private/` path stable (settings and budget identity must not move).
- Passive display, operated only via phone with one-time-code pairing over HTTPS on the home network (no local dialogs on the display).
- One weather location (place + ISO country) drives weather, local time and map (places with the same name must not share data).
- Budget protection: reserve before HTTP, max. 1000/day (Berlin and UTC), 3 requests every 5 minutes take priority; extra series only with per-device approval.
- Never show missing radar coverage as "dry"; attribution on international maps always visible.
- Design format 4, older formats readable; Qt only on the PC, Tk on the Pi.
- Pi updates only manual, with backup, offline check, and restart only of the mode that was running before.
- Public repo without device data, private data or old Git history.

## Aktueller Stand
@ai/STATUS.md
