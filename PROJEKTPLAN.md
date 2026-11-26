# Projektplan Wetterstation

Dieses Dokument ist die kompakte, fortzuschreibende Kontextquelle für Folgearbeit.
Änderungen am Projekt werden nach den untenstehenden Status getrennt. Eine
notierte Idee ist keine Freigabe zur Implementierung.

## Bestätigt

- Am 26.11.2026 wurde die Veröffentlichung der bereinigten Projektfassung
  in einem öffentlichen GitHub-Repository beauftragt. Gerätespezifische Werte,
  private Daten und die bisherige lokale Git-Historie bleiben lokal.

- Am 28.10.2026 freigegeben: OneDrive-/Pi-Optimierung gemäß Chatplan. Aktive
  Designer-Laufzeit geprüft außerhalb OneDrive verlagern; temporäre Prüfkopien
  auslagern und alte Ausgaben erst nach Archivprüfung bereinigen. Private Daten
  erhalten. HTTPS jederzeit erreichbar, Browser nur für Position, Größe und
  Seitenzuordnung; Berechnung im Browser, Übertragung nach fertiger Geste,
  Ruhepause nach 60 Sekunden. Ereignisgesteuerte Anmeldung, weniger permanente
  Schreibzugriffe, begrenzte Hintergrund-Bildvorbereitung und 32-MiB-Bildcache.
  Offline-Abnahme vor gesicherter Pi-Übernahme und Vorher-/Nachher-Messung.

- Am 28.10.2026 beauftragt: Seitenraster hinter Widgets zeichnen und Spalten/Zeilen
  nach bestätigter Eingabe direkt übernehmen; Vorlagen gemeinsam, Rückgängig,
  Schutz vor veralteten Qt-Ereignissen und bestehende Handy-Kompatibilität erhalten.
  Nur isolierte Offline-Abnahme, keine Wetterabrufe oder Pi-Übertragung.

- Am 28.10.2026 beauftragt: unsichtbare Rechtecke/Ellipsen korrigieren, sichtbare
  neue Formen eindeutig auswählen, Minusknöpfe pro Inhalt unter Beibehaltung
  geschützter Datenblöcke und Mausradsperre gegen unbeabsichtigte Wertänderungen.
  Nur Offline-Umsetzung und isolierte Abnahme, keine Pi-Übertragung/Liveabrufe.

- Am 27.10.2026 anschließend als Arbeitsziel beauftragt: grafischer Editor gemäß
  abgestimmtem Plan mit acht Größenanfassern, direkter Inhaltsauswahl, gemeinsamer
  Innenrasterweite (8 Displaypixel als Vorgabe), proportionaler Anpassung,
  Inhaltsausrichtung und moderner heller/dunkler Oberfläche. Strukturierte Daten
  bleiben verschiebbare Inhaltsblöcke, normale Widgets behalten ihren Typ.
  Gestaltungsformat 4 mit Erhalt älterer Layouts und der Handy-Anordnung.
  Nur Umsetzung und isolierte Offline-Abnahme, keine echten Wetterabrufe oder
  reale Pi-Übernahme.

- Am 27.10.2026 beauftragt: Designer-Absturz nach „Änderung nicht übernommen,
  Widget liegt außerhalb des Rasters oder ist zu klein“ beheben. Ungültige
  Eingaben müssen den letzten gültigen Entwurf erhalten und weitere Bedienung
  ermöglichen. Nur lokale Offline-Prüfung, keine Wetterabrufe oder Pi-Übernahme.

- Am 27.10.2026 anschließend ausdrücklich freigegeben: zusätzliche Zeitreihen
  im normalen Programmablauf fertig anbinden, jedoch erst nach ausdrücklicher
  Aktivierung im Konfigurator für das jeweilige Gerät abrufen. Entwicklung und
  Abnahme bleiben ohne echte Wetterabrufe. Die Antwort „Mit ausdrücklicher
  Aktivierung fertigstellen“ ersetzt die zuvor offene Freigabe dieser Anbindung;
  sie aktiviert keine Zusatzabrufe auf PC oder Pi durch die Entwicklung.

- Am 27.10.2026 als aktives Arbeitsziel beauftragt: Wetterstation-Designer gemäß
  `docs/DESIGNER.md` und dem abgestimmten Chatplan umsetzen. Windows-Konfigurator
  mit getrennten Tabs für schnelle Anordnung und erweiterte Gestaltung; variable
  Raster, Quer-/Hochformatvarianten, Stile, eigene Inhalte/Bilder/Schriften und
  frei konfigurierbare echte Zeitreihen. Die Handy-Anordnung bleibt erhalten und
  muss sämtliche PC-Gestaltungseigenschaften bewahren; kein neuer erweiterter
  Handy-Gestaltungseditor nötig. Bisherige drei Wetteranfragen alle fünf Minuten
  und Budgetschutz erhalten; Zusatzreihen nur mit berechnetem freien Budget und
  Reserve. Entwürfe automatisch sichern, Anwendung/SSH-Übernahme ausdrücklich
  auslösen. Umsetzung und Abnahme zunächst isoliert/offline, keine neuen realen
  Wetterabrufe oder erste Pi-Übernahme durch die Entwicklung. Dieser Auftrag
  konkretisiert den früher nur vorgemerkten Gestaltungseditor; ein E-Ink-Treiber
  bleibt außerhalb des Umfangs.

- Am 26.10.2026 ausdrücklich beauftragt: missverständliches Windows-Updatefenster
  korrigieren. Laufender Vorgang, erfolgreicher Abschluss und Fehler müssen sofort
  unterscheidbar sein; nach Erfolg kein stehen gebliebener unbestimmter Balken.

- Am 25.10.2026 nach gemeinsamer Planung ausdrücklich beauftragt: OneDrive-Ordner
  nach gemeinsamem Programmkern, Windows-/Pi-Startern, Werkzeugen, Tests, Dokumentation,
  erzeugten Paketen und Archiven ordnen; vorher vollständige Sicherung. Privaten
  Speicher und beide Budgetpfade erhalten. GitHub nur vorbereiten, kein Remote/Upload.
  Manueller Doppelklick-Updater mit eingefrorenem aktuellem Quellstand und isolierter
  Offline-Prüfung; vollständige Bereitstellung vor geordnetem Beenden, Pi-Sicherung,
  Installation und Offline-Prüfung, Wiederstart nur bei zuvor laufender Anwendung
  im bisherigen Demo-/Live-Modus. Pi-Layout und sonstige private Daten erhalten.
  Einmalige SSH-Schlüsseleinrichtung mit Windows-Schlüsseldienst, Passphrase und
  gegebenenfalls Administratorfreigabe; danach keine Passwortdialoge im Update.
  Diese Freigabe ersetzt für diesen Ablauf die frühere Vorgabe ohne Wiederstart.
  Keine automatischen Betriebssystem-/Bibliotheksupdates und kein Updater-Autostart.
  Ältere Pi-Version für die Erstmigration einmal manuell schließen.

- Am 24.10.2026 nach Bildanmerkung beauftragt: acht Stunden und fünf Tage je
  Vorhersage immer in einer einzigen Reihe gleich breiter Spalten. Gemeinsame
  Zeilenpositionen, dünne senkrechte Trennlinien ausschließlich zwischen den
  Vorhersagespalten; keine inneren Linien in anderen Widgets. Alle Widget-Titel,
  Werte, mehrzeiligen Texte und eigenen Karten-/Demo-/Hinweisbeschriftungen
  horizontal zentrieren. Dunkelgraue Widget-Rahmen bei 1024×600 zwei Pixel dick,
  auf größeren Anzeigen mitskalieren. Alle gewählten Daten vollständig erhalten
  und innerhalb dieser Vorgaben möglichst groß einpassen. Handy-Vorschau übernimmt
  stärkere Rahmen und zentrierte Widget-Beschriftungen. Layout, Größen, Zeitzonen,
  API-/Speicherformat und Anmeldung unverändert. PC-Umsetzung und Offline-Abnahme
  mit Dummy-Speicher; kein Liveabruf und keine Pi-Übertragung.

- Am 24.10.2026 nach Bildanmerkungen und gemeinsamer Planung beauftragt:
  passive weiße Displayanzeige ohne Aktualisieren-/Einstellungstasten, lokale
  Orts-/Länderfelder, Übernehmen-Knopf, obere Abrufzeit, Ortsstatus und Fußzeile.
  Vollständige Fensterfläche nutzen, Widget-Raster und gespeichertes Layout
  erhalten, Inhalte anhand tatsächlicher Textmaße möglichst groß und kontrastreich
  einpassen. Handy-Vorschau mit derselben Displaygeometrie. HTTPS startet automatisch
  im Heimnetz; Browser fordern eigene Einmalcodes an, die nur auf einer eigenen
  Verbindungsseite am Display erscheinen und nach Anmeldung oder zwei Minuten
  verschwinden. Vier Anfragen in Warteschlange, acht parallele Browser, Sitzungen
  bis Abmeldung oder Programmneustart; alles ausschließlich im Arbeitsspeicher.
  Bedienung ohne Bestätigung am Gerät. Schutzmechanismen und automatische Abrufe
  erhalten. Diese Freigabe ersetzt lokale Einstellungen, manuelle Handy-Aktivierung
  und die 20-Minuten-Sitzungen. PC-Umsetzung mit Dummy-Abnahme; kein Pi-Transfer,
  normaler Live-Start, OpenWeather-Abruf oder E-Ink-Treiber.

- Am 24.10.2026 beauftragt: internationale Ortsauswahl und Regenkarte. PC und
  Handy erhalten ein durchsuchbares Land mit deutschen Namen und ISO-Kennung;
  Ort/Land gemeinsam speichern und übernehmen, vorhandenen Schlüssel und das
  Widget-Layout erhalten. Alte deutsche Eingaben bleiben DE, erkennbare Länder
  übernehmen; unbekannte alte Länder verlangen eine Auswahl. Geocoding auf das
  gewählte Land begrenzen, internationale Postleitzahlen und Mehrdeutigkeit prüfen.
  Wetter-/Ortscache und verspätete Ergebnisse nach Ort/Land trennen. Deutschland
  behält BKG/DWD; Ausland nutzt deckungsgleiche OSM-/RainViewer-Kacheln mit Zoom 7,
  Abdeckungsmaske, sichtbaren Quellen und regelkonformem bedarfsgerechtem Cache.
  RainViewer-Beobachtungen alle zehn Minuten, Prüfung im bestehenden Fünf-Minuten-
  Raster; gleiche Bilder wiederverwenden. Fehlende Versorgung kenntlich machen,
  gültige Karte desselben Orts bei Ausfall nach bisherigen Altersgrenzen behalten.
  Regenzug-Pfeile nur für DWD. Ortszeit samt Sommerzeit/Datum aus Wetterdaten,
  bei unbekannter Zeitzone gekennzeichnete UTC; Raster und Budgettage unverändert.
  einen deutschen Beispielort, Wien, Paris, London, New York und Tokio offline simulieren; PC bei
  1024×600 und Handy visuell prüfen. Diese Freigabe ersetzt die historische
  Beschränkung auf Deutschland. Kein OpenWeather-Livetest, normaler Programmstart,
  Pi-Transfer, neues Konto oder kostenpflichtiger Dienst.

- Am 24.10.2026 beauftragt: Handy-Verbindung am Pi reparieren. Nutzer bestätigt
  eine angezeigte `127…`-Adresse. Aktive Linux-IPv4-Schnittstellen statt nur
  Rechnernamen auslesen; keine Loopback-Auswahl für das Handy. Erkennung im
  Hintergrund, bei fehlender Heimnetz-Adresse kein Start. Offline prüfen und
  Reparaturpaket ohne PC-Layoutimport vorbereiten. Sichere Pi-Übernahme mit
  Sicherung und geschlossener Anwendung; anschließend Widget-Demo und Handy prüfen.
  Keine automatischen Live-Starts, Wetterabrufe oder Firewall-/Routeränderungen.

- Am 24.10.2026 gewünscht: echtes Programm über ein Desktop-Symbol am Pi starten.
  Verknüpfung auf den bestehenden Live-Starter anlegen, vorhandene Einstellungen
  und Zähler verwenden. Keine automatische Ausführung durch die Einrichtung.

- Am 24.10.2026 anschließend ausdrücklich beauftragt: vorbereiteten Transfer
  auf den bestehenden Pi beginnen. Zielprüfung, Sicherung, Programm-/Layoutupdate
  und Offline-Prüfung sind freigegeben; kein automatischer Live-Start. Der Nutzer
  bestätigt nach Aktivierung von SSH erneut die Heimnetzadresse des Pi.

- Am 24.10.2026 beauftragt: vollständigen aktuellen Pi-Transfer vorbereiten,
  einschließlich Widget-Seiten, Handy-Editor, Kartenfunktionen und gespeichertem
  PC-Widget-Layout. Separates geprüftes Programmarchiv ohne private Daten,
  Layout separat unter `private/`, neuer Update-Starter und Wiederherstellungsweg.
  Bestehende Pi-Einstellungen, Schlüssel, Zertifikate und beide Zählerspeicher
  erhalten. Späteres Update nur nach Ziel-/SSH-/Prozessprüfung und lokaler
  Pi-Sicherung; bei Fehlern kein Programmstart. Python-3.11-Syntax und simulierte
  Updates prüfen, Offline-Vorabprüfung erweitern, Linux-Widget-Demo bereitstellen.
  Diese Vorbereitung umfasst keine Verbindung, Übertragung oder Neustarts am Pi.

- Am 24.10.2026 nach gemeinsamer Planung beauftragt: Widget-Seiten für alle
  vorhandenen Anzeigedaten, einzeln und kombiniert. Vier bearbeitbare Startseiten
  (Übersicht, Vorhersage, Regenkarte, Sensoren), weitere Seiten anlegen, benennen,
  umsortieren und entfernen; mindestens eine Seite erhalten. Festes 12×8-Raster
  je Seite, vollständig auf 1024×600 ohne Scrollen. Widgets hinzufügen/entfernen,
  mehrfach verwenden, zwischen Seiten verschieben, am Raster ziehen und in
  Breite/Höhe aufziehen. Nachbarn kollisionsfrei umordnen; bei Platzmangel letzte
  passende Anordnung erhalten und andere/neue Seite anbieten. Inhalte pro
  Widget einzeln ein-/ausblenden, ohne seine Größe zu verändern (z. B. Uhr/Datum).
  Bearbeitung vollständig über die vorhandene geschützte Handy-Schnittstelle;
  Layout dauerhaft im privaten Projekt speichern. Direkte Übernahme nach fertigen
  Gesten und Inhaltsauswahl, kein Übernehmen-Knopf. Rückgängig für 20 Schritte.
  Seitenwahl im Handy-Editor zeigt dieselbe Seite am Gerät, dort weiterhin nur
  manueller Wechsel per Pfeiltasten. Bestehende Schutzregeln erhalten; konkurrierende
  Sitzungen und Verbindungs-/Speicherfehler sichtbar behandeln.
  Ruhige, minimalistische Gestaltung in Richtung Apple; zuerst Funktionalität,
  endgültige Gestaltung gemeinsam weiterentwickeln. Alle vorhandenen Wetter-,
  Vorhersage-, Karten- und Demo-Sensordaten anbieten; keine neue Datenanbindung.
  PC-Umsetzung und Offline-Prüfung, keine Liveabrufe oder Pi-Übertragung.

