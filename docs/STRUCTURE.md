# Struktur und Entwicklung

## Ein Programm, zwei Startumgebungen

`wetterstation/ui` enthält Tk-Anzeige und Widgets, `weather` die Wetter-/Ortslogik,
`maps` die Kartenverarbeitung, `storage` Einstellungen und Budgetschutz und `mobile`
die Handy-Schnittstelle samt Webdateien. `paths.py` bestimmt den unveränderten
Projektordner zentral; das Verschieben von Modulen ändert keinen privaten Speicherpfad.

Windows-Starter liegen unter `windows`, Pi-Starter unter `raspberry_pi`.
`tools/pi/update.py` bleibt mit der Standardbibliothek allein ausführbar, damit
Sicherung und Wiederherstellung auch aus dem Pi-Zwischenordner funktionieren.
`tools/pi/controller.py` steuert ausschließlich ausdrücklich gestartete Updatevorgänge.
`tools/legacy` enthält die frühere einmalige Schlüssel-/Zählermigration; sie ist kein Updateweg.

Die Rootdateien `app.py`, `pi_update.py`, `pi_preflight.py` und die alten Starter sind
Kompatibilitätseinstiege. Es gibt keine zweite Kopie der Programmlogik.
Das Pi-Paketformat 2 enthält eine ausdrückliche Dateiliste. Bei der Umstellung werden
nur benannte alte Programmdateien nach Sicherung entfernt. Unbekannte Dateien bleiben erhalten.

## Laufzeit und Tests

Die Optimierung und der Prüfmodus zur abgesicherten Bereinigung sind unter
[OPTIMIZATION.md](OPTIMIZATION.md) beschrieben. Die Designer-Laufzeit und neue
eingefrorene Prüfarbeitskopien liegen außerhalb OneDrive. Nur geprüfte Pakete und
Abnahmeberichte werden im Projekt aufbewahrt. Gemeinsame Auflösung: `tools/dev_paths.py`.

Python >=3.11 mit Tkinter und den Bibliotheken aus `requirements.txt` verwenden.
Windows sucht zuerst eine lokale Umgebung unter `%LOCALAPPDATA%/Wetterstation/venv`,
danach die vorhandene gebündelte Laufzeit und anschließend Python über `py` beziehungsweise PATH.
Es wird nichts automatisch installiert. Virtuelle Umgebungen außerhalb OneDrive halten.
`python -m wetterstation --widget-demo` startet eine gekennzeichnete Demo.

`python tools/offline_tests.py` führt alle automatisierten Python-/Tk-/HTTPS-Tests
mit externen Verbindungen gesperrt aus. Windows-Mehrprozesstests aus dieser gespeicherten
Datei starten, nicht über PowerShell-Standardeingabe.

Für Browserabnahmen `python tests/widget_demo.py` als isolierten lokalen HTTPS-Server
starten; dann mit vorhandener Node-/Playwright-Umgebung
`node tests/widget_browser_check.cjs` und `node tests/pairing_browser_check.cjs` ausführen.
Die Browserprüfungen blockieren externe Seitenzugriffe. `tests/international_visual_check.py`
und `tests/international_browser_check.cjs` prüfen entsprechend internationale Beispieldaten.
`tests/display_visual_check.py` erzeugt synthetische Displaybilder. Die Ausgaben liegen
unter `build/checks/`; persönliche Einstellungen werden nicht verändert.

## GitHub und lokale Projektdaten

Quellcode, Tests, Dokumentation, Paketdefinition und Zeilenendenvorgaben sind für ein
gemeinsames Repository vorbereitet. `private`, `build`, `archive`, alte `transfer`-Ordner,
Python-Caches, Umgebungen und Laufzeitkennungen sind ausgeschlossen.
Vor dem ersten Commit die tatsächlich vorgesehene Dateiauswahl auf vertrauliche Inhalte
prüfen. Vor einem Upload zusätzlich die vollständige Git-Historie prüfen.
Das öffentliche Repository enthält einen geprüften Quellstand mit neutraler Beispielkonfiguration.

OneDrive darf den gesamten Ordner einschließlich der unverschlüsselten Einstellungen
synchronisieren. Der Ausschluss aus Git ändert daran nichts. Den Projektordner auf
diesem PC auf „Immer auf diesem Gerät behalten“ stellen. Nicht gleichzeitig an mehreren
Computern in demselben synchronisierten Git-Arbeitsordner arbeiten.
Bei regelmäßiger GitHub-Nutzung eigene lokale Arbeitskopien außerhalb von OneDrive verwenden.

Die Sicherung vor der Umordnung liegt unter `archive/before-restructure-*/workspace.zip`.
Sie enthält auch vertrauliche Dateien und den vorherigen Git-Stand. Alte Transferpakete
liegen unter `archive/transfer-*`. Archive werden nicht automatisch gelöscht.
