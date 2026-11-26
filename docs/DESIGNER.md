# Wetterstation-Designer

## Auftrag vom 27.10.2026

Verbindliche Grundlage ist der im Chat abgestimmte Plan „Wetterstation-Designer
mit PC-Gestaltung und Handy-Anordnung“, unverändert unter `DESIGNER_SPEC.md`.
Die freigegebene grafische Erweiterung steht unverändert unter
`GRAPHICAL_DESIGNER_SPEC.md` und ergänzt diesen Auftrag.
Die Umsetzung erfolgt lokal und offline;
neue reale Wetterabrufe und die erste Pi-Übernahme sind gesondert abzunehmen.

## Abnahmeliste

- [x] PC: zwei Tabs, gemeinsamer Entwurf, Auswahl, Mehrfachbearbeitung, Tastatur,
  Kontextmenüs, 100 Undo-/Redo-Schritte, anpassbare Seitenleisten, hell/dunkel.
- [x] Raster 1–128 je Achse, genaue Positionen/Größen, Sperren, keine Überlappung,
  verlustfreie Rastervorschläge und ausdrücklich automatische Anordnung.
- [x] Profile 1024×600, 800×480, eigene Maße, getrennte Quer-/Hochformatvarianten,
  Ausgabe 0/90/180/270 Grad.
- [x] Stile: Flächen/Bilder/Verläufe, Transparenz, Rahmen/Seiten/Strichelung,
  einzelne Eckradien einschließlich null, Schatten, Abstände, Ausrichtungen.
- [x] Inhalte: eigene Texte, Bilder, Formen, Datenbindungen, freie Position,
  Rotation/Ebenen, Schriftimport, Formate, Einheiten, globale Vererbung/Overrides.
- [x] Vorlagen/Stile/Raster speichern, übertragen, zurücksetzen; Bilder/Schriften
  im schlüsselfreien Import-/Exportpaket.
- [x] Zusätzliche Live-Anbindung mit ausdrücklicher Geräteaktivierung: Minuten-/
  15-Minutenwerte im normalen Wetterzyklus; Transport und Schalter offline geprüft.
- [x] Zeitreihen-Abnahme mit simulierten Antworten: Minuten-/15-Minuten-/Stunden-/Tageswerte, freie Auswahl,
  Karten/Tabelle/Linie/Balken, Lücken/DST, keine Interpolation.
- [x] Offline-Budgetprüfung für Zusatzabrufe: reguläre 3/5-Minuten-Abrufe erhalten, beide Budgettage,
  24 Reserveanfragen, Pagination begrenzen, geteilte Caches, kein HTTP beim Gestalten.
- [x] Handy: vorhandene Funktionen, variables aktives Raster, gezielte Änderungen,
  Erhalt aller Details, Versionskonflikte, direkte Displaybestätigung.
- [x] Entwürfe automatisch, Crash-Wiederherstellung, explizit anwenden, alte
  Layouts erhalten, Settings-/Schlüssel-/Budgetschutz.
- [x] Pi-Übernahme isoliert simuliert: vorhandenes SSH, Kompatibilität, Staging/Assets, Sicherung, atomarer
  Wechsel, Bestätigung, Konflikte/Verbindungsabbruch, geschlossene App bleibt zu.
- [x] Offline-Tests und visuelle/Bedienabnahme einschließlich 100/150/200 %.

## Grenzen

Keine Hardwaretreiber, historischen Messwertarchive, neuen Konten, Veröffentlichung
oder Änderung der bestehenden Ort-/Schlüsselverwaltung. Qt wird nur am PC benötigt.

## Arbeitsstand

Der Konfigurator und die ausdrücklich freigegebene Live-Anbindung sind
implementiert. Zusatzabrufe sind standardmäßig ausgeschaltet. Erst eine
bestätigte Aktivierung am jeweiligen Gerät erlaubt sie im normalen Livebetrieb.
Entwicklung und Abnahme verwenden ausschließlich simulierte Antworten;
neue echte Wetterabrufe und die erste reale Pi-Übernahme stehen weiterhin aus.

## Start und Bedienung

`windows/Wetterstation gestalten.cmd` doppelklicken. Der Konfigurator arbeitet
mit klar gekennzeichneten Beispieldaten und startet keinen Handyserver oder
Wetterabruf. Er öffnet die aktive Gestaltung als Entwurf oder stellt den zuletzt
automatisch gesicherten Entwurf wieder her. Die aktive Anzeige ändert sich erst
über **Anwenden → Am PC anwenden** beziehungsweise **An Pi übertragen**.

