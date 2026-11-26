# Historisch: vorbereitetes Pi-Update · 24.10.2026

**Seit 25.10.2026 ersetzt durch [den manuellen Doppelklick-Updater](UPDATE.md).**
Die folgenden Paketnamen, Pfade und Passwortabläufe dokumentieren ausschließlich
die frühere Installation. Alte Transferpakete liegen jetzt unter `archive/transfer-*`.

Hinweis: Die neue passive Anzeige und Anmeldung mit Einzelcodes sind bisher nur
im PC-Workspace abgenommen. Die unten genannten Archive sind frühere Stände;
für diese Änderung wurde kein neues Archiv gebaut und kein Pi-Transfer gestartet.


## Aktuell: Handy-Reparatur ohne Layoutimport

Aktuelles Paket: `transfer/Wetterstation-Pi-Update-2026-10-24-handy-reparatur.zip`.
Es korrigiert die Linux-Adresserkennung und den Handy-Verbindungsdialog.
Vorbereitet mit `pi_update.py build --release 2026-10-24-handy-reparatur --keep-layout`.
Keine PC-Einstellungen oder Layoutdatei werden gelesen, exportiert oder übertragen.
Die Paketbeschreibung `transfer/pi-update-ready.json` legt `keep_layout: true`
fest; der vorhandene Transferstarter berücksichtigt diesen Modus automatisch.

Vor der Übernahme Wetterstation am Pi schließen, dann auf dem PC
`transfer_pi_update.cmd` starten und das Pi-Passwort nur dort eingeben.
Vor der SSH-Anmeldung erscheint „Programmreparatur: vorhandenes Pi-Layout bleibt
erhalten“. Zielprüfung, Sicherung, Startsperre, Dateiprüfung und Offline-Abnahme
bleiben aktiv. Sämtliche privaten Pi-Dateien werden vor/nach der Installation
per SHA-256 verglichen, einschließlich Einstellungen und Layout. Auch eine
Rücksetzung dieser Reparatur schreibt keine privaten Einstellungen zurück.
Kein automatischer Programmstart. Lokal bestehen 251 Tests, davon 31 Updateprüfungen.

Nach erfolgreicher Übernahme die Widget-Demo nach Abschnitt 3 starten und im
Handy-Dialog eine echte Heimnetz-Adresse erwarten, beispielsweise
`https://<Pi-Adresse>:8765` bei unveränderter Pi-Adresse. Die angezeigte aktuelle
Adresse ist maßgeblich. Anmeldung und Widget-Steuerung am persönlichen Handy
prüfen; das lokale Zertifikat erfordert gegebenenfalls eine eigene
Vertrauensentscheidung im Browser. Pi-Übernahme und Offline-Prüfung wurden
am 24.10.2026 durch die vollständige Nutzerausgabe bestätigt, danach auch
Anmeldung und Widget-Änderung am persönlichen Handy. Reparatur abgeschlossen.
Sicherung: `~/wetterstation/Wetterstation-Backups/<Zeitstempel>`.
Das übertragene Archiv bleibt unverändert; spätere Dokumentationsfortschreibungen
sind darin als historischer Stand enthalten. Vor einem weiteren Transfer mit
aktuellen Quellen ist wie üblich ein neues Paket vorzubereiten.

## Bisheriges vollständiges Update mit PC-Layout

Diese Vorbereitung stellt keine Verbindung zum Pi her. Das neue Programm,
einschließlich Widgets, Handy-Editor und Kartenfunktionen, liegt im datierten
Archiv unter `transfer/`. Die jeweils aktuelle Zuordnung und Prüfsummen stehen
in `transfer/pi-update-ready.json`; das reine PC-Widget-Layout liegt separat
unter `private/pi-update-layout-<Version>.json`.

Aktuell vorbereitet: `transfer/Wetterstation-Pi-Update-2026-10-24-vollstaendig-r3.zip`
und `private/pi-update-layout-2026-10-24-vollstaendig-r3.json`. Das Programmarchiv
enthält 32 Dateien plus eingebettetes Inhaltsverzeichnis. Die lokale Abnahme
umfasst 232 bestandene Tests, davon 23 speziell für Update und Wiederherstellung,
Python-3.11-Syntax und Linux-Starter-Syntax. Die tatsächliche Pi-Kompatibilität
wird erst bei der späteren Offline-Abnahme auf dem Gerät bestätigt.

## 1. Vor dem späteren Transfer

- Die Wetterstation auf dem Pi schließen und während des Updates geschlossen lassen.
- Am PC nur eine Demo betreiben, solange der Pi die Live-Installation verwendet.
- Vorgesehenes Ziel: `pi@<Pi-Adresse>`, bestehender Programmordner
  `/home/pi/wetterstation/Wetterstation`.
- Der SSH-Hostschlüssel muss bereits bekannt sein. Bei einer abweichenden Identität
  bricht SSH ab; das Werkzeug akzeptiert oder ersetzt keinen Hostschlüssel.
- Falls sich seit der Vorbereitung Programm oder PC-Layout geändert haben,
  zuerst `prepare_pi_update.cmd` auf dem PC ausführen. Das erstellt nur ein neues
  Paket und stellt keine Pi-Verbindung her.