- Am 23.10.2026 freigegeben: geschätzten Regenzug aus zwei DWD-Radaraufnahmen
  durch höchstens drei dezente, unbewegte Pfeile darstellen. Keine Bodenwind-
  Ersatzwerte, Geschwindigkeitsanzeige oder zusätzliche Legende. Beim Start,
  Ortswechsel und nach längeren Unterbrechungen nötigenfalls ein fünf Minuten
  älteres Radarbild im Hintergrund nachladen, vorhandene Aufnahmen bevorzugen.
  Keine zusätzlichen Grundkarten-/OpenWeather-Anfragen oder Abhängigkeiten.
  Neue Karte ohne Warten auf die Analyse anzeigen; schnelle Seitenwechsel,
  Fünf-Minuten-Raster, Ortsmarker und Zeit-/Knopffeld erhalten. Offline-Umsetzung
  im PC-Workspace; keine Pi-Übertragung oder Pi-Leistungsmessung.

- Am 23.10.2026 ausdrücklich beauftragt: Regenkarte entsprechend Bildreferenz
  und ausführlicher Beschreibung gestalten. Weiche organische Niederschlagsflächen,
  breite transparente Ränder, fließende Farben von Blau/Lila über Türkis/Grün bis
  Gelb, durchscheinende Karte. Helle farbige Straßenkarte mit blassgrüner Landschaft,
  orange-gelben Hauptstraßen und grauen Beschriftungen ersetzt die frühere graue
  Kartendarstellung. Ausgewählter Ort als weißes abgerundetes Namensschild und
  orangefarbener Punkt mit weißem Ring oberhalb des Radars. Kein fester Ort Hamburg;
  Auswahl, Abrufzeitfeld, Fünf-Minuten-Raster und schneller Seitenwechsel erhalten.

- Am 23.10.2026 ausdrücklich freigegeben: Regenkarte auf allen Seiten im selben
  festen Fünf-Minuten-Raster wie Wetter aktualisieren (00:00, 00:05 usw., deutsche
  Zeit). Dies ersetzt den bisherigen 5-/15-Minuten-Takt und das Nachladen beim
  Seitenwechsel. Startabruf erhalten; manuelle Abrufe verschieben das Raster nicht.
  DWD/BKG bleiben unabhängig vom unveränderten 1000er-OpenWeather-Zähler.
- Infofeld ausdrücklich unten rechts gewählt: Abrufzeit der angezeigten Karte
  (heute Uhrzeit, sonst Datum/Uhrzeit) und kleiner Knopf „Aktualisieren“ daneben.
  Bei Fehlern/Cache-Rückfall keine neue Zeit anzeigen; Zeit erst mit fertigem Bild
  übernehmen. Keine angezeigte Karte: „Noch nicht aktualisiert“. F5 und der Knopf
  nutzen denselben Weg, Demo bleibt ohne Abruf. Lokale Offline-Prüfung beauftragt,
  keine Pi-Übertragung oder Neustarts.

- Am 23.10.2026 freigegeben: Verzögerung beim Wechsel zur Regenkarte beheben.
  Fertige Bildpaare wiederverwenden, neue Daten/Größen im Hintergrund vorbereiten,
  ausschließlich Tk-Bilder im UI-Thread anlegen. Gültige vorige Karte während
  der Vorbereitung behalten; überholte Aufträge nach Orts-/Größenwechsel verwerfen,
  höchstens eine Vorbereitung mit einem aktuellen Folgeauftrag. Ortsdaten nach
  dem Dateilesen im Speicher halten. Offline prüfen, keine neuen Abhängigkeiten,
  zusätzlichen Abrufe, Pi-Übertragung oder Pi-Leistungsmessung.

- Am 23.10.2026 ausdrücklich freigegeben: One Call 4.0 mit drei Anfragen pro
  gemeinsamem Wetter-/Vorhersagelauf zu festen Fünf-Minuten-Terminen deutscher
  Zeit (00:00, 00:05 usw.). Beim Start fehlende oder mindestens fünf Minuten alte
  Daten nachladen; manuelle Abrufe verschieben das Raster nicht. Tagesgrenzen
  lokal und beim UTC-Anbietertag auf genau 1000 erhöhen, ohne Zählerhistorie oder
  Prüfspeicher zurückzusetzen. Dies ersetzt die frühere 999er-Vorgabe. Der Nutzer
  bestätigt ein Kontolimit von 1000; dieses wurde hier nicht eingesehen/geändert.
- Wetterübersicht: nur eine Abrufzeit (heute Uhrzeit, sonst Datum und Uhrzeit)
  neben „Aktualisieren“; keine API-Namen, Anfragezahlen, Messzeit oder technischen
  Statuszeilen. Lade-/Fehlerhinweise knapp halten, Demo-Kennzeichnung erhalten.
  Lokale Umsetzung und Offline-Prüfung sind beauftragt; kein Pi-Update/Livestart.

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
- Das vorhandene LCD soll nach der PC-Vorschau getestet werden. Als künftiges
  E-Ink-Ziel ist seit 26.10.2026 das unten vorgemerkte Waveshare-Display mit
  800 × 480 Pixeln benannt; die Anpassung ist noch nicht zur Umsetzung freigegeben.
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

## Umgesetzt

- Optimierung am 28.10.2026 abgeschlossen und vom Nutzer praktisch bestätigt:
  „Passt alles, läuft auch flüssig“. Finaler Stand
  `2026-10-28-optimization-174804`, 389 Offline-Tests bestanden, vollständig
  eingefroren und geprüft übertragen. Geordneter Wiederstart der Widget-Demo
  bestätigt; Pi-Layout nach SHA-256 unverändert, private Daten/Zähler erhalten.
  Finale Sicherung: ~/wetterstation/Wetterstation-Backups/<Zeitstempel>.
  Zehn-Sekunden-Stichprobe der Demo: 21,1 auf 1,1 % eines CPU-Kerns,
  Datenträger-Schreibbytes 65.536 auf 0; RSS 45.324 auf 66.328 KiB.
  Identischer isolierter 1024×600-Renderer: Übersicht erstmals 4031 auf 1163 ms,
  wiederholt 3927 auf 84 ms; Vorhersage erstmals 3691 auf 524 ms, wiederholt
  3640 auf 65 ms. Keine zusätzlichen Providerabrufe. build nach Bereinigung
  und neuen Belegen rund 7,9 MiB statt 341 MiB; alte Belege/Sicherungen archiviert,
  Designer-Laufzeit außerhalb OneDrive. Zwei neueste geprüfte Pakete erhalten.
  Vergleich und Grenzen: docs/OPTIMIZATION.md, Rohbelege unter build/reports/.

- Erste Optimierungsübernahme am 28.10.2026 installierte den mit 387 Tests
  geprüften Stand, Wiederstart der zuvor laufenden Widget-Demo scheiterte aber
  am fehlenden optionalen `PIL.ImageTk` auf Debian. Keine Startsperre verblieben,
  kein laufender Prozess. Sicherung:
  ~/wetterstation/Wetterstation-Backups/<Zeitstempel>.
  Ursache isoliert mit Dummy-Einstellungen reproduziert. Abhilfe ohne neue
  Systempakete: native Tk-PNG-Übernahme als Rückfall, eigener Transparenz-/Farbtest
  und Importprüfung im Pi-Preflight. Geordnetes Schließen wartet außerdem auf
  Bildaufträge und gibt Tk-Ressourcen im Hauptthread frei. Die erneute vollständige
  Offline-Abnahme und korrigierte Übernahme sind vor dem Wiederstart erforderlich.

- Optimierung vom 28.10.2026 lokal umgesetzt: Designer-Laufzeit außerhalb
  OneDrive kopiert, bytegleich und per Qt-Start geprüft; alte Laufzeit entfernt.
  Bekannte Prüfkopien vollständig archiviert und nach erneuter Prüfung entfernt;
  build von rund 341 MB auf rund 10 MB reduziert (vor neuen Abnahmeausgaben).
  Private Daten unangetastet. Zweiten Projektplan bytegleich archiviert und
  abweichende historische Abschnitte unter docs/PROJECT_HISTORY_ALT.md erhalten.
  Zustandsabhängige Laufzeitdatei, ereignisgesteuerte Anmeldung, Browser-Ruhemodus,
  wiederverwendbare Schriftinstanzen/-messungen und begrenzte asynchrone Bild-
  vorbereitung ergänzt. Displaybestätigung erst nach tatsächlicher Übernahme.
  Erste lokale Gesamtprüfung 386 Tests bestanden; Browserabnahmen und 18 Qt-
  Oberflächenprüfungen bestanden. Abschließende eingefrorene Abnahme und reale
  Übernahme noch ausstehend. Pi-Vorherwerte mit vom Nutzer gestarteter alter
  Widget-Demo sowie getrenntem synthetischem Renderer erhoben, keine Providerabrufe.
  Belege und genaue Grenzen: docs/OPTIMIZATION.md.

- Am 28.10.2026 auf Nutzerhinweis: abgeschnittene Minusknöpfe in der Inhaltsliste
  korrigiert. Eigene Inhaltszeilen ohne zusätzliche innere Listeneintrag-Abstände
  und mit ausreichender Höhe; Löschverhalten unverändert.

- Am 28.10.2026: Seitenraster vor den Widgets auf dem Hintergrund gezeichnet.
  Spalten/Zeilen übernehmen bestätigte Eingaben ereignisversetzt direkt; schnelle
  Eingaben werden zusammengeführt, veraltete Inspector-Ereignisse verworfen.
  Vorlagen ändern beide Werte gemeinsam; Alle-Seiten-Auswahl bleibt im Fenster
  erhalten. Proportionale Anpassung, Konfliktmarkierung und Entwurf/Rückgängig
  bleiben erhalten. Kein Formatwechsel und keine reale Übernahme.

- Am 28.10.2026 Formen-Renderer, sichtbare neue Rechtecke/Ellipsen und eindeutige
  Inhaltsauswahl korrigiert. Minusknöpfe löschen gezielt per Inhaltskennung mit
  Undo; geschützte Datenblöcke bleiben gesperrt. Mausradänderungen an Einstellfeldern
  werden verhindert und im Eigenschaftenbereich an dessen Scrollfläche geleitet.
  Gemeinsames Gestaltungsformat 4 unverändert, nur lokale Offline-Abnahme.

- Am 27.10.2026 grafische Designer-Erweiterung lokal umgesetzt: acht skalierungsfeste
  Widget-/Inhaltsanfasser, direkte Auswahl, gemeinsame Innenrasterweite, Alt-Ausnahme,
  Escape-Abbruch, echte Ziehvorschau und gemeinsame Undo-Schritte. Inhaltsflächen und
  Text haben getrennte Ausrichtungsbefehle; strukturierte Reihen und Karten bleiben
  Datenblöcke. Normale Widgets behalten ihren Typ. Format 4, geteilte PC-/Pi-Darstellung
  und Erhalt der Inhaltspositionen bei Handy-Anordnung. Alte Layouts bleiben ohne
  grafische Änderung auf ihrem bisherigen Renderweg. Moderne helle/dunkle Oberfläche
  mit Vektorsymbolen und Systemschrift. Verbindlicher Zusatzauftrag unter
  `docs/GRAPHICAL_DESIGNER_SPEC.md`; Bedienung und Prüfwege unter `docs/DESIGNER.md`.
  Die Rastermeldung nach einer Verbindungsseite wird auch bei wiederverwendetem Bild
  aktualisiert. Keine realen Wetterabrufe oder Pi-Übertragung durch diese Umsetzung.

- Am 27.10.2026 Absturz nach ungültiger Widgetgeometrie reproduziert und behoben:
  Der Eigenschaftsbereich löschte das gerade bediente Eingabefeld noch während
  dessen Qt-Tastenereignis. Beim Neuaufbau werden alte Bedienelemente jetzt
  abgetrennt, ihre Signale gesperrt und erst nach Abschluss des Ereignisses
  freigegeben. Echte Warnungsdialoge mit wiederholten ungültigen Positionen,
  ungültiger Breite und Schrittbedienung geprüft; Entwurf/aktive Einstellungen,
  weitere gültige Eingaben, Undo/Redo und Anwenden bleiben funktionsfähig.
  Derselbe Ablauf besteht im nativen Windows-Fenster; Regressionstest unter
  `tests/designer_ui_check.py`. Keine privaten Einstellungen oder Pi-Daten geändert.

- Am 27.10.2026 PC-Designer lokal umgesetzt: zwei Tabs, variable Seitenraster,
  getrennte Displayvarianten und Ausgabedrehung, vererbbare Gestaltungsregler,
  eigene Inhalte/Bilder/Schriften, automatische Entwurfssicherung, Import/Export
  und eine manuelle Gestaltungstransaktion für den Pi. Handy-Anordnung über
  gezielte Befehle einschließlich Erhalt der Gestaltungsdetails beim Undo.
  Gemeinsamer Pillow-Renderer; laufende Uhren ersetzen nur ihren Bildausschnitt.
  Übertragungskennung und Paket bleiben auch nach Schließen des Dialogs erhalten;
  getrennte Upload-Datei wird erst nach Prüfung atomar bereitgestellt. Fortsetzen
  verwendet dieselbe Kennung, bestätigte Übernahmen werden nicht erneut installiert.
  Zusätzliche Zeitreihen sind mit simulierten Antwortdaten geprüft und in den
  regulären Wetterzyklus eingebunden. Eine getrennte Gerätefreigabe bleibt
  standardmäßig aus; PC-Menü und Pi-Übertragungsdialog bieten ausdrücklich
  bestätigte Aktivierung und Ausschalten. Vollständige ohnehin geladene erste
  Stunden-/Tagesseiten werden wiederverwendet, weitere Seiten schützen beide
  Budgettage und die Reserve. Zwischenspeicher bleiben nach Ort/Land getrennt.
  Neue echte
  Wetterabrufe und die erste Pi-Übernahme bleiben gesondert abzunehmen. Anleitung,
  Belegpfade und genaue Grenzen unter `docs/DESIGNER.md`; unveränderter Auftrag
  unter `docs/DESIGNER_SPEC.md`. E-Ink-Treiber weiterhin nicht umgesetzt.

