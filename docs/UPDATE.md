# Pi aktualisieren

## Einmalige Einrichtung

1. PC und Pi müssen im Heimnetz sein; am Pi muss SSH eingeschaltet sein.
2. `windows/SSH einmalig einrichten.cmd` starten. Die Einrichtung fragt gegebenenfalls
   nach Windows-Administratorfreigabe für den OpenSSH-Schlüsseldienst.
3. Eine eigene Schlüsselpassphrase eingeben; anschließend gegebenenfalls einmal das
   Pi-Passwort im sichtbaren OpenSSH-Dialog eingeben. Beides niemals in den Chat kopieren.
4. Die Einrichtung prüft danach ausdrücklich eine Anmeldung ohne Passwortdialog.

Bei einem abgebrochenen Verbindungsversuch denselben Starter erneut aufrufen.
Ein vollständig vorhandenes Schlüsselpaar wird wiederverwendet; dieselbe Passphrase
verwenden. Der frühere Bash-Syntaxfehler bei `base64.b64decode` wurde behoben: Das
Registrierungsskript wird nun über SSH-stdin übertragen, ohne verschachtelte
Anführungszeichen. Andere Pi-Schlüssel bleiben erhalten; Wiederholungen legen
keinen doppelten Eintrag für denselben Schlüssel an.

Der eigene Ed25519-Schlüssel liegt unter `%USERPROFILE%/.ssh/`, außerhalb von OneDrive.
Der private Schlüssel bleibt passphrasengeschützt und auf den Windows-Benutzer beschränkt.
Der Windows-Schlüsseldienst speichert die Anmeldefähigkeit für dieses Windows-Konto.
Auf dem Pi wird nur der öffentliche Schlüssel ergänzt; andere Schlüssel bleiben erhalten.
Die Option `restrict` sperrt Weiterleitungen und interaktive Terminals für diesen Schlüssel,
erlaubt aber die für das Update nötigen Befehle und Dateiübertragungen im Benutzerkonto.

Eine bereits bekannte SSH-Geräteidentität ist Voraussetzung. Bei geänderter Identität
bricht die Einrichtung ab; sie akzeptiert und ersetzt keinen Hostschlüssel automatisch.
Das Passwort wird nicht gespeichert. Zielangaben stehen in `private/pi-update.json`.
Beim ersten Aufruf den Hostnamen oder die IPv4-Adresse des Raspberry Pi eingeben.
Der Updater erwartet das Pi-Konto `pi` und den Programmordner
`~/wetterstation/Wetterstation`. Bei einer geänderten Adresse das Feld `host`
anpassen und die bekannte Geräteidentität erneut prüfen. Die historischen CLI-
Transferwerkzeuge verwenden den lokalen SSH-Hostalias `wetterstation-pi`.

Beim ersten Update muss die ältere Pi-Anwendung einmal von Hand geschlossen werden.
Sie unterstützt die neue geordnete Fernbeendigung noch nicht. Das Update startet eine
vorher geschlossene Anwendung nicht; danach einmal das vorhandene Pi-Desktop-Symbol nutzen.

## Künftige Updates

`windows/Pi aktualisieren.cmd` doppelklicken. Das Fenster zeigt den Fortschritt.
Während der Arbeit steht ausdrücklich „Update läuft“ im Fenster. Nach Erfolg
erscheinen „Update abgeschlossen“, ein vollständig gefüllter grüner Balken und
„Fertig. Du kannst dieses Fenster jetzt schließen“. Bei Fehlern steht stattdessen
rot „Update mit Fehler beendet“ mit dem konkreten Hinweis und ohne grünen Balken.
„Fenster schließen“ wird nach jedem Endzustand freigegeben. Sicherungspfad und
Programm-Laufzustand stehen unterhalb des Abschlusshinweises.
Eine zweite Aktualisierung desselben Arbeitsordners wird gesperrt. Der Updater hat
weder Autostart noch Zeitplan; nur der separat eingerichtete Schlüsseldienst startet mit Windows.

