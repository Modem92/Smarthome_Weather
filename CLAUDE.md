# WeatherStation – Projektleitfaden für Claude Code

WeatherStation (`wetterstation`) ist eine Python-Anwendung mit gemeinsamer Codebasis für Windows und Raspberry Pi. Die passive Tk-Anzeige zeigt Uhr, Wetter, Vorhersage und Regenkarte. Die Handy-Oberfläche im Heimnetz dient für Einstellungen und Widget-Anordnung. Der separate Qt-Designer gestaltet Widgets mit Beispieldaten. Im öffentlichen Checkout ist Potsdam der Beispielort.

## Wo du nachliest

- Lies [AGENTS.md](AGENTS.md) und [PROJEKTPLAN.md](PROJEKTPLAN.md) vor Projektänderungen. Der Plan unterscheidet bestätigte Aufträge, umgesetzte Punkte, künftige Ideen und offene Entscheidungen. Setze vorgemerkte Ideen erst nach ausdrücklicher Freigabe um. Nutze bei widersprüchlichen historischen Einträgen die jeweils neuere bestätigte Entscheidung und prüfe die Umsetzung im Code.
- [README.md](README.md) und [docs/STRUCTURE.md](docs/STRUCTURE.md) beschreiben Einstiegspunkte, Aufbau und Entwicklung. [docs/FEATURE_STATUS.md](docs/FEATURE_STATUS.md) enthält datierte Abnahmen. Berichte bei Änderungen getrennt, was der Code unterstützt, was du selbst geprüft hast und welche Live- oder Geräteprüfungen ausstehen.
- [docs/DESIGNER.md](docs/DESIGNER.md) und [docs/GRAPHICAL_DESIGNER_SPEC.md](docs/GRAPHICAL_DESIGNER_SPEC.md) beschreiben Gestaltung, Layoutkompatibilität und Zusatzdaten. [docs/UPDATE.md](docs/UPDATE.md) und [docs/OPTIMIZATION.md](docs/OPTIMIZATION.md) erklären Pi-Updates und die gemessenen Optimierungen.

## Orientierung im Code

| Bereich | Einstieg und Zuständigkeit |
| --- | --- |
| Anzeige | `app.py` und `python -m wetterstation` führen zu `wetterstation/ui/app.py`. `dashboard.py` zeichnet das Display, `widgets.py` definiert Widgettypen und das Standardlayout. |
| Wetter und Ortszeit | `wetterstation/weather/weather_service.py` verarbeitet Geocodierung, Abrufe und Vorhersagen. `countries.py` und `location_time.py` behandeln Land und Zeitzone. |
| Regenkarte | `wetterstation/maps/radar_map.py` verarbeitet die Deutschlandkarte, `international_map.py` die internationalen Kacheln, `radar_render.py` die Darstellung und `radar_motion.py` die DWD-Regenzugschätzung. |
| Einstellungen und Budget | `wetterstation/paths.py` bestimmt den Projektordner. `storage/api_key_store.py` und `storage/file_io.py` verwalten Einstellungen und Dateizugriffe. `storage/openweather_budget.py` schützt die Abrufgrenzen. |
| Handy | `wetterstation/mobile/mobile_settings.py` stellt das lokale HTTPS-Angebot, Pairing und Layoutzugriffe bereit. Browsercode liegt unter `wetterstation/mobile/web/`. |
| Designer | `wetterstation/designer/app.py` ist der Qt-Einstieg. `model.py` validiert die Gestaltung, `storage.py` verwaltet Entwürfe und Medien. `render.py` und `runtime.py` verbinden das Design mit der Tk-Anzeige. |
| Start und Update | Plattformstarter liegen unter `windows/` und `raspberry_pi/`. `tools/windows/updater.py`, `tools/pi/controller.py` und `tools/pi/update.py` bilden den manuellen Programmupdatepfad. `tools/legacy/` enthält die frühere einmalige Migration. |

## Entscheidungen und ihre belegten Gründe