- Startdiagnose auf anderem Windows-PC am 26.10.2026: frisch installiertes
  Python 3.15.2 hat weder Pillow noch cryptography noch tzdata; der Import des
  Programmeinstiegs scheitert an fehlenden Europe/Berlin-Zeitzonendaten. Der
  bestehende Windows-Starter bevorzugt hier jedoch die vorhandene gebündelte
  Python-3.12.14-Laufzeit, deren Bibliotheken und Programmeinstieg erfolgreich
  geprüft wurden, auch im normalen Windows-Benutzerkontext. Die konkrete Ursache
  des gemeldeten Doppelklick-Abbruchs ist deshalb noch nicht abschließend belegt.
  Starter hält das Konsolenfenster nach Fehlern nun offen und erhält den Exitcode;
  erfolgreicher Abschluss bleibt ohne Pause. Beide Fälle mit simuliertem
  Python-Starter geprüft (Fehlercode 7 und Erfolgscode 0). Keine Bibliotheken installiert,
  privaten Daten verändert, Anwendung gestartet oder Liveabrufe ausgelöst.

- Updatefenster am 26.10.2026 korrigiert: getrennte Zustände mit eindeutiger
  Überschrift und Fenstertitel. Während der Arbeit bewegter unbestimmter Balken
  und ausdrücklicher Wartehinweis; nach bestätigtem Erfolg grüner Abschlusshinweis,
  vollständig gefüllter Balken und Schließhinweis. Fehler rot gekennzeichnet,
  ohne grünen Balken; nach jedem Endzustand Schließen freigegeben. Version,
  Sicherungspfad und tatsächlicher Wiederstart/geschlossen gebliebener Zustand
  stehen getrennt vom Abschluss. Späte Fortschrittsmeldungen überschreiben den
  Abschluss nicht; unvollständige Rückmeldungen zählen nicht als Erfolg.
  26 gezielte Tk-/Updateablauftests bestanden; drei synthetische Fensterzustände
  gerendert, Erfolg und Fehler visuell kontrolliert. Nur Windows-Anzeige geändert,
  keine erneute Pi-Aktualisierung oder Wetterabrufe durch die Prüfung.

- Am 26.10.2026 nach Meldung eines vermeintlich hängenden Updatefensters direkt
  und ausschließlich lesend per Schlüsselanmeldung am Pi geprüft: Version
  `2026-10-25-235944` erfolgreich installiert; alle 57 Programmdateien stimmen mit
  den erwarteten Prüfsummen überein, keine Abweichungen bei den vorgesehenen
  entfernten Altdateien, keine Updatesperre und kein laufender Updateprozess.
  Sicherung `Wetterstation-Backups/<Zeitstempel>` vorhanden, ihr
  Installationsprotokoll meldet `installed`; PC-Erfolgsprotokoll stimmt überein.
  Anwendung blieb gemäß vorherigem Zustand geschlossen; kein Start oder
  Wetterabruf durch diese Diagnose. Damit sind Schlüsselanmeldung und erste
  Übernahme der neuen Struktur praktisch bestätigt. Windows-Neustart,
  Wiederstart einer zuvor laufenden Anwendung und aktuelle Display-/Handyabnahme
  bleiben davon getrennte, noch offene Prüfungen. Der nach Abschluss stehen
  bleibende unbestimmte Balken wurde vom Nutzer als mögliche Blockade verstanden.

- Reparatur der SSH-Ersteinrichtung nach Nutzerausgabe: Windows PowerShell 5.1
  entfernte die eingebetteten Anführungszeichen des `python3 -c`-Befehls; Anmeldung
  am Pi war erreicht, Registrierung scheiterte vor Ausführung mit Bash-Syntaxfehler.
  Registrierung wird jetzt als getrenntes Standardbibliothek-Skript über SSH-stdin
  ausgeführt (`python3 - --key-base64 ...`), ohne Python-Code in Shellargumenten.
  Vorhandene lokale Schlüssel werden weiterhin verwendet; private Schlüssel und
  Passwörter werden nicht übertragen. Andere autorisierte Pi-Schlüssel bleiben
  bytegleich erhalten, Wiederholungen erzeugen keinen doppelten Eintrag.
  26 gezielte Offline-Tests bestanden, darunter echte PowerShell-5.1-/native
  Argument-/stdin-Übergabe mit Python-Testgegenstelle, Fehlerweitergabe, atomare
  Speicherung und idempotente Registrierung. Keine Pi-Verbindung oder Wetterabrufe
  durch diese Reparaturprüfung; echte Einrichtung ist vom Nutzer erneut zu starten.

- Am 25.10.2026 im PC-Workspace umgesetzt: gemeinsame Pakete für Anzeige,
  Wetter/Orte, Karten, Speicherung und Handy-Weboberfläche; getrennte Windows-/Pi-
  Starter, Werkzeuge und Dokumentation. Vollständige geprüfte Sicherung unter
  `archive/before-restructure-*`, frühere Transferpakete unter `archive/transfer-*`.
  Zentraler Projektpfad hält `private/` und die Budgetzuordnung am bisherigen Ort.
  Alle 756 vor der Umordnung vorhandenen privaten Dateien bytegleich geprüft.
  Kompatibilitätseinstiege und vorhandener Pi-Installationsordner bleiben erhalten.
- Manueller Doppelklick-Updater mit Fortschrittsfenster, eigenem SSH-Einrichtungsstarter,
  Schlüsselanmeldung ohne Passwortdialog, eingefrorenem Quellstand, Offline-Abnahme,
  Paketformat 2, vollständigem Bereitstellen vor Beenden, Prozess-/Desktopsitzungs-
  prüfung, Sicherung/Installation/Rücksetzung und bedingtem Wiederstart umgesetzt.
  Pi-Layout und private Daten werden nicht vom PC importiert. Keine Zeitpläne,
  automatischen Paketinstallationen, normalen Programmstarts oder GitHub-Aktionen.
- Lokale Abnahme: 299 Python-/Tk-/HTTPS-Tests bestanden, keine übersprungenen Tests.
  Der tatsächliche Einfrieren/Testen/Paketbau-Ablauf bestand in einer getrennten
  Kopie mit ausschließlich simuliertem Transfer; Paket und Tests verwenden denselben
  Stand. Migration und Rücksetzung einschließlich alter Programmdateien simuliert.
  Widget-, Mehrbrowser- und internationale Browserprüfung bestanden, keine externen
  Browseranfragen. Displaybilder und Updatefenster mit Beispieldaten visuell geprüft.
  PowerShell-Syntax und Windows-Starter samt Fehlerweitergabe geprüft.
  Ein Codierungsfehler im Umordnungsskript wurde vor dieser Abnahme korrigiert;
  ein früherer unterbrochener Testlauf zählt nicht als bestandene Abnahme.
- Noch nicht am echten Gerät abgenommen: interaktive SSH-Schlüsseleinrichtung,
  Passwortfreiheit nach Windows-Neustart, erste Übernahme der neuen Struktur und
  anschließender Wiederstart/Display-/Handytest auf dem Pi. Der Updater startet
  ausschließlich durch manuellen Aufruf. PC-Tests sind keine Pi-/Live-Abnahme.

- Funktionsbestandsaufnahme vom 24.10.2026: aktueller Code, Tests und
  Dokumentation abgeglichen; Übersicht in `FEATURE_STATUS.md`. Erneute isolierte
  Offline-Abnahme: 280 Python-/Tk-/HTTPS-Tests bestanden, Widget-Browsertest und
  unabhängiger Mehrbrowser-Anmeldetest bestanden, keine externen Browseranfragen.
  Displaybilder neu erzeugt und Übersicht/Vorhersage visuell kontrolliert.
  Neueste PC-Funktionen umgesetzt; Pi-Übernahme und aktuelle Geräteabnahme noch
  offen. Frühere Pi-Handyreparatur bleibt abgeschlossen. Veraltete Dokumentations-
  stellen und noch nicht umgesetzte/vorgemerkte Funktionen getrennt erfasst.
  Keine Funktionsänderung, kein Livestart, Providerabruf oder Pi-Zugriff.

- Einreihige, zentrierte Widgets vom 24.10.2026 umgesetzt: Vorhersagen verwenden
  genau eine Reihe mit acht Stunden beziehungsweise fünf Tagen. Gemeinsame
  Schriftgrößen und Zeilenmittelpunkte je Datenfeld halten alle Spalten auch bei
  unterschiedlich langen Beschreibungen ausgerichtet; Wörter werden bevorzugt
  vollständig umgebrochen. Alle Einträge und gewählten Felder bleiben erhalten.
  Sieben beziehungsweise vier dünne senkrechte Linien trennen ausschließlich
  die Vorhersagespalten. Sonstige Widgets erhalten keine inneren Trennlinien.
- Widget-Titel, Werte, mehrzeilige Texte und eigene Karten-/Quellen-/Demo-/
  Hinweisbeschriftungen sind horizontal zentriert. Der Zeitstempel der Vollkarte
  liegt jetzt unten mittig; dies ersetzt die frühere Platzierung unten rechts.
  Dunkelgraue Rahmen sind bei 1024×600 zwei Pixel dick, auf größeren Displays
  entsprechend stärker; auch die Vollkarte erhält einen Rahmen. Rahmen und
  Trennlinien sind in Innenabständen berücksichtigt. Die Handy-Vorschau zeigt
  stärkere Rahmen und zentrierte Widget-Titel. Layout, Raster, Widget-Abmessungen,
  Zeitzonen, API-/Speicherformat und Anmeldung unverändert.
- Offline-Abnahme: 280 Tests bestanden. Sieben neue Tk-Prüfungen umfassen
  1024×600, 1600×800, 600×900 und 360×600, volle und minimale Vorhersagegrößen,
  ausgewählte Feldkombinationen, vollständige Werte, Spalten-/Zeilenzentren,
  Textgrenzen, Linienanzahlen, Uhr-Ticks, leere Widgets und doppelte Ortsstunden
  bei der Zeitumstellung. Temporäre Dummy-Einstellungen bleiben bytegleich.
  Der vorhandene Browsertest besteht einschließlich berechneter Zentrierung und
  2-Pixel-Rahmen im Handy-Editor, Ziehen/Skalieren/Undo/Konflikten/Neuanmeldung;
  keine Browserfehler und keine externen Anfragen. Aktuelle Prüfbilder einschließlich
  beider Mindestgrößen: `private/display-check/`; Suite: `private/alignment-full-tests.txt`.
  Kein echter Wetterabruf, normaler Programmstart, Pi-Transfer oder neue Abhängigkeit.

- Passive Anzeige vom 24.10.2026 im PC-Workspace umgesetzt: weißer Hintergrund,
  schwarze/dunkelgraue Texte und dünne Widget-Ränder; lokale Bedienelemente und
  Einstellungsdialoge entfernt. Automatisches Abrufraster unverändert. Das 12×8-
  Raster füllt beide Fensterachsen; kleiner Titel statt Orts-/Status-/Fußzeilen.
  Echte Schriftmaße bestimmen die Größen ohne bisherige Obergrenzen. Lange
  Zusatzwerte umbrechen vollständig; freie Höhe vergrößert den Hauptwert weiter.
  Uhr und Datum werden bei Ticks neu eingepasst. Alle Vorhersageeinträge und
  ausgewählten Felder bleiben vorhanden. Widget-Abmessungen, Layoutversion,
  private Speicherung, Demo-/Kartenquellen-/Radarversorgungshinweise erhalten.
- Automatische Handy-Verbindung: Hintergrundermittlung echter Heimnetz-Adressen,
  Port 8765, Wiederholung nach zehn Sekunden bei Netzwerk-/Startproblemen,
  kein blockierender Dialog. Browsergebundene Anmeldeanforderungen mit eigenen
  Displaycodes, FIFO-Warteschlange (vier), Zweiminutenfrist ab Anzeige und
  höchstens acht Sitzungen ohne Verdrängung. Neue HTTPS-Endpunkte für Anforderung
  und Status; Code nie in HTTP-Antworten. Cookies, Origin-/Host-Prüfung, CSRF,
  Versuchslimits und privates TLS erhalten. Sitzungen/Codes nur im RAM; Abmeldung,
  Dienst-/Programmneustart und Adresswechsel widerrufen den jeweiligen Zugriff.
  Handy übernimmt Displaymaße; Draft-/Konflikt-/Undo-Verhalten bleibt erhalten.
- Abnahme dieser Änderung: 273 Python-/Tk-/TLS-Tests bestanden; getrennte mobile Browser mit
  Dummy-Speicher, keine echten Schlüssel oder Providerabrufe. Prüfung der vollen
  Fläche bei 1024×600, breiten und hohen Fenstern, Ein-/Ausblenden ohne Geometrie-
  Änderung und ungekürzten gewählten Inhalten. Renderbilder: `private/display-check/`.
  Browserprüfungen: `private/widget-check/browser-results.json` und
  `private/widget-check/pairing-browser-results.json`; keine Browserfehler oder
  externen Anfragen. Offline-Pi-Vorabprüfung um Einmalcode/Widerruf ohne Serverstart
  erweitert. Keine Pi-Verbindung, Paketinstallation oder Hardwareansteuerung.

- Internationale PC-Umsetzung vom 24.10.2026: Offline-Katalog von 249 ISO-Ländern
  mit deutschen Anzeigenamen, filterbares PC-Länderfeld und durchsuchbare Handy-
  Auswahl. `country_code` ergänzt die geschützte HTTPS-Schnittstelle; Ort/Land
  werden atomar geschrieben und aus einer gemeinsamen Datei-Momentaufnahme gelesen.
  Schlüssel, andere Einstellungen und Widget-Layout bleiben erhalten. Unbekannte
  alte Länder sperren Geocoding bis zur Auswahl; bisherige deutsche Eingaben und
  erkennbare deutsche/englische Ländernamen werden kompatibel geladen.
- OpenWeather-Ortssuche begrenzt Namen und Postleitzahlen auf das gewählte Land;
  eindeutige ISO-Query steuert getrennte Orts-, Wetter- und Vorhersagecaches.
  Länderwechsel entfernt sichtbare Daten und Karten sofort und erhöht die
  Arbeitsgeneration. Verspätete Wetter-/Karten-/Bildresultate werden verworfen.
- Deutschland verwendet weiterhin die bestehende helle BKG-/DWD-Karte. Ausland:
  OSM, RainViewer und Abdeckungsmaske auf demselben Web-Mercator-XYZ-Raster bei
  Zoom 7, Datumsgrenzen-Umbruch und maximal ±85,051° Breite. Außerhalb erscheint
  ein klarer Hinweis. Fehlende Versorgung wird schraffiert und als fehlend/teilweise
  bezeichnet; unbekannte Flächen bleiben auch bei transparentem Radar unbekannt.
  Internationale Quellen sind in Vollkarte und Kartenwidgets sichtbar und nicht
  durch Inhaltsauswahl ausblendbar. DWD-Regenzug-Pfeile bleiben unverändert.
