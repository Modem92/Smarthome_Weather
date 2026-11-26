# Wetterstation

Stand 24.10.2026: Die weiße passive Displayanzeige, automatische Handy-Verbindung
und browsergebundene Codes sind im PC-Workspace umgesetzt. Keine Pi-Übertragung
dieser Änderungen. Internationale Ortsauswahl, Regenkarte und Ortszeit sind im
PC-Workspace umgesetzt und offline geprüft. Diese Erweiterung wurde noch nicht
auf den Pi übertragen; vorhandene Transferarchive sind frühere Stände. Es gab
keine OpenWeather-Liveprüfung und keinen normalen Programmstart für diese Abnahme.
Prüfbilder und Berichte: `private/international-check/`.

Das vollständige Pi-Update einschließlich Widget-Layout ist separat vorbereitet:
siehe [PI_UPDATE.md](PI_UPDATE.md). Die Vorbereitung verändert den Pi nicht;
der neue Übertragungsstarter wird nur auf ausdrücklichen Auftrag ausgeführt.
Abnahme der Vorbereitung: 230 Tests bestanden, einschließlich 21 Update-/
Wiederherstellungsprüfungen mit Dummy-Einstellungen. Es wurde keine echte
Pi-Verbindung hergestellt und keine neue Wetterabfrage ausgelöst.

## Lokale Displayvorschau

Die Windows-Vorschau startet mit vier frei gestaltbaren Widget-Seiten. Die Wetterübersicht zeigt aktuelle
OpenWeather-One-Call-4.0-Beobachtungen und -Vorhersagen. Sensoren bleiben
Beispieldaten. Die Regenkarte zeigt für eindeutig aufgelöste Orte in Deutschland
eine helle amtliche Straßenkarte (basemap.de Web Raster Farbe, farblich angepasst) mit dem
aktuellen DWD-WN-Radarkomposit-Beobachtungslayer darüber. Die Karte stellt Orte,
Straßen und Landschaftsflächen stilisiert dar. Sie enthält kein Luft- oder
Satellitenbild und keine Höhenlinien. Wetter und Karte verwenden dieselbe
Ortsposition; die Karte benötigt keinen zusätzlichen OpenWeather-Aufruf.
Für ausländische Orte werden OpenStreetMap und RainViewer mit sichtbarer
Radar-Abdeckungsmaske verwendet. Ohne eindeutige Position im gewählten Land
verschwindet die alte Karte. Uhr, Datum und angezeigte Zeiten folgen der
Wetter-Ortszeit; solange diese unbekannt ist, steht ausdrücklich UTC dabei.

### Starten

`start_preview.cmd` doppelklicken. Der Starter verwendet auf diesem Rechner die
vorhandene Python-3.12-Laufzeit mit Tkinter; er installiert nichts. Falls diese
Laufzeit später nicht mehr vorhanden ist, sucht der Starter nach einer
Windows-Python-Installation mit Tkinter. `start_preview.cmd --show-rain-map`
öffnet direkt die echte Regenkartenansicht.
`start_preview.cmd --mock-preview` öffnet eine ausdrücklich als Demo markierte
Testansicht mit acht Stunden- und fünf Tageswerten; Wetter- und Kartenabrufe,
Schlüsseleinstellungen und Ortsänderungen sind darin deaktiviert.

**Widget-Bedienung sicher ausprobieren:** `start_widget_demo.cmd` doppelklicken
(entspricht `start_preview.cmd --widget-demo`). Dieser Start
verwendet ausschließlich Beispieldaten und einen getrennten temporären Speicher
unter `private/widget-demo/`. Die geschützte Handy-Verbindung startet automatisch,
sobald eine Heimnetz-Adresse vorliegt. Am Handy sind nur die Widgets
bearbeitbar, keine Ort-/Schlüsseleingaben. Die echten Einstellungen werden nicht
geöffnet oder verändert; es gibt keine Wetter-/Kartenabrufe. Beim Beenden wird
der temporäre Stand entfernt. Der normale Start speichert Layoutänderungen dauerhaft.

### Bedienung

- Das Display ist eine passive Anzeige ohne Tasten, Ortseingaben oder Dialoge.
  Wetter, Vorhersagen und Karten aktualisieren sich weiter automatisch.
- Weißer Hintergrund und schwarze/dunkelgraue Schrift. Widget-Rahmen sind dunkelgrau,
  bei 1024 × 600 zwei Pixel dick und auf größeren Displays entsprechend stärker.
  Titel, Werte und mehrzeilige Texte innerhalb der Widgets sind horizontal zentriert.
  Schriftgrößen werden anhand der gewählten Inhalte und tatsächlichen Widget-
  Fläche eingepasst; weniger Inhalte schaffen größere Werte. Ausblenden ändert
  weder Widget-Größe noch Rasterposition. Vorhersagen behalten alle Einträge.
- Acht Stunden beziehungsweise fünf Tage stehen immer in einer einzigen Reihe
  gleich breiter Spalten. Zeit-/Datumszeilen und Datenfelder haben über alle
  Spalten gemeinsame Zeilenpositionen. Nur zwischen diesen Vorhersagespalten
  erscheinen dünne senkrechte Linien; andere Widgets haben keine inneren Linien.
  Lange Beschreibungen umbrechen innerhalb ihrer Spalte; bei schmalen Widgets
  werden die Schriften passend kleiner. Es werden keine Stunden/Tage ausgeblendet.
- Die Handy-Vorschau zeigt ebenfalls stärkere Rahmen und zentrierte Widget-Titel.
  Kartenbeschriftungen, Quellen und Hinweise sind mittig ausgerichtet; die
  gewählte Abrufzeit einer alleinigen Regenkarte steht unten in der Mitte.
- Alle Fensterformen nutzen ihre gesamte Fläche. Referenz bleibt **1024 × 600**;
  Widget-Seiten passen vollständig ohne Scrollen. Die Handy-Vorschau übernimmt
  die tatsächlichen Displaymaße und dieselbe Rastergeometrie.
- Das Programm startet im Vollbild. **F11** wechselt zur PC-Fenstervorschau.
  Pfeiltasten bleiben für den manuellen Seitenwechsel verfügbar; die Seitenwahl
  am Handy zeigt ebenfalls die gewählte Seite. Wetterseiten wechseln nicht automatisch.
- Eine alleinige Regenkarte füllt weiterhin die gesamte Fläche. Ortsmarker,
  Quellenangaben, Versorgungs-/Altershinweise und gewählte Abrufzeit bleiben erhalten.
  Es gibt keinen Aktualisieren-Knopf und keine F5-Aktion.
- Ein anfragender, noch unangemeldeter Handy-Browser zeigt vorübergehend eine
  eigene Verbindungsseite am Display. Nach Anmeldung oder Codeablauf kehrt die
  Anzeige zur gewählten Wetterseite zurück. Am Display muss nichts bestätigt werden.

### Widgets und Seiten gestalten

