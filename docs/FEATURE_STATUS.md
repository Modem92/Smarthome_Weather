# Funktionsstand · Stand vom 28.10.2026

## Optimierung und Pi-Abnahme vom 28.10.2026

Finaler Programmkern einschließlich der Optimierungen auf dem Pi installiert;
389 Tests im eingefrorenen Stand bestanden. Widget-Demo geordnet wieder gestartet,
Anordnung und flüssige Bedienung vom Nutzer bestätigt. Gespeichertes Pi-Layout und
private Daten erhalten. CPU-/Render-Vergleich, Ordnerbereinigung und Grenzen:
[OPTIMIZATION.md](OPTIMIZATION.md). Die älteren Abschnitte unten sind historische
Abnahmestände; diese Demo-Abnahme ersetzt keine internationale Live-Prüfung.

## Designer vom 27.10.2026

PC-Konfigurator mit getrennten Tabs für Anordnung und erweiterte Gestaltung,
variablen Rastern, Displayvarianten, Stilen, eigenen Inhalten und Zeitreihen.
Die Handy-Anordnung bleibt erhalten und bewahrt Gestaltungsdetails.
Die grafische Erweiterung ergänzt acht Größenanfasser, direkt wählbare Inhalte,
ein gemeinsames Innenraster, Ausrichtung und eine modernisierte helle/dunkle
Oberfläche. Format 4 erhält Widgettypen, Datenbindungen und die Handy-Anordnung;
ältere Layouts bleiben ohne grafische Änderung auf ihrem bisherigen Renderweg.
Zusatzdaten sind im normalen Wetterzyklus angebunden und benötigen eine eigene
ausdrückliche Geräteaktivierung. Konfigurator, Transferabbrüche und Anbindung
sind isoliert/offline geprüft; neue echte Wetterabrufe und die erste reale
Pi-Übernahme stehen aus. Umfang, Bedienung und Belege: [Designer](DESIGNER.md).

## Struktur und Updateablauf vom 25.10.2026

- Gemeinsamer Programmkern nach Aufgaben unter `wetterstation/`; Windows-/Pi-Starter,
  Werkzeuge, Tests, Dokumentation, erzeugte Pakete und Archive getrennt. Eine gemeinsame
  Codebasis; alte Einstiegspunkte bleiben als Weiterleitungen erhalten.
- Manueller grafischer Pi-Updater mit eingefrorenem aktuellem Quellstand, Offline-Tests,
  Paketprüfung, Schlüsselanmeldung, Bereitstellen vor Beenden, Sicherung, Installation,
  Rücksetzung und bedingtem Wiederstart. Pi-Layout und private Daten bleiben erhalten.
- 299 Offline-Tests bestanden, keine übersprungenen Tests. Zusätzlich Widget-,
  Mehrbrowser- und internationale Browserabnahmen bestanden, ohne externe Anfragen.
  Display und Updatefenster mit Beispieldaten visuell geprüft. Derselbe Test-/Paketbau-
  Ablauf wie im Updater in getrennter Kopie mit simuliertem Transfer geprüft.
- Alle 756 ursprünglichen privaten Dateien nach der Umordnung bytegleich. Vorherige
  Workspace-Sicherung einschließlich privater Daten und Git unter `archive/`.
- Echte SSH-Einrichtung, Anmeldung nach Windows-Neustart, Erstmigration und aktueller
  Pi-Wiederstart/Display-/Handytest stehen noch aus. Kein Pi-Transfer oder Liveabruf
  durch diese lokale Abnahme. Keine GitHub-Veröffentlichung oder Git-Remote-Einrichtung.

Aktuelle Anleitung: [Pi aktualisieren](UPDATE.md), Entwicklung: [Struktur](STRUCTURE.md).

## Vorherige Funktionsbestandsaufnahme vom 24.10.2026

Diese Übersicht gleicht den aktuellen PC-Quellcode, Tests und Dokumentation mit
dem Projektplan ab. Sie ist eine Funktionsbestandsaufnahme, keine vollständige
Fehlerfreiheit-, Sicherheits- oder Hardwarezusage. Historische Einträge im
Projektplan bleiben als Verlauf erhalten; neuere Aufträge ersetzen ältere Vorgaben.

## Aktuell geprüft

- Vollständiger Python-/Tk-/HTTPS-Testsatz: **280 Tests bestanden**, keine
  übersprungenen Tests; Laufzeit 75,217 Sekunden.