- RainViewer-Metadaten werden im bestehenden Fünf-Minuten-Takt geprüft; unveränderte
  Zehn-Minuten-Beobachtungen verwenden dieselben Bilder und Abrufzeit weiter.
  OSM lädt ausschließlich Kacheln der betrachteten Kartenfläche, nie vorsorglich
  im Hintergrund. Bereits geladene Grundkarten können im Hintergrund mit neuen
  Radaraufnahmen weiterverwendet werden. HTTP-Frische, ETag/Last-Modified und
  bedingte Wiederholungen werden berücksichtigt, sonst mindestens sieben Tage.
  Gültige gleichörtige Bildsätze bleiben bei Ausfall höchstens 60 Minuten erhalten,
  einschließlich Abdeckungsstatus; defekte/fehlende Masken ergeben keine Trockenkarte.
- Uhr, Datum, Stunden-/Tagesvorhersagen und Abrufanzeigen verwenden die IANA-
  Zeitzone aus dem Wetter einschließlich Sommerzeit und Tageswechsel. Fehlt eine
  nutzbare Zeitzone, steht UTC ausdrücklich dabei. Die Berliner Fünf-Minuten-
  Termine sowie deutsche/UTC-Budgettage und sämtliche Zähler bleiben unverändert.
- Offline-Abnahme: internationaler Testsatz mit allen sechs beauftragten Orten,
  mehreren Postleitzahlformaten, gleichnamigen Orten, Länderwechsel, Altbestand,
  Neustart, Handy-HTTPS, Cachetrennung, verspäteten Wetter-/Kartenergebnissen,
  Radarversorgung, kaputten Masken, Dienstausfällen, Datumsgrenze, Polargebieten
  und Sommerzeit. PC-Übersicht, Vorhersage und Regenkarte bei 1024×600 visuell
  geprüft; Handy bei 320/375 Pixeln ohne horizontalen Überlauf. Speicherung,
  Neuladen und unverändertes Widget-Layout im Browser bestätigt. Alle Daten
  simuliert, Dummy-Schlüssel und temporäre Einstellungen. Kein normaler App-Start,
  kein externer Wetter-/Kartenabruf, keine Pi-Verbindung und keine Übertragung.
  Prüfbilder und Berichte unter `private/international-check/`. Die aktuellen
  Testzahlen stehen im dortigen Prüfbericht; ältere Zahlen unten sind historisch.

- Handy-Reparatur am 24.10.2026 abschließend vom Nutzer abgenommen: Auf die
  Frage nach Öffnen der Pi-Handyseite, Anmeldung mit Zugangscode und Änderung
  eines Widgets bestätigt er „Ja, Anmeldung und Widget-Änderung funktionieren“.
  Damit sind Installation, lokale Offline-Prüfung, HTTPS-Erreichbarkeit im LAN
  und persönlicher Handy-Funktionstest bestätigt. Die Reparatur ist abgeschlossen.

- Ergänzende LAN-Prüfung nach der Handy-Reparatur am 24.10.2026: Vom PC liefert
  `https://<Pi-Adresse>:8765/` HTTP 200 und die erwartete Wetterstation-Seite.
  Damit ist die HTTPS-Seite über die tatsächliche Heimnetz-Adresse erreichbar.
  Nur die öffentliche Anmeldeseite gelesen, keine Zugangsdaten gesendet und
  keine Wetter-/Kartenabrufe ausgelöst. Das eigene Zertifikat wurde bei dieser
  technischen Erreichbarkeitsprüfung nicht auf Browservertrauen geprüft.
  Diese technische Prüfung allein bestätigt keine Anmeldung oder Widget-
  Bearbeitung; der persönliche Handytest wurde anschließend vom Nutzer bestätigt.

- Handy-Reparatur am 24.10.2026 laut vollständiger Nutzerausgabe erfolgreich
  auf `pi@<Pi-Adresse>` installiert: Programmarchiv und `pi_update.py` vollständig
  übertragen, Installation und Offline-Prüfung erfolgreich. Kein PC-Layoutimport;
  Updater bestätigt Erhalt von Ort, Schlüssel, Zertifikaten und Zählern. Kein
  automatischer Programmstart. Sicherung:
  `~/wetterstation/Wetterstation-Backups/<Zeitstempel>`.
  Paket-SHA-256: `<interne Prüfsumme>`.
  Grundlage ist die vom Nutzer geteilte Abschlussausgabe, keine unabhängige
  SSH-Nachprüfung. Frühere lokale Fensterdiagnose meldete Unterbrechung; diese
  ist kein Gegenbeleg zur anschließend geteilten erfolgreichen Ausführung.
  Die PSReadline-Warnung verhinderte die Installation nicht. Die anschließend
  angeforderte Abnahme mit dem persönlichen Handy wurde inzwischen bestätigt.

- Handy-Reparatur am 24.10.2026 lokal umgesetzt: Linux liest aktive IPv4-
  Schnittstellen über `ip -j -4 address show up scope global` mit zwei Sekunden
  Zeitlimit. Bisherige Namensauflösung bleibt Rückfall; Windows unverändert.
  Debian-Rechnername auf `127.0.1.1` bei vorhandener WLAN-Adresse als Regression
  geprüft. Handy-Dialog sucht asynchron und bietet keine `127…`-Adresse mehr an;
  ohne Heimnetz-Adresse bleibt Einschalten gesperrt. Verspätete Suchergebnisse
  nach Schließen/Wiederöffnen werden ignoriert. HTTPS und Zugriffsschutz erhalten.
  Reparaturmodus `pi_update.py build --keep-layout` exportiert keine PC-Einstellungen;
  Installation und Rücksetzung lassen sämtliche privaten Pi-Dateien bytegleich.
  Spätere Pi-Layoutänderungen bleiben auch bei Rücksetzung einer Reparatur erhalten.
  Lokale Abnahme: 251 Tests bestanden, davon 26 Netzwerk-/Handytests und 31
  Updateprüfungen; Python-3.11-Syntax bestanden. Dummy-Schlüssel und temporäre
  Daten verwendet. Ein erster Gesamtlauf offenbarte einen Aufräumfehler im neuen
  Tk-Test, der vor dem erfolgreichen Gesamtlauf korrigiert wurde.
  Paket: `transfer/Wetterstation-Pi-Update-2026-10-24-handy-reparatur.zip`.
  Bei dieser lokalen Prüfung waren Pi-Übernahme und persönlicher Handytest
  noch nicht bestätigt; die direkte
  SSH-Diagnose verlangte Passwortanmeldung. Keine Änderungen am Pi durch diese
  lokale Prüfung, keine Wetter-/Kartenabrufe.

- Desktop-Symbol für den Livebetrieb am 24.10.2026 laut Nutzerausgabe erfolgreich
  auf dem Pi erstellt: `/home/pi/Desktop/Wetterstation.desktop`. Startziel ist
  der vorhandene `start_pi_live.sh` ohne Demo-Argumente, Arbeitsordner bleibt die
  bestehende Pi-Installation. Eigenes SVG-Wettersymbol, kein Terminalfenster;
  vorhandene abweichende Verknüpfung wird vor Ersetzen privat gesichert. Keine
  automatische Vertrauensfreigabe oder Anwendungsausführung. Einrichtung per
  `install_pi_desktop_icon.cmd` und einmaliger lokaler SSH-Passworteingabe bestätigt.
  Lokale Struktur-/Sicherungs-/Idempotenzprüfung mit Dummy-Verzeichnissen bestanden.
  Doppelklick/Live-Start selbst noch nicht bestätigt. Vorherige Demo schließen.

- Pi-Update r3 am 24.10.2026 laut vollständiger Nutzerausgabe erfolgreich:
  Ziel-/Prozessprüfung passiert, Programmarchiv, separates PC-Widget-Layout und
  Updatewerkzeug jeweils vollständig per SCP kopiert. Installation und echte
  Offline-Vorabprüfung auf dem Pi meldeten Erfolg. Der Updater bestätigt Erhalt
  von Ort, Schlüssel, Zertifikaten und Zählern. Keine Anwendung automatisch
  gestartet; kein Liveabruf durch das Update. Dies ist durch die vom Nutzer
  geteilte Ausführungsausgabe belegt, keine zusätzliche unabhängige SSH-Prüfung.
  Sicherung: `~/wetterstation/Wetterstation-Backups/<Zeitstempel>`.
  Übertragen: `Wetterstation-Pi-Update-2026-10-24-vollstaendig-r3.zip`, SHA-256
  `<interne Prüfsumme>`.
  Nächster Schritt: Widget-Demo am tatsächlichen Pi-Display und Handy prüfen;
  ein Live-Neustart des neuen Stands ist noch nicht erfolgt.

- Der erste sichtbare SSH-Versuch nach Aktivierung hat Anmeldung, Zielsystem
  und Programmordner erreicht, dann aber beim Arbeitsordner eines fremden eigenen
  Desktop-Prozesses abgebrochen (`/proc/.../cwd` nicht lesbar). Prozessprüfung
  korrigiert: Arbeitsordner nur möglicher Wetterstationsprozesse auflösen;
  unzugängliche fremde Arbeitsordner nicht anrühren. Zwei gezielte Regressionen
  für lokalen und tatsächlich übertragenen Prüfcode ergänzt. Laufende
  Wetterstation weiterhin als Abbruchgrund erhalten. Neues Paket r3 für den
  nächsten freigegebenen Versuch; Gesamtlauf mit 232 Tests bestanden, davon
  23 Updateprüfungen. Bisher noch keine Dateien auf den Pi kopiert.

- Transfer zunächst ohne Kopieren an der SSH-Verbindung angehalten. Nach der
  vom Nutzer vorgenommenen SSH-Aktivierung ist die Adresse erreichbar, benötigt
  aber Passwortanmeldung. Passwort wird ausschließlich lokal im sichtbaren
  Übertragungsfenster eingegeben. Die zuvor abgefangene SSH-Fehlerausgabe wurde
  für Passwortabfrage und konkrete Diagnose wieder an das Fenster durchgereicht;
  nur die schlüsselfreie Zielantwort bleibt intern erfasst. 21 Updateprüfungen
  einschließlich dieser Ausgabezuordnung bestanden. Aktualisiertes Paket r2
  wird für den erneuten Versuch verwendet; noch kein erfolgreicher Transfer belegt.

- Vollständiger Pi-Transfer am 24.10.2026 lokal vorbereitet: datiertes Archiv
  `transfer/Wetterstation-Pi-Update-2026-10-24-vollstaendig.zip`, SHA-256-Datei,
  separates Inhaltsverzeichnis und `transfer/pi-update-ready.json`. Reines
  aktuelles PC-Widget-Layout separat unter `private/pi-update-layout-2026-10-24-vollstaendig.json`.
  Öffentliche Programmdateien und alle Handy-/Linux-Ressourcen vollständig;
  keine privaten Einstellungen, Schlüssel, Zertifikate, Zähler oder Caches im Archiv.
- Neue Starter `prepare_pi_update.cmd` (nur lokale Vorbereitung) und
  `transfer_pi_update.cmd` (erst später ausdrücklich ausführen). `pi_update.py`
  prüft vor dem späteren Kopieren SSH-Identität, Linux/Python 3.11, Benutzer,
  Installationsordner und geschlossene Pi-Anwendung. Privates Staging, strenge
  Pfad-/Inhalts-/Hashprüfung, vollständige geschützte Pi-Sicherung, Startsperre
  und atomarer Dateiaustausch. Nur `dashboard` wird in die Pi-Einstellungen
  übernommen; alle anderen Felder und privaten Dateien werden auf Erhalt geprüft.
- Rückfall/Wiederherstellung ohne Budget-Rücksprung: Programmdateien und altes
  Layout wiederherstellen, niemals Zähler, Caches oder Zertifikate aus der Sicherung
  zurückspielen. Spätere Ort-/Schlüsseländerungen erhalten; anderweitige Code-/
  Layoutänderungen führen zum Abbruch. Unterbrechungen behalten eine Startsperre
  samt Sicherungspfad; keine automatische Anwendungsausführung.
- Offline-Vorabprüfung um Widget-Modell, Kollisionen und private Layoutspeicherung
  mit Dummy-Schlüssel erweitert. `start_pi_widget_demo.sh` für geschützte
  Handy-Demo mit temporären Beispieldaten. `PI_UPDATE.md`, README und Pi-Anleitung
  beschreiben Kopieren, Sichern, Aktualisieren, Offline-Abnahme und Rückfall.
- Abnahme: 230 Tests bestanden, davon 21 neue Updateprüfungen mit simulierten
  PC-/Pi-Verzeichnissen. Erfolg, Erhalt privater Werte/beider Zählerspeicher,
  laufende/später gestartete Anwendung, Archivfehler, Layoutfehler, Kopierfehler,
  Stromausfall und Wiederherstellung, spätere Zähler-/Schlüsseländerungen und
  ausschließlich simulierte SSH/SCP-Aufrufe geprüft. Python-3.11-Syntax,
  tatsächliche lokale Offline-Vorabprüfung sowie `sh -n` aller drei Linux-Starter
  bestanden. Keine echte Pi-Verbindung, Übertragung, Paketinstallation oder Neustarts.

- Widget-Seiten am 24.10.2026 lokal umgesetzt. Version 2 des privaten Layouts
  enthält geordnete, benannte Seiten und Widgets mit stabilen Kennungen,
  Rasterposition, Breite/Höhe und separaten Inhaltsfeldern. Vier bearbeitbare
  Startseiten; bis zu zwölf Seiten, mindestens eine erhalten. 12×8-Raster je
  Seite, kein Scrollen. Fehlendes Layout startet mit Vorlagen; früher Entwurf
  wird beim Lesen ohne Datenverlust auf begrenzte Seiten verteilt. Programmstart
  zeigt die erste Seite. Schlüssel und Ort bleiben bei Layoutänderungen erhalten.
- Handy-Editor: maßstabsgetreue Anordnungsvorschau, Ziehen, Größen-Griff,
  Breiten-/Höhenregler, Richtungstasten, Inhalts-Schalter, mehrfache Widgets,
  Seiten anlegen/benennen/umsortieren/entfernen und Widgets zwischen Seiten
  verschieben. Einzelne Wetter- und Demo-Sensorwerte sowie kombinierte Widgets,
  Uhr/Datum, Stunden-/Tagesvorhersage und Regenkarte. Leere Inhaltsauswahl lässt
  die Fläche leer; Ausblenden ändert nie die gewählte Größe.
- Kollisionsfreie Anordnung durch begrenzte Platzsuche innerhalb der Seite;
  bei Platzmangel unveränderten letzten Stand erhalten und andere/neue Seite
  anbieten. Direkte Speicherung nach abgeschlossener Geste/Auswahl, kein
  Übernehmen-Knopf. Rückgängig für 20 Änderungen der Sitzung. Handy-Seitenwahl
  wird ausdrücklich am Gerät angezeigt; Pfeiltasten bleiben manuell, kein
  automatischer Seitenwechsel.
