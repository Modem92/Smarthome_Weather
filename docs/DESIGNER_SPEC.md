# Wetterstation-Designer mit PC-Gestaltung und Handy-Anordnung

Der PC-Konfigurator erhält die beiden Tabs **„Widgets anordnen“** und **„Erweiterte Gestaltung“**. **Die Anordnung bleibt zusätzlich über das Handy bedienbar.** Die erweiterte Gestaltung wird ausschließlich am PC umgesetzt.

## 1. Bedienung am PC und Handy

**PC: „Widgets anordnen“**

- Seiten und Widgets hinzufügen, duplizieren, entfernen und sortieren.
- Widgets verschieben, ihre Rastergröße ändern und zwischen Seiten verschieben.
- Position und Größe durch Ziehen oder genaue Eingaben einstellen.
- Widgets gegen versehentliche Änderungen sperren.
- Raster und Displayformat einstellen.

**PC: „Erweiterte Gestaltung“**

- Erscheinungsbild, Inhalte und innere Aufteilung umfassend gestalten.
- Dieselbe Vorschau und derselbe Entwurf wie im ersten Tab.
- Auswahl und aktuelle Seite bleiben beim Tabwechsel erhalten.

**Handy: Anordnung weiterhin möglich**

- Seiten auswählen und verwalten.
- Widgets hinzufügen, entfernen, verschieben und vergrößern oder verkleinern.
- Widgets zwischen Seiten verschieben und Änderungen rückgängig machen.
- Das am PC gewählte Raster und die aktive Quer-/Hochformatvariante verwenden.
- Änderungen nach abgeschlossener Bedienbewegung direkt auf der Wetterstation übernehmen.
- Farben, Rahmen, Schriftarten, Zeitreihenaufbau und andere Gestaltungsdetails bleiben beim Umordnen vollständig erhalten.

Ein neuer erweiterter Gestaltungseditor für das Handy ist nicht erforderlich. Vorhandene Handyfunktionen werden hierfür nicht entfernt.

## 2. Variables Raster und Displayformate

- Zeilen und Spalten je Seite unabhängig von 1 bis 128 einstellen; Rastervorlagen und eigene Voreinstellungen speichern.
- Widgets bleiben an ganze Rasterzellen gebunden und dürfen weder überlappen noch außerhalb der Seite liegen.
- Bisherige Mindestgrößen in Rasterzellen entfallen. Kleine Inhalte erhalten Lesbarkeitswarnungen.
- Rasterlinien lassen sich ausblenden und erscheinen nicht auf dem fertigen Display.
- Beim Verschieben bleiben Nachbarn stehen. Ungültige Positionen werden markiert; die letzte gültige Anordnung bleibt erhalten.
- Rasteränderungen erzeugen einen proportional umgerechneten Vorschlag. Konflikte lassen sich manuell oder durch ausdrücklich ausgelöste automatische Anordnung beheben.
- Kein Widget wird bei einer Rasteränderung gelöscht.

Profile: 1024×600, 800×480 und eigene Auflösungen, jeweils mit getrennten Layoutvarianten für Quer- und Hochformat. Beim ersten Wechsel wird eine Ausgangsanordnung übernommen; anschließend bleiben beide Varianten unabhängig gespeichert.

Eine Ausgabedrehung um 90°, 180° oder 270° ermöglicht gedreht montierte Displays. Betriebssystemeinstellungen werden dabei nicht automatisch geändert. Das E-Ink-Profil umfasst zunächst Bildschirmgeometrie und Vorschau.

## 3. Erweiterte Gestaltung und Oberfläche