- Widget-Browsertest bestanden: Inhalte, 20 Undo-Schritte, Touch-Verschieben,
  Größenänderung, Seitenverwaltung, Speicher-/Verbindungsfehler, Konflikte,
  Neuanmeldung und Bestätigung der Übernahme am Tk-Display.
- Getrennter Anmelde-Browsertest bestanden: unabhängige Browser, verschiedene
  Einmalcodes, Warteschlange, gleichzeitige Sitzungen, erneutes Laden und
  Widerruf nach Dienstneustart. Beide Browserberichte ohne Konsolenfehler oder
  externe Anfragen.
- Display-Prüfbilder neu erzeugt; Übersicht und Vorhersage bei 1024×600 visuell
  kontrolliert: vollständige Einträge, zentrierte Inhalte, einreihige Vorhersagen.
- Python-Prüfungen mit temporären Dummy-Einstellungen und zusätzlicher Sperre
  externer Socket-Verbindungen. Browserprüfung ausschließlich an Loopback-HTTPS.
  Kein normaler Livestart und keine Pi-Verbindung.
- Der erste Testaufruf über Standardeingabe konnte unter Windows den
  Mehrprozesstest nicht starten. Dieser bestand mit gespeichertem Teststarter;
  anschließend wurde der gesamte Testsatz erfolgreich wiederholt.

Prüfbelege liegen ausschließlich lokal unter `private/`:
`feature-audit-tests-final.txt`, `feature-audit-process-test.txt`,
`widget-check/browser-results.json`, `widget-check/pairing-browser-results.json`
und `display-check/`. Der Testserver wurde anschließend beendet.

## Im aktuellen PC-Programm umgesetzt

| Bereich | Vorhandener Funktionsumfang | Hauptquellen |
| --- | --- | --- |
| Anzeige | Passive weiße Oberfläche, dunkle Schrift, skalierende Rahmen, dynamische Schriftanpassung, Referenz 1024×600, Vollbild/F11 | `app.py`, `dashboard.py` |
| Seiten | Vier Startseiten; 1–12 Seiten, Umbenennen, Reihenfolge und Entfernen; manuelle Auswahl per Pfeiltasten oder Handy | `widgets.py`, `mobile_web/app.js` |
| Widgets | 12×8-Raster, maximal 16 Widgets je Seite; hinzufügen, mehrfach verwenden, verschieben, skalieren, Seitenwechsel, Kollisionsbehandlung, Inhaltsauswahl ohne Größenänderung | `widgets.py`, `dashboard.py`, `mobile_web/layout.js` |
| Speicherung | Dauerhaftes Layout, atomare Einstellungen, Versionskonflikte, sichtbare Speicher-/Verbindungsfehler und Erhalt des Browserentwurfs | `api_key_store.py`, `file_io.py`, `mobile_web/app.js` |
| Rückgängig | Bis zu 20 Bearbeitungsschritte im Handy-Editor | `mobile_web/app.js` |
| Wetter | Aktuelles Wetter, Temperatur, gefühlte Temperatur, Beschreibung, Luftfeuchte, Wind und Luftdruck | `weather_service.py`, `dashboard.py` |
| Vorhersage | Acht Stunden und fünf Tage, jeweils eine Reihe; ein-/ausblendbare Datenfelder, gemeinsame Zeilen und zentrierte Inhalte | `weather_service.py`, `dashboard.py` |
| Internationale Orte | 249 Länder mit deutschen Namen und ISO-Code; Handy-Suche, gemeinsame Ort-/Landspeicherung, landesbezogene Geocodierung und getrennte Caches | `countries.py`, `countries.json`, `weather_service.py`, `mobile_settings.py` |
| Ortszeit | Uhr, Kalender, Vorhersage und Abrufzeit in der Wetter-Ortszeit; Sommerzeit und gekennzeichnete UTC-Rückfallanzeige | `location_time.py`, `app.py`, `dashboard.py` |
| Deutschlandkarte | Helle BKG-Straßenkarte, weiche transparente DWD-Radarflächen, Ortsmarker und Bildcache | `radar_map.py`, `radar_render.py` |
| Internationale Karte | OSM-/RainViewer-Kacheln bei Zoom 7, Abdeckungsmaske, sichtbare Quellen, HTTP-Cache und bedarfsgerechte Grundkartenabrufe | `international_map.py`, `radar_render.py` |
| Regenzug | Bis zu drei geschätzte Pfeile aus DWD-Bildpaaren; Ausblenden bei veralteten oder unsicheren Daten; keine Auslandspfeile | `radar_motion.py`, `app.py` |
| Abrufsteuerung | Feste Fünf-Minuten-Termine, Hintergrundabrufe und Wiederverwendung fertiger Bilder; RainViewer-Beobachtungen werden bei unverändertem Stand wiederverwendet | `app.py`, `international_map.py` |
| Budgetschutz | 1000 Aufrufe pro deutschem/UTC-Budgettag, Minutenlimit, Reservierung vor HTTP, Dateisperren, redundanter lokaler Prüfspeicher | `openweather_budget.py`, `weather_service.py` |
| Fehlerfälle | Zeitlimits, Anfragepausen, validierte Antworten, teilweise Vorhersagen und begrenzter gleichörtiger Cache; veraltete Ergebnisse nach Ortswechsel verwerfen | `weather_service.py`, `radar_map.py`, `international_map.py`, `app.py` |
| Handyverbindung | Automatischer lokaler HTTPS-Start im normalen Hauptprogramm und in der Widget-Demo; Hintergrundsuche und Wiederholung bei Startproblemen | `app.py`, `mobile_settings.py` |
| Anmeldung | Browsergebundene Einmalcodes nur am Display; vier wartende Anfragen, zwei Minuten ab Anzeige, acht Sitzungen bis Abmeldung/Neustart | `mobile_settings.py`, `dashboard.py` |
| Zugriffsschutz | TLS, sichere Cookies, Host-/Origin-Prüfung, CSRF und Versuchslimits; gespeicherter Wetter-Schlüssel wird nicht zurückgeliefert | `mobile_settings.py` |
| Demo | Gekennzeichnete Wetter-/Sensordaten; Widget-Demo mit temporärem Speicher; keine Providerabrufe | `app.py`, `start_widget_demo.cmd`, `start_pi_widget_demo.sh` |
| Pi-Werkzeuge | Demo-/Live-Starter, Offline-Vorabprüfung, Paketprüfung, Sicherung, Update und Wiederherstellung unter Erhalt privater Daten | `pi_preflight.py`, `pi_update.py`, `pi_live_transfer.py` |
| Pi-Startsymbol | Werkzeug zum Anlegen der Desktop-Verknüpfung; Einrichtung auf dem Pi laut früherer Nutzerausgabe bestätigt | `pi_desktop_icon.py`, `RASPBERRY_PI.md` |