- Layout- und Seitenbefehle über dieselbe lokale HTTPS-Anmeldung mit unveränderter
  CSP, Host-/Origin-/CSRF-Prüfung. Atomare Speicherung mit bestehender Dateisperre,
  Versionskonflikte abweisen. UI-Warteschlange übernimmt Layout/Seite; erst die
  tatsächliche Display-Bestätigung meldet Erfolg. Fehlende Antworten, Speicherung,
  Verbindungsabbrüche und abgelaufene Anmeldung behalten den lokalen Entwurf;
  Wiederverbinden und Neuladen sind ausdrücklich bedienbar. Fremde Änderungen
  werden nicht still überschrieben.
- Helle, ruhige Widget-Darstellung mit abgerundeten Flächen. Pro Typ lesbare
  Mindestgröße; alle Inhalts-Schalter auch bei dieser Größe geprüft. Die fertige
  Regenkartenseite verwendet weiterhin die optimierten Bildpaare, Ortsmarker,
  Abrufzeit/Knopf und Regenzug-Pfeile. Kleinere Karten-Widgets verwenden separat
  vorbereitete, ausgerichtete und wiederverwendete Bilder ohne neue HTTP-Anfragen;
  falscher Ort, Bildfehler und Cache-/Altershinweise berücksichtigt.
- `start_widget_demo.cmd` startet eine ausdrücklich temporäre Widget-Demo mit
  getrenntem Speicher unter `private/widget-demo/`, ausschließlich Beispieldaten
  und opt-in Handy-Verbindung. Ort-/Schlüsseländerungen in dieser Demo auch auf
  dem Server gesperrt. Echte Einstellungen werden nicht geöffnet; kein Wetter- oder
  Kartenabruf. Beim Beenden wird der temporäre Stand entfernt. Normaler Start
  speichert das Layout dauerhaft. Keine Änderung oder Übertragung auf den Pi.
- Abnahme: lokale HTTPS-/Tk-Integration und Browserprüfung bei 320/375 Pixeln,
  echte Browser-Touch-Ereignisse, Verschieben/Größen-Griff/Regler/Inhalte, Seiten-
  verwaltung/Transfer, volle Seite, 20 Rückgängig-Schritte, Speicherfehler,
  verlorene Erfolgsantwort, erneute Anmeldung mit erhaltenem Entwurf, parallele
  Sitzung und Display-Bestätigung bestanden. Keine Browser-Konsolenfehler und
  keine externen Browser-Anfragen. Native PC-Ansicht 1024×600 und Handy-Seiten
  visuell geprüft. Persönliches Handy und Pi sind noch nicht neu geprüft.
  Abschließender Gesamtlauf: 209 automatisierte Tests bestanden, ohne Tk-
  Hintergrundfehler. JavaScript-Syntaxprüfung und `git diff --check` bestanden.
  Automatisierte Abnahme und Artefakte: siehe README, `tests/test_widgets.py`,
  `tests/widget_browser_check.cjs` und `private/widget-check/`.

- Regenzug-Pfeile lokal umgesetzt: normalisierte Kreuzkorrelation überlappender
  9×9-Ausschnitte auf einem geografisch ausgerichteten Raster von rund einem
  Kilometer. Analyse der ursprünglichen DWD-Klassen, einschließlich getrennter
  hoher Klassen; unbekannte Farben und No-data-Flächen maskiert. Paare müssen
  denselben Ort und fünf oder zehn Minuten Beobachtungsabstand haben.
  Mindestkorrelation 0,85, Abstand zum konkurrierenden Treffer 0,08,
  Rückwärtsprüfung und benachbarte Richtungen innerhalb 30 Grad erforderlich.
  Stillstand, zu wenig Struktur, mehrdeutige Muster und Verschiebungen über
  120 km/h liefern keine Pfeile. Diese Grenze ist nur ein Plausibilitätsfilter;
  angezeigt werden weder Geschwindigkeit noch Vorhersagestrecke.
- Höchstens drei gleich lange, rund 44 Pixel große dunkelgraue Pfeile mit hellem
  Saum bei 1024×600, ungefähr 160 Pixel Mindestabstand. Proportionaler Zuschnitt
  und Versatz wie bei den Kartenbildern; Ortsmarker, Namensschild, Problemhinweise
  und Aktualisierungsfeld bleiben frei. Auf schmalen Fenstern gegebenenfalls
  weniger Pfeile. Keine zusätzliche Legende entsprechend Nutzerentscheidung.
- Kartenbild und Bewegungsauswertung getrennt: ein Analyseauftrag plus neuester
  Folgeauftrag, keine Warteschlange veralteter Aufgaben. Ergebnisse nur für das
  passende angezeigte Bild; nach Ortswechsel oder Schließen verwerfen. Cache-
  Rückfälle und mehr als 15 Minuten alte Beobachtungen ohne Pfeile. Ablauf über
  bestehende UI-Ergebnisabholung; kein zusätzlicher Abruf-Timer. Seitenwechsel
  und Größenänderungen verwenden Ergebnisse erneut und lösen keine Analyse aus.
- Vergleichsbild ausschließlich über denselben DWD-WMS-Layer mit expliziter
  älterer TIME-Angabe. Zeitbereich aus den vorhandenen Metadaten beachten.
  Vorherige Aufnahmen aus Speicher und bestehendem Dateicache vorziehen;
  Zusatzbild im Speicher behalten, aktuellen Dateicache und Abrufzeit nicht
  ersetzen. Fehlgeschlagene Zusatzversuche nicht im selben Fünf-Minuten-Slot
  wiederholen. Wetterzählung, Grundkartenabrufe und regulärer Takt unverändert.
- Offline-Abnahme: 184 Tests bestanden, darunter acht Bewegungsrichtungen
  (höchstens 15 Grad Abweichung), getrennt ziehende Gebiete, Intensitätsänderung,
  Wiederholungsmuster, Stillstand, Störpixel, fehlende Daten, Zeit-/Ortsgrenzen,
  Neustart mit Cache, Hintergrundaufträge und verspätete Ergebnisse. Tatsächliche
  Tk-Fenster bei 1024×600, 480×800 und 360×600 mit synthetischer Karte und Regen
  visuell geprüft. 30 vorbereitete Seitenwechsel: Median 16,80 ms, P95 18,35 ms,
  Maximum 20,92 ms. Weitere 30 während laufender Analyse: Median 16,77 ms,
  P95 22,66 ms, Maximum 60,07 ms. Analyse des Testmusters rund 388 ms im Hintergrund.
  Alle Messungen auf diesem PC; ausschließlich simulierte Antworten, Dummy-
  Einstellungen und temporärer Speicher. Keine Liveabrufe oder Pi-Änderungen.

- Radargestaltung vom 23.10.2026 lokal umgesetzt. Weiterhin amtliche BKG-/DWD-
  Geometrie, nun basemap.de Web Raster Farbe mit warmer, zurückhaltender Farbgebung.
  Kräftige Straßenblautöne werden orange-gelb dargestellt, violette Flächen
  zurückgenommen; Wasser, Landschaft und Schrift bleiben erkennbar und scharf.
  Alte graue Karten sind über Cache-Layerkennung vom neuen Hintergrund getrennt.
- Der verifizierte DWD-WN-Farbstil wird im Hintergrund in geordnete Anzeigeklassen
  überführt, geglättet und mit stetigen Blau/Lila–Türkis–Grün–Gelb-Verläufen versehen.
  Räumlicher Gaußradius rund 0,65 km, separate Glättung der Deckungsfläche,
  maximale Deckkraft rund 62 Prozent. So bleiben Karte, Straßen und Ortsnamen
  unter den Regenflächen sichtbar. Bekannte No-data-Flächen bleiben ohne Färbung;
  unbekannte vollständige Farbskalen werden abgewiesen. Die Darstellung ist keine
  Umrechnung in mm/h; hohe Originalklassen sind im Gelbbereich gesättigt. Der
  ursprüngliche WMS-Bildcache bleibt unverändert. Ortsname in weißem abgerundetem
  Schild und orange-weißer Marker liegen klar über den Regenflächen.
- Alle 168 Tests bestehen, einschließlich Farbklassen, weicher Ränder,
  kontinuierlicher Übergänge, Alpha-Begrenzung, durchsichtigem Kartenuntergrund,
  Trocken-/No-data-Flächen, unbekannter Farbskala, Kartenfarben, alten Grau-Caches
  und Marker-/Beschriftungsreihenfolge. Sichtprüfung echter Tk-Fenster bei
  1024 × 600, 600 × 800 und 360 × 600 mit amtlicher Hamburg-Farbkarte und
  gekennzeichnetem synthetischem Regen. 30 sichtbare PC-Seitenwechsel:
  18,56 ms Median, 20,75 ms im 95. Perzentil, 23,46 ms Maximum. Keine Pi-Messung.
- Öffentliche DWD-Stil-/Legendeninformationen und eine BKG-Farbkarte wurden zur
  Gestaltung geprüft. Keine OpenWeather-Abfrage, kein Schlüsselzugriff, keine
  neue Abhängigkeit und keine Übertragung/Neustarts auf dem Pi. Der bisherige
  Fünf-Minuten-Takt, Zeit-/Knopffeld, Fehler-/Cache-Rückfall und Bildvorbereitung
  bleiben erhalten. Die frühere Idee besser lesbarer Ortsnamen ist nun durch
  Transparenz und Hervorhebung des ausgewählten Orts umgesetzt. Der Nutzer
  bestätigt, dass damit keine separate Beschriftungsebene mehr benötigt wird.

- Radar-Takt und Infofeld am 23.10.2026 lokal umgesetzt. Die Karte verwendet auf
  jeder Seite dieselbe Zeitgrenzen-Berechnung wie das Wetter: 00:00, 00:05 usw.
  Startabruf bleibt; ein einzelner Timer wird bei Seitenwechseln nicht verschoben
  oder dupliziert. Manuelle Abrufe, Fehler und verspätete Läufe kehren zum Raster
  zurück; keine nachgeholten Abrufserien nach Standby. Ohne Position kein Abruf.
- Kleines Infofeld unten rechts bleibt über Karte/Lade-/Fehleransicht sichtbar.
  Es zeigt fetched_at des tatsächlich angezeigten Bildpaars in deutscher Zeit,
  heute als Uhrzeit, ab dem nächsten Kalendertag mit Datum. Die Beobachtungszeit
  bleibt getrennt. Neue Daten verändern die Anzeige erst zusammen mit den
  fertigen Bildern; identische Bildobjekte übernehmen nur neue Metadaten, ohne
  Bildaufbereitung. Größenänderung und Fehler-/Cache-Rückfall behalten die Zeit.
  „Aktualisieren“ und F5 verwenden denselben Abrufweg; bei laufendem Abruf ist
  der Knopf deaktiviert, ebenso im Demomodus. Kartenfläche und bisherige
  Problemhinweise bleiben erhalten, vorbereitete Bilder werden weiterverwendet.
- Alle 159 automatisierten Tests bestehen. Unter anderem feste Zeitgrenzen,
  Mitternacht, Sommer-/Winterzeit, Hintergrundbetrieb, Standby, unveränderte Timer
  bei Seitenwechseln, Zeit-/Bildübernahme, Cache-Rückfall, Fehler, Demo und echte
  WMS-Clientverarbeitung mit simuliertem Transport ohne OpenWeather-Budgetzugriff.
  Sichtprüfung mit synthetischen Ebenen bei 1024 × 600, 600 × 800 und 360 × 600.
  Mit Infofeld im sichtbaren PC-Test: 13,15 ms Median, 16,26 ms im 95. Perzentil,
  17,49 ms Maximum bei 30 Seitenwechseln. Keine Liveabrufe, keine Pi-Übertragung;
  dies ist keine gemessene Pi-Laufzeit. Frühere Testberichte bleiben historisch.

- Radar-Seitenwechsel am 23.10.2026 lokal beschleunigt. Ursache: zuvor wurden bei
  jedem Zeichnen beide PNGs dekodiert, skaliert, neu komprimiert und als Tk-Bilder
  angelegt. Nun bleibt ein fertiges Paar im Speicher; Vorbereitung erfolgt nach
  Daten-/Größenwechsel im Hintergrund, auch auf anderen Seiten. Das Zeichnen nutzt
  bestehende Tk-Bilder. Beide Ebenen werden gemeinsam ersetzt; gültige alte Bilder
  bleiben bei Fehlern oder während der Vorbereitung zentriert sichtbar.
- Genau eine aktive Bildvorbereitung mit höchstens einem aktuellen Folgeauftrag;
  Orts-/Größenwechsel und Programmende verwerfen verspätete Ergebnisse. Tk-Aufrufe
  bleiben im UI-Thread. Transparenz, identischer Zuschnitt, Ortsmarker, Warnungen,
  F5/Pfeiltasten und Karten-/Wetterintervalle bleiben erhalten. Aufgelöste Orte aus
  dem Dateicache bleiben im Speicher; keine zusätzliche Bibliothek/API nötig.
- Alle 150 Tests bestehen. Ergänzte Fälle prüfen unter anderem unveränderte
  Bildobjekte bei Seitenwechseln, Vorbereitung vor dem ersten Kartenbesuch,
  begrenzte Folgeaufträge, verspätete Ortsresultate, UI-/Worker-Zuständigkeit,
  fehlerhafte erste/neue Bilder, abgelaufene Ersatzbilder und Programmende.
  Sichtprüfung mit synthetischen Ebenen bei 1024 × 600 und 600 × 800 erfolgreich.
- Gemessen auf diesem Windows-PC, ausschließlich synthetische Daten: derselbe
  1024×600-Vergleich im verborgenen Tk-Fenster sank von 366,9 ms Median
  (361,0–384,7 ms vorher) auf 0,20 ms Median, 0,32 ms im 95. Perzentil und
  14,68 ms Maximum bei 30 Wechseln. Ergänzend im sichtbaren Fenster mit
  synthetischem Kartengitter: 11,61 ms Median, 12,58 ms im 95. Perzentil,
  13,47 ms Maximum bei 30 Wechseln. Keine Aussage über gemessene Pi-Laufzeiten;
  keine echten Wetter-/Kartenabrufe und keine Übertragung/Neustarts auf dem Pi.

- Änderung vom 23.10.2026 lokal umgesetzt: Fünf-Minuten-Raster nach deutscher
  Zeit, fünf Minuten Cachefrist beim Start, erzwungener Abruf aller drei
  Wetterbereiche an festen Terminen. Gleichzeitige Auslöser desselben Orts
  werden zusammengefasst; Ortswechsel erhalten ihren Folgeabruf. Nach langen
  Abrufen/Standby wird zum nächsten festen Termin geplant, ohne Abrufserie.
- Beide Tagesgrenzen betragen jetzt 1000; Anfrage 1000 wird reserviert, Anfrage
  1001 vor dem Transport blockiert. Bestehende Historie und Spiegeldateien bleiben
  kompatibel; der lokale Mitternachtswechsel und der separate UTC-Schutz bleiben
  wirksam, ebenso Minutenlimit, Anfragepausen und HTTP-429-Behandlung.