1. **Widgets anordnen:** Seite wählen, Widget ziehen oder Breite/Höhe und Zelle
   rechts eingeben. Rastergröße ändern und den Vorschlag prüfen. Rote Umrisse
   markieren Überlappungen; diese müssen vor dem Anwenden behoben werden. Die
   acht Anfasser am ausgewählten Widget verändern seine Größe an Ecken und Seiten.
2. **Erweiterte Gestaltung:** Widget oder Inhalt auswählen. Oben rechts zwischen
   Anzeige, Seite, Widget und Inhalt wechseln. Einstellungen suchen, Gruppen
   aufklappen und Werte ändern. Blaue Eigenschaftsnamen markieren eigene Abweichungen;
   der Rücksetzpfeil verwendet wieder die übergeordnete Vorgabe.
3. **Inhalte direkt anordnen:** Titel, Werte, Bilder und Formen anklicken und ziehen;
   über die acht Anfasser ihre Größe ändern. Das ganze Widget wird in diesem Tab
   über seinen Rahmen bewegt. Ein gewöhnliches Wetterwidget behält seinen Typ
   und seine Datenbindungen. Karte, Diagramm oder Tabelle bleiben ein Inhaltsblock.
   Die Inhaltsliste links hilft bei überlagerten Elementen. Strg+Klick wählt mehrere
   Inhalte desselben Widgets; „Ausrichten“ bietet Textbündigkeit sowie davon getrennt
   Positionierung und gleichmäßiges Verteilen von Inhaltsflächen.
4. **Quer-/Hochformat:** Profil oben wählen. Die Anordnungen bleiben getrennt
   erhalten. Die zusätzliche Ausgabedrehung berücksichtigt die Displaymontage;
   sie ändert keine Betriebssystemeinstellung.

Unter **Innenraster** gilt ein gemeinsamer Zellabstand für alle Widgets, zunächst
8 logische Displaypixel, einstellbar von 1 bis 128. Der Ursprung liegt innerhalb
der Widget-Innenabstände. Anzeige und Einrasten sind getrennt schaltbar; **Alt**
setzt das Einrasten während des Ziehens aus. Vorhandene Inhalte werden durch eine
Rasteränderung nicht verschoben. Das Innenraster erscheint ausschließlich im Editor.
Beim Vergrößern eines Widgets wachsen Inhaltspositionen und -flächen proportional
mit; Schrift folgt ihrer bisherigen automatischen Größenanpassung.
Die Positionssperre schützt den äußeren Widgetrahmen; seine Inhalte bleiben
weiterhin gestaltbar.

Während einer Bewegung zeigt die Vorschau das Ergebnis samt Hilfslinien und
Positions-/Größenangabe. **Escape** verwirft die laufende Bewegung. Erst beim
Loslassen entsteht ein gemeinsamer Rückgängig-Schritt; ungültige Widgetpositionen
behalten den letzten gültigen Stand. Zahlenfelder werden nach der Bewegung aktualisiert.

Grafische Inhaltsänderungen und Innenrastereinstellungen verwenden **Format 4**.
Formate 2 und 3 bleiben lesbar; ein bloßes Öffnen oder Auswählen verändert weder
den aktiven Stand noch dessen Darstellung. Neue Format-4-Pakete benötigen den
aktuellen Programmstand auf dem Pi; „Stand prüfen“ weist ältere Programme ab.
Die Oberfläche nutzt helle/dunkle Flächen, Vektorsymbole und unter Windows bevorzugt
Segoe UI. Die Schriften der gestalteten Wetteranzeige sind davon unabhängig.

Strg+Z/Strg+Y: Rückgängig/Wiederholen; Strg+C/Strg+V: Widgets kopieren/einfügen;
Strg+D: duplizieren. Strg+Klick wählt mehrere Widgets. Pfeiltasten verschieben
die Auswahl um eine Zelle, Umschalt+Pfeiltaste um fünf. Entwurf und Historie sind
für beide Tabs gemeinsam. Die Anordnung am Handy bewahrt die PC-Gestaltung
einschließlich beim Rückgängigmachen gelöschter Widgets.