Die frühere lokale Ort-/Länderauswahl und Einstellungsdialoge wurden durch den
bestätigten Auftrag zur passiven Anzeige ersetzt. Einstellungen erfolgen nun am
Handy. Auch lokale Aktualisieren-Tasten/F5 sind bewusst entfernt und kein Defekt.

## Umgesetzt, aber für den aktuellen Stand noch nicht praktisch abgenommen

- **Pi-Übernahme:** Internationale Funktionen, passive Anzeige, Einmalcode-Anmeldung
  und letzte Widget-Ausrichtung sind im PC-Workspace vorhanden. Die dokumentierten
  älteren Pi-Archive enthalten diesen vollständigen Stand nicht. Neues Paket,
  gesicherte Übernahme und anschließende Offline-/Display-/Handy-Abnahme stehen aus.
- **Internationale Livefunktion:** Die implementierten Providerwege sind offline
  simuliert geprüft. Eine aktuelle reale Prüfung von Geocoding, Wetter, OSM und
  RainViewer im Zusammenspiel wurde in diesem Audit nicht durchgeführt.
- **Langzeitbetrieb:** Ältere Pi-Laufprobe von etwa dreieinhalb Stunden laut
  Nutzerbericht vorhanden. Mehrtägiger Betrieb, Neustart/Stromunterbrechung,
  Netzwerkausfall und Wiederherstellung des aktuellen Stands bleiben offen.
- **Display/Leistung:** Tk-Geometrie und PC-Bilder geprüft; keine aktuelle Messung
  von Lesbarkeit, Reaktionszeit und Ressourcenverbrauch dieses Stands am Pi.
  Am 26.10.2026 meldet der Nutzer nach Pi-Test hohe CPU-Spitzen beim Seitenwechsel
  und mehrere Sekunden Blockade beim ersten Wechsel bis zur vierten Demo-Ansicht.
  Ursachenanalyse und Optimierung sind im Projektplan für später vorgemerkt;
  ein Einfluss des Handy-Servers ist bislang eine unbestätigte Vermutung.
