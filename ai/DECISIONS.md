# Entscheidungen (neueste oben)

Übernommen am 27.11.2026 aus PROJEKTPLAN.md, AGENTS.md, der alten CLAUDE.md und docs/ (alter Wortlaut in der Git-Historie, Commit `bbc838e`).

## 2026-11-27: Planungsdoku nach CLAUDE.md und ai/ überführt, Altdateien gelöscht
- Warum: 13 Dateien mit doppelten und teils widersprüchlichen Ständen. Künftige Sessions brauchen eine Quelle für Stabiles (CLAUDE.md), Stand (ai/STATUS.md) und Gründe (hier).
- Verworfen: Dateien als „historisch“ markiert behalten (weil weiter doppelt gepflegt würde). Gelöschte Pi-Doku steht in `RETIRED_FILES`, damit sie beim nächsten Update auch auf dem Pi entfernt wird.
- Status: gilt

## 2026-11-26: Öffentliches GitHub-Repo mit bereinigter Fassung
- Warum: Nutzerauftrag. Gerätespezifische Werte, private Daten und die alte lokale Git-Historie bleiben lokal; Beispielort Potsdam.
- Verworfen: privates Repo mit Codex Cloud (Idee vom 24.10., nie freigegeben).
- Status: gilt

## 2026-10-28: Optimierung für Pi und OneDrive
- Warum: Nutzer meldete am 26.10. CPU-Spitzen und mehrsekündiges Stocken beim ersten Seitenwechsel am Pi. Vorgabe: erst messen, dann entscheiden; keine vorweggenommene Abschaffung der Handy-Verbindung.
- Umsetzung: Browser berechnet Ziehen/Skalieren lokal und sendet erst nach fertiger Geste; Abfragepause nach 60 s Inaktivität; Server-Leerlauf 500 ms; Bildvorbereitung im Hintergrund, Übernahme nur im Tk-Hauptthread; Bildcache begrenzt; Designer-Laufzeit und Prüfkopien außerhalb OneDrive.
- Höherer Speicherbedarf wird akzeptiert (Preis für wiederverwendete Schrift-/Darstellungsdaten). ImageTk-Ausfall: Rückfall auf native Tk-PNG statt neuer Systempakete.
- Status: gilt (Messwerte in docs/OPTIMIZATION.md)

## 2026-10-28: Designer-Bedienung absichern
- Warum: versehentliche Wertänderungen und Datenverlust.
- Mausrad auf Eingabefeldern gesperrt; geschützte Datenblöcke lassen sich nicht löschen; ungültige Eingaben behalten den letzten gültigen Entwurf.
- Status: gilt

## 2026-10-27: Grafischer Designer, Gestaltungsformat 4
- Warum: Nutzer will Widgets selbst gestalten, ohne Code oder KI.
- Format 4 ergänzt frei bearbeitbare Inhaltsblöcke, Widgets behalten Typ und Datenbindung; Formate 2 und 3 werden verlustfrei gelesen; inkompatible Pi-Programme dürfen Gestaltungen nicht übernehmen.
- Qt (PySide6) nur am PC, Tk auf dem Pi (Pi bekommt keine Qt-Abhängigkeit); gemeinsamer Pillow-Renderer.
- Handy-Änderungen sind begrenzte Anordnungsoperationen mit Versionsprüfung, damit die PC-Gestaltung nie ersetzt wird. Import/Export ohne Schlüssel und Zähler.
- Verworfen: erweiterter Gestaltungseditor am Handy (Nutzer: PC-Anwendung genügt).
- Status: gilt

## 2026-10-27: Zusatzzeitreihen nur nach Freigabe pro Gerät
- Warum: Eine kopierte Gestaltung darf keine zusätzlichen Abrufe auslösen. Grundversorgung (3 Anfragen/5 Min) und 24 Reserveanfragen haben Vorrang.
- Offener Vorschlag aus der Spec: Minutenregen alle 30 Min, Viertelstundenwetter alle 60 Min.
- Status: gilt

## 2026-10-26: Updatefenster mit klaren Zuständen
- Warum: Nutzer hielt den unbestimmten Fortschrittsbalken nach Erfolg für einen Hänger. Laufend, Erfolg und Fehler müssen sofort unterscheidbar sein.
- Status: gilt