- Die Übersicht zeigt nur die letzte erfolgreiche aktuelle Wetter-Abrufzeit
  neben „Aktualisieren“. Fehlversuche verändern die Zeit nicht; Datum erscheint
  ab dem nächsten deutschen Kalendertag. API-/Budget-/Messzeitzeilen und der
  technische Vorhersagestatus entfallen hier. Die Vorhersageseite und der
  Regenkarten-Takt bleiben unverändert. Demo-Daten bleiben gekennzeichnet.
- Offline-Prüfung: Alle 140 automatisierten Tests bestehen. Tests für feste
  Uhrzeiten, Sommer-/Winterzeit, Standby,
  manuelle Auslöser, drei Wetteranfragen, fünf Minuten Cachefrist, Tageswechsel,
  1000er-Grenze, Parallelität, Neustart und Darstellung ergänzt/angepasst.
  Sichtprüfung der tatsächlichen Tk-Fenster mit Beispieldaten bei 1024 × 600
  und 600 × 600; zusätzlich Layoutprüfung bis 360 Pixel Breite. Keine echten
  Wetteranfragen und keine Übertragung/Neustarts auf dem Pi.

- Erste unbeaufsichtigte Pi-Laufprobe vom 23.10.2026 erfolgreich laut Nutzerbericht:
  rund dreieinhalb Stunden ohne Absturz, Ansichtswechsel danach weiterhin bedienbar.
  Die bereitgestellten Fotos IMG_4741.HEIC und IMG_4744.HEIC wurden lokal für die
  Sichtprüfung umgewandelt; die Originale bleiben unverändert. Die Aufnahmezeiten
  lauten 17:51 und 21:18 Uhr deutscher Zeit (Abstand etwa 3 Stunden 27 Minuten).
  Sichtbar sind derselbe Kartenausschnitt für den Testort mit Ortsmarker und zunächst
  ein großes farbiges Niederschlagsgebiet östlich des Ortes, später keine farbigen
  Radarflächen. Auf beiden Fotos ist kein Kartenfehlerhinweis erkennbar. Der Nutzer
  bestätigt, die Änderung sei ohne manuelle Aktualisierung erfolgt. Damit ist die
  automatische Aktualisierung im Praxistest belegt; einzelne Abrufintervalle,
  Wetter-Aktualisierungen und der API-Zähler sind auf diesen Kartenfotos nicht
  prüfbar. Längere Laufproben, Geräte-Neustart und Autostart bleiben separat offen.
- Während der geplanten Laufprobe wurde die Pi-Anwendung versehentlich geschlossen.
  Der Nutzer bestätigt den erfolgreichen erneuten Livestart und einen unveränderten
  sichtbaren Abrufzähler. Ein Anwendungsneustart ist damit praktisch geprüft;
  ein Neustart des Raspberry Pi selbst wurde weiterhin nicht durchgeführt.
- Der Nutzer nennt nach dem ersten Pi-Livebetrieb einen sichtbaren Zählerstand
  von 7/999 Anfragen und 992 verbleibenden Abrufen. Er lässt die Anwendung nun
  für die nächsten Stunden laufen und möchte anschließend selbst Rückmeldung
  geben. Diese erste Laufprobe wurde später durch Nutzerbericht und Bildvergleich
  bestätigt. Ein Geräte-Neustart-/Autostarttest und eine automatische Überwachung
  wurden damit nicht beauftragt oder durchgeführt.
- Der Nutzer bestätigt anschließend den Start über den Pi-Livestarter und
  funktionierende Wetterübersicht, Vorhersage und Regenkarte mit sichtbarem
  Niederschlagsradar. Er hält die Temperaturen nach einem eigenen Vergleich für
  plausibel. Dies ist ein bestätigter Nutzer-Funktionstest, keine unabhängige
  Messwertprüfung. Die Sensorseite zeigt erwartungsgemäß weiterhin Demo-Werte.
  Damit ist der erste Pi-Livebetrieb erfolgreich; Autostart, längere Laufprobe
  und Prüfung der Handy-Einstellungen auf dem Pi sind noch offen.
- Der Nutzer hat den Übertragungsstarter ausgeführt und meldet die erfolgreiche
  Übernahme von Einstellungen, Zählerhistorie und Prüfspeicher. Die gepostete
  Ausgabe zeigt heute 0/999 sowie Anbietertag 0/999 und bestätigt ausdrücklich,
  dass noch keine Wetterabfrage gesendet wurde. Dies bestätigt die Einrichtung
  laut Nutzerausgabe; der erfolgreiche Live-Funktionstest folgte anschließend.
- Die Pi-Vorabprüfung ist laut Nutzerausgabe für Bildverarbeitung, lokale
  HTTPS-Zertifikate und Dateisperren erfolgreich. Für den nächsten Schritt sind
  ein Windows-Übertragungsstarter und ein Export-/Importwerkzeug vorbereitet.
  Der Export läuft im normalen Windows-Benutzerkontext mit Abgleich des lokalen
  Zähler-Prüfspeichers. Einstellungen und Zähler werden ausschließlich über SSH
  in den geschützten privaten Pi-Ordner übertragen, ohne Geheimnisse auszugeben.
  Bestehende Pi-Einstellungen oder Kennungen verhindern einen Import. Vorhandene
  Sperren, Kontingente und Zählerstände werden nicht aufgehoben oder zurückgesetzt.
  Der Import selbst sendet keinen Wetterabruf; der Live-GUI-Start wurde danach
  vom Nutzer separat durchgeführt und bestätigt.
- Der Nutzer hat die Systemaktualisierung ausgeführt. Laut geposteter Ausgabe
  sind alle Pakete aktuell; die Option ohne Entfernen hat die vorgeschlagene
  Entfernung von vier Kernelpaketen verhindert. Keine Entfernung oder erfolgreiche
  Bereinigung behaupten. Ein Offline-Prüfskript für die vorhandenen Pi-Bibliotheken
  ist vorbereitet; es nutzt synthetische Bilder, temporäre Zertifikate und
  eine Test-Dateisperre, ohne Wetterabrufe oder echte Einstellungen zu verwenden.
- Ein gesonderter Pi-Livestarter ist übertragen und vom Nutzer gestartet. Er prüft vor dem Start
  Tkinter, Pillow, cryptography und Zeitzonendaten. Er installiert nichts und
  ändert keine Budgetgrenzen. Schlüsselbereitstellung und erster Livebetrieb
  sind inzwischen durch die Nutzerausgaben beziehungsweise Sichtprüfung bestätigt.
- Ein gesonderter Linux-Demostarter und eine Anleitung für den ersten Pi-Test
  sind vorbereitet. Der Starter erzwingt Beispieldaten und installiert nichts.
  Das Übertragungsarchiv enthält keine privaten Einstellungen, Schlüssel, lokalen
  Zertifikate, Zähler oder Caches. Der Nutzer bestätigt die Übertragung per SCP,
  das Entpacken und den erfolgreichen Demostart auf dem Pi. Dies ist ein
  Nutzerbericht, keine selbst durchgeführte Hardwareprüfung. Anschließend
  bestätigt der Nutzer sichtbare Wetterübersicht und Vorhersage mit korrekter
  orangefarbener Demo-Kennzeichnung sowie den Wechsel durch alle Ansichten.
  Die verwendeten Bild- und HTTPS-Funktionen wurden anschließend offline geprüft;
  Livebetrieb ist eingerichtet, Autostart noch offen. Die PC-Vorschau bleibt
  unverändert.
- Die DWD-Beobachtungszeit wird über die auf den freigegebenen WN-Layer begrenzten
  GetCapabilities-Metadaten ermittelt. Dabei werden sowohl der vollständige als
  auch der in dieser Antwort unqualifizierte Layername erkannt. Die Live-Diagnose
  zeigte knapp 989 KB und rund 17 Sekunden für die vollständigen Metadaten;
  die gezielte Antwort enthielt rund 12 KB und kam wesentlich schneller.
  Der ursprüngliche Fehler war bei der erneuten Prüfung vorübergehend nicht mehr
  reproduzierbar; die laufende Vorschau zeigte nach erneutem Abruf wieder die Karte.
- Fehlermeldungen unterscheiden DWD-Metadaten, graue Grundkarte und Radar sowie
  Nichterreichbarkeit und ungültige Antworten. Rohe Fehlerdetails bleiben intern.
  Nach einem fehlgeschlagenen Abruf mit geänderter Fenstergröße bleibt die zuvor
  angezeigte, zum selben Ort passende Karte erhalten, solange sowohl Beobachtung
  als auch Abruf höchstens 60 Minuten alt sind. Sie wird als zwischengespeichert
  markiert. Abgelaufene, zukünftige oder fremde Ortsdaten werden nicht erhalten.
  Eine erfolgreiche Aktualisierung entfernt den Fehlerhinweis wieder.
- Der korrigierte Kartenabruf wurde bei 1024 × 600 mit der bereits gespeicherten
  Ortsposition live geprüft: beide PNG-Ebenen frisch und dekodierbar, Cache ohne
  Speicherwarnung. Kein OpenWeather-Aufruf. Acht zusätzliche Tests prüfen die
  gezielte Metadatenantwort, Namensvarianten, Zeitangaben, Antwortgrenzen,
  Fehlerstufen, Cache-Rückfall und den Erhalt gültiger Karten nach Größenwechseln.
  Nach dieser Korrektur bestehen alle 125 Tests.
- Die Anzeige verwendet 1024 × 600 Pixel als Referenz und startet im Vollbild.
  F11 wechselt zum frei veränderbaren Fenster. Tatsächliche Canvasmaße bestimmen
  Schriftgrößen, native Eingabeelemente, Abstände und Kartenanordnung. Pixelbasierte
  Schriftgrößen vermeiden eine zusätzliche Multiplikation durch die Tk-DPI-Skalierung.
- Alle vier Seiten passen sich an andere Fensterformen an. Schmale Ansichten
  verwenden zusätzliche Vorhersagezeilen beziehungsweise eine Sensorkartenspalte;
  bei Platzmangel bleiben Inhalte über Bildlaufleiste/Mausrad erreichbar. Lange
  Ortsnamen, Cache- und Fehlermeldungen werden vor der Platzierung ausgemessen.
  Im normalen Zustand passen bei 1024 × 600 alle wesentlichen Inhalte ohne Scrollen.
- Beide PC-Einstellungsdialoge werden auf die Bildschirmfläche begrenzt und sind
  veränderbar sowie scrollbar. Schrift und Schaltflächen passen sich an; lange
  Verbindungsinformationen und schmale Schaltflächenreihen bleiben erreichbar.
  Regenkarte, Ortsmarker und Hinweise skalieren mit. Fensteränderungen ändern
  weder Abrufintervalle noch API-Budgets und behalten Fokus und Eingabeentwurf.
- Zehn neue Tk-Prüfungen decken 1024 × 600, 800 × 480, 1280 × 800,
  1920 × 1080 und 600 × 1024 ab: sichtbare Inhalte, Kartenumbruch, lange Hinweise,
  Scrollbarkeit, beide Dialoge, lange Verbindungsinformationen, F11/Vollbildstart,
  DPI-Skalierung und Fokus bei echten Fensteränderungen. Die Sichtprüfung lief
  mit gekennzeichneten Beispieldaten und getrenntem temporärem Speicher ohne
  echte Wetter-/Kartenabrufe. Der frühere starre Vorhersage-Test prüft jetzt den
  Inhalt der anpassbaren Darstellung statt unveränderlicher Pixelpositionen.
  Nach Abschluss dieser Anpassung bestehen alle 117 Tests.
- `app.py` stellt vier PC-Vorschauseiten in einem Tkinter-Fenster dar.
- Die Regenkartenseite verwendet die tatsächlichen Canvasmaße bis zum Fensterrand.
  Die gemeinsame Seitenumrahmung und ihre Bedienelemente sind dort ausgeblendet;
  auf den übrigen Ansichten erscheinen sie wieder. Beide Kartenebenen werden
  identisch proportional skaliert und mittig beschnitten. Der nächste planmäßige
  oder manuelle Abruf passt die Bildgröße innerhalb von 1800 × 1100 Pixeln
  proportional an das Fenster an. Vergrößern/Verkleinern ändert nur die Darstellung.
- Legenden-PNGs werden nicht mehr angefordert, dargestellt oder im Cache benötigt.
  `RadarMapResult` enthält nur Grundkarte, Radar und die bisherigen Metadaten.
  Vorhandene Cache-Manifeste mit zusätzlichem Legendeneintrag bleiben lesbar;
  die Legende darf fehlen. Die bisherigen Cachekennungen bleiben kompatibel.
- Auf der Regenkarte zeigen Lade-/Fehlerfälle kompakte Hinweise; veraltete
  Daten oder Cacheprobleme werden dezent über der Karte gekennzeichnet. Eine
  gesunde Karte zeigt nur Grundkarte, Radar und Ortsmarker ohne Ortsbeschriftung.
  Pfeiltasten wechseln weiterhin die Ansichten, Escape öffnet die Wetterübersicht,
  F5 aktualisiert die Karte. Beim Betreten erhält die Kartenfläche den Fokus.
- Nach dieser Erweiterung bestehen alle 107 Tests. Die Tk-Prüfungen umfassen
  800 × 560 bis 3440 × 1440 sowie Hochformat, pixelgenaue Flächennutzung,
  kreisförmig bleibende Testmerkmale und deckungsgleiche Ebenen, verborgene und
  wiederhergestellte Bedienelemente, Tastaturfokus, Escape/F5, Lade-/Fehlerfälle,
  Ortszuordnung und Legacy-Caches ohne Legendendatei. Resize-Aufrufe erzeugen
  keine zusätzlichen Downloads; neue Abrufe nutzen die aktuelle Fensterform.
  Die Sichtprüfung erfolgte zusätzlich mit einer ausdrücklich markierten
  Layout-Testvorschau und einem gespeicherten öffentlichen Berlin-Bild,
  ohne weitere Wetter- oder Kartenabrufe.
- Die Kacheln für Luftfeuchte, Wind und Luftdruck zeigen bei echten Werten
  keine zusätzlichen farbigen Quellenzeilen mehr. Demo-Markierung und Hinweis
  bei fehlenden Messwerten bleiben erhalten.
- Pfeiltasten wechseln die Seite manuell. Beim Texteingabefeld wechseln sie die
  Seite nicht; links/rechts bleiben für den Texteingabecursor verfügbar.
- Klicks auf die Anzeigefläche, Beschriftungen oder Schaltflächen verlassen das
  Ortsfeld. Enter übernimmt und verlässt es; Escape lässt den ungespeicherten
  Text stehen und gibt den Fokus ebenfalls an die Anzeige zurück. Klicks im
  Eingabefeld und in separaten Einstellungsdialogen bleiben davon unabhängig.