Nach dem Anmelden mit dem Code vom Display erscheint
am Handy der Widget-Editor. Vier Startseiten sind vorbereitet: Wetterübersicht,
Vorhersage, Regenkarte und Sensoren. Sie verwenden ein unsichtbares Raster aus
zwölf Spalten und acht Zeilen. Jede Seite passt auf das Display mit 1024 × 600;
es gibt keine scrollbaren Widget-Seiten. Bis zu zwölf Seiten sind möglich.

- Seite antippen, um sie zu bearbeiten und gleichzeitig am Display anzuzeigen.
  Mit „+ Seite“, Seitenname und den Seitentasten anlegen, umbenennen oder umsortieren.
  „Entfernen“ löscht die ausgewählte Seite samt Widgets; die letzte Seite bleibt erhalten.
- Widget-Typ auswählen und „+ Widget“ verwenden. Einzelne Werte und kombinierte
  Widgets sind verfügbar, auch mehrfach. Sensorwerte bleiben ausdrücklich Demo.
- Widget ziehen, um es zu verschieben. Am Griff unten rechts die Größe aufziehen;
  Richtungstasten sowie Breiten-/Höhenregler erlauben feine Korrekturen.
- Nachbarn weichen innerhalb derselben Seite aus. Bei Platzmangel bleibt die
  bisherige Anordnung erhalten; der Editor bietet eine andere oder neue Seite an.
- Ein Widget antippen und seine Inhalts-Schalter bedienen. Ein ausgeblendetes
  Datum verändert beispielsweise die Größe des Uhr-Widgets nicht. Ohne sichtbare
  Inhalte bleibt das Widget leer und am Handy weiterhin auswählbar.
- Über die Zielseite kann ein Widget auf eine andere oder neue Seite verschoben
  werden. „Automatisch anordnen“ räumt die aktuelle Seite auf.
- Änderungen werden nach abgeschlossenen Gesten und Auswahlen automatisch
  gespeichert und am Display bestätigt. „Rückgängig“ erhält die letzten 20
  Änderungen der aktuellen Sitzung. Es gibt keinen zusätzlichen Übernehmen-Knopf.

Das Layout liegt versioniert unter `dashboard` in `private/settings.json`;
Ort und Schlüssel bleiben erhalten. Ein früher Einseiten-Entwurf wird beim Lesen
auf begrenzte Seiten verteilt, ohne das Original beim Start zu überschreiben.
Neustarts laden das gespeicherte Layout und beginnen auf der ersten Seite.
Fehlgeschlagene Übertragungen und gleichzeitige Bearbeitung durch andere Sitzungen
werden sichtbar gemeldet. Der lokale Entwurf bleibt bis zum Neuladen bzw. Schließen
erhalten, auch bei einer nötigen Neuanmeldung. „Erneut verbinden / speichern“
wiederholt die Übertragung; fremde Änderungen müssen zuerst neu geladen werden.
Widget-Bearbeitung löst keine zusätzlichen Wetter- oder Kartenabrufe aus.
- Bis zu drei dezente Pfeile zeigen den geschätzten Regenzug aus zwei
  aufeinanderfolgenden DWD-Radarbildern. Die Spitze zeigt in Bewegungsrichtung.
  Gleiche Pfeillänge bedeutet ausschließlich Richtung, keine Geschwindigkeit
  und keine Vorhersagestrecke. Ortsmarker und Bedienfeld bleiben frei.
  Ohne verlässliche Bewegung, bei Cache-Rückfall oder mehr als 15 Minuten alten
  Beobachtungen bleiben Pfeile aus. Eine fehlende Richtung ist kein Kartenfehler.
- Luftfeuchte, Wind und Luftdruck zeigen ihre Messwerte ohne zusätzliche
  farbige Quellenzeile. Beispieldaten und fehlende Messwerte sind gekennzeichnet.
- Es gibt keinen automatischen Seitenwechsel. Beim Start lädt die Wetterübersicht
  aktuelle OpenWeather-Daten, Stunden-/Tagesvorhersage und die Regenkarte im
  Hintergrund DWD-Radar und helle Grundkarte. Die Wetteraktualisierung läuft
  zu festen Fünf-Minuten-Terminen deutscher Zeit (00:00, 00:05, 00:10 usw.).
  Seitenwechsel lösen keine OpenWeather-Aufrufe aus. Internationale Grundkarten
  werden bedarfsgerecht erst beim Betrachten geladen, anschließend wiederverwendet.

Die Ortsauswahl wird beim Anwenden im Projektordner gespeichert und beim nächsten
Start wiederhergestellt. Die Ortsauswahl unterstützt Länder weltweit;
internationale Radarversorgung hängt von RainViewers verfügbarer Abdeckung ab.
Bei einem neuen Ort wird die Position während der nächsten normalen
Wetteraktualisierung ermittelt. Dann lädt die Karte diesen Ausschnitt; alte
Ergebnisse anderer Orte werden verworfen. Mehrdeutige Ortsnamen benötigen einen
eindeutigen Zusatz wie Postleitzahl oder Region innerhalb des gewählten Landes.
Der öffentliche Kartenabruf für Berlin wurde am 18.10.2026 zusätzlich live
geprüft; Grundkarte, Radar und Legende kamen frisch vom jeweiligen WMS.

### Einstellungen vom Handy

1. Wetterstation und Smartphone mit demselben Heimnetz verbinden. Der normale
   Programmstart aktiviert HTTPS im Hintergrund automatisch. Fehlt das Netzwerk
   oder ist Port 8765 belegt, erfolgt alle zehn Sekunden ein erneuter Versuch.
2. Die Adresse der Wetterstation öffnen und als Lesezeichen speichern, am bisherigen
   Pi beispielsweise **https://<Pi-Adresse>:8765**. Eine durch den Router geänderte
   Geräteadresse muss im Lesezeichen angepasst werden; es gibt keine Cloud-Suche.
3. Der unangemeldete Browser fordert automatisch einen eigenen Code an. Seine
   Kennung, zum Beispiel „Anfrage 01“, erscheint am Handy und auf einer weißen
   Verbindungsseite am Display. Den dortigen Code am Handy eingeben.
4. Nach der Anmeldung verschwindet der Code. Widgets gestalten oder unter
   **Verbindung & Ort → Ort und Wetterschlüssel ändern** Ort, Land und optional
   einen neuen Schlüssel speichern. Leer lassen behält den bestehenden Schlüssel.

Jeder Anmeldeversuch gehört zu genau einem Browser. Codes werden ausschließlich
am Display ausgegeben und sind einmalig für zwei Minuten gültig. Bis zu vier
Anfragen warten nacheinander; wartende Handys sehen ihre Position. Abgelaufene
Anfragen lassen sich über „Neuen Code anfordern“ erneut beginnen. Bereits
angemeldete Browser bleiben während weiterer Anmeldungen nutzbar.

Bis zu acht Browser können gleichzeitig angemeldet sein. Weitere Anmeldungen
verdrängen keine vorhandenen Sitzungen. Die bisherige 20-Minuten-Frist entfällt:
Anmeldungen gelten bis zum Abmelden oder Programmneustart. Alle Sitzungen und
Codes liegen ausschließlich im Arbeitsspeicher. Nach Stromunterbrechung oder
Neustart müssen sich alle Browser neu anmelden; ein erneutes Laden eines bereits
angemeldeten Browsers während desselben Programmlaufs erzeugt keinen Code.
Ein anderes Browserprofil oder ein anderer Browser gilt als eigene Anmeldung.