Im Menü **Entwurf**: Bilder/TTF-/OTF-Schriften importieren, Gestaltungspakete
mit Dateien exportieren/importieren, PNG-Vorschau und frühere Sicherung laden.
Im Menü **Vorlagen**: vorgegebene Gestaltung sowie eigene Stile, Widgets und Raster.
Im Menü **Ansicht**: Raster, Seitenleisten, Werkzeugfarbe und Prüfszenarien.

## Zusatzdaten ausdrücklich aktivieren

Zeitreihen zuerst gestalten und **Am PC anwenden** wählen. Unter **Datenquellen →
Zusatzabrufe auf diesem PC aktivieren** den Bedarf und die Tageslast prüfen und
bestätigen. Die nächste reguläre Live-Aktualisierung kann dann die Zusatzquellen
abrufen. Der Konfigurator selbst bleibt bei Beispieldaten und startet weder die
Anzeige noch einen Wetterabruf. **Zusatzabrufe auf diesem PC ausschalten**
widerruft diese Freigabe. Eine bereits laufende HTTP-Anfrage kann noch enden;
vor jeder Folgeseite wird die Freigabe erneut geprüft.

Am Pi im Übertragungsdialog zuerst **Stand prüfen** und anschließend
**Zusatzabrufe am Pi aktivieren** wählen. Bestätigt wird der geprüfte aktive
Pi-Bedarf. **Zusatzabrufe am Pi ausschalten** beendet die Freigabe. Eine reine
Gestaltungsübertragung aktiviert keine Zusatzdaten; geschlossene Programme bleiben
geschlossen. Auf dem echten Pi wurde dieser Ablauf noch nicht ausgeführt.

Die Gerätefreigabe liegt getrennt von der Gestaltung und enthält keine Schlüssel.
Ein Export oder eine OneDrive-Kopie aktiviert kein anderes Gerät. Änderungen am
Abrufbedarf verlangen eine erneute Aktivierung; Farben, Rahmen und Positionen
verändern die Freigabe nicht. Stunden-/Tagesreihen verwenden die vollständigen
ohnehin geladenen ersten Antwortseiten. Weitere Seiten und Minuten-/Viertelstunden-
werte teilen sich Quellen-Caches und Abrufintervalle. Fehlende Werte bleiben Lücken.
Die regulären drei Anfragen alle fünf Minuten, beide geschützten Budgettage und
24 Reserveanfragen haben Vorrang. Hinweise im Widget kennzeichnen ausgeschaltete
oder unvollständige Zusatzdaten.

## Installation auf weiteren PCs

Nur der Konfigurator benötigt zusätzlich `requirements-designer.txt`
(PySide6-Essentials). Der Starter verwendet die vorhandene Projekt-Pythonumgebung;
fehlende Bibliotheken werden gemeldet und niemals automatisch installiert.
Für diese lokale Entwicklung liegen die Qt-Bibliotheken isoliert unter
`build/designer-runtime/`. Dieser Ordner wird nicht in Pi-Pakete übernommen.
Auf weiteren PCs die Zusatzbibliotheken ausdrücklich in der gewünschten lokalen
Pythonumgebung installieren, vorzugsweise der bestehenden Umgebung unter
`%LOCALAPPDATA%/Wetterstation/venv`. Die Anzeige auf dem Pi benötigt kein Qt.

## Dateien und Schutz

- `private/designer/draft.json`: automatisch gesicherter Entwurf und Ausgangsrevision.
- `private/designer/assets/`: Bilder und Schriften, nach Inhaltsprüfsumme benannt.
- `private/designer/backups/`: vor dem Ersetzen gesicherte Gestaltung.
- `private/designer/phone-undo.json`: begrenzte Wiederherstellungsdaten für Handy-Undo.
- `private/designer/timeline-activation.json`: getrennte, standardmäßig fehlende
  Gerätefreigabe; kein Bestandteil von Gestaltungspaketen.
- `private/designer/incoming/`: nachvollziehbare Pi-Übertragung mit Transaktionskennung.
- `private/designer/transfer.json` und `transfer-packages/`: lokale Zuordnung und
  unverändertes Paket für das Fortsetzen nach Schließen des Übertragungsdialogs.

Gestaltungspakete enthalten ausschließlich das geprüfte Gestaltungsformat und
benannte Medien. Der bestehende Schlüssel, Ort, Zertifikate und Zähler werden
nicht exportiert oder ersetzt. Private Dateien können gemäß Projektentscheidung
weiter unverschlüsselt über OneDrive synchronisiert werden.

