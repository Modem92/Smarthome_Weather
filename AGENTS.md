# Arbeitsregeln für dieses Projekt

- Am 25.10.2026 freigegeben: gemeinsame Programmstruktur mit Windows-/Pi-Startern
  und manueller Doppelklick-Updater gemäß `docs/UPDATE.md`. Eingefrorenen Stand
  offline prüfen, vollständig bereitstellen, eindeutig erkannte Anwendung geordnet
  beenden, sichern und installieren. Nur eine vorher laufende Anwendung nach Erfolg
  im bisherigen Modus wieder starten (Liveabrufe dabei vom Nutzer akzeptiert).
  Pi-Layout, private Daten und Budgetidentitäten erhalten. SSH-Schlüssel außerhalb
  OneDrive mit Windows-Schlüsseldienst und einmaliger interaktiver Einrichtung.
  Kein Zeitplan, Updater-Autostart, Betriebssystem-/Paketupdate oder GitHub-Upload.

- Lies `PROJEKTPLAN.md` vor Änderungen und halte bestätigte, umgesetzte,
  vorgemerkte und offene Punkte getrennt.
- Dokumentiere neue Ideen dort, aber implementiere sie nur nach ausdrücklicher
  Freigabe ihres Umfangs.
- Am 24.10.2026 ausdrücklich beauftragt: internationale Ortsauswahl auf PC und
  Handy, gemeinsame Speicherung von Ort und ISO-Land, nach Ländern getrennte
  Orts-/Wettercaches und Anzeige aller Uhr-/Kalenderzeiten in der Wetter-Ortszeit
  (bei unbekannter Zeitzone ausdrücklich UTC). Diese Freigabe ersetzt den früheren
  Ausschluss ausländischer Orte. Deutschland behält BKG/DWD; im Ausland werden
  bedarfsgerecht OpenStreetMap-Kacheln und RainViewer-Beobachtungen samt
  Abdeckungsmaske bis Zoom 7 verwendet. Quellenangaben auf internationalen Karten
  sichtbar erhalten; OSM mit Anwendungskennung, HTTP-Cache und ohne Vorabdownloads.
  Radar außerhalb der Abdeckung nie als trocken darstellen. Regenzug-Pfeile
  bleiben auf DWD beschränkt. Abrufraster und geschützte Budgettage unverändert.
  Zunächst nur Umsetzung und Offline-Abnahme im PC-Workspace: keine OpenWeather-
  Liveprüfung, kein automatischer Programmstart, keine Pi-Übertragung, keine neuen
  Konten oder kostenpflichtigen Dienste. Einstellungen, Schlüssel und Widget-
  Layout erhalten; Tests mit Dummy-Werten und getrenntem Speicher.
- Am 24.10.2026 anschließend freigegeben: passive weiße Anzeige ohne lokale
  Einstellungs-/Aktualisieren-Tasten, Orts-/Länderfelder oder Statusfußzeile.
  Vorhandenes Widget-Raster erhalten, volle Fensterfläche nutzen und sichtbare
  Inhalte nach realen Schriftmaßen möglichst groß einpassen. Handy-HTTPS startet
  im normalen Programm und in der getrennten Widget-Demo automatisch im Heimnetz.
  Jeder neue Browser fordert einen eigenen, nur am Display sichtbaren Einmalcode
  an; eigene Verbindungsseite ohne Bestätigung am Gerät, zwei Minuten gültig,
  höchstens vier wartende Anfragen und acht parallele Sitzungen bis zum Abmelden
  oder Programmneustart. Dieser Auftrag ersetzt die vorherige manuelle Aktivierung
  und lokale Orts-/Schlüsseleingabe. Schutzmechanismen, private Einstellungen,
  Zähler und Layout erhalten. Nur PC-Umsetzung und isolierte Offline-Abnahme;
  keine Pi-Übertragung, E-Ink-Treiber oder Liveabrufe.
- Erhalte die PC-Vorschau als erstes Ziel und verwende nur klar gekennzeichnete
  Beispieldaten, bis echte Datenquellen ausdrücklich freigegeben sind.
- Keine API-Schlüssel, echten Abrufe, Sensorzugriffe, Cloud-Dienste, öffentlichen
  Server oder Hardwarekäufe ohne konkrete Freigabe.
- Für die bestätigte Kartenfunktion sind aktuelle öffentliche WMS-Abrufe von
  basemap.de / BKG (Web Raster Farbe) und des DWD (WN-Radarkomposit,
  Beobachtungslayer) freigegeben. Der ausdrückliche Gestaltungsauftrag vom
  23.10.2026 ersetzt die zuvor gewählte graue Grundkarte durch eine helle,
  farblich angepasste Straßenkarte sowie weiche, durchscheinende Radarflächen
  nach Bildreferenz. Ortsname und orange-weißer Marker liegen über dem Radar.
  Historisch ersetzte die graue Karte am 18.10.2026 das DOP20-Luftbild.
  Auf ausdrücklichen Wunsch vom
  18.10.2026 umfasst die Kartenfunktion nun alle eindeutig aufgelösten Orte
  innerhalb Deutschlands und den projektbezogenen Bild-/Metadaten-Cache.
  Wetter und Karte verwenden dieselbe Ortsposition; die Karte löst keine
  zusätzlichen OpenWeather-Abfragen aus. Keine Freigabe für weitere
  OpenWeather-Liveprüfungen, Sensoren oder öffentliche Veröffentlichung.
- Behandle API-Schlüssel als vertraulich: nie in Quellcode, Logs, Screenshots,
  Toolausgaben oder Dokumentation aufnehmen. Tests ausschließlich mit Dummy-Werten
  und getrenntem temporärem Speicher durchführen.
- Projekteinstellungen einschließlich API-Schlüssel und Karten-/Metadaten-Cache
  liegen relativ zum Projektordner unter `private/`. Dies ist die ausdrückliche
  Nutzerentscheidung: OneDrive darf den gesamten Wetterstation-Ordner samt dieser
  unverschlüsselten Datei synchronisieren. `private/` bleibt von Git ausgeschlossen;
  das verhindert keine OneDrive-Synchronisierung. Keine API-Schlüssel-Umgebungsvariable.
- Einmalig darf ein alter Geräteschlüssel aus dem bisherigen Benutzerordner in `private/`
  kopiert werden, aber nur wenn die Projekteinstellungen noch nicht existieren. Nie
  überschreiben oder löschen; nach der Migration ist ausschließlich `private/` aktiv.
- Keine Live-Daten aktivieren, nur weil ein Schlüssel gespeichert wurde; die
  Gültigkeit wird erst bei einer später ausdrücklich freigegebenen Anbindung geprüft.
- Freigegeben ist eine lokal eingeschaltete Handy-Einstellungsseite im Heimnetz
  für Ort und OpenWeather-Schlüssel, mit Zugangscode und HTTPS. Keine öffentliche
  Bereitstellung, keine automatische Firewall-/Routeränderung und keine automatische
  Installation von Zertifikatsvertrauen. Tests weiter nur mit Dummy-Schlüsseln und
  getrennten temporären Einstellungen. Den gespeicherten Schlüssel nie zurückgeben.
  Eine eingeschaltete Verbindung bleibt beim Schließen ihres Dialogs aktiv;
  ausdrückliches Ausschalten oder Beenden der Vorschau beendet sie.
- Keine globale Git-Konfiguration ändern. Weitere Veröffentlichungen nur nach ausdrücklicher Freigabe.
