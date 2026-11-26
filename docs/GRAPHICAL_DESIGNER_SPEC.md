# Grafischer Widget-Editor mit moderner Oberfläche

## Ziel und Bedienprinzip

Die parametrischen Einstellungen werden durch eine gleichwertige grafische Bearbeitung ergänzt. Beide arbeiten am selben Entwurf und bleiben jederzeit synchron.

Die zwei Tabs bleiben erhalten:

- **Widgets anordnen:** ganze Widgets verschieben und skalieren.
- **Erweiterte Gestaltung:** zusätzlich sämtliche Inhaltsblöcke direkt anklicken, verschieben und skalieren.

Die Handy-Anordnung bleibt bestehen. Die erweiterte Inhaltsgestaltung bleibt am PC.

## Grafische Bearbeitung

- Ausgewählte Widgets und Inhalte erhalten **acht gut greifbare Größenanfasser** an Ecken und Seiten. Größe und Trefferfläche der Anfasser bleiben unabhängig vom Zoom bedienbar.
- Im erweiterten Tab wählt ein Klick unmittelbar den getroffenen Inhalt. Ziehen verschiebt ihn. Das gesamte Widget lässt sich über seinen Rahmen bewegen; bei überlagerten Inhalten hilft die vorhandene Inhaltsliste.
- Während des Ziehens aktualisiert sich die tatsächliche Vorschau. Hilfslinien und eine kompakte Positions-/Größenanzeige unterstützen die Platzierung.
- **Escape** verwirft die laufende Bewegung. Eine abgeschlossene Bewegung bildet genau einen Rückgängig-Schritt.
- Widgets bleiben an das äußere Seitenraster gebunden. Überschneidungen werden markiert; beim Loslassen einer ungültigen Position bleibt der letzte gültige Stand erhalten.
- Beim Skalieren eines Widgets passen sich Positionen und Inhaltsflächen **proportional** an. Schriftgrößen folgen weiterhin ihrer Einstellung zur automatischen Größenanpassung.

### Gemeinsames Innenraster

- Alle Widgets verwenden denselben einstellbaren Rasterabstand, zunächst **8 logische Displaypixel**, wählbar von 1 bis 128.
- Das Raster beginnt jeweils innerhalb der nutzbaren Inhaltsfläche nach Abzug der Innenabstände.
- Rasteranzeige und Einrasten sind getrennt schaltbar. **Alt** setzt das Einrasten während einer Bewegung vorübergehend aus.
- Das Innenraster erscheint ausschließlich im Editor. Bestehende Positionen werden beim Einschalten oder Ändern des Rasters nicht automatisch verschoben; Einrasten greift bei der nächsten grafischen Bearbeitung.

### Ausrichtung und Inhaltsblöcke

- Gut sichtbare Schaltflächen für **linksbündigen, zentrierten und rechtsbündigen Text** sowie vertikale Textausrichtung.
- Davon getrennte Befehle zum Ausrichten ausgewählter Inhaltsflächen an linken/rechten Kanten, Mitte sowie oben/unten. Mehrfachauswahl ermöglicht gemeinsames Verschieben und gleichmäßiges Verteilen.
- Titel, Wetterwerte, Texte, Bilder und Formen bleiben einzeln bearbeitbar.
- Karten, Diagramme und Tabellen werden als zusammenhängende Inhaltsblöcke verschoben und skaliert. Einzelne Zeitreihenzellen erhalten keinen zusätzlichen freien Editor.
- Ein normales Wetterwidget behält seinen Typ und seine Datenbindungen. Zum grafischen Bearbeiten ist keine manuelle Umwandlung in ein eigenes Widget mehr erforderlich.
- Notwendige Quellen-, Abdeckungs- und Demohinweise bleiben geschützt.

## Modernes Erscheinungsbild

Die Oberfläche orientiert sich an der ruhigen Gestaltung von Pages und Keynote:

- Helle Flächen, großzügige Abstände, dezente Trennlinien und sparsame blaue Akzente; der vorhandene Dunkelmodus erhält dieselbe Gestaltung.
- Kompakte, überwiegend rahmenlose Werkzeuggruppen mit konsistenten Vektorsymbolen und verständlichen Tooltips.
- Zusammenhängende Segmentsteuerungen für die beiden Tabs und die Ausrichtung.
- Klar gegliederte Eigenschaften mit Suche, aufklappbaren Gruppen und weiterhin verfügbaren präzisen Zahlenfeldern.
- Moderne Systemschrift für das Werkzeug; unter Windows bevorzugt Segoe UI. Die Schriftwahl der gestalteten Wetteranzeige bleibt davon unabhängig.
- Auswahlrahmen, Raster und Hilfslinien erscheinen zurückhaltend und nur dort, wo sie bei der Bearbeitung helfen.

## Speicherung und Kompatibilität

- Das Gestaltungsformat wird auf **Version 4** erweitert: gemeinsames Innenraster und frei positionierbare Inhaltsblöcke einschließlich strukturierter Blöcke.
- Bestehende Formate 2 und 3 werden verlustfrei eingelesen. Ohne grafische Änderungen bleiben Darstellung und Datenversorgung erhalten.
- PC-Vorschau und Pi-Anzeige verwenden weiterhin denselben Renderer.
- Handy-Anordnungsbefehle bewahren die neuen Inhaltspositionen vollständig.
- Vor einer Pi-Übernahme wird Unterstützung für das neue Format geprüft. Inkompatible Programme dürfen Gestaltungen weder übernehmen noch stillschweigend zurücksetzen.
- Entwurfssicherung, explizites Anwenden und gemeinsame Rückgängig-/Wiederholen-Historie bleiben erhalten.

## Prüfung und Abnahme

- Ziehen und Skalieren über alle acht Anfasser bei unterschiedlichen Zoomstufen und 100/150/200 Prozent Skalierung.
- Direktauswahl überlagerter Inhalte, Mehrfachauswahl, Textausrichtung und Ausrichtung ganzer Inhaltsflächen.
- Innenraster, Einrasten, Alt-Ausnahme und proportionaler Größenwechsel.
- Erhalt von Datenbindungen, Zeitreihen, Kartenhinweisen und bestehenden Gestaltungen nach Laden, Export/Import und Handy-Anordnung.
- Wiederholte ungültige Bewegungen und Zahleneingaben ohne Absturz oder Entwurfsverlust; anschließend Weiterbearbeiten und Anwenden.
- Visuelle Kontrolle beider Tabs im hellen und dunklen Modus.

Die Umsetzung und Abnahme erfolgen mit Beispieldaten und isolierten Einstellungen. Echte Wetterabrufe oder eine Übertragung auf den realen Pi gehören nicht zu diesem Auftrag.