- **Gemeinsamer Kern und stabiler Speicherpfad.** Die Umordnung in Python-Module sollte vorhandene Einstellungen und Budgetidentitäten erhalten. Daher bestimmen `paths.py` und die Kompatibilitätseinstiege den bisherigen Projektordner unabhängig vom Modulpfad. `private/` bleibt gemäß ausdrücklicher Nutzerentscheidung projektbezogen und Git-ignoriert. OneDrive darf die unverschlüsselten Dateien synchronisieren. [Struktur und Entwicklung](docs/STRUCTURE.md)
- **Passive Anzeige, Bedienung am Handy.** Der Auftrag vom 24.10.2026 gab der Anzeige die volle Fensterfläche und behielt das vorhandene Widget-Raster. Einstellungen und Anordnung wanderten zum Handy. Jeder Browser koppelt sich über einen eigenen, nur am Display sichtbaren Einmalcode. Vier wartende Anfragen, zwei Minuten Gültigkeit ab Anzeige und acht Sitzungen bis Abmeldung oder Neustart gehören zum dokumentierten Ablauf. Erhalte TLS, sichere Cookies, Host-/Origin-Prüfung, CSRF-Schutz und Versuchslimits. [Arbeitsregeln](AGENTS.md) · [Funktionsstand](docs/FEATURE_STATUS.md)
- **Ein Wetterort für Wetter, Zeit und Karte.** Ort und ISO-Land werden gemeinsam gespeichert. Länderbezogene Geocodierung und getrennte Caches verhindern, dass gleichnamige Orte Ergebnisse teilen. Die Anzeige verwendet Wetter-Ortszeit mit gekennzeichnetem UTC-Rückfall. Deutschland nutzt die helle BKG-Straßenkarte und transparentes DWD-Radar gemäß Bildreferenz. Im Ausland nutzt das Projekt bedarfsgerecht OSM und RainViewer bei Zoom 7. Erhalte Quellenangaben, Cache und Abdeckungsmaske, damit fehlendes Radar nicht als Trockenheit erscheint. Regenzugpfeile bleiben auf DWD beschränkt. [Projektentscheidungen](PROJEKTPLAN.md)
- **Grundversorgung hat beim Budget Vorrang.** Der reguläre Zyklus sieht drei Wetteranfragen alle fünf Minuten vor. Der lokale Schutz reserviert vor HTTP und begrenzt den deutschen Kalendertag und den UTC-Anbietertag auf jeweils 1.000 Anfragen. Das ist eine Anwendungsgrenze. Die tatsächlichen Billing-Einstellungen wurden laut Projektplan nicht unabhängig geprüft. Zusatzzeitreihen brauchen eine getrennte Freigabe pro Gerät. So aktiviert eine kopierte Gestaltung keine zusätzlichen Abrufe. Die Grundanfragen und 24 Reserveanfragen haben Vorrang. [Projektplan](PROJEKTPLAN.md) · [Zusatzdaten](docs/DESIGNER.md#zusatzdaten-ausdrücklich-aktivieren)
- **Gestaltung und Handy-Anordnung greifen auf dasselbe Layout zu.** Format 4 ergänzt frei bearbeitbare Inhaltsblöcke und bewahrt Widgettypen und Datenbindungen. Ältere Layouts bleiben ohne grafische Bearbeitung auf ihrem bisherigen Renderweg. Handy-Änderungen einschließlich Rückgängig müssen die Gestaltung erhalten. Qt ist eine PC-Designer-Abhängigkeit. Für die Pi-Anzeige genügt Tk. [Grafischer Designer](docs/GRAPHICAL_DESIGNER_SPEC.md) · [Designer-Anleitung](docs/DESIGNER.md)
- **Weniger Last während der Anzeige und im Leerlauf.** Die Optimierung folgte auf Berichte über CPU-Spitzen und stockende Seitenwechsel am Pi. Der Browser berechnet Ziehen und Skalieren lokal, speichert nach dem Loslassen und pausiert Abfragen bei Inaktivität. Das Display bereitet gestaltete Seiten im Hintergrund vor und übernimmt nur das aktuelle Ergebnis im Tk-Hauptthread. [Optimierung und Messungen](docs/OPTIMIZATION.md)
- **Pi-Updates sind manuell und sichern den vorhandenen Zustand.** Der Updater testet und paketiert denselben eingefrorenen Quellstand. Vollständige Bereitstellung und Identitätsprüfung gehen der geordneten Beendigung voraus. Sicherung, Prüfsummen und Offline-Tests schützen Installation und Wiederherstellung. Der Wiederstart betrifft nur eine zuvor laufende Anzeige und verwendet deren bisherigen Modus. Ein Programmupdate erhält Pi-Layout und private Daten. Für eine gezielte Gestaltungsübertragung gibt es einen eigenen Ablauf. Das Standalone-Updatewerkzeug verwendet die Standardbibliothek, damit Wiederherstellung aus dem Zwischenordner möglich bleibt. [Pi-Update](docs/UPDATE.md) · [Projektstruktur](docs/STRUCTURE.md)

## Entwickeln und prüfen

Python 3.11 oder neuer mit Tkinter ist erforderlich. Die Laufzeitabhängigkeiten stehen in `requirements.txt` und `pyproject.toml`. In einer geeigneten lokalen virtuellen Umgebung installiert `python -m pip install -e '.[designer]'` zusätzlich PySide6 Essentials. Verwende in einem vorbereiteten Cloud-Checkout den Interpreter `.venv/bin/python`.

```sh
python tools/offline_tests.py --report build/checks/offline-tests.txt
python tests/display_visual_check.py
python tests/designer_scale_check.py
```

- Der Offline-Runner sperrt externe Python-Socketverbindungen und erlaubt Loopback für HTTPS-Tests. Starte die gespeicherte Datei direkt, insbesondere für Windows-Mehrprozesstests. Für Tk-Prüfungen brauchst du ein Display, etwa Xvfb unter Linux. Der Qt-Skalierungstest nutzt Qt offscreen. Prüfbilder und Berichte liegen unter `build/checks/`.
- Für eine manuelle Widget-Demo mit temporären Einstellungen gibt es `python -m wetterstation --widget-demo`. Dieser Einstieg kann Handy-HTTPS im Heimnetz starten. Für eine isolierte visuelle Prüfung verwende `tests/display_visual_check.py`. Den Qt-Designer kannst du für isolierte Prüfungen mit `python -m wetterstation.designer.app --workspace <temporärer-ordner>` starten.
- Browserabnahmen sind separat. Starte dafür `python tests/widget_demo.py` als isolierten Loopback-HTTPS-Server und verwende die Node-/Playwright-Prüfungen aus [docs/STRUCTURE.md](docs/STRUCTURE.md). Für die eingefrorene Designer-Abnahme mit Pi-Paketbau siehe `tools/designer_acceptance.py` und [docs/DESIGNER.md](docs/DESIGNER.md#lokale-prüfung).
- Die Cloud-Einrichtung hat Tk-Beispielbilder und alle drei Qt-Skalierungsläufe erfolgreich geprüft. In der vollständigen Cloud-Offlinesuite blieben schmale Tk-Layouts und Vollbild, das sofortige erneute Binden des HTTPS-Ports und eine Pi-Testfixture mit Root-Besitzannahme auffällig. Falls vorhanden, siehe den lokalen Bericht `build/checks/cloud-offline.txt`. Historische Pi-Abnahmen und aktuelle Cloud-Ergebnisse betreffen unterschiedliche Testumgebungen.

## Änderungen im freigegebenen Umfang halten

- Standard für die Entwicklung sind klar gekennzeichnete Beispieldaten, Dummy-Schlüssel und temporäre Speicherpfade. Live-Wetterprüfung, reale Pi-Übertragung, Sensorzugriff, neue Dienste und Veröffentlichungen erfordern eine konkrete Freigabe. E-Ink-Anbindung, physische Eingabetasten und das endgültige Stromsparkonzept sind offene Entscheidungen.
- Halte API-Schlüssel aus Quellcode, Dokumentation, Logs und Screenshots heraus. Der gespeicherte Schlüssel bleibt aus HTTP-Antworten ausgeschlossen. Der Projektpfad unter `private/` ist der vorgesehene Speicher für Wetter-Schlüssel. Schütze bei Änderungen auch Zertifikate, Caches, Zähler und Geräteidentität.
- Bewahre beim Ändern von Display oder Handy-Editor bestehende Layouts und Gestaltungsdaten. Prüfe bei Änderungen an Wetter, Karte oder Budget auch Ortswechsel, ausstehende Hintergrundarbeiten, Cache-Zuordnung und Tageswechsel mit isolierten Tests.