Der Dienst bindet ausschließlich an eine tatsächlich vorhandene Heimnetz-IPv4-
Adresse auf Port 8765, niemals öffentlich oder an eine Wildcard-Adresse. Linux
verwendet aktive Schnittstellen; Loopback bleibt isolierten Tests vorbehalten.
Bei Verlust/Wechsel der gebundenen Adresse wird der Dienst neu eingerichtet;
auch dabei werden bestehende Anmeldungen ungültig.

HTTPS verwendet das vorhandene lokale Zertifikat unter `private/mobile/`.
Eine Zertifikatswarnung beim ersten Öffnen wird ausschließlich am Handy geprüft
und bestätigt. Es gibt keine automatische Vertrauensinstallation, Firewall- oder
Routeränderung. Zugangscodes, begrenzte Versuche, geschützte Sitzungscookies,
Herkunftsprüfung und CSRF-Schutz bleiben aktiv. Der gespeicherte Wetterschlüssel
wird niemals zurückgegeben. Speichern startet keinen zusätzlichen Wetterabruf.
Die nächsten planmäßigen Abrufe verwenden den gespeicherten Ort und das Land.

Abnahme: 280 Tests bestanden, einschließlich 7 Tk-Prüfungen für einreihige
Vorhersagen, Trennlinien, vollständige Werte, Zentrierung, Rahmen und Zeitumstellung;
zusätzlicher Handy-Editor- und Mehrbrowser-Test
ohne Browserfehler oder externe Anfragen. Bilder unter `private/display-check/`.
Die Abnahme nutzt ausschließlich Dummy-Einstellungen, lokale HTTPS-Testserver
auf Loopback und getrennte Browserprofile. Tests starten keine Heimnetz-Verbindung.
Die Widget-Demo verwendet temporären Speicher und erlaubt nur Layoutänderungen.
Pillow, cryptography, tzdata und Tkinter müssen vorhanden sein; keine automatische
Paketinstallation. Die vorhandenen Pi-Archive enthalten diesen neuen Stand noch nicht.

### Regenkarte und Quellen

Die folgenden WMS-Angaben beschreiben die deutsche Karte. Für ausländische Orte
gilt der anschließende Abschnitt „Internationale Karte und Ortszeit“.

Beide WMS-Kartenbilder nutzen WMS 1.1.1 mit EPSG:4326 sowie identische Begrenzung und Pixelmaße. Die BBOX-Reihenfolge ist min. Länge, min. Breite, max. Länge, max. Breite.
Die Radarebene verwendet den DWD-Layer `dwd:Radar_wn-analysis_1x1km_ger` mit dem
Stil `radar_wn-analysis_1x1km_ger`. Das ist der WN-Analyse-Beobachtungslayer mit
Reflektivität, keine Wolkenkarte und keine Vorhersage. Der Beobachtungszeitpunkt
kommt aus den aktuellen WMS-Zeitmetadaten. Die Ebene wird beim Start sowie zu
festen Fünf-Minuten-Terminen deutscher Zeit aktualisiert: 00:00, 00:05, 00:10 usw.
Das gilt auf jeder Seite, einschließlich Hintergrundbetrieb. Wetter und Karte
verwenden dieselbe Berechnung der Zeitgrenzen, behalten aber getrennte Abrufe.
Seitenwechsel lösen keinen Abruf aus und verändern den Timer nicht. Manuelle
Abrufe und Abrufdauer verschieben das Raster nicht; gleichzeitige Auslöser werden
zusammengefasst. Nach Standby gibt es keine Serie nachgeholter Abrufe. Ohne
Ortsposition wird keine Kartenanfrage gesendet.

Im Normalbetrieb sind die Karte, ein dezenter Ortspunkt und unten mittig das
kleine Infofeld sichtbar. Es zeigt die Abrufzeit der angezeigten Karte: heute
`18:05`, bei einem früheren Kalendertag am Wetterort `22.10.2026 23:55`. Gemeint ist
der erfolgreiche Abruf (fetched_at), nicht die DWD-Beobachtungszeit. Erst mit dem
fertigen Kartenbild wechselt die Zeit; Fehlversuche, Cache-Rückfälle und
Größenänderungen verändern sie nicht. Ohne angezeigtes Bild steht dort
„Noch nicht aktualisiert“. Es gibt keine Taste zur manuellen Aktualisierung.
Im Demomodus erfolgen keine Abrufe. Das Feld bleibt auch bei Lade- und
Fehlerzuständen sichtbar. Veraltete Radardaten, Cacheprobleme und Abruffehler
erscheinen weiterhin oben links beziehungsweise ohne Bild als Lade-/Fehlermeldung.
Die DWD-/BKG-Anfragen verwenden weder den OpenWeather-Zähler noch dessen Transport;
die bestehende Wettergrenze von 1000 bleibt unverändert.
Eine Legende wird weder angezeigt noch heruntergeladen. Alte Karten-Caches
mit zusätzlichen Legendendateien bleiben verwendbar.

Die neue Darstellung folgt der Bildreferenz vom 23.10.2026. Nur die Radarflächen
werden weichgezeichnet; die Karte und ihre Beschriftung bleiben scharf. Die
Originalfarben des DWD-WN-Stils werden als geordnete Anzeigeklassen gelesen und
räumlich geglättet (Gaußfilter, Radius entsprechend etwa 0,65 km im Kartenausschnitt).
Die Deckungsfläche wird separat geglättet. So entstehen organische Konturen,
ausgefederte Ränder und kontinuierliche Übergänge von blassem Blau/Lila über
Türkis und Grün zu Gelbgrün und Gelb. Die maximale Deckkraft beträgt 158/255,
also rund 62 Prozent; zu den Rändern fällt sie gegen null ab. Transparente
Flächen bleiben ohne Regenfärbung, bekannte DWD-No-data-Bereiche werden nicht
mit Regen übermalt. Eine vollständig unbekannte Farbskala wird abgewiesen.

Die DWD-Stildefinition wurde über den öffentlichen GetStyles-Aufruf geprüft.
Dies ist eine visuelle Klassendarstellung, keine Umrechnung in mm/h; höhere
Originalklassen werden im gewünschten gelben Farbbereich gesättigt. Die
unveränderten ursprünglichen WMS-Bilder bleiben im Cache. Die Grundkarte wird
warm aufgehellt, violette Flächen zurückgenommen und kräftige Straßenblautöne
orange-gelb dargestellt; blassblaue Gewässer und blassgrüne Landschaftsflächen
bleiben erkennbar. Das ist eine farblich angepasste Darstellung der BKG-Daten,
keine neue Datenquelle und keine Änderung ihrer Geometrie. Alte Grau-/Luftbild-
Caches werden wegen der Layerkennung nicht als Farbkarte verwendet.