Der Konfigurator orientiert sich an Pages und Keynote: Seitenminiaturen links, große Arbeitsfläche mittig, Eigenschaften rechts und eine kompakte Werkzeugleiste oben. Seitenleisten sind anpassbar und ausblendbar. Die Gestaltung folgt Apples Mustern für [Seitenleisten](https://developer.apple.com/design/human-interface-guidelines/sidebars) und [Werkzeugleisten](https://developer.apple.com/design/human-interface-guidelines/toolbars).

Die Eigenschaften erhalten Suchfunktion, deutsche Bezeichnungen, direkte Zahleneingaben, Schieberegler und kurze Hilfetexte. Mehrfachauswahl, Kontextmenüs, Tastaturbedienung und mindestens 100 gemeinsame Rückgängig-/Wiederholen-Schritte gehören dazu.

Einstellbar sind:

- **Flächen:** Hintergrundfarben, Transparenz, Farbverläufe, Hintergrundbilder und Bildausschnitte für Anzeige, Seiten und Widgets.
- **Rahmen:** Farbe, Stärke einschließlich null, Transparenz, Linienart und einzelne Rahmenseiten.
- **Ecken und Schatten:** gemeinsamer oder je Ecke eigener Radius einschließlich null für eckige Widgets; Schattenfarbe, Versatz und Unschärfe.
- **Abstände und Positionen:** Außen- und Innenabstände, Widgetabstände, Ausrichtung sowie automatische oder freie Anordnung innerhalb eines Widgets.
- **Schriften und Werte:** mitgelieferte und eigene TTF-/OTF-Schriften, Größe, Gewicht, Farbe, Zeilenabstand, Umbruch, automatische Größenanpassung, Beschriftungen, Einheiten und Zahlen-/Zeitformate.
- **Eigene Inhalte:** Datenfelder frei kombinieren; Texte, Bilder, Logos, Linien, Rechtecke und Ellipsen ergänzen; Größe, Rotation und Ebenenreihenfolge einstellen.
- **Karten:** Grundkartenhelligkeit und Farbsättigung, Karten-/Radartransparenz sowie Marker-, Beschriftungs- und Zeitdarstellung.
- **Zeitreihen:** Zeitraum, Schrittweite, Datenfelder, Anordnung und Diagrammdarstellung.

Globale Stile können je Seite, Widget und Inhalt überschrieben werden. Abweichungen sind sichtbar und zurücksetzbar. Stile und eigene Widgetvorlagen lassen sich speichern und übertragen.

Gestaltungswarnungen sollen Experimente ermöglichen. Harte Sperren bleiben auf ungültige Daten, Rasterüberschneidungen und außerhalb liegende Widgets begrenzt. Erforderliche Quellen-, Abdeckungs- und Demohinweise bleiben erhalten.

## 4. Frei konfigurierbare Zeitreihen

Die bisherigen Acht-Stunden-/Fünf-Tage-Ansichten bleiben Vorlagen. Zusätzlich entsteht ein Zeitreihenwidget mit unabhängig wählbarem Beginn, Zeitraum, Werteabstand und Darstellung als Wertkarten, Tabelle, Linien- oder Balkendiagramm.

Minutenregen und Viertelstundenwetter werden beim bisherigen Anbieter angebunden. Verfügbare Kombinationen richten sich nach dessen dokumentierter Datenauflösung und Reichweite. Größere Abstände wählen vorhandene Werte aus; fehlende Werte bleiben Lücken. [OpenWeather-Dokumentation](https://openweathermap.org/api/one-call-4)

Die bisherigen drei Abrufe alle fünf Minuten bleiben erhalten. Zusätzliche Reihen werden gemeinsam zwischengespeichert und innerhalb des 1000er-Limits geplant:

- Datenauflösung und Aktualisierungshäufigkeit getrennt anzeigen.
- Ausgangsvorschlag: Minutenregen alle 30 Minuten, Viertelstundenwetter alle 60 Minuten aktualisieren.
- Zusätzliche Antwortseiten, beide Budgettage, verbleibende reguläre Abrufe und 24 Reserveanfragen berücksichtigen.
- Bei unpassender Tageslast kürzere Zeiträume oder langsamere Aktualisierung anbieten.
- Bestehende Abrufe haben Vorrang; Bearbeitung und Vorschau erzeugen keine Anbieterabrufe.

## 5. Umsetzung, Speicherung und Abnahme

- PC-Konfigurator mit PySide6/Qt; die Pi-Anzeige behält Python/Tkinter.
- Gemeinsamer Pillow-Renderer und dieselben Schriftdateien für PC-Vorschau und Anzeige.
- Gestaltungsformat Version 3 mit Displayvarianten, variablen Rastern, Stilen, Inhalten und Zeitreihen.
- Bestehende Layouts als 12×8-Variante übernehmen und ihre Darstellung erhalten.
- **Handyänderungen als begrenzte Anordnungsoperationen mit Versionsprüfung verarbeiten.** Der Server verändert nur betroffene Positionen, Größen und Seitenzuordnungen; er ersetzt keine Gestaltung durch einen vereinfachten Handyentwurf.
- Entwürfe automatisch unter `private/designer/` sichern; aktive Gestaltung erst durch „Anwenden“ ersetzen.
- Import/Export einschließlich Bildern und Schriften, ohne Schlüssel oder Zähler.
- Pi-Übertragung über bestehendes SSH mit Kompatibilitätsprüfung, vollständiger Bereitstellung, Sicherung, atomarer Übernahme und Bestätigung durch die Anzeige. Geschlossene Anwendungen bleiben geschlossen.

Die Abnahme prüft beide PC-Tabs, Rasterwechsel, Quer-/Hochformat, Gestaltungsdetails, Entwurfssicherung, Zeitreihen und Budgetgrenzen. Zusätzlich wird ausdrücklich geprüft, dass **Handy-Anordnung, Größenänderung und Seitenwechsel funktionieren und sämtliche PC-Gestaltungseigenschaften dabei erhalten bleiben**. Gleichzeitige PC-/Handyänderungen und Übertragungsabbrüche werden simuliert.

Entwicklung und erste Abnahme erfolgen isoliert mit Beispieldaten. Reale neue Wetterabrufe und die erste Pi-Übernahme werden anschließend gesondert abgenommen. Ort und Schlüsselverwaltung bleiben im bestehenden Einstellungsweg.