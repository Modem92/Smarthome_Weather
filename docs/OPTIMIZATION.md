# Optimierung vom 28.10.2026

## Abschließendes Ergebnis

Final auf dem Pi installiert: `2026-10-28-optimization-174804`, SHA-256
`<interne Prüfsumme>`.
389 Tests bestanden im eingefrorenen Stand. Die Widget-Demo wurde geordnet
wieder gestartet. Nutzerabnahme: „Passt alles, läuft auch flüssig“.

| Messung | Vorher | Final |
|---|---:|---:|
| CPU, 10-Sekunden-Demostichprobe, ein Kern | 21,1 % | 1,1 % |
| Datenträger-Schreibbytes in dieser Stichprobe | 65.536 | 0 |
| RSS derselben Demo | 45.324 KiB | 66.328 KiB |
| Übersicht, erste Berechnung | 4.031 ms | 1.163 ms |
| Übersicht, Median dreier Wiederholungen | 3.927 ms | 84 ms |
| Vorhersage, erste Berechnung | 3.691 ms | 524 ms |
| Vorhersage, Median dreier Wiederholungen | 3.640 ms | 65 ms |
| Sensorseite, erste Berechnung | 859 ms | 293 ms |
| Sensorseite, Median dreier Wiederholungen | 474 ms | 73 ms |

Die Regen-Demoseite blieb ungefähr bei 10–14 ms. Die Renderwerte stammen aus
dem identischen getrennten 1024×600-Test mit Standard-Demodaten und enthalten
die Tk-Aufbereitung, nicht die vollständige physische Displaylatenz. Der
Speicheranstieg ist der Preis für wiederverwendete Schrift-/Darstellungsdaten.
Die Stichproben sind keine Langzeitmessung. Ein Livebetrieb wurde für diese
Tests nicht gestartet; externe Wetterabrufe wurden durch die Renderprobe gesperrt.
Die Zustände eines realen Handybrowsers waren in der Prozessmessung nicht
fernüberwacht. Browser-Ruhepause, Wiederaufnahme, keine Übertragung während des
Ziehens und genau eine danach wurden separat mit isolierten Browser-/Zeitprüfungen
nachgewiesen; die Bedienung am Pi wurde zusätzlich vom Nutzer bestätigt.

Das bestehende gespeicherte Pi-Layout hat vor/nach der Übernahme denselben
SHA-256-Wert. Die Demo bleibt geöffnet. Finale Sicherung:
`~/wetterstation/Wetterstation-Backups/<Zeitstempel>`.
Der bekannte funktionsfähige Stand vor der ersten Optimierung bleibt außerdem in
`~/wetterstation/Wetterstation-Backups/<Zeitstempel>`
gesichert. Der erste Stand mit fehlgeschlagenem Start liegt ausdrücklich unter
`archive/failed-start-packages`, nicht unter den zwei aktuellen geprüften Paketen.

build enthält nach Bereinigung und neuen Prüfbelegen rund 7,9 MiB/109 Dateien
statt rund 341 MiB/5.186 Dateien. Alte Belege wurden komprimiert aufbewahrt, nicht
ersatzlos gelöscht. Die zusätzlichen Archive belegen weiterhin OneDrive-Speicher.
Die folgenden Abschnitte dokumentieren Vorgehen und Zwischenstände chronologisch.

## Geprüfte Struktur

Die gemeinsame Codebasis, Kompatibilitätseinstiege, Tests und Wiederherstellungswege
bleiben erhalten. Persönliche Einstellungen, Entwürfe, Layouts, Zertifikate,
Caches und Budgetidentitäten wurden durch die Bereinigung nicht verändert.

Die PC-Designer-Laufzeit wurde vollständig und bytegleich nach
`%USERPROFILE%/AppData/Local/Wetterstation/designer-runtime` kopiert. Ein isolierter
Qt-Start war erfolgreich. Starter und Qt-Prüfung verwenden `tools/dev_paths.py`;
der alte Suchweg bleibt als Rückfall für noch nicht umgestellte Arbeitsplätze.
Die lokale Ersatzlaufzeit wurde nach Prüfsummen- und Prozessprüfung entfernt.
Neue eingefrorene Prüfkopien liegen ebenfalls außerhalb OneDrive.

Bekannte alte Prüfausgaben sind vollständig in
`archive/optimization-20261028T165303357535Z.zip` mit Inhaltsprüfsummen gesichert.
Windows-Schreibschutz führte beim ersten Entfernen zum Abbruch; der zweite
Durchlauf prüfte die verbliebenen Dateien gegen dasselbe Archiv und setzte fort.
Unbekannte Restordner bleiben erhalten. Der zusätzliche Projektplan liegt
bytegleich im Archiv; seine abweichenden Abschnitte sind in `ai/DECISIONS.md` eingeflossen.

Prüfmodus: `python tools/workspace_maintenance.py`. Erst `--apply` verändert etwas.
Die Optionen `--resume-archive` und `--retire-runtime` unterstützen die abgesicherte
Fortsetzung. `--prune-packages` erhält die zwei neuesten inhaltlich geprüften Pakete
und verschiebt ältere mit Prüfsummen nach `archive/retired-pi-packages`.

## Laufzeit und Bedienung

- HTTPS bleibt erreichbar; der Server wartet im Leerlauf mit 500 ms statt 100 ms
  Prüfintervall. Ein eintreffender Socket wird unmittelbar verarbeitet.
- Browserabfragen pausieren nach 60 Sekunden ohne Bedienung, bei verborgenem Tab
  oder Fokusverlust. Vor weiteren Änderungen wird der Displaystand geprüft.
  Eine abweichende Revision sperrt Bearbeitung, aber nicht Neuladen/Abmelden.