Der ausgewählte Ort erhält ein weißes, abgerundetes Namensschild mit dunkler
Schrift und einen orangefarbenen Punkt mit weißem Ring, jeweils über dem Radar.
Es wird der tatsächlich ausgewählte Ort verwendet; Hamburg ist nur das Beispiel
der Referenz. Das Infofeld steht entsprechend der zentrierten Widget-Darstellung unten mittig.

Fertige Kartenbilder bleiben im Arbeitsspeicher und werden beim Seitenwechsel
sofort wiederverwendet. Dekodierung, proportionale Skalierung und PNG-Aufbereitung
laufen nach einem Abruf bereits im Hintergrund, auch bei geschlossener Kartenseite.
Tk-Bilder werden einmalig im UI-Thread erzeugt; beim Seitenwechsel entfallen diese
Arbeitsschritte. Aufgelöste Ortskoordinaten werden nach dem Lesen aus dem Dateicache
im Speicher gehalten. Es entstehen keine zusätzlichen Wetter- oder Kartenabrufe.

Beim Vergrößern oder Verkleinern bleibt das vorhandene Bild zunächst zentriert
sichtbar, ohne die Ebenen zu verzerren. Die neue, fensterfüllende Darstellung wird
im Hintergrund vorbereitet: beide Ebenen identisch proportional skaliert und bei
Bedarf mittig beschnitten. Es laufen höchstens eine Vorbereitung und ein aktueller
Folgeauftrag; überholte Größen-/Ortsresultate werden verworfen. Auch ein schlechtes
neues Bild entfernt kein noch gültiges Kartenbild desselben Orts. Beim allerersten
Laden ohne fertiges Bild ist ein kurzer Vorbereitungshinweis möglich.
Größenänderungen lösen keine zusätzlichen Abrufe aus; der nächste geplante oder
manuelle Abruf nutzt passende Bildmaße innerhalb der bestehenden Größenlimits. Die Fenstergröße und der normale Windows-Fensterrahmen bleiben
vom Nutzer steuerbar. Ein
transparentes Radarbild bedeutet „kein dargestelltes Echo“ und beweist wegen
möglicher Abdeckungslücken nicht, dass es sicher niederschlagsfrei ist.
Die deutsche Karte der privaten PC-Vorschau zeigt auf ausdrücklichen Nutzerwunsch weder den erklärenden
Fußnotenblock noch eine zusätzliche Quellenzeile. Quellen und Lizenzangaben bleiben
nachfolgend dokumentiert. Dies bestätigt keine Ausnahme von den Nutzungsbedingungen.

