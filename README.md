# Wetterstation

Gemeinsames Python-Programm für Windows und Raspberry Pi. Anzeige, Wetterdienste,
Regenkarte und geschützte Handy-Oberfläche verwenden denselben Programmstand.

## Starten

- **Gestaltung am PC:** `windows/Wetterstation gestalten.cmd` öffnet den getrennten
  Konfigurator mit Beispieldaten. Zwei Tabs für Anordnung und erweiterte Gestaltung;
  acht Größenanfasser, direkt verschiebbare Inhaltsblöcke und gemeinsames Innenraster.
  Der Handy-Editor bleibt für die Anordnung nutzbar. Anleitung und Abnahmestand:
  [Designer](docs/DESIGNER.md). Zusätzliche Zeitreihen verlangen eine ausdrückliche
  Aktivierung je Gerät unter **Datenquellen** beziehungsweise im Pi-Übertragungsdialog.
  Der Konfigurator selbst ruft keine Wetterdaten ab.

- **Windows:** `windows/Wetterstation starten.cmd` startet den normalen Betrieb.
  Solange der Pi dieselbe Budgetidentität live verwendet, am PC ausschließlich
  **`windows/Widget-Demo.cmd`** mit klar gekennzeichneten Beispieldaten verwenden.
- **Pi aktualisieren:** einmal `windows/SSH einmalig einrichten.cmd`, danach
  **`windows/Pi aktualisieren.cmd`** doppelklicken. Der Updater startet nur manuell.
- **Pi:** vorhandenes Desktop-Symbol oder `sh start_pi_live.sh` im Pi-Projektordner.
  `sh start_pi_widget_demo.sh` verwendet getrennte temporäre Beispieldaten.

Beim ersten Update auf die neue Struktur die alte Pi-Wetterstation einmal selbst
schließen. Spätere Updates beenden eine laufende neue Version geordnet und starten
denselben Demo-/Live-Modus wieder. Eine geschlossene Anwendung bleibt geschlossen.
Wiederstart im Livemodus kann reguläre Wetter- und Kartenabrufe auslösen.

## Ordner

| Ordner | Inhalt |
|---|---|
| `windows/` | Doppelklick-Starter und einmalige SSH-Einrichtung |
| `raspberry_pi/` | Linux-Starter |
| `wetterstation/` | Gemeinsamer Programmkern, nach Aufgaben gruppiert |
| `tools/` | Offline-Prüfung, Update-/Sicherungswerkzeuge, historische Migration |
| `tests/` | Automatisierte Tests, Browser- und Displayprüfungen |
| `docs/` | Aktuelle Anleitungen und gekennzeichnete Historie |
| `build/` | Erzeugte Pakete, isolierte Prüfbilder und Berichte; nicht in Git |
| `archive/` | Vollständige vertrauliche Sicherung und alte Transferpakete; nicht in Git |
| `private/` | Unveränderte Einstellungen, Schlüssel, Zertifikate, Caches und Zähler; nicht in Git |

Die wenigen Starter im Hauptordner bleiben als Weiterleitungen für vorhandene
Verknüpfungen erhalten. Programmcode liegt in den zugehörigen Unterordnern.

## Anleitungen und Prüfung

- [Ordnerbereinigung, Ressourcen und Browser-Ruhemodus](docs/OPTIMIZATION.md)
- [Pi-Update und Wiederherstellung](docs/UPDATE.md)
- [Struktur und Entwicklung](docs/STRUCTURE.md)
- [Designer](docs/DESIGNER.md)
- Entscheidungen mit Begründung und aktueller Stand (nur im Repository, nicht auf dem Pi):
  [ai/DECISIONS.md](ai/DECISIONS.md), [ai/STATUS.md](ai/STATUS.md)

Python 3.11 oder neuer mit Tkinter ist erforderlich. `requirements.txt` beziehungsweise
`pyproject.toml` beschreiben die Entwicklungsbibliotheken. Die bestehende Pi-Installation
wird funktional geprüft; Updates installieren keine Bibliotheken oder Betriebssystempakete.

Isolierte Offline-Tests: `python tools/offline_tests.py`. Externe Python-Verbindungen
werden dabei gesperrt; lokale HTTPS-Tests verwenden Dummy-Daten. Browserprüfungen sind
separat beschrieben und benötigen einen vorhandenen Browser mit Playwright.

Diese öffentliche Fassung verwendet Potsdam als Beispielort. Eigene Einstellungen
werden lokal unter `private/` abgelegt. Die Widget-Demo verwendet Beispieldaten.

## Datenquellen und Lizenzen

- **Grundkarte Deutschland:** [basemap.de-WMS](https://sgx.geodatenzentrum.de/wms_basemapde?SERVICE=WMS&REQUEST=GetCapabilities&VERSION=1.1.1),
  Layer `de_basemapde_web_raster_farbe`. Lizenz [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/),
  Quellenvermerk „© GeoBasis-DE / BKG 2026 · CC BY 4.0“; [Nutzungsbedingungen](https://basemap.de/produkte-und-dienste/web-raster/).
- **Radar Deutschland:** [DWD-WMS](https://maps.dwd.de/geoserver/wms?SERVICE=WMS&REQUEST=GetCapabilities&VERSION=1.3.0)
  (WN-Radarkomposit), Quellenvermerk „Datenbasis: Deutscher Wetterdienst“; siehe
  [DWD-Geodienste](https://www.dwd.de/DE/leistungen/geodienste/help/nutzung_geodienste.html?lsbId=621762)
  und [WN-Produktsteckbrief](https://www.dwd.de/DE/leistungen/radarprodukte/radarkomposit_wn_hdf5.pdf?__blob=publicationFile&v=4).
- **Ausland:** Kacheln von OpenStreetMap ([Mitwirkende und Lizenz](https://www.openstreetmap.org/copyright),
  [Kachelnutzung](https://operations.osmfoundation.org/policies/tiles/)) und Radar von
  [RainViewer](https://www.rainviewer.com/api/weather-maps-api.html). Internationale Karten zeigen immer
  „© OpenStreetMap-Mitwirkende · RainViewer“. Der Client meldet sich als `WetterstationPreview/2.0`,
  nutzt den HTTP-Cache (ohne Frischeangabe mindestens sieben Tage) und lädt nur benötigte Kacheln bei Zoom 7.
- **Wetter:** [OpenWeather One Call 4.0](https://openweathermap.org/api/one-call-4) und
  [Geocoding](https://openweathermap.org/api/geocoding-api) mit eigenem Schlüssel.

Die Quellenzeile der deutschen Karte ist in der Anzeige auf Nutzerwunsch ausgeblendet; die Angaben
stehen hier. Eine Ausnahme von den Nutzungsbedingungen ist damit nicht bestätigt.