## 2. Kopieren, sichern und aktualisieren

Erst wenn die Übertragung gewünscht ist, auf dem PC `transfer_pi_update.cmd`
doppelklicken. SSH/SCP können nach dem Pi-Passwort fragen; es wird nicht vom
Programm gespeichert. Das Werkzeug prüft zuerst Benutzer, Linux/Python 3.11,
bestehenden Programmordner und laufende Wetterstationsprozesse. Bei einem
Fehler der Zielprüfung wird nichts übertragen.
Die Passwortabfrage und die konkrete SSH-Fehlermeldung bleiben im Fenster sichtbar.

Danach werden Programmarchiv, reine Layoutdatei und Updatewerkzeug in einen
neuen geschützten Zwischenordner auf dem Pi kopiert. Es folgen:

1. Vollständige Archiv-, Pfad-, Inhalts- und SHA-256-Prüfung vor dem Entpacken.
2. Vollständige Sicherung der vorhandenen Installation auf dem Pi unter
   `~/wetterstation/Wetterstation-Backups/<Zeitstempel>/installation/`.
   Der Sicherungsordner ist nur für den Pi-Benutzer zugänglich. Er enthält
   vertrauliche Pi-Einstellungen und darf nicht öffentlich weitergegeben werden.
3. Startsperre während der Aktualisierung und atomarer Austausch der
   Programmdateien. Vorhandene Dateien außerhalb des Pakets werden nicht gelöscht.
4. Nur das Feld `dashboard` wird in den Pi-Einstellungen durch das PC-Layout
   ersetzt. Ort, Schlüssel, Zertifikate, Caches, Gerätekennung, lokale
   Zählerhistorie und externer Zähler-Prüfspeicher werden nicht importiert oder
   zurückgesetzt. Das Werkzeug schreibt keine Zählerdateien.
5. Prüfung der installierten Dateien und unveränderten übrigen privaten Dateien;
   anschließend die Offline-Vorabprüfung. Keine Paketinstallation und kein
   automatischer Anwendungsstart.

Die Erfolgsausgabe nennt den konkreten Sicherungsordner. Bitte diesen Pfad für
eine mögliche Wiederherstellung aufbewahren.

## 3. Offline auf dem Pi prüfen

Im Desktop-Terminal des Pi:

```sh
cd ~/wetterstation/Wetterstation
python3 pi_preflight.py
sh start_pi_widget_demo.sh
```

Die Widget-Demo verwendet ausdrücklich Beispieldaten und ein frisches temporäres
Standardlayout. Über die Einstellungen lässt sich die geschützte Handy-Verbindung
einschalten. Seitenwahl, Verschieben, Größe, Inhalts-Schalter und Rückgängig prüfen.
Es gibt keine Wetter-/Kartenabrufe und keine Ort-/Schlüsseleingaben. Demoänderungen
verschwinden beim Beenden. Das dauerhaft übernommene PC-Layout wird vom Updater
unabhängig davon geprüft und später beim normalen Start geladen.

Für den Livebetrieb bleibt `sh start_pi_live.sh` erhalten. Dieser Schritt ist
keine automatische Folge des Updates; zuerst den Offline-Test abschließen.
Ein Live-Start kann echte Wetter-/Kartenabrufe auslösen. PC-Livevorschau und Pi
weiterhin nicht gleichzeitig mit dieser kopierten Zähleridentität betreiben.

## 4. Bei Fehlern wiederherstellen

Normale Installations- oder Offline-Prüffehler führen automatisch zum vorherigen
Programmstand und Widget-Layout zurück. Es wird anschließend nichts gestartet.
Bei Stromausfall oder fehlgeschlagener Wiederherstellung bleibt die Datei
`.pi-update-in-progress.json` als Startsperre bestehen. Sie enthält den
Sicherungspfad, aber keine Schlüssel. Diese Datei nicht einfach löschen.

Auf dem Pi mit dem **konkreten Pfad aus der Ausgabe oder Startsperre**:

```sh
python3 pi_update.py restore --target "$HOME/wetterstation/Wetterstation" --backup "KONKRETER_SICHERUNGSPFAD"
```

Falls das Updatewerkzeug im Programmordner noch nicht vollständig angekommen ist,
das bereits kopierte Werkzeug aus dem zugehörigen Verzeichnis
`~/wetterstation/.Wetterstation-update-staging/<Version>/pi_update.py`
für denselben Befehl verwenden. Das konkrete Unterverzeichnis trägt zusätzlich
eine zufällige Kennung und bleibt für die Wiederherstellung erhalten.

Wiederhergestellt werden nur die ausgetauschten Programmdateien und das frühere
Widget-Layout. Zähler, Zertifikate und Caches werden niemals aus der Sicherung
zurückgespielt; auch spätere Ort-/Schlüsseländerungen bleiben erhalten. Bei
anderweitig veränderten Programmdateien oder Widget-Layouts hält die
Wiederherstellung an, statt sie ungeprüft zu überschreiben.

**Nicht verwenden:** `prepare_pi_live.cmd` ist für die frühere einmalige
Schlüssel-/Zählermigration gedacht und gehört nicht zu diesem Updateablauf.