## 2026-10-25: Gemeinsamer Programmkern und manueller Doppelklick-Updater
- Warum: Ordner sollte nach Kern, Startern, Werkzeugen, Tests und Doku geordnet werden, ohne private Daten oder Budgetidentität zu verschieben → `paths.py` bestimmt den bisherigen Projektordner.
- Updater: eingefrorenen Stand offline testen und paketieren, vollständig hochladen, dann laufende App geordnet beenden, sichern, installieren, prüfen; Wiederstart nur, wenn sie vorher lief, im bisherigen Modus. Pi-Layout und private Daten bleiben.
- `tools/pi/update.py` nur mit Standardbibliothek, damit Wiederherstellung aus dem Pi-Zwischenordner funktioniert. Wiederherstellung setzt keine Zähler, Caches oder Zertifikate zurück (kein Budget-Rücksprung).
- SSH-Schlüssel außerhalb OneDrive im Windows-Schlüsseldienst; Registrierung per Skript über stdin (PowerShell 5.1 entfernte eingebettete Anführungszeichen).
- Prozessprüfung untersucht nur mögliche Wetterstation-Prozesse (`/proc/…/cwd` fremder Prozesse war nicht lesbar).
- Verworfen: automatische Updates, Updater-Autostart, Zeitpläne, Betriebssystem-/Bibliotheksupdates.
- Status: gilt

## 2026-10-24: Passive Anzeige, Bedienung per Handy-Pairing
- Warum: Nutzer will eine ruhige Anzeige ohne lokale Knöpfe und Felder.
- Jeder Browser fordert einen eigenen Einmalcode an, der nur am Display erscheint; 2 Minuten gültig, max. 4 wartende Anfragen, 8 Sitzungen bis Abmeldung oder Neustart, alles nur im Arbeitsspeicher. TLS, sichere Cookies, Host-/Origin-Prüfung, CSRF-Schutz und Versuchslimits bleiben.
- Ersetzt: lokale Einstellungsdialoge, manuelle Handy-Aktivierung, 20-Minuten-Sitzungen, „Verbindung bleibt nach Schließen des Dialogs aktiv“ (18.10.).
- Status: gilt

## 2026-10-24: HTTPS nur an echter Heimnetz-IPv4
- Warum: Am Pi wurde dem Nutzer eine `127…`-Adresse angezeigt. Aktive Schnittstellen auslesen, nie Loopback oder Wildcard; ohne Heimnetzadresse kein Start.
- Verworfen: Firewall-/Routeränderungen, automatisches Zertifikatsvertrauen, öffentliche Bereitstellung.
- Status: gilt

## 2026-10-24: Internationale Orte, Ortszeit und Karte
- Warum: Nutzerauftrag; ersetzt die Beschränkung auf Deutschland vom 18.10.
- Ort und ISO-Land werden gemeinsam gespeichert; Geocodierung auf das Land begrenzt; Wetter-/Ortscache nach Ort und Land getrennt, verspätete Ergebnisse verworfen (gleichnamige Orte dürfen keine Daten teilen).
- Uhr und Kalender in Wetter-Ortszeit, bei unbekannter Zeitzone gekennzeichnetes UTC.
- Deutschland: BKG/DWD. Ausland: OSM + RainViewer bei festem Zoom 7, nur benötigte Kacheln, HTTP-Cache (ohne Frischeangabe ≥ 7 Tage), Anwendungskennung, keine Vorabdownloads. Abdeckungsmaske: fehlendes Radar nie als trocken darstellen. Quellen auf internationalen Karten immer sichtbar (Lizenzpflicht OSM).
- Regenzugpfeile nur für DWD.
- Status: gilt

## 2026-10-24: Widget-Seiten
- 12×8-Raster je Seite, 1–12 Seiten, vier Startseiten; Speichern direkt nach jeder Geste (kein Übernehmen-Knopf), 20 Schritte Rückgängig; bei Kollision bleibt die letzte gültige Anordnung.
- Gerät wechselt Seiten nur manuell; automatischer Wechsel ist nur eine Idee.
- Status: gilt

## 2026-10-24: Vorhersagen einreihig, Inhalte zentriert
- Acht Stunden und fünf Tage je in einer Reihe gleich breiter Spalten; Trennlinien nur zwischen Vorhersagespalten; Widget-Rahmen 2 px bei 1024×600, skalierend.
- Status: gilt