Die Karte verwendet die mit dem Wetter gemeinsam aufgelösten Koordinaten. Bis
zur Auflösung des Startorts nutzt die Regenkarte einen fest hinterlegten Referenzpunkt.
Die helle farbige Grundkarte kommt über den [basemap.de-WMS](https://sgx.geodatenzentrum.de/wms_basemapde?SERVICE=WMS&REQUEST=GetCapabilities&VERSION=1.1.1),
Layer `de_basemapde_web_raster_farbe`, Stil `default`. Es gelten
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) und der Quellenvermerk
„© GeoBasis-DE / BKG 2026 · CC BY 4.0“. Produktbeschreibung und
[Nutzungsbedingungen](https://basemap.de/produkte-und-dienste/web-raster/) sind beim Anbieter dokumentiert.
Die Wetterebene stammt vom [DWD-WMS](https://maps.dwd.de/geoserver/wms?SERVICE=WMS&REQUEST=GetCapabilities&VERSION=1.3.0);
Quellenvermerk: „Datenbasis: Deutscher Wetterdienst“. Siehe auch die [DWD-Informationen zu Geodiensten](https://www.dwd.de/DE/leistungen/geodienste/help/nutzung_geodienste.html?lsbId=621762)
und den [WN-Produktsteckbrief](https://www.dwd.de/DE/leistungen/radarprodukte/radarkomposit_wn_hdf5.pdf?__blob=publicationFile&v=4).

### Internationale Karte und Ortszeit

Das Länderfeld enthält einen lokalen Katalog von 249 ISO-3166-1-Ländern/Gebieten
mit deutschen Namen (Anzeigenamen aus der vorhandenen ICU/Intl-Länderliste).
Auf dem PC filtert Tippen die Liste; per Pfeil nach unten lässt sie sich öffnen.
Auf dem Handy unterstützt das Länderfeld die native Such-/Vorschlagsliste des
Browsers. Ein nicht zugeordnetes Land kann nicht gespeichert werden. Intern
steht `country_code` neben `location` in `private/settings.json`. Beide werden
gemeinsam atomar gespeichert und aus derselben Datei-Momentaufnahme übernommen;
Schlüssel und Dashboard bleiben unverändert. Alte Einstellungen ohne Länderfeld
übernehmen ein erkennbares Land (ISO, deutscher oder englischer Name), sonst
werden bisherige unqualifizierte deutsche Eingaben Deutschland zugeordnet.
Ein unbekannter Länderzusatz oder eine ungültige gespeicherte ISO-Kennung
verlangt eine neue Auswahl, bevor Wetter oder Ortsposition abgefragt werden.

Die [OpenWeather-Ortssuche](https://openweathermap.org/api/geocoding-api) erhält
das ausgewählte ISO-Land sowohl für Namens- als auch Postleitzahlabfragen.
Unterstützt sind unter anderem `14467` (DE), `1010` (AT), `75001` (FR),
`SW1A 1AA` (GB), `10001`/`10001-1234` (US), `100-0001` (JP), `K1A 0B1` (CA)
und `1012 AB` (NL). Mehrdeutige Treffer innerhalb des Landes werden abgewiesen;
eine Postleitzahl oder Region hilft bei der Eingrenzung. Die Query enthält
stets das Land, auch für gleichnamige Orte. Alte landlose Caches werden nicht
ungeprüft als ausländische Daten übernommen. Orts-/Länderwechsel leert sichtbare
Wetter-/Vorhersage-/Karteninhalte sofort; alte Hintergrundresultate passen nicht
mehr zur aktuellen Arbeitsgeneration und werden verworfen. Die Karte verwendet
die bereits aufgelöste Wetterposition und fragt OpenWeather nicht selbst ab.

Außerhalb Deutschlands werden OSM und RainViewer aus deckungsgleichen
Web-Mercator-Kacheln zusammengesetzt. Festes Zoom 7 begrenzt die Detailauflösung
bewusst. Kacheln umschließen nur den benötigten Ausschnitt; Längengrade werden
an der Datumsgrenze umgebrochen. Die Karte endet bei ±85,051° Breite; außerhalb
erscheint ein Hinweis. Die Darstellung bleibt hell mit durchsichtigem Regen
und orange-weißem Marker über den Ebenen. Regenzug-Pfeile gibt es weiterhin
ausschließlich für DWD-Daten in Deutschland.

Die [RainViewer-Dokumentation](https://www.rainviewer.com/api/weather-maps-api.html)
beschreibt Beobachtungsbilder im Zehn-Minuten-Abstand sowie die Abdeckungsmaske.
Die App prüft die Metadaten im vorhandenen Fünf-Minuten-Raster; bei unverändertem
Bildzeitpunkt bleiben Bilder und Abrufanzeige gleich. Die schwarze Maskenfläche
bedeutet fehlende Versorgung: Sie erscheint schraffiert mit einem sichtbaren
Hinweis auf teilweise oder fehlende Radarversorgung, niemals als „kein Regen“.
Fehlt die Maske oder ist sie defekt, wird keine vermeintlich trockene neue Karte
angezeigt. Bei Ausfällen bleibt eine gültige Karte desselben Orts nach den
bestehenden 60-Minuten-Grenzen erhalten, einschließlich Abdeckung und Quellen.
Der RainViewer-Zeitpunkt bezeichnet die Frame-Erstellung, keine punktgenau
gleichzeitige Messung aller beteiligten Radare.

Die internationalen Karten tragen stets „© OpenStreetMap-Mitwirkende · RainViewer“;
auch Kartenwidgets können diese Quellenangabe nicht ausblenden. Siehe
[OSM-Mitwirkende und Lizenz](https://www.openstreetmap.org/copyright) sowie
[OSM-Kachelnutzung](https://operations.osmfoundation.org/policies/tiles/).
Der native Client identifiziert sich als `WetterstationPreview/2.0`, nutzt HTTPS
und HTTP-Cachefristen/ETag/Last-Modified mit bedingter Wiederholung. Ohne nutzbare
Frischeangaben bleiben OSM-Kacheln mindestens sieben Tage im Cache. Keine
Vorabdownloads, Gebietsarchive oder zusätzlichen Zoomstufen. Neue OSM-Kacheln
werden nur für eine betrachtete Karte geladen. Auf anderen Seiten können bereits
zwischengespeicherte Grundkarten weiterverwendet und RainViewer-Daten geprüft
werden; fehlt ein benötigtes OSM-Bild, wartet dessen Abruf bis zur Kartenanzeige.
Der öffentliche Cache liegt unter `private/cache/radar/international/`;
Manifest, Prüfsummen, Ortskennung und Bildmaße verhindern gemischte Bildstände.

Uhr, Datum, Vorhersagezeiten und Wetter-/Kartenabrufanzeigen verwenden die
IANA-Zeitzone aus Wetter-/Vorhersagedaten, einschließlich Sommerzeit und
Tagesgrenzen. Ohne nutzbare Zeitzone ist der Rückfall auf UTC sichtbar markiert.
Das feste Abrufraster bleibt unverändert; die deutschen und UTC-Budgettage
in `openweather_budget.py` hängen weiterhin nicht vom ausgewählten Wetterort ab.

Die Offline-Abnahme verwendet ausschließlich simulierte Antworten für den damaligen Testort,
Wien, Paris, London, New York und Tokio. Sie umfasst Länderwechsel und Neustart,
alte Einstellungen, geschütztes Handy-Speichern, Cachetrennung und verspätete
Ergebnisse, volle/teilweise/fehlende Versorgung, ungültige Masken, Dienstausfälle,
Datumsgrenze, hohe Breiten und Sommerzeit. Übersicht, Vorhersage und Karte wurden
bei 1024×600, die Handy-Seite bei 320/375 Pixeln visuell geprüft. Prüfungen und
synthetische Bilder liegen unter `private/international-check/`; die Browser-
Abnahme speichert Ort/Land, lädt neu und bestätigt das unveränderte Widget-Layout
und den erhaltenen Dummy-Schlüssel. Kein realer Schlüsselzugriff oder Liveabruf.
Für eine Wiederholung startet `tests/international_visual_check.py` ausschließlich
das gekennzeichnete temporäre Testfenster mit Loopback-HTTPS; anschließend prüft
`tests/international_browser_check.cjs` die Handy-Oberfläche. Die Testumgebung
schließt sich automatisch, spätestens nach fünf Minuten. Diese Skripte starten
nicht die normale Wetteranwendung. Die tatsächliche internationale Versorgung
und Erreichbarkeit der Anbieter sind damit nicht live abgenommen.

### Wettercache und Schlüssel

Karten-PNGs und Abrufmetadaten liegen unter `private/cache/radar/`; aktuelle
Wetterbeobachtungen, Vorhersagen und Ortskoordinaten liegen getrennt unter
`private/cache/weather/`. Die App nutzt One Call 4.0 `current`, `timeline/1h` und
`timeline/1day` sowie Geocoding nur, wenn die Koordinaten eines Orts noch fehlen.
Die Stunden- und Tageszeitleisten werden jeweils nur einmal abgefragt; vorbereitete
`next`-/`prev`-Links werden nie automatisch verfolgt. API-Schlüssel werden nicht
zwischengespeichert. One Call 4.0 gehört laut OpenWeather ausschließlich zum
separaten Abo „One Call API“; dessen dokumentierte kostenlose Tagesmenge und das
Konto-Limit sind von den älteren One-Call-Produkten getrennt. Details stehen in
der [4.0-Dokumentation](https://openweathermap.org/api/one-call-4) und der
[OpenWeather-FAQ](https://openweathermap.org/faq). Der Nutzer teilt mit, das neue
Abo selbst aktiviert und dessen Tageslimit auf 1000 gesetzt zu haben (Mitteilung
vom 23.10.2026); Konto und
Limit wurden hier nicht eingesehen oder geändert.

### OpenWeather-Schlüssel

Über **Verbindung & Ort** am Smartphone kann der Nutzer einen OpenWeather-Schlüssel eingeben.
Die gemeinsamen Projekteinstellungen liegen in `private/settings.json`, relativ
zum Wetterstation-Projektordner. Dort werden Schlüssel und Ort gemeinsam gespeichert.
Die Datei wird angelegt, sobald ein Ort angewendet oder ein Schlüssel gespeichert wird.
Die Datei ist unverschlüsselt. OneDrive synchronisiert sie zusammen mit dem Projekt
auf weitere Computer. Git ignoriert `private/`; das schaltet OneDrive-Synchronisierung
nicht ab. Python muss auf jedem Computer verfügbar sein. Eine Windows-Umgebungsvariable
ist nicht erforderlich. Der Schlüssel wird im UI nie angezeigt; ein leeres Feld
überschreibt ihn nicht. Speichern prüft
nicht vorab die API-Gültigkeit. Beim Start erscheinen vorhandene Wetterdaten sofort;
fehlende oder mindestens fünf Minuten alte Daten werden nachgeladen. Danach laufen
Wetter und beide Vorhersagen gemeinsam zu festen Terminen: 00:00, 00:05, 00:10 usw.
(Europe/Berlin). Jeder vollständige Lauf sendet drei Wetteranfragen, auch wenn kurz
zuvor manuell aktualisiert wurde. Geocoding kommt nur bei unbekannten Koordinaten
hinzu. Laufzeiten und manuelle Abrufe verschieben das Raster nicht. Gleichzeitige
Auslöser werden zusammengefasst; nach Standby gibt es keine nachträglichen
Abrufserien. Ein Ortswechsel verwirft sofort die sichtbaren Werte des alten Orts.

Die Wetterübersicht zeigt keine obere Abrufzeit oder technische Statuszeile.
Fehlende Werte und Demo-Daten bleiben innerhalb ihrer Widgets erkennbar.
Die Anzeige von Kartenalter, Quellen und fehlender Radarversorgung bleibt erhalten.

Jeder ausgehende One-Call- oder Geocoding-Aufruf dieser Projektkopie reserviert
vor dem Senden dauerhaft einen Slot. Das lokale harte Limit beträgt 1000 Aufrufe
pro deutschem Kalendertag, zusätzlich 1000 pro UTC-Anbietertag sowie 60 in jedem
rollierenden 60-Sekundenfenster; Stunden- und
Tagesvorhersage, aktuelle Daten, Geocoding und Fehler teilen sich den Zähler.
Zeitüberschreitungen und HTTP-Fehler zählen mit. Der Zähler liegt unter
`private/openweather_budget/` und wird mit Dateisperre, atomarem Schreiben und
lokalem Prüfspeicher vor einem unbemerkten Rücksprung auf einen älteren OneDrive-
Stand geschützt. Ist der Zähler beschädigt, nicht schreibbar oder widersprüchlich,
wird OpenWeather gesperrt.

Bei der ersten Einrichtung ist der bisherige Verbrauch dieses Tages unbekannt.
Deshalb sperrt die App neue OpenWeather-Anfragen bis nach dem nächsten
OpenWeather-Resetfenster zwischen 00:00 und 00:05 UTC; sie gibt erst ab 00:05 UTC
frei. Unter Windows wird dafür die Gerätekennung im tatsächlichen Benutzerordner
wiederverwendet, auch wenn ein Starter die Umgebungsvariable LOCALAPPDATA umleitet.
Identische Pfadangaben garantieren jedoch keinen gemeinsamen lokalen
Gerätespeicher über verschiedene Ausführungsumgebungen hinweg.
Der normale Starter legt seinen Budgetordner zusätzlich ausdrücklich unter
`%USERPROFILE%\AppData\Local\Wetterstation\openweather-budget` fest. Dafür setzt
er `WETTERSTATION_BUDGET_ROOT` ausschließlich für den gestarteten Prozess;
geerbte abweichende Werte werden ersetzt. Das ist keine globale Einstellung
und enthält keinen API-Schlüssel. Der vorhandene Zähler samt Prüfspeicher wird
weiterverwendet. Eine bereits gespeicherte Erstinitialisierungssperre wird durch
eine reine Pfadanpassung nicht aufgehoben.

Die vom Nutzer am 18.10.2026 ausdrücklich freigegebene Startsperre wurde nach
Diagnose seines tatsächlichen Programmstarts gezielt aufgehoben. Dabei wurden
die 19 bereits bekannten Projektabrufe konservativ übernommen; Tages- und
Minutenlimits sowie der lokale Prüfspeicher bleiben aktiv. Der Nutzer hat nach
erneutem Start bestätigt, dass der Sperrtext verschwunden ist. Für neue Geräte
mit unbekanntem Verbrauch gilt weiterhin die normale Erstinitialisierung.

Der interne Tageszähler setzt sich um **00:00 Uhr deutscher Zeit** zurück
(Europe/Berlin, automatisch Sommer-/Winterzeit), bevor die erste Anfrage des neuen
Tages reserviert wird. Bei einem vollständigen Lauf um 00:00 Uhr zählt er danach
3 und nach dem Lauf um 00:05 Uhr 6, sofern keine zusätzlichen Abrufe oder Sperren
vorliegen. Nach einer ausgeschalteten Nacht gilt beim nächsten Start ebenfalls
der neue Tag. Die Wetterübersicht zeigt keinen Zähler mehr. Bestehende Historie
und Prüfspeicher bleiben beim Wechsel von 999 auf 1000 erhalten; Anfrage 1000
ist erlaubt, Anfrage 1001 wird lokal vor dem Senden blockiert.

Zusätzlich bleibt der Zähler für den UTC-Anbietertag geschützt. Der lokale
Mitternachtswechsel setzt diesen zweiten Zähler nicht zurück; er wird erst nach
dem sicheren Anbieterreset um 00:05 UTC freigegeben. So erzeugt der frühere lokale
Tageswechsel keine zusätzlichen Aufrufe über die bisherige Anbietergrenze hinaus.
Intern gilt die kleinere Restmenge beider Tagesgrenzen. Diese lokale Grenze
zählt keine Anfragen anderer Programme oder weiterer Computer. OneDrive ist kein
atomarer gemeinsamer Zähler über Geräte. OpenWeather setzt Pay-as-you-Call-Limits
im Konto pro Produkt und über alle API-Schlüssel des Kontos durch; die FAQ nennt
den Reset zwischen 00:00 und 00:05 UTC. Der Nutzer hat laut eigener Angabe im
neuen One-Call-Abo 1000 pro Tag gesetzt (Mitteilung vom 23.10.2026). Diese
Kontoeinstellung bleibt ungeprüft. Der lokale Schutz bleibt unabhängig davon aktiv;
Anbieter-Resetpause, Minutenlimit und Fehlerpausen können Abruftermine aussetzen.
Für andere Anwendungen und Geräte gilt ausschließlich deren Nutzung im
gemeinsamen Kontolimit; der lokale Zähler erfasst nur diese Projektkopie auf
diesem PC und ersetzt die Kontogrenze nicht.

Die Migration auf One Call 4.0 ist im Code umgesetzt und mit offiziellen
Mock-Schemata geprüft. Die ausdrücklich beauftragte Live-Prüfung für den damaligen Testort
war am 18.10.2026 um 18:04 Uhr Berliner Zeit erfolgreich: `current`, `timeline/1h`
und `timeline/1day` lieferten aktuelle Daten, acht Stundenwerte und fünf Tageswerte.
Ohne zusätzliches Geocoding oder Pagination wurden genau drei Aufrufe über den
bestehenden Gerätezähler verbucht: Stand unmittelbar danach 3/999, Rest 996.
Die getrennten Wettercaches konnten unverändert wieder eingelesen werden und
enthielten keinen API-Schlüssel. Der schlüsselfreie Prüfbericht liegt unter
`private/cache/weather/live-check-2026-10-18.json`. Das Kontolimit selbst wurde
nicht eingesehen oder geändert. Nach Erweiterung der deutschen Ortskarten und
Korrektur der Lebensdauer des Handy-Dienstes sowie lokalem Mitternachtswechsel
und stabiler Geräteerkennung sowie Hintergrund-Kartenaktualisierung bestehen
107 Tests einschließlich fensterfüllender Kartenansicht, Größenwechsel,
Kartenebenen ohne Verzerrung, Tastatursteuerung, Legacy-Cache ohne Legende,
Eingabefokus und Pfeiltastenbedienung,
Starter-Pfadbindung, Spiegelabgleich nach einer freigegebenen Initialisierung
und vollständigen HTTPS-Fehlerantworten.
Die Budgettests verwenden
eine feste Testuhr, damit ein realer Datumswechsel ihre simulierten Abrufe nicht
auf einen anderen Zählertag verschiebt. Die Tests verwenden ausschließlich
Dummy-Schlüssel, Mock-Transport und getrennte temporäre Dateien.

### Verhalten bei Fehlern

- Bei HTTP 401/403 pausiert der OpenWeather-Client weitere Abrufe bis zum erneuten
  Speichern eines Schlüssels, einem Schlüsselwechsel oder Neustart. Speichern
  sendet selbst keine Anfrage. Die automatische Prüfung erfolgt weiter im
  normalen Aktualisierungstakt.
- HTTP 429 sperrt alle OpenWeather-Endpunkte dieses Clients für `Retry-After`
  (Sekunden oder HTTP-Datum), mindestens 60 Sekunden; ohne gültigen Wert für
  15 Minuten. Netzwerkfehler und HTTP 5xx pausieren nur den betroffenen Endpunkt,
  zunächst 60 Sekunden und bei wiederholten Fehlern bis höchstens 30 Minuten.
  Manuelles Aktualisieren umgeht diese Pausen nicht. Pausen gelten für die
  laufende Sitzung; die dauerhaften Budgetlimits gelten weiterhin über Neustarts.
- Fehlerhafte, übergroße und unvollständige Antworten werden abgewiesen. Leere
  oder komplett ungültige Vorhersagen ersetzen keinen guten Cache. Ein beschädigter
  Stunden-Cache verwirft nicht die weiterhin gültige Tagesvorhersage.
- Wettercaches werden höchstens sechs Stunden nach ihrem Abruf angezeigt.
  Defekte, erheblich in die Zukunft datierte oder zeitlich nicht zuordenbare
  Cachedateien werden ignoriert. Ohne gültige Werte zeigt die App einen Fehler.
- Scheitert nur das Speichern, bleiben erfolgreich geladene Daten für die
  Sitzung nutzbar; die Oberfläche zeigt einen Speicherhinweis. Scheitert dagegen
  die sichere Budgetreservierung, wird keine Wetteranfrage gesendet.
- Kartenbilder werden vor der Anzeige auf PNG-Inhalt, Dekodierbarkeit und
  passende Pixelmaße geprüft. Ein Karten-Cache darf höchstens 60 Minuten alt
  sein (Abruf- und Beobachtungszeit). Seine Kennung enthält auch die Grundkarte;
  alte Luftbildcaches werden nicht als Ersatz verwendet. Ein zuletzt atomar
  geschriebener Manifeststand verhindert gemischte Bildstände nach Abbrüchen.
- Die Beobachtungszeit wird aus einer gezielten, kleinen DWD-Metadatenantwort
  für den Radar-Layer gelesen. Bei einem Fehler nennt die Anzeige den betroffenen
  Schritt: DWD-Metadaten, helle Grundkarte oder DWD-Radar. Auch nach einer
  Größenänderung bleibt eine zuvor angezeigte passende Karte bei Abruffehlern
  sichtbar, solange Abruf und Beobachtung höchstens 60 Minuten alt sind.
  Sie trägt einen Hinweis auf zwischengespeicherte Daten. Die nächste planmäßige
  Aktualisierung versucht es erneut; nach Erfolg verschwindet der Hinweis.
- Automatische Kartenversuche bleiben auch nach Fehlern auf den festen
  Fünf-Minuten-Terminen deutscher Zeit. Ein verspäteter Abruf führt anschließend
  zum nächsten festen Termin; verpasste Termine werden nicht gesammelt nachgeholt.
  Ergebnisse aus Hintergrundthreads werden im UI-Thread übernommen; unerwartete
  Arbeitsfehler geben die Aktualisierung wieder frei und zeigen einen allgemeinen
  Hinweis ohne private Fehlerdetails. Beim Schließen werden anstehende UI-Aufträge
  verworfen. Eine vollständige Garantie gegen Prozessabbruch, Betriebssystemfehler
  oder Hardwareausfälle ist damit nicht verbunden.

Die Kartenprüfung benötigt Pillow, das in der hier verwendeten Python-Laufzeit
bereits vorhanden ist. Auf einem anderen Rechner ohne Pillow erscheint ein
Hinweis; die Wetteransichten bleiben davon unabhängig.

### Regenzug-Pfeile

Die Auswertung vergleicht ursprüngliche DWD-Farbklassen auf einem geografisch
ausgerichteten Raster von ungefähr einem Kilometer, vor der weichen Darstellung.
Normalisierte Kreuzkorrelation kleiner überlappender Ausschnitte, eindeutige
Treffer, Rückwärtsprüfung und benachbarte übereinstimmende Bewegungen begrenzen
Fehlanzeigen. Gleichförmige oder mehrdeutige Muster, Stillstand, neu entstehender
oder verschwindender Regen können deshalb ohne Pfeile bleiben. Das ist eine
vorsichtige Schätzung der zuletzt beobachteten Bewegung, keine garantierte
Niederschlagsvorhersage und keine Darstellung des Bodenwinds.

Es werden nur Bilder desselben Orts mit fünf oder zehn Minuten Abstand genutzt.
Beim Start, Ortswechsel und nach längeren Unterbrechungen wird nötigenfalls
ein fünf Minuten älteres Radarbild über den vorhandenen DWD-WMS nachgeladen.
Vorhandene Aufnahmen aus Speicher oder Dateicache haben Vorrang. Das ältere
Bild ersetzt weder die aktuelle Karte noch deren Abrufzeit. Fehler im Zusatzabruf
bleiben ohne zusätzlichen Hinweis; erneuter Versuch frühestens im nächsten
Fünf-Minuten-Slot. Keine zusätzlichen Grundkarten- oder OpenWeather-Anfragen.

Neue Karten erscheinen unabhängig von der Analyse. Diese läuft auf allen Seiten
im Hintergrund mit einem laufenden Auftrag und höchstens dem neuesten Folgeauftrag.
Seitenwechsel verwenden die fertigen Bilder und Vektoren erneut; Größenänderungen
rechnen nur deren Darstellung um. Keine neuen Abhängigkeiten oder Abruf-Timer.
Im Demomodus werden auch keine Vergleichsbilder geladen.

Offline-Prüfung der Regenzug-Pfeile am 23.10.2026: 184 Tests bestanden.
Synthetische Bewegungen in acht Richtungen (maximal 15 Grad Abweichung),
gegensätzlich ziehende Gebiete, Intensitätsänderungen und unsichere Muster sowie
Zeit-, Cache-, Geometrie- und Hintergrundfälle geprüft. Sichtprüfung echter
Tk-Fenster bei 1024×600, 480×800 und 360×600 mit synthetischer Karte und Regen.
30 Seitenwechsel mit vorbereiteten Bildern: Median 16,80 ms, P95 18,35 ms,
Maximum 20,92 ms; weitere 30 bei laufender Analyse: Median 16,77 ms,
P95 22,66 ms, Maximum 60,07 ms. Die Analyse des Testmusters dauerte rund 388 ms
im Hintergrund. Keine Wetter-/Karten-Liveabrufe, kein Schlüsselzugriff und keine
Pi-Übertragung oder Pi-Leistungsmessung. Frühere Testberichte folgen unverändert.

Aktuelle Prüfung der neuen Radargestaltung vom 23.10.2026: Alle 168
automatisierten Tests bestehen. Zusätzlich geprüft werden weiche Außenränder,
kontinuierliche Farbwechsel, alle DWD-Farbklassen, begrenzte Deckkraft, sichtbarer
Kartenuntergrund, transparente Trocken-/No-data-Flächen, unbekannte Farbskalen,
warme Kartenfarben, alte Grau-Caches und die Lage von Ortsname/Marker über dem
Radar. Die tatsächlichen Tk-Fenster wurden bei 1024 × 600, 600 × 800 und
360 × 600 mit einer amtlichen Hamburg-Grundkarte und deutlich gekennzeichnetem
synthetischem Regen visuell geprüft. 30 Seitenwechsel im sichtbaren PC-Fenster:
18,56 ms Median, 20,75 ms im 95. Perzentil, 23,46 ms Maximum. Keine Pi-Messung.
Für die Stilprüfung wurden öffentliche DWD-Stil-/Legendeninformationen und eine
BKG-Farbkarte abgerufen. Keine OpenWeather-Anfrage, kein Schlüsselzugriff,
keine Pi-Übertragung und keine neue Abhängigkeit.

Bei der vorherigen Änderung von Radar-Takt/Infofeld bestanden 159 Tests.
Neue Fälle prüfen das gemeinsame Fünf-Minuten-Raster einschließlich Mitternacht,
Zeitumstellungen, Hintergrundbetrieb und Standby sowie unveränderte Timer bei
Seitenwechseln, Abrufzeit/Bildübernahme, Fehler, Cache-Rückfall, Demo und den
vom OpenWeather-Transport/Zähler getrennten WMS-Client. Das Infofeld wurde mit
synthetischen Bildern bei 1024 × 600, 600 × 800 und 360 × 600 visuell geprüft.
Ein sichtbarer PC-Test mit Infofeld bei 1024 × 600 ergab bei 30 Seitenwechseln
13,15 ms Median, 16,26 ms im 95. Perzentil und 17,49 ms Maximum. Keine Liveabrufe
oder Pi-Übertragung; diese Messung ist keine gemessene Pi-Laufzeit.

Bei der vorherigen Radaroptimierung bestanden 150 Tests.
Die Radaroptimierung prüft Wiederverwendung, Hintergrundvorbereitung, überholte
Größen-/Ortsresultate, Thread-Zuständigkeit, Bildfehler, Transparenz und Programmende.
Synthetische Karten wurden bei 1024 × 600 und 600 × 800 visuell geprüft.
Der Vergleich mit identischen synthetischen Bildern bei 1024 × 600 im verborgenen
Tk-Fenster sank von 366,9 ms auf 0,20 ms Median; 95. Perzentil 0,32 ms,
Maximum 14,68 ms bei 30 Wechseln. Eine ergänzende Messung im sichtbaren Tk-Fenster
mit synthetischem Kartengitter ergab 11,61 ms Median, 12,58 ms im 95. Perzentil
und 13,47 ms Maximum (30 Wechsel). Das sind PC-Messungen, keine Pi-Leistungszusage.
Keine echten Wetter-/Kartenabrufe, keine neuen Bibliotheken und keine Übertragung
auf den Pi. Bei der vorherigen Wetterübersichtsänderung bestanden 140 Tests;
deren Sichtprüfung erfolgte bei 1024 × 600 und 600 × 600, das Layout zusätzlich
bis 360 Pixel Breite. Ältere Testzahlen unten sind historische Stände.

Tests lokal ausführen: `python -m unittest discover -s tests -v`.

Die Widget-Erweiterung vom 24.10.2026 wird mit Modell-/Speicher-/HTTPS- und echten
Tk-Prüfungen sowie einer durchgehenden Browserprüfung abgenommen. Die Browser-
prüfung startet separat `python tests/widget_demo.py` und anschließend
`node tests/widget_browser_check.cjs` (Playwright und ein vorhandener Chromium-
Browser erforderlich; keine Installation durch das Testskript). Der Prüfserver
verwendet ausschließlich Loopback-HTTPS, Dummy-Werte und temporären Speicher.
Er beendet sich nach spätestens 15 Minuten; ein `stop.request` unter
`private/widget-check/` beendet ihn früher. Dort liegen auch Browser-Prüfbericht,
Handy-Bilder und die native Displayaufnahme. Die Prüfung sendet keine externen
Browser-Anfragen. Eine Übertragung auf den Pi wurde nicht vorgenommen.
Der abschließende Gesamtlauf besteht aus **209 bestandenen Tests**. Die Browser-
Abnahme mit Touch-Gesten und Display-Bestätigung besteht ebenfalls; bei 320/375
Pixeln Breite wurden keine horizontalen Überläufe oder Konsolenfehler festgestellt.

Beim ersten Start wird eine gültige alte Benutzereinstellung einmalig nach
`private/settings.json` kopiert, aber nur, wenn diese Projektdatei noch nicht
existiert. Eine vorhandene Projekteinstellung hat Vorrang; die alte Quelle wird
weder überschrieben noch gelöscht. Auf dem Entwicklungsrechner war keine alte
lokale Einstellungsdatei (Windows: `%LOCALAPPDATA%\Wetterstation\settings.json`)
vorhanden, daher wurde nichts migriert. Ein alter lokaler Karten-Cache wird nicht
kopiert; die Karten werden neu geladen.

Das vorgesehene Display hat 1024 × 600 Pixel. Die Vorschau startet im Vollbild;
nach F11 steht ein veränderbares Fenster mit zunächst 1024 × 600 Pixeln bereit.
Andere Auflösungen und Fensterformen werden durch Skalierung und Umbruch
unterstützt. Der tatsächliche Hardwaretest und eine spätere E-Ink-Anpassung
stehen weiterhin aus. Alle 125 Tests bestehen; die Layoutprüfung verwendet
ausschließlich Beispieldaten und getrennten temporären Speicher.

## Projektstand und spätere Schritte

Python ist die Basis für die Vorschau. Als mögliche spätere Zielhardware gilt
vorläufig ein Raspberry Pi unter Linux mit Netzversorgung; stromsparendere
Alternativen bleiben offen. Das spätere Ziel verbindet Internet-Wetterdaten und
eigene Außensensoren. Übersicht und Vorhersage nutzen One Call 4.0; die
Sensoranbindung bleibt Demo. Die Regenkarte nutzt Live-WMS-Dienste und speichert ihren öffentlichen Cache
im Projektordner. Eine langfristige Speicherung von Messwerten gibt es noch nicht.
Die Anzeige ist für 1024 × 600 vorbereitet und passt sich an andere verfügbare
Flächen an; der Betrieb auf dem tatsächlichen Display muss noch geprüft werden.

Den bestätigten Stand, offene Entscheidungen und nur vorgemerkte Ideen hält
[PROJEKTPLAN.md](PROJEKTPLAN.md) fest. Neue Ideen dort zu dokumentieren bedeutet
nicht automatisch, dass ihre Umsetzung freigegeben ist.
