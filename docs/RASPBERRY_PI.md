# Raspberry Pi · Installation und Updates

**Aktueller Ablauf seit 25.10.2026:** [Pi aktualisieren](UPDATE.md).
Die folgende Dokumentation beschreibt frühere Installationsstände. Linux-Starter
liegen jetzt unter `raspberry_pi/`; bisherige Root-Starter bleiben Weiterleitungen.

**Neuer PC-Stand vom 24.10.2026:** passive weiße Displayanzeige und automatische
Handy-Anmeldung mit einzelnen Codes, mehreren Browsern und Sitzungen bis zum
Programmneustart. Noch nicht auf den Pi übertragen und nicht in den älteren
Archiven enthalten. Nach einem späteren Update: Smartphone im Heimnetz auf
`https://<Pi-Adresse>:8765` öffnen, Code vom Display eingeben; am Pi ist keine
Bestätigung nötig. Vollständiger Ablauf in [README.md](../README.md).


Handy-Reparatur vom 24.10.2026: aktualisiertes Paket und Anleitung unter
[PI_UPDATE.md](PI_UPDATE.md). Es erkennt die tatsächlichen Linux-Heimnetz-Adressen
und entfernt `127…` aus der Handy-Auswahl. Der Reparaturmodus erhält das vorhandene
Pi-Layout und sämtliche privaten Dateien. Lokale Offline-Prüfung bestanden;
Übernahme und Offline-Prüfung auf dem Pi durch Nutzerausgabe bestätigt;
Anmeldung und Widget-Änderung am persönlichen Handy anschließend ebenfalls
vom Nutzer bestätigt. Reparatur abgeschlossen.

## Aktuelles Programmupdate vom 24.10.2026

Ein Desktop-Symbol **Wetterstation** wurde inzwischen auf dem Pi eingerichtet
(`/home/pi/Desktop/Wetterstation.desktop`, durch Nutzerausgabe bestätigt).
Es startet den echten Betrieb über `start_pi_live.sh` mit den vorhandenen
Pi-Einstellungen und Zählern. Zuerst eine noch laufende Demo schließen, dann
das Symbol doppelklicken und einen gegebenenfalls angezeigten Ausführungsdialog
selbst bestätigen. Die Einrichtung allein startet keine Wetterabrufe.

Die vollständige Vorbereitung für den bestehenden Pi steht in [PI_UPDATE.md](PI_UPDATE.md).
Das neue datierte Programmarchiv enthält Widgets, Handy-Editor und aktuelle
Kartenfunktionen. Das gespeicherte PC-Widget-Layout wird separat bereitgestellt;
Pi-Ort, Schlüssel, Zertifikate und sämtliche Zähler bleiben erhalten.
`prepare_pi_update.cmd` bereitet nur lokal vor. `transfer_pi_update.cmd` führt
erst bei späterem ausdrücklichem Start die Übertragung mit Ziel-/Prozessprüfung,
Pi-Sicherung und Offline-Abnahme aus. Kein automatischer Anwendungsstart.

Die folgenden Abschnitte dokumentieren die frühere Ersteinrichtung. Das alte
`Wetterstation.zip` und `prepare_pi_live.cmd` sind kein aktuelles
Programmupdate und werden dafür nicht verwendet.

## Historisch: erster Test

Zielgerät laut Nutzer: Raspberry Pi 3 Model A Plus, Debian 12 Bookworm mit Desktop.
Der erste Start verwendet ausschließlich gekennzeichnete Beispieldaten.

## Übertragung

Das vorbereitete Archiv `transfer/Wetterstation.zip` enthält den Programmcode,
die Handy-Oberfläche und Dokumentation. Private Einstellungen, Schlüssel,
Zertifikate, Zählerstände und Caches werden nicht mitgeliefert.

Das Archiv auf den Pi kopieren und in einen neuen Ordner entpacken. Bereits
vorhandene Installationen oder Einstellungen dabei nicht überschreiben.

## Start auf dem Desktop des Pi

Ein Terminal im entpackten Programmordner öffnen und starten:

```sh
sh start_pi_demo.sh
```

F11 wechselt zwischen Vollbild und Fenster. Pfeiltasten wechseln die Ansichten.
Die Regenkarte zeigt in der Demo ausdrücklich keine echten Kartenbilder.

Falls Tkinter fehlt, ist vor dem Start das Debian-Paket `python3-tk` erforderlich.
Der Starter installiert selbst keine Pakete und verändert keine Systemdienste.

## Bestätigter Teststand

- Der Nutzer bestätigt Demostart, sichtbare Ansichten und Seitenwechsel.
- Der Offline-Funktionstest bestätigt Bildverarbeitung, lokale TLS-Zertifikate
  und Dateisperren mit den installierten Debian-Bibliotheken. Deren Versionen
  liegen unter den konservativen Mindestversionen der allgemeinen requirements.txt;
  diese gezielte Funktionsprüfung ist kein vollständiger Sicherheitstest.

## Freigegebene Umstellung auf Livebetrieb

Der Nutzer hat Livebetrieb und ersten Wetterabruf ausdrücklich freigegeben.
`prepare_pi_live.cmd` wird auf dem Windows-PC im normalen Benutzerkontext
ausgeführt, während beide Wetterprogramme geschlossen sind. Es überträgt
Einstellungen und die komplette bestehende Zähleridentität samt Historie und
lokalem Prüfspeicher verschlüsselt an den bereits geprüften Pi. Die
Windows-Dateien bleiben bestehen. Die private Übertragungsdatei enthält den
Schlüssel; sie gehört ausschließlich in private/ und wird nie ausgegeben.

Ein Import ersetzt keine vorhandenen Einstellungen oder Kennungen auf dem Pi.
Der Nutzer hat die erfolgreiche Übertragung anhand der Ausgabe des Importprogramms
bestätigt. Die Übernahme
sendet selbst keine Wetteranfrage. Vorhandene Limits und Sperren bleiben erhalten.
Nach erfolgreicher Prüfung startet `sh start_pi_live.sh` im Programmordner auf
dem Desktop des Pi die Live-Anwendung. Das Windows-Wetterprogramm danach nur
im Demomodus verwenden, solange die umgezogene Installation auf dem Pi live
läuft: getrennte Kopien besitzen keine gemeinsame Sperre für das Anbieterbudget.

## Praxisprüfung laut Nutzerbericht

- Der Nutzer bestätigt inzwischen den Livestart sowie Wetterübersicht,
  Vorhersage und Regenkarte mit Niederschlag. Die Sensorwerte bleiben Demo.
- Erste unbeaufsichtigte Laufprobe von rund dreieinhalb Stunden bestätigt:
  kein Absturz, Seitenwechsel weiterhin möglich und verändertes Niederschlagsradar
  ohne manuellen Abruf. Zwei geprüfte Fotos von 17:51 und 21:18 Uhr am 23.10.2026
  stützen den Radarvergleich. Exakte Aktualisierungstakte und API-Verbrauch wurden
  damit nicht geprüft.
## Noch offen

- Weitere längere Laufproben, Geräte-Neustart und Prüfung der Handy-Einstellungen auf dem Pi.
- Automatischer Start beim Einschalten ist noch nicht eingerichtet.

Alle 131 automatisierten Tests bestehen unter Windows, einschließlich sechs
Migrationstests mit Dummy-Schlüsseln und temporären Zählern. Die Pi-Prüfungen
oben sind Nutzerberichte, keine selbst durchgeführten Hardwareprüfungen.