Es wird eine getrennte Kopie der aktuellen Programm- und Testdateien angelegt, ohne
private Daten. Änderungen während des Kopierens führen zum Abbruch. Änderungen nach
dem Kopieren gehören erst zum nächsten Update. Die Offline-Tests prüfen diese Kopie;
derselbe Stand wird paketiert und übertragen. Der Bericht liegt unter
`build/reports/last-update-tests.txt`, das geprüfte Paket unter `build/pi/`.

Vor dem Beenden der Anzeige werden Ziel, Bibliotheken, Speicher und Programmidentität
geprüft und sämtliche benötigten Dateien übertragen. Nur die eindeutig identifizierte
Wetterstation wird geordnet beendet. Kein erzwungenes Beenden bei Zeitüberschreitung.
Es folgen Sicherung, Installation, Prüfsummenvergleich und Offline-Prüfung auf dem Pi.
Ort, Land, API-Schlüssel, Zertifikate, Caches, Gerätekennung, Zähler und Pi-Widget-Layout
werden nicht vom PC importiert oder zurückgesetzt.

Eine zuvor laufende Anwendung startet im bisherigen Modus und in derselben
Desktopsitzung wieder. Der neue Prozess muss seine Bereitschaft bestätigen.
Dies bestätigt den Programmstart, nicht den Erfolg externer Wetterdienste.
Ein Livestart kann echte Wetterabrufe auslösen; eine zuvor geschlossene Anwendung bleibt geschlossen.
Handy-Sitzungen enden durch den Programmneustart; Browser melden sich mit einem neuen Displaycode an.

## Fehler und Wiederherstellung

Bei Installations- oder Offline-Prüffehlern stellt der Installer die vorherigen
Programmdateien wieder her. Nach einem fehlgeschlagenen Update wird nichts automatisch
gestartet. Bei Wiederstartfehlern bleibt die neue, geprüfte Version installiert; das
Fenster meldet ausdrücklich, dass der Start nicht bestätigt werden konnte.

Bei Verbindungsabbruch während der Installation ist der Zustand zunächst unbekannt.
Am Pi nachsehen, bevor ein weiterer Versuch gestartet wird. Die Startsperre
`.pi-update-in-progress.json` niemals einfach löschen. Sie nennt die Sicherung.

Sicherungen liegen außerhalb des Programmordners unter
`~/wetterstation/Wetterstation-Backups/<Zeitstempel>/installation/`.
Sie enthalten vertrauliche Pi-Daten und gehören nicht auf GitHub.

Auf dem Pi mit dem konkreten Sicherungspfad:

```sh
python3 pi_update.py restore --target "$HOME/wetterstation/Wetterstation" --backup "KONKRETER_SICHERUNGSPFAD"
```

Falls das Programmwerkzeug beschädigt ist, das standalone `update.py` aus dem passenden
Unterordner in `~/wetterstation/.Wetterstation-update-staging/` verwenden.
Die Wiederherstellung setzt keine Zähler, Zertifikate oder neueren privaten Änderungen zurück.
Bei Rückkehr zu einem Stand vor der Umordnung werden auch die gesicherten alten
Programmdateien wiederhergestellt. Alte Sicherungen von früheren Updater-Versionen
werden mit dem jeweils dazugehörigen damaligen Stand des Werkzeugs wiederhergestellt.

Am 28.10.2026 wurden Schlüsselanmeldung, gesicherte Übernahme, geordnetes Beenden
und Wiederstart in der tatsächlichen Pi-Desktopsitzung mit der Widget-Demo geprüft.
Display und Handy-Anordnung wurden anschließend vom Nutzer als flüssig und
funktionierend bestätigt. Ein fehlendes optionales ImageTk wurde ohne
Paketinstallation durch native Tk-PNG-Bildübernahme abgefangen; Details und
Messbelege unter [OPTIMIZATION.md](OPTIMIZATION.md). Weiterhin nicht durch diese
Demo-Abnahme bestätigt: Anmeldung nach Windows-Neustart und Wiederstart im Livebetrieb.
