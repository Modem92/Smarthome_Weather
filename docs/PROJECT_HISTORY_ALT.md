# Abgleich der zusätzlichen Projektplanfassung

Historische Abweichungen aus PROJEKTPLAN-ALEXCOMPI.md, am 28.10.2026 gesichert.
Diese Sammlung erteilt keine neuen Freigaben. Aktuelle Entscheidungen stehen in PROJEKTPLAN.md.

- Der Nutzer bestätigt den bestandenen Offline-Funktionstest auf dem Pi und
  gibt anschließend ausdrücklich den ersten Liveabruf frei. Er bestätigt ferner,
  dass die Wetterprogramme auf PC und Pi für die Übernahme geschlossen sind.
  Die bestehende Installation wird mitsamt Zählerkennung, Historie und lokalem
  Prüfspeicher umgezogen. Die PC-Livevorschau soll während des Pi-Livebetriebs
  geschlossen bleiben; getrennte Kopien besitzen keinen gemeinsamen Sperrmechanismus.
- Der Nutzer gibt zusätzlich ein System-/Paketupdate des vorhandenen Pi frei.
  Gemeint ist die Aktualisierung der bestehenden Installation; eine Neuinstallation
  oder ein Wechsel der Betriebssystem-Hauptversion ist damit nicht beauftragt.
  Gemeldet: Python 3.11.2, ARM64/aarch64, python3-tk 3.11.2,
  Debian-Pillow 9.4.0 und cryptography 38.0.4 vor der Updateprüfung; deren Ergebnis
  ist unter „Umgesetzt“ dokumentiert.
- Nach dem erfolgreichen Demotest hat der Nutzer ausdrücklich die Einrichtung
  des Livebetriebs mit echten Wetterdaten und Regenkarte auf dem Pi freigegeben.
  Vor dem ersten Abruf sind Abhängigkeiten, Schlüsselbereitstellung und der
  geschützte Gerätezähler zu prüfen; vorhandene PC-Zähler bleiben erhalten.
- Der Nutzer möchte das Programm auf seinen Raspberry Pi übertragen. Er nennt
  Raspberry Pi 3 Model A Plus und Debian 12 Bookworm mit Desktop. Der erste Test
  soll mit gekennzeichneten Beispieldaten ohne echte Wetterabrufe erfolgen.
  Pi und PC sind im selben Heimnetz; SSH wurde am Pi vom Nutzer gestartet.
- Am 19.10.2026 beauftragt: Fehler „Kartenabruf oder Bildprüfung fehlgeschlagen;
  kein gültiger Karten-Cache“ in der Regenkarte beheben. Öffentliche BKG-/DWD-
  Kartenabrufe sind dafür freigegeben; keine weitere OpenWeather-Liveprüfung.
- Am 19.10.2026 freigegeben: Alle vier Ansichten und beide PC-Einstellungsdialoge
  für das vorhandene Display mit 1024 × 600 Pixeln anpassen. Start im Vollbild,
  F11 wechselt zum veränderbaren Fenster. Anzeigen, Texte und Bedienelemente
  skalieren mit; bei schmaler Fläche werden Karten neu angeordnet und bei Bedarf
  vertikal gescrollt. Die Handy-Webseite bleibt unverändert. Keine zusätzlichen
  Abrufe durch Größenänderungen; Fokus und Eingabeentwürfe bleiben erhalten.
- Zuerst am Windows-PC mit einem virtuellen Display entwickeln.
- Python ist die Basis für die Vorschau und die zunächst einheitliche Anwendung.
- Als spätere Hardware ist ein Raspberry Pi unter Linux vorläufig vorgesehen;
  Steckdosenversorgung ist gewählt. Sparsamere Alternativen bleiben möglich.
- Das vorhandene LCD soll nach der PC-Vorschau getestet werden. Ein E-Ink-Display
  kommt erst später infrage; Modell und Auflösung sind nicht ausgewählt.
- Das spätere Gerät soll Internet-Wetterdaten und eigene Außensensoren verbinden.
- Ein OpenWeather-Schlüssel soll in den Programmeinstellungen eingegeben werden;
  eine Windows-Umgebungsvariable ist dafür nicht nötig. Der gesamte
  Wetterstation-Projektordner einschließlich unverschlüsselter Einstellungen darf
  auf ausdrücklichen Wunsch des Nutzers über OneDrive synchronisiert werden.
  Der Nutzer hat einen Schlüssel eingegeben und gespeichert.