Die Pi-Übertragung prüft zuerst den Zielstand. Ein veraltetes Pi-Programm wird
über den bisherigen manuellen Updater aktualisiert. Erst **Jetzt übertragen**
ersetzt die Gestaltung nach Sicherung. Eine geschlossene Anzeige bleibt geschlossen;
eine laufende Demo behält ihre temporären Einstellungen. Nach unklarer Verbindung
**Stand prüfen** verwenden. Die vorige Gestaltung lässt sich im Übertragungsdialog
wiederherstellen, ohne andere private Einstellungen zurückzusetzen.

Ein Upload landet zuerst in einer getrennten Datei. Erst nach vollständiger
Prüfsumme wird er atomar für die Installation bereitgestellt. Nach erneutem Öffnen
ordnet **Stand prüfen** dieselbe Übertragung wieder zu. **Übertragung fortsetzen**
verwendet dasselbe gespeicherte Paket und dieselbe Kennung; eine bereits bestätigte
Installation wird nicht wiederholt. **Neue Übertragung vorbereiten** beendet einen
alten offenen Vorgang unter derselben Sperre wie die Installation und liest den
Zielstand neu. Eine spätere Wiederholung des beendeten Vorgangs wird abgewiesen.

## Lokale Prüfung

- `python tools/offline_tests.py --report build/checks/designer-all-tests-final.txt`
- `python tests/designer_scale_check.py`: achtzehn Qt-Bedienprüfungen bei simuliertem
  effektivem Pixelfaktor 1, 1.5 und 2; keine Änderung der Windows-Einstellungen.
  Einschließlich aller acht Widget-/Inhaltsanfasser bei drei Zoomstufen, direkter
  Auswahl, Alt/Escape, Mehrfachauswahl, Ausrichtung, ausstehenden Texteingaben und
  echter Warnungsdialoge mit Weiterbearbeitung nach ungültiger Widgetgeometrie.
- `python tests/widget_demo.py --design`, anschließend
  `node tests/designer_phone_check.cjs`: isoliertes lokales HTTPS, Dummy-Schlüssel,
  Handy-Größen 320/375, Tk-Übernahme und ausschließlich Anordnungsbefehle.
  Mit `python tests/widget_demo.py --design --graphical` wird derselbe Browserablauf
  einschließlich Erhalt verschobener Inhaltsblöcke mit Format 4 geprüft.
- `python tools/designer_acceptance.py`: komplette Offline-Abnahme in eingefrorener
  Quellkopie, anschließend Paketbau und bytegleiche Schriftprüfung desselben Stands.

Belege unter `build/checks/`. Eine reale Pi-Übernahme oder neue echte Wetterabrufe
sind aus diesen Prüfungen nicht abzuleiten.

## Korrekturen vom 28.10.2026

Neue Rechtecke und Ellipsen erhalten sichtbare graue Flächen und Rahmen und werden
sofort als Inhalt ausgewählt. Bestehende Formen verwenden wieder ihren geerbten Stil;
explizite Transparenz bleibt erhalten. Rechts neben jedem Inhalt steht ein Minusknopf.
Er entfernt nur diesen Inhalt ohne Rückfrage; Strg+Z stellt ihn wieder her. Geschützte
Karten-/Zeitreihenblöcke behalten einen deaktivierten Knopf mit Erklärung.
Das Mausrad verändert keine Auswahl-, Zahlen- oder Schiebefelder mehr. Im rechten
Bereich scrollt es stattdessen die Eigenschaften, auch bei fokussierten Eingabefeldern.


Das Seitenraster liegt hinter den Widgets und ist durch transparente Flächen sichtbar.
Spalten und Zeilen werden nach Enter oder Verlassen des Feldes direkt im Entwurf
übernommen; während des Tippens erfolgt keine Änderung. Eine Rastervorlage ändert
beide Werte gemeinsam. „Auf alle Seiten dieser Variante“ bleibt beim Neuaufbau der
Eigenschaften ausgewählt. Strg+Z nimmt die Rasteränderung zurück. Widgets werden
proportional angepasst; Rundungen können markierte Überlappungen erzeugen.
„Automatisch anordnen“ bleibt eine gesonderte Aktion. Die laufende Anzeige ändert
sich erst nach ausdrücklicher Übernahme. Das Innenraster für Inhalte bleibt separat.