- Der klebende Eingabefokus wurde zunächst in einem echten Tk-Test reproduziert.
  Zwei neue Tests prüfen Cursorbewegung im Feld, Klicks auf freie Fläche,
  Beschriftung und Schaltflächen, anschließenden Seitenwechsel sowie Enter und
  Escape. Die Tests verwenden ausschließlich Dummy-Einstellungen und keine
  Anbieterabrufe. Nach der Korrektur bestehen alle 101 Tests. Die Tk-Testobjekte
  werden nach jedem Test im Hauptthread freigegeben, damit ihre Bereinigung
  nicht versehentlich in einem späteren HTTPS-Testthread läuft.
- Das gemeinsame Ortseingabefeld übernimmt den Namen mit Enter oder per Schaltfläche.
  Leere Eingaben behalten den vorherigen Ort bei. Der bestätigte Ort wird in der
  gemeinsamen Projekteinstellung gespeichert. Startwert: ein deutscher Beispielort.
- Die Wetterübersicht und die bestehende Vorhersageseite nutzen die getrennten
  One Call 4.0-Endpunkte `current`, `timeline/1h` und `timeline/1day`; angezeigt
  werden acht Stunden- und höchstens fünf Tageswerte ohne automatische Pagination.
  Sensoren bleiben klar als Demo gekennzeichnet. Für eindeutig gefundene Orte
  in Deutschland ist die Regenkarte eine echte Karte: Die graue amtliche Grundkarte
  basemap.de Web Raster Grau ersetzt seit 18.10.2026 das frühere DOP20-Luftbild;
  darüber liegt der DWD-WN-Radarkomposit-Beobachtungslayer.
  Beide WMS-Anfragen verwenden EPSG:4326, denselben Ausschnitt und
  dieselben Pixelmaße. Die Zeit kommt aus den WMS-Zeitmetadaten des reinen Analyse-Layers; der
  Analyse-und-Vorhersage-Layer wird nicht als Beobachtung verwendet. Die BBOX wird
  für beide Dienste gleich mit WMS 1.1.1/EPSG:4326 (Länge/Breite) angefordert.
  Abruf beim Start, manuell und in fünfminütigem Abstand während die Regenkarte
  geöffnet ist, sowie alle 15 Minuten bei anderen Ansichten. Beim Öffnen wird ab
  fünf Minuten seit dem letzten Versuch zeitnah nachgeladen. Veraltete
  Cachebilder sind gekennzeichnet. Reflektivitätsradar zeigt
  Niederschlagsechos, keine Wolkendecke. Wetter und Karte verwenden dieselbe
  aufgelöste Ortsposition. Für den damaligen Testort bleibt bis zur Ortsauflösung der bereits
  bestätigte amtliche Referenzpunkt (Koordinaten der damaligen Testkonfiguration) verfügbar.
- Die Kartendienste werden nebenläufig und mit Zeitlimit abgerufen. Öffentliches
  Kartenmaterial und Metadaten werden in `private/cache/radar/` relativ zum
  Projektordner zwischengespeichert. Der Cache ist orts-, Ausschnitts-, CRS- und
  pixelgrößengebunden. Datenzeit und Abruffehler werden angezeigt; beim Ortswechsel
  wird die alte Karte sofort entfernt. Die Position wird ohne zusätzlichen
  Geocoding-Aufruf aus Wetter-/Ortscache übernommen. Bei erstmals eingegebenen
  Orten steht sie nach der normalen oder manuellen Wetteraktualisierung bereit.
  Mehrdeutige, unbekannte und ausländische Orte erhalten keine Ersatzkarte von
  den damaligen Testort. Verspätete Ergebnisse des vorherigen Ortes werden verworfen.
- Eine transparente Radarfläche bedeutet „kein dargestelltes Echo“, nicht den
  sicheren Nachweis von Niederschlagsfreiheit. Radarabdeckung kann variieren.
  Ein Dienstfehler wird getrennt von einem erfolgreich abgerufenen leeren Bild
  angezeigt.
- Grundkarte: basemap.de-WMS beim BKG, Layer `de_basemapde_web_raster_grau`,
  Stil `default`, CC BY 4.0, Quellenvermerk „© GeoBasis-DE / BKG 2026“.
  DWD-Geodienst: Quellenvermerk Deutscher Wetterdienst. Die stilisierte graue
  Karte enthält keine Luftbilder und keine Höhenlinien. Der neue Kartenabruf
  für den damaligen Testort wurde zusammen mit dem DWD-Radar erfolgreich live geprüft.
- Der erklärende Fußnotenblock und die zusätzliche Quellenzeile sind auf Wunsch
  des Nutzers aus der privaten PC-Vorschau entfernt. Quellen, Lizenzangaben und
  die Erläuterung zu Radarechos bleiben in der README dokumentiert.
- `settings.py` enthält die kleine gemeinsame Einstellung für den gewählten Ort.
- Das Fenstermenü `Einstellungen` nimmt einen maskierten OpenWeather-Schlüssel an.
  `api_key_store.py` speichert ihn zusammen mit dem gewählten Ort in
  `private/settings.json`, relativ zum tatsächlichen Projektordner. `radar_map.py` legt öffentliche Kartenbilder in `private/cache/radar/` ab;
  `weather_service.py` speichert ortsbezogene aktuelle Beobachtungen ohne Schlüssel
  unter `private/cache/weather/`. Diese Pfade bleiben
  beim Verschieben des Wetterstation-Ordners gleich.
- `private/` ist in Git ausgeschlossen; OneDrive synchronisiert den Ordner dennoch
  als Teil des Projekts. Die Einstellungsdatei ist unverschlüsselt. Der gespeicherte
  Schlüssel wird im UI nicht angezeigt; leeres Speichern behält ihn bei, und Löschen
  ist eine eigene bestätigte Aktion. Das Speichern prüft nicht vorab die API-Gültigkeit.
- Eine einmalige Migration kopiert eine gültige alte Benutzerdatei nur, wenn
  `private/settings.json` noch nicht existiert; sie überschreibt/löscht keine Quelle.
  Unter Windows ist die frühere Quelle `%LOCALAPPDATA%\Wetterstation\settings.json`.
  Auf diesem Rechner gab es sie nicht, daher war nichts zu migrieren. Der alte
  lokale Karten-Cache wird nicht kopiert; Karten werden neu geladen.
- Aktuelle Daten und Vorhersage werden beim Start, höchstens alle zehn Minuten
  sowie manuell aktualisiert. Ortssuche bleibt getrennt über Geocoding; mehrdeutige
  Ortsnamen werden abgewiesen. Die Ortskoordinaten sowie aktuelle Daten, Stunden-
  und Tageswerte haben getrennte Cache-Dateien. Cachealter, lokale Datenzeit und
  Anbieterfehler werden angezeigt; bei Fehlern bleibt nur der Cache desselben Orts.
  Ein Ortswechsel entfernt sichtbare alte Daten sofort. One Call 4.0 `current`,
  `timeline/1h` und `timeline/1day` werden jeweils einmal pro Aktualisierung
  aufgerufen; vorbereitete `next`-/`prev`-Paginierungs-URLs werden nicht verfolgt.
  Sensoren bleiben Demo.
- One Call 4.0-Migration und Vorhersage sind umgesetzt und gegen offizielle
  Mock-Schemata geprüft. Der Nutzer berichtet, selbst auf das separate Abo „One
  Call API“ gewechselt und dort das Tageslimit auf 999 gesetzt zu haben; nicht
  unabhängig verifiziert, keine Kontoänderung vorgenommen. Am 18.10.2026 um
  18:04 Uhr Berliner Zeit wurde nach Ablauf der Erstinitialisierungssperre die
  One-Call-4.0-Anbindung live erfolgreich geprüft: `current`, `timeline/1h` und
  `timeline/1day` lieferten aktuelle Daten, acht Stundenwerte und fünf Tageswerte
  für den damaligen Testort. Die vorhandenen Ortskoordinaten wurden wiederverwendet; kein
  Geocoding und keine Pagination. Genau drei Aufrufe wurden über den bestehenden
  Gerätezähler reserviert (vorher 0/999, danach 3/999, Rest 996). Getrennte Caches
  wurden gespeichert und erfolgreich wieder eingelesen; der Wettercache enthält
  keinen API-Schlüssel. Schlüssel und Kontoeinstellungen wurden nicht geändert.
  Der schlüsselfreie Prüfbericht liegt unter
  `private/cache/weather/live-check-2026-10-18.json`.
- Vor jedem OpenWeather-Netzwerkversuch reserviert ein lokaler Budgetzähler
  dauerhaft einen Slot, gemeinsam für One Call 4.0 und Geocoding. Harte Grenze:
  999 pro deutschem Kalendertag, zusätzlich 999 pro UTC-Anbietertag und
  60 pro rollierendes 60-Sekundenfenster; Fehler/Timeouts zählen mit.
  Der Zähler liegt pro Gerät unter `private/openweather_budget/`, nutzt eine
  prozessübergreifende Dateisperre und atomare Speicherung. Ein lokaler Prüfspeicher
  erkennt auf demselben PC ältere OneDrive-Zählerstände und sperrt dann fail-closed.
  Nicht lesbare, ungültige oder nicht schreibbare Zustände erlauben keinen Abruf.
  Bei erstmaliger Einrichtung mit unbekanntem Tagesvorverbrauch bleibt die API bis
  nach 00:05 UTC des nächsten sicheren Provider-Resets gesperrt. DWD-/Grundkarten-WMS
  werden nicht mitgezählt.
- Der sichtbare Tageszähler wechselt jetzt um 00:00 Uhr in Europe/Berlin auf
  null, mit automatischer Sommer-/Winterzeit. Eine reine Budgetaktualisierung
  erneuert dann auch die PC-Anzeige ohne Wetterabruf. Die getrennte UTC-Schutzgrenze
  bleibt bis zum sicheren Anbieterreset um 00:05 UTC aktiv; ein lokaler Tageswechsel
  kann daher keinen weiteren Verbrauch über die Providergrenze hinaus freigeben.
- Die Gerätekennung verwendet unter Windows den tatsächlichen Benutzerordner
  aus den Windows-Einstellungen, unabhängig von einem umgeleiteten LOCALAPPDATA
  beim Start. Damit werden der vorhandene Geräte-Zähler und sein Prüfspeicher
  wiederverwendet. Die Pfadänderung allein hat die später beim Nutzer auftretende
  Startsperre jedoch nicht behoben (siehe Diagnose unten). Vor Umstellung lag der gültige Stand bei neun Abrufen;
  bestehende Abrufe werden bei der Migration konservativ übernommen. Datenmodell
  Version 2 trennt lokalen Tag/Zähler und UTC-Tag/Zähler; alte Programmprozesse
  müssen für die Verwendung der neuen Datei neu gestartet werden.
- Die erste Pfadkorrektur allein beseitigte die Startsperre beim Nutzer nicht
  zuverlässig. In der sichtbaren Vorschau stand weiterhin ein neuer Zähler mit
  Sperre, während der gültige Zähler 13 Abrufe enthielt. Der Starter legt deshalb
  den Budgetordner jetzt ausdrücklich als prozesslokale Einstellung unter dem
  Windows-Benutzerprofil fest; ein abweichender geerbter AppData-/Budgetpfad wird
  dabei überschrieben. Es wird keine globale Umgebungsvariable eingerichtet und
  kein API-Schlüssel über eine Variable übergeben. Ein ungültiger relativer
  Budgetpfad wird abgewiesen. Die bisherigen Zählerdateien bleiben unverändert
  erhalten; die Korrektur löscht keine Startsperren oder Abrufe aus fremden Zählern.
- Nach der Starterkorrektur bestehen alle 97 Tests. Die Vorschau wurde danach
  ausdrücklich über `start_preview.cmd` gestartet und ihr sichtbares Fenster
  geprüft: kein orangefarbener Startsperrhinweis, stattdessen 16/999 mit 983
  verbleibenden Abrufen. Der Stand stieg beim freigegebenen Diagnose-Neustart
  zuvor regulär von 13 auf 16; der abschließende Startertest verwendete den
  frischen Cache und erhöhte den Zähler nicht. Die genaue Windows-Umleitung
  im zuvor beendeten Prozess wurde nicht mehr direkt erfasst; verifiziert sind
  die unterschiedlichen Zählerzustände und die nun ausdrückliche Pfadbindung.
- Dieser Prüfstart war kein Beleg für den tatsächlichen Nutzerstart: Der Nutzer
  meldete die Sperre danach weiterhin. Die anschließende Diagnose direkt im
  Nutzerprozess zeigte trotz identischer Pfadangaben eine andere lokale
  Gerätekennung. Deren Projektzähler war tatsächlich noch uninitialisiert
  (`day=null`, `count=0`, `blocked_until` am 19.10.); die Agenten-Prüfstarts
  verwendeten den anderen, bereits aktiven Zähler. Daher halfen Pfadkorrekturen
  und erneute Agentenstarts nicht gegen die eigentliche Erstinitialisierung.
- Die ausdrücklich beauftragte Aufhebung wurde am 18.10.2026 gezielt auf diesen
  diagnostizierten Nutzerzähler angewandt: unter Dateisperre gültigen Zustand
  geprüft, alle 19 bekannten Projektabrufe konservativ übernommen, nur die
  Erstinitialisierung freigegeben und die Revision erhöht. Der Nutzerprozess
  führt seinen vorhandenen lokalen Prüfspeicher über den regulären Abgleich
  der neueren Projektdatei nach. Keine Gerätekennung wurde überschrieben,
  kein bestehender Verbrauch gelöscht und keine Grenzprüfung entfernt.
  Backup und schlüsselfreier Prüfvermerk liegen unter
  `private/qa/user-budget-before-activation.json` und
  `private/qa/user-budget-activation.json`.
- Beim folgenden echten Nutzerstart meldete die temporäre Prozessdiagnose
  `ready`, 19 Abrufe und keine Startsperre. Der Nutzer bestätigte ausdrücklich
  „Der Sperrtext ist verschwunden“. Der Diagnosecode und die temporären
  Diagnosehilfsprogramme wurden danach entfernt. Alle 98 Tests bestehen;
  zusätzlich geprüft wird der Spiegelabgleich nach freigegebener Initialisierung
  einschließlich Neustart und weiterhin wirksamer 999er-Grenze. Neue unbekannte
  Geräte bleiben regulär bis zum sicheren Reset gesperrt.