- Verschieben, Kollisionsvorschau und Größenänderung laufen im Browser. Während
  des Ziehens wird nichts gespeichert, nach dem Loslassen genau einmal.
  Sichtbare Inhalte, Farben und Schriften werden im PC-Designer bearbeitet.
- Sitzungen, Einmalcodes, TLS-, Origin- und CSRF-Schutz bleiben erhalten.
- Die Laufzeitdatei wird nur bei Zustandsänderung geschrieben. Stop-Anforderungen
  werden unverändert regelmäßig geprüft. Ohne wartende Anmeldung gibt es keinen
  Anmeldetimer; wartende Codes erhalten gezielte Ablaufzeitpunkte.
- Legacy-Anzeigen verwenden wiederverwendbare Schriftinstanzen und Messungen;
  unveränderte Uhrtexte werden nicht neu berechnet.
- Gestaltete Seiten werden durch einen einzelnen Hintergrundauftrag vorbereitet.
  Nur der jeweils aktuelle Auftrag darf am Tk-Display übernommen werden. Tk-Bilder
  bleiben im Hauptthread. Die Bestätigung erfolgt erst nach tatsächlicher Anzeige
  samt gültiger Geometrie. Seiten- und Widgetcaches sind auf je 16 MiB begrenzt.

## Abnahme und Grenzen

Die erste lokale Gesamtprüfung bestand aus 386 Python-Tests. Nachfolgende
Korrekturen und zusätzliche Regressionen werden durch die abschließende
eingefrorene Abnahme erneut geprüft. Maßgeblich sind die Berichte unter
`build/reports/` und `build/checks/designer-acceptance.json`.
Normale Anordnungs-, Mehrbrowser-Anmelde- und Designformat-Browserprüfungen sowie
18 PC-Designer-Oberflächenprüfungen bestanden mit Dummy-Daten ohne externe Abrufe.

Der Pi wurde vor der Übernahme rein lesend geprüft: alter Programmstand ohne
Designer-Laufzeit, bestehendes Layoutformat 2. Die vom Nutzer gestartete
Widget-Demo belegte in einer 10-Sekunden-Stichprobe 21,1 % eines CPU-Kerns,
45.324 KiB RSS und 522 Schreib-Systemaufrufe. Schreib-Systemaufrufe enthalten
auch Socketkommunikation und sind nicht mit SD-Karten-Schreibvorgängen gleichzusetzen.

Ein getrennter unsichtbarer Test mit temporären Standard-Demodaten auf demselben
Pi ergab vor der Optimierung ungefähr 4,03/3,93 Sekunden für die Übersicht und
3,69/3,64 Sekunden für die Vorhersage (erste Berechnung/Median dreier Wiederholungen).
Er verändert die laufende Demo nicht und sperrt Provideraufrufe. Dieser Test
misst Berechnung inklusive Tk-Aufbereitung, nicht die vollständige physische
Displaylatenz. Die Rohbelege liegen unter `build/reports/pi-*-before*.json`.

Gesicherte Übernahme und Nachher-Messung folgen erst nach der eingefrorenen
Offline-Abnahme. Ein PC-Testergebnis ist kein Pi-Leistungsnachweis. Wetterraster,
Budgetschutz, Ortszeit und die Quellenkennzeichnung sind unverändert.

Die erste Übernahme bestand die Installation, konnte die Demo aber nicht starten:
Debian stellt `PIL.ImageTk` als optionales separates Paket bereit, das auf diesem
Pi fehlt. Die Korrektur nutzt vorhandenes Tkinter mit PNG-Übernahme als Rückfall,
ohne Paketinstallation. Sie wird ausdrücklich ohne ImageTk auf Farbinhalt, Größe
und Transparenz geprüft; auch die Pi-Vorabprüfung importiert nun den Anzeigepfad.
Beim Schließen werden Bildaufträge beendet und Tk-Ressourcen im Hauptthread
freigegeben. Der erneute eingefrorene Stand wird vor einer korrigierten Übernahme
vollständig offline geprüft. Die ursprüngliche Demo soll anschließend wieder
hergestellt werden; kein Wechsel in den Livebetrieb.

Die korrigierte Fassung wurde anschließend mit 388 Tests abgenommen, erfolgreich
installiert und die ursprüngliche Widget-Demo wieder gestartet. In der gleichen
10-Sekunden-Stichprobe sank die CPU-Belegung von 21,1 auf 1,6 % eines Kerns;
Datenträger-Schreibbytes von 65.536 auf 0, RSS stieg von 45.324 auf 50.864 KiB.
Das bestehende Pi-Layout blieb nach SHA-256 unverändert. Wiederholte synthetische
Seitenberechnung sank auf etwa 87 ms (Übersicht) bzw. 64 ms (Vorhersage).

Die erste Berechnung blieb zunächst mit 2,69 bzw. 1,38 Sekunden zu langsam.
Eine weitere Linux-Optimierung engt die Schriftgrößensuche mit den mitgelieferten
DejaVu-Schriften ein; die endgültigen Zeilenumbrüche, Größen und Grenzen werden
weiterhin mit tatsächlichen Tk-Metriken geprüft. Ein getrennter Test dieses
zusätzlichen Codes im Speicher des Pi ergab 1,18 bzw. 0,53 Sekunden für erste
Berechnungen und unverändert etwa 86/65 ms für Wiederholungen. Vor der Installation
auch dieser Ergänzung folgt erneut die vollständige eingefrorene Abnahme.