- **OpenWeather-Konto:** Lokaler Budgetschutz implementiert und getestet; tatsächliche
  Anbieter-Kontogrenze/Billing-Einstellungen nicht unabhängig bestätigt.

Die frühere Pi-Handyreparatur ist dagegen bereits durch Nutzerausgabe und
persönlichen Handytest als abgeschlossen dokumentiert. Das ist keine Abnahme der
später geänderten Anmeldung auf dem Pi.

## Noch nicht umgesetzt beziehungsweise nicht eingerichtet

- Echte Außen-/Innensensoren: Sensorwidgets verwenden feste Beispieldaten;
  Hardware, Protokoll und Anschluss sind nicht festgelegt.
- Langfristige Messwertspeicherung und Auswertung: vorhandene Wetter-/Karten-
  Caches sind keine dauerhafte Messreihenarchivierung.
- Automatischer Programmstart beim Einschalten des Pi: Desktop-Symbol und
  manueller Starter vorhanden, kein eingerichteter Autostart.
- GitHub-Übertragung und Codex-Cloudumgebung: weiterhin nur bewertet/vorgemerkt.
  Lokal enthält Git nur README und `.gitignore`; kein Remote konfiguriert.
- Allgemeine Geräteinstallation: vorhandene Starter/Abhängigkeiten und Pi-Updater,
  aber kein universeller Installationsassistent. Pi-Transferziel ist derzeit im
  Code auf das bekannte Gerät festgelegt. Testbrowser verwenden lokale Pfade.
- E-Ink-Treiber, physische Tasten und endgültiges Stromspar-/Hardwarekonzept.
- Nur vorgemerkt: optionaler automatischer Seitenwechsel, Markierung auffälliger
  Messwerte, weitergehende Datenanalyse sowie Cloud-/ML-Funktionen.
- Reliefkarte/Höhenlinien: nicht umgesetzt; bisher keine aktuelle Beauftragung.

Diese Auflistung erteilt keine Umsetzung-, Abruf-, Konto- oder Transferfreigabe.

## Dokumentations- und Übergabebedarf

- Historische Abschnitte nennen weiter frühere Dialoge, 999er-Grenzen, alte
  Testzahlen oder nur deutsche Karten. Für den aktuellen Stand gelten die
  jüngsten Umsetzungsabschnitte und der heutige Code.
- Unter „Offene Entscheidungen“ steht noch eine Handyprüfung nach Schließen des
  PC-Dialogs; dieser Dialog existiert im aktuellen passiven Programm nicht mehr.
  Die frühere Handyreparatur ist abgenommen, die neue Pi-Anmeldung noch nicht.
- Der Schlussabschnitt der README beschreibt weiterhin nur WMS-Karten und
  den Pi als vorläufig, obwohl internationale Karten und ein bestehender Pi
  an anderer Stelle dokumentiert sind.
- Die Pi-Anleitung nennt bewusst historische Testzahlen und Paketstände; diese
  sind kein Nachweis für die aktuelle vollständige PC-Version.
- Vor einer Geräte-/GitHub-Übergabe Bibliotheksanforderungen mit dem Pi abstimmen:
  dokumentierte Debian-Bibliotheken sind älter als die allgemeinen Mindeststände.
- Für GitHub erzeugte Archive, Prüfdateien und temporäre Testreste separat prüfen;
  `private/` ist ausgeschlossen, `transfer/` und Testreste bisher nicht pauschal.

## Sinnvolle Reihenfolge der nächsten Entscheidungen

1. Bei gewünschter Nutzung am Gerät: aktuellen PC-Stand für den Pi paketieren,
   sichern, übernehmen und lokal abnehmen.
2. Neustart, längeren Betrieb und Ausfall/Wiederherstellung gezielt prüfen.
3. GitHub-/Cloud-Einrichtung als eigenen Umfang freigeben.
4. Sensorhardware und gewünschte dauerhafte Datenspeicherung konkret planen.

Es wurden in diesem Audit keine Funktionsänderungen implementiert, keine
privaten Benutzereinstellungen bearbeitet und keine Daten veröffentlicht.