## 2026-10-23: One Call 4.0 im festen Fünf-Minuten-Raster, Grenze 1000
- Warum: Nutzer hat das One-Call-Abo nach eigener Angabe auf 1000/Tag gesetzt (Konto nicht von uns geprüft).
- 3 Anfragen pro Lauf (`current`, `timeline/1h`, `timeline/1day`) zu festen Terminen deutscher Zeit; manuelle Abrufe verschieben das Raster nicht; kein Nachhol-Burst nach Standby; Paginierung `next`/`prev` nie folgen.
- Grenze 1000 je deutschem Kalendertag und je UTC-Anbietertag, ohne Zählerhistorie zurückzusetzen. Ersetzt die frühere 999er-Grenze.
- Regenkarte nutzt dasselbe Raster; ersetzt den 5-/15-Minuten-Takt und das Nachladen beim Seitenwechsel.
- Status: gilt

## 2026-10-23: Kartenstil nach Bildreferenz
- Helle farbige BKG-Straßenkarte, weiche transparente DWD-Radarflächen; Ortsname und orange-weißer Marker über dem Radar.
- Ersetzt: DOP20-Luftbild (bis 18.10.) und graue Grundkarte (18.–23.10.). Verworfen: Reliefkarte mit Höhenlinien, eigene Beschriftungsebene, Legende.
- Quellenzeile auf der deutschen Karte auf Nutzerwunsch ausgeblendet; Quellen und Lizenzen stehen im README. Eine rechtliche Ausnahme ist damit nicht bestätigt.
- Status: gilt

## 2026-10-23: Regenzug aus zwei DWD-Aufnahmen
- Höchstens 3 dezente, unbewegte Pfeile; nur Richtung, keine Geschwindigkeit, Legende oder Bodenwind-Ersatz. Korrelation ≥ 0,85 und 120 km/h dienen nur als Plausibilitätsfilter. Karte erscheint ohne Warten auf die Analyse.
- Status: gilt

## 2026-10-23: Bildvorbereitung im Hintergrund
- Warum: Jedes Zeichnen dekodierte beide PNGs (366,9 ms → 0,20 ms).
- Fertige Bildpaare wiederverwenden; Tk-Bilder nur im UI-Thread; höchstens eine Vorbereitung plus ein aktueller Folgeauftrag; überholte Aufträge nach Orts-/Größenwechsel verwerfen.
- Status: gilt

## 2026-10-19: Displaygröße 1024×600
- Start im Vollbild, F11 wechselt zum Fenster; Größenänderungen lösen keine Abrufe aus.
- Status: gilt

## 2026-10-18: Fehlerbehandlung und Backoff
- 401/403: Pause bis zum Schlüsselwechsel. 429: alle Endpunkte warten `Retry-After` (min. 60 s, sonst 15 Min). Netzwerk/5xx: nur betroffener Endpunkt, 60 s bis 30 Min.
- Wetter-Cache max. 6 h, Radar-Rückfall max. 60 Min. Bedienung wird nach Fehlern zuverlässig freigegeben.
- Status: gilt

## 2026-10-18: Lokaler Budgetzähler, fail-closed
- Warum: Reservierung vor jedem HTTP-Abruf, damit kein Absturz Abrufe unzählbar macht. Zusätzlich UTC-Anbietertag, weil sonst Verbrauch über die Anbietergrenze freigegeben werden könnte. Bei unbekanntem Tagesvorverbrauch (Ersteinrichtung) wird gesperrt.
- Zähler pro Gerät, weil OneDrive keine geräteübergreifende atomare Zählung liefert → PC-Live und Pi-Live nie gleichzeitig.
- Starter setzt `WETTERSTATION_BUDGET_ROOT` nur für den eigenen Prozess (umgeleiteter AppData-Pfad führte zu einem anderen Zähler). Verworfen: globale Umgebungsvariable.
- Status: gilt

## 2026-10-18: Einstellungen und Schlüssel unter `private/` im Projekt
- Warum: ausdrücklicher Nutzerwunsch; derselbe projektrelative Pfad auf allen PCs; OneDrive darf den Ordner samt unverschlüsselter Datei synchronisieren. `private/` ist Git-ignoriert.
- Verworfen: Umgebungsvariable für den Schlüssel, Speicherung im Benutzerordner (alte Geräteschlüssel einmalig migriert, nie überschrieben).
- Ein gespeicherter Schlüssel aktiviert keine Liveabrufe.
- Status: gilt

## 2026-10-18: Grundsätze der Entwicklung
- Zuerst am Windows-PC mit virtuellem Display, Python als Basis; Pi mit Netzteil (sparsamere Optionen offen); vorhandenes LCD vor E-Ink.
- Erst funktionales Grundgerüst; endgültige UI gestaltet der Nutzer selbst.
- Innerhalb freigegebener Features ist die technische Umsetzung frei; neue Features und Kontoaktionen nicht.
- Status: gilt