- Beim abschließenden Gesamttest trat unabhängig von der Zählersperre eine
  unvollständige HTTPS-Fehlerantwort der Handy-Seite auf: Früh abgewiesene
  POST-Anfragen ließen ihren kleinen Eingabekörper ungelesen, wodurch das
  Schließen der Verbindung die Fehlerantwort verwerfen konnte. Kleine,
  eindeutig längenbegrenzte Eingaben werden vor der Antwort jetzt verworfen
  (maximal 8192 Bytes; verarbeitet werden weiterhin höchstens 4096 Bytes).
  Authentifizierung und Herkunftsprüfung bleiben unverändert. Ein neuer Test
  prüft 30 aufeinanderfolgende Ablehnungen auf vollständige JSON-Antworten.
  Danach bestehen abschließend alle 99 Tests ohne echte Anbieterabrufe.
- Anschließend bestehen alle 89 Tests: lokaler Mitternachtswechsel, Sommer- und
  Winterzeit, 23-/25-Stunden-Tage, Erhalt des UTC-Limits, Neustart, korrupte lokale
  Zähler und stabile Gerätekennung sind mit isoliertem Speicher geprüft.
  Der freigegebene Start der aktualisierten PC-Vorschau war erfolgreich. Vorhandene
  neun Abrufe blieben erhalten; nach dem Start lagen 13/999 vor (Rest 986),
  einschließlich frischer aktueller Wetterdaten und Vorhersage für den gewählten
  Ort. Keine Konto- oder Schlüsseländerung; kein manuelles Nullsetzen bestehender
  Abrufe. Der Nutzer bestätigte zuvor auch die Ortskarten-/Handy-Korrekturen als
  funktionierend.
- Der 999-Zähler gilt nur für diese Projektkopie auf diesem PC. OneDrive liefert
  keine geräteübergreifende atomare Zählung; andere Programme mit demselben Konto
  und weitere PCs sind nicht erfasst. Der Nutzer berichtet, ein Kontolimit bereits
  eingestellt zu haben; dessen Produkt und Höhe wurden nicht geprüft oder geändert.
- `tests/test_openweather_budget.py` prüft Grenzwert, Tageswechsel, Neustart,
  Parallelität, Fehler und Zählerdefekte ausschließlich mit Mock-Transport und
  temporären Dateien; es werden keine echten Wetteranfragen für Tests gesendet.
- Vor der Erweiterung am 18.10.2026 bestanden alle 29 Tests. Vier zuvor datumsabhängige Budgettests
  verwenden jetzt für simulierte Abrufe dieselbe feste Uhrzeit wie für ihren
  vorbereiteten Zählerstand. Produktiver Zähler und Limits bleiben unverändert.
- Fehlerbehandlung erweitert; anschließend bestehen 57 Tests mit Dummy-Schlüsseln
  und isolierten temporären Dateien. Neue Fälle umfassen Authentifizierung,
  Überlastung, Timeouts, Serverfehler, beschädigte/übergroße Antworten, ungültige
  Messwerte, Cachedefekte, Schreibfehler, ungültige Budgetstände, beschädigte
  Kartenbilder und unerwartete Hintergrundfehler. Kein weiterer OpenWeather-
  Liveabruf war für diese Änderungen erforderlich. Ein zusätzlicher Test rendert
  alle vier Seiten sowie die skalierte Karte mit echtem Tk und synthetischen
  Bildern ohne Netzwerkzugriff bei 1000 × 650 und 1280 × 800 Pixeln.
- 401/403 pausieren weitere Wetteranfragen bis zum erneuten Speichern eines
  Schlüssels, Schlüsselwechsel oder Neustart. 429 beachtet `Retry-After`
  (mindestens 60 Sekunden, sonst 15 Minuten) für alle Endpunkte; Netzwerk-/5xx-
  Fehler verwenden pro Endpunkt wachsende Pausen von 60 Sekunden bis 30 Minuten.
  Pausen sind sitzungsbezogen; der dauerhafte 999/60-Zähler bleibt unverändert.
- Wettercaches gelten höchstens sechs Stunden ab Abruf. Einzelne defekte
  Vorhersageteile beeinflussen gültige andere Teile nicht. Leere/ungültige
  Antworten überschreiben keine guten Vorhersagen. Bei Cache-Schreibfehlern
  bleiben frisch abgerufene Daten mit Hinweis für die Sitzung nutzbar.
- PNG-Dekodierung und Pixelmaße werden mit Pillow geprüft; Radar-Ersatzcache ist
  auf 60 Minuten nach Abruf und Beobachtung begrenzt. Kartenkennung enthält die
  neue Grundkarte, atomarer Manifestwechsel verhindert gemischte Bilderstände.
  Auch bei Abruffehlern liegen automatische Kartenversuche fünf Minuten bei
  geöffneter Karte beziehungsweise 15 Minuten im Hintergrund auseinander.
- Die Kartenplanung verwendet einen gemeinsamen Timer und den letzten
  Abrufversuch. Ansichtswechsel passen dessen Frist an; wiederholtes Zeichnen
  verschiebt sie nicht und legt keinen weiteren Timer an. Hintergrundabrufe
  setzen die eindeutige Ortsposition voraus und verwenden nur DWD/BKG, ohne
  zusätzliche OpenWeather-Abfragen. Nach dieser Erweiterung bestehen alle
  95 Tests, einschließlich Hintergrundintervall, Wechsel beider Richtungen,
  früh aufgerufener Timer, Fehlerabstand sowie gesperrtem/geschlossenem Zustand.
- Hintergrundarbeiten liefern Ergebnisse über eine UI-Warteschlange; bei
  unerwarteten Fehlern werden Bedienelemente freigegeben und private Fehlerdetails
  unterdrückt. Dateiaustausch behandelt kurzzeitige Windows-Dateisperren mit
  begrenztem Wiederholen; fehlgeschlagene Budgetreservierung sperrt weiterhin HTTP.
- Mobile Einstellungen umgesetzt: Im PC-Einstellungsfenster öffnet „Handy-
  Einstellungen öffnen“ einen lokalen Verbindungsdialog. Der Dienst ist zunächst
  aus und wird nur per „Verbindung einschalten“ an eine konkrete lokale IPv4-
  Adresse gebunden. HTTPS, ein zufälliger Zugangscode, auf 20 Minuten begrenzte
  Sitzungen, begrenzte Anmeldeversuche sowie Host-/Origin-/CSRF-Prüfung schützen
  die Verbindung. Keine öffentlichen Adressen, keine Wildcard-Bindung und keine
  automatische Änderung von Firewall, Router oder Zertifikatsvertrauen.
- Die Handy-Seite kann Ort und Schlüssel gemeinsam atomar speichern. Ein leeres
  Schlüsselfeld behält den vorhandenen Schlüssel bei. Die Antworten enthalten nur
  den Ort und die Information, ob ein Schlüssel vorhanden ist; nie den Schlüssel.
  PC und Handy teilen sich Projekteinstellungen und lokale Dateisperren. Die
  PC-Vorschau übernimmt Änderungen über ihre UI-Warteschlange; ein Ortswechsel
  entfernt alte Ortsdaten sofort. Speichern sendet keine zusätzliche Wetteranfrage;
  die normale geplante oder manuelle Aktualisierung nutzt danach die Einstellung.
- Zertifikat und lokaler Zertifikatsschlüssel liegen unter `private/mobile/` und
  werden daher ebenfalls mit OneDrive synchronisiert. Ein eigenes Zertifikat
  erzeugt beim ersten Handy-Zugriff möglicherweise eine Browserwarnung. Sein
  Fingerabdruck steht im PC-Dialog; eine Vertrauensentscheidung trifft der Nutzer
  selbst. Beim Schließen des Verbindungsdialogs läuft der Dienst jetzt weiter;
  erneutes Öffnen zeigt dieselbe Verbindung und denselben Code. Erst „Ausschalten“
  oder Beenden der Vorschau beendet den Dienst und widerruft die Sitzungen.
  Auch ein noch laufender Verbindungsstart bleibt vom Dialog unabhängig.
- Neue Tests prüfen die reale lokale HTTPS-Verbindung mit temporär vertrautem
  Testzertifikat und Dummy-Schlüsseln sowie die Übernahme in echtem Tk ohne
  Wetterabruf. Die Browserprüfung lief separat mit deutlich gekennzeichneten
  Beispieldaten; die echten Projekteinstellungen wurden dafür nicht verwendet.
  Nach der mobilen Erweiterung bestehen insgesamt alle 73 Tests. Die Browser-
  Oberfläche wurde außerdem bei 375 und 320 Pixeln Breite ohne horizontales
  Überlaufen geprüft. Der Nutzer berichtet anschließend, die Seite auf seinem
  persönlichen Handy erfolgreich geöffnet zu haben. Das gemeldete Abschalten
  beim Schließen des PC-Dialogs war das bisherige Verhalten und wurde korrigiert.
- Nach Erweiterung der Ortskarten und Korrektur der Handy-Verbindung bestehen
  alle 80 Tests ohne Netzwerk-Wetterabrufe. Neue Prüfungen decken getrennte
  Ortscaches, identische Karten-/Radarausschnitte für Berlin und Hamburg,
  verworfene verspätete Ortsresultate, ausgeschlossene Auslandspositionen und
  die Wiederverwendung vorhandener Koordinaten ohne zusätzlichen API-Aufruf ab.
  Eine reale lokale HTTPS-Testsitzung mit Dummy-Einstellungen bleibt beim
  Schließen des Dialogs nutzbar und kann danach einen Ort speichern; auch
  Schließen/Wiederöffnen während eines Verbindungsstarts wird geprüft.
  Der öffentliche WMS-Abruf für Berlin wurde zusätzlich erfolgreich live
  geprüft (frische Grundkarte, Radar und Legende, Beobachtung 18.10.2026,
  20:15 UTC). Kein zusätzlicher OpenWeather-Aufruf; Budget unverändert.
- `start_preview.cmd` startet die Windows-Vorschau ohne sichtbares Terminal.
- `start_preview.cmd --mock-preview` zeigt ein klar markiertes 8-Stunden-/5-Tage-
  Raster mit ausschließlich synthetischen Daten. Wetter- und Karten-HTTP sind in
  diesem Modus deaktiviert; er dient zur Layout-/Funktionsprüfung ohne Anbieterabruf.

## Künftige Ideen, noch nicht zur Umsetzung freigegeben

- Am 26.10.2026 ausdrücklich als zukünftige Änderung vormerken: Programm an
  das „Waveshare 7.3inch E Ink Spectra 6 (E6) Full Color E-Paper Display“ mit
  800 × 480 Pixeln anpassen. Modell und Auflösung gemäß Nutzerangabe.
  Status: vorgemerkt, keine Freigabe zur Implementierung oder Hardwarebeschaffung.
  Konkreten Umfang von Anzeigeanpassung, Displayansteuerung und Aktualisierungs-
  verhalten vor Umsetzung festlegen. Bestehende PC-Vorschau bleibt erhalten.

- Am 26.10.2026 ausdrücklich zur späteren Umsetzung vormerken: eigenständig
  bedienbares grafisches Konfigurations- und Gestaltungswerkzeug für die
  Wetterstation. Ziel: alle dafür vorgesehenen Einstellungen selbst ändern und
  Widgets gestalten können, ohne Code bearbeiten oder jedes Mal die KI hinzuziehen
  zu müssen. Gewünscht sind insbesondere Hintergrundfarben der gesamten Anzeige
  und einzelner Widgets, Rahmenfarben/-dicken sowie Position und Ausrichtung der
  Inhalte innerhalb eines Widgets; weitere Darstellungsparameter und die allgemeine
  Wetterstationskonfiguration sollen im später festzulegenden Umfang zugänglich sein.
  Dies erweitert den vorhandenen Widget-Editor für Anordnung, Größe und Inhaltswahl
  um die Gestaltung innerhalb der Widgets und übergreifende Einstellungen.
  Anschließend präzisiert: Eine reine PC-Anwendung genügt ausdrücklich; eine Web-
  oder Handy-Version ist keine Anforderung. Später klären: weitere Parameter,
  Vorschau/Speicherung und Übernahme der Konfiguration auf den Pi. Sicherheits-,
  Schlüssel- und Budgetschutz dürfen durch allgemeine Gestaltungsregler nicht
  umgangen werden. „Alles konfigurieren“ bedeutet hier die vorgesehenen
  Programmeinstellungen, nicht beliebige neue Funktionen oder Hardwarefähigkeiten.
  Status: Nutzerwunsch aufgenommen; noch keine Freigabe zur Implementierung.

- Am 24.10.2026 zur Bewertung angefragt: privates GitHub-Repository für
  Programmcode, Tests und Dokumentation, einfachere Geräteübertragung und
  Entwicklung mit Codex Cloud. Empfehlung: private Laufzeitdaten ausschließen,
  Cloud nur mit Dummy-Daten prüfen und den gesicherten Pi-Updateweg erhalten.
  Repository-Erstellung, Upload und Cloud-Einrichtung sind noch nicht freigegeben.

- Vorschlag vom 18.10.2026: Die PC-Vorschau vor der nächsten Erweiterung gezielt
  auf längeren Betrieb, Neustart, Internetausfall und Wiederherstellung sowie
  konsistente Anzeige bei nur teilweise erfolgreicher Aktualisierung prüfen.
  Fehlerfälle zunächst mit simulierten Antworten prüfen; zusätzliche Live-
  oder Dauerabrufe sind durch diesen Vorschlag nicht freigegeben.
- Automatischer Ansichtswechsel als später optional einschaltbare Funktion.
- Physische Tasten, Markierung auffälliger Messwerte und gesonderte Datenanalyse.
- Cloud- und ML-Funktionen.

Diese Punkte sind vorgemerkt. Vor Implementierung ist eine konkrete Freigabe nötig.
Die Regenkarte und die erste mobile Konfiguration sind umgesetzt.

## Offene Entscheidungen

- Eine Reliefkarte mit Höhenlinien ist nicht umgesetzt; gewählt ist zunächst
  die helle farbige amtliche Straßenkarte nach Bildreferenz ohne Luftbild.
- Eingabetasten, Stromsparanforderungen und konkrete E-Ink-Anbindung. Das bisherige
  Display hat 1024 × 600 Pixel; als künftiges Ziel ist seit 26.10.2026 das Waveshare
  7.3inch E Ink Spectra 6 (E6) Full Color mit 800 × 480 Pixeln vorgemerkt.
- Erneute Alltagsprüfung der Handy-Verbindung nach Schließen des PC-Dialogs;
  der Nutzer hat den ersten Zugriff vom persönlichen Handy als funktionierend bestätigt.
- Konkrete Tarif-/Billing-Einstellungen des Nutzerkontos wurden nicht geprüft.
  Der Nutzer berichtet, das separate One-Call-Abo aktiviert und dessen Limit auf
  1000 pro Tag (aktuelle Mitteilung vom 23.10.2026) gesetzt zu haben; eine Kontoänderung wurde nicht vorgenommen.
  OpenWeather dokumentiert ein produktspezifisches Tageslimit und Reset zwischen
  00:00–00:05 UTC. Der Live-Zugriff wurde am 18.10.2026 erfolgreich geprüft;
  daraus folgt keine unabhängige Bestätigung der Kontogrenze.