- Auf weiteren Computern soll derselbe projektrelative Pfad gelten; OneDrive
  synchronisiert den Projektordner. Python muss dort verfügbar sein.
- Für die Vorschau wurde ein deutscher Beispielort festgelegt.
- Der Ort soll am Gerät änderbar sein und später Wetter- und Kartendaten gemeinsam
  steuern. Ein Ortswechsel darf alte Daten nicht dem neuen Ort zuordnen.
- Für die Wetterübersicht, Vorhersage, Regenkarte und eigene Sensorwerte sind
  getrennte Ansichten gewünscht. Der Ansichtswechsel ist zunächst manuell.
- Zuerst wird ein funktionales Grundgerüst entwickelt. Grundlegende Bedienbarkeit,
  Lesbarkeit und klare Kennzeichnung von Sperren/Fehlern gehören dazu; endgültiges
  visuelles Design und spätere E-Ink-Anpassungen folgen erst nach den Funktionstests.
- Innerhalb ausdrücklich beauftragter Features darf die technische Umsetzung
  selbstständig gewählt werden. Neue Features und Kontoaktionen sind davon nicht
  umfasst. Die aktuelle Oberfläche ist eine Testvorschau; die endgültige UI/UX
  gestaltet der Nutzer später mit eigenen Ideen.
- Am 18.10.2026 wurde die einmalige Live-Prüfung der bestehenden One-Call-4.0-
  Anbindung für den damaligen Testort mit unveränderter lokaler API-Begrenzung beauftragt.
- Datenaufbewahrung ist für spätere Analyse gewünscht; eine konkrete Lösung ist
  noch nicht festgelegt.
- Am 18.10.2026 freigegeben: Fehlerbehandlung für Wetter, lokale Dateien,
  Budget und Karten verfeinern und simulierte Fehlerfälle prüfen. Dazu gehören
  Anfragepausen, validierte Antworten, begrenztes Cachealter und die zuverlässige
  Freigabe der Bedienung nach Fehlern.
- Die Luftbild-Grundkarte der Regenkarte für den Testort wird durch eine einfache,
  stilisierte amtliche Karte ersetzt. Öffentliche, schlüsselfreie Abrufe und
  projektbezogener Cache für diesen Kartenausschnitt sind dafür freigegeben.
- Der Nutzer hat den Hinweisblock unten im Kartenbild abgewählt. Die Kartenfläche
  bleibt frei. Anschließend wurde ausdrücklich auch das Ausblenden der Quellenzeile
  in der privaten PC-Vorschau gewünscht. Quellen und Lizenzangaben bleiben in der
  Dokumentation; eine rechtliche Ausnahme ist damit nicht bestätigt.
- Mobile Einstellungen sind nun freigegeben: Eine Handy-Seite im selben Heimnetz
  soll sowohl den Ort als auch den OpenWeather-Schlüssel speichern/ersetzen können.
  Zugangscode und verschlüsselte lokale Übertragung schützen den Zugriff; der
  gespeicherte Schlüssel wird nie zurückgegeben. Die PC-Vorschau übernimmt die
  gespeicherten Einstellungen. Keine öffentliche Bereitstellung oder Kontoaktion.
- Auf Wunsch vom 18.10.2026 wird die Regenkarte für alle eindeutig aufgelösten
  Orte innerhalb Deutschlands freigegeben, einschließlich der öffentlichen
  WMS-Abrufe und des ortsbezogenen Caches. Ausland ist vorerst ausgeschlossen.
- Die eingeschaltete Handy-Verbindung soll beim Schließen des Verbindungsdialogs
  weiterlaufen und erst durch „Ausschalten“ oder Beenden der Vorschau enden.
- Der Nutzer wünscht die Aufhebung der angezeigten zusätzlichen Startsperre
  und einen Tageswechsel des sichtbaren Zählers um 00:00 Uhr deutscher Zeit.
  Der bestehende Schutz gegen mehr als 999 Abrufe im OpenWeather-Anbietertag
  bleibt zusätzlich erhalten. Der anschließende Start der aktualisierten
  Vorschau einschließlich echter Wetterabrufe wurde ausdrücklich freigegeben.
- Regenkarte: zusätzlich alle 15 Minuten im Hintergrund aktualisieren, auch
  wenn eine andere Seite ausgewählt ist. Geöffnet bleibt der Fünf-Minuten-Takt;
  beim Öffnen ab fünf Minuten seit dem letzten Abrufversuch zeitnah nachladen.
- Die zusätzlichen Quellenzeilen „One Call 4.0“ unter Luftfeuchte, Wind und
  Luftdruck in der Wetterübersicht sollen entfallen.
- Die erneut gemeldete Startsperre über den gewohnten Starter ist zu beheben;
  vorhandene Zählerstände und die Begrenzungen bleiben erhalten.
- Das Ortsfeld muss den Tastaturfokus bei einem Klick außerhalb wieder abgeben,
  damit Pfeiltasten anschließend die Ansichten wechseln. Enter übernimmt den
  Ort und verlässt das Feld; Escape verlässt es ohne Übernahme des Entwurfs.
- Regenkarte über die gesamte Innenfläche des Programmfensters: ohne Kopfzeile,
  Ortsfeld, Seitenleiste, Legende oder Fußzeile. Ein dezenter Ortsmarker bleibt;
  Statushinweise erscheinen nur bei Problemen. Escape führt zur Wetterübersicht,
  F5 aktualisiert manuell. Größenänderungen lösen keine zusätzlichen Abrufe aus.

- Am 26.10.2026 vom Nutzer nach Test am aktualisierten Pi gemeldet, für die
  nächste gemeinsame Bearbeitung vorgemerkt (gewünscht: morgen, 27.10.2026):
  hohe CPU-Spitzen beim Ansichtswechsel. Besonders beim ersten Durchwechseln
  nach Programmstart von Seite 1 über 2 und 3 zur vierten, vom Nutzer als
  Demo-Seite bezeichneten Ansicht hängt die Oberfläche mehrere Sekunden.
  Nutzerbeobachtung, noch keine eigene Reproduktion oder Pi-Leistungsmessung.
  Ziel: Ursache ermitteln und Seitenwechsel auf dem Pi spürbar flüssiger machen,
  insbesondere ohne mehrsekündige Blockade beim ersten Besuch einer Seite.
  Später ersten und wiederholten Seitenwechsel getrennt messen; Aufwand für
  Darstellung/Schriftanpassung, erstmalige Vorbereitung/Caches und Hintergrund-
  arbeiten untersuchen. Den lokalen Handy-/HTTPS-Server ausdrücklich als
  mögliche, unbestätigte Ursache prüfen: Vergleich mit/ohne Server sowie ohne
  verbundenen Browser und bei aktiver Handynutzung. Erst anhand der Messungen
  entscheiden, ob Optimierung genügt oder die Handy-Anbindung anders aufgebaut
  werden sollte; keine vorweggenommene Abschaffung ihrer Funktionen.
  Frühere schnelle PC-Messungen sind kein Nachweis für die aktuelle Pi-Leistung.
  Bestehende Einstellungen, Layouts, Abrufraster und Budgetschutz erhalten;
  Diagnose möglichst mit Beispieldaten ohne zusätzliche Wetterabrufe.
  Status: Problem und gewünschte spätere Optimierung aufgenommen; heute keine
  Programmänderung, Pi-Diagnose, Übertragung oder Architekturänderung beauftragt.

- Eine Reliefkarte mit Höhenlinien ist nicht umgesetzt; gewählt ist zunächst
  die helle farbige amtliche Straßenkarte nach Bildreferenz ohne Luftbild.
- Endgültige Hardware, Eingabetasten und Stromsparanforderungen. Die Auflösung
  des vorgesehenen vorhandenen Displays ist mit 1024 × 600 Pixeln bestätigt.
- Erneute Alltagsprüfung der Handy-Verbindung nach Schließen des PC-Dialogs;
  der Nutzer hat den ersten Zugriff vom persönlichen Handy als funktionierend bestätigt.
- Konkrete Tarif-/Billing-Einstellungen des Nutzerkontos wurden nicht geprüft.
  Der Nutzer berichtet, das separate One-Call-Abo aktiviert und dessen Limit auf
  1000 pro Tag (aktuelle Mitteilung vom 23.10.2026) gesetzt zu haben; eine Kontoänderung wurde nicht vorgenommen.
  OpenWeather dokumentiert ein produktspezifisches Tageslimit und Reset zwischen
  00:00–00:05 UTC. Der Live-Zugriff wurde am 18.10.2026 erfolgreich geprüft;
  daraus folgt keine unabhängige Bestätigung der Kontogrenze.

