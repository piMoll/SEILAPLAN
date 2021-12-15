# Seilaplan Changelog

## Version 3.3.0 (Dezember 2021)
### Neue Features
* Erfassen und Speichern von Projekt-Metadaten wie Autor, Projektnummer, Waldort, etc. Projekt-Metadaten werden in den Berichten aufgelistet
* Projekteinstellungen werden neu im JSON-Format anstatt Textformat abgepseichert (alte Projekteinstellungen im Textformat werden weiterhin unterstützt)
* Überarbeitung und Vereinheitlichung diverser Fachbegriffe in der deutschen Version
* Anzeige von Kennwerten im Diagramm des Überarbeitungsfensters: Neu werden Kennwerte immer angezeigt, egal ob der Grenzwert überschritten wurde
* Die Standardeinstellung für Anfangs- und Endpunkt der Seillinine ist neu eine Verankerung anstatt eine Stütze

### Fehlerbehebung
* Berichtinhalt ist nur teilweise sichtbar, bzw. verschoben, wenn eine Seillinie ohne Zwischenstützen oder nur mit Verankerungen erstellt wird
* Im Parameterset "MSK 3t 20/11/8mm" wurde der Seildurchmesser von 22 auf 20 mm korrigiert
* Der Stützentyp (Verankerung, Stütze, Seilkran) wird korrekt aus den Projekteinstellungen ausgelesen
* Bei der Erstellung von Geländeprofilen aus Vertex-Dateien werden neu nicht nur die GPS-Messungen, sondern auch die relativen Distanz- und Winkelmessungen berücksichtigt.

## Version 3.2.1 (Juni 2021)
### Neue Features
* Fehlermeldung bei Plugin-Installation in QGIS 3.20 / 3.16.8
* Rasterlayer werden in Auswahlliste nicht selektiert, wenn eine Projektdatei geladen wird

## Version 3.2 (Juni 2021)
### Neue Features
* Mehrfachauswahl von Raster-Kacheln: Neu können mehrere Rasterlayer ausgewählt werden, sodass die Seillinien über Kachelgrenzen hinweg konstruiert werden kann

### Fehlerbehebung
* Korrektur der Berechnung für Angriffswinkel bei 0 Meter hohen Stützen

## Version 3.1 (November 2020)
### Neue Features
* Einführung Maschinen-Parameter "Grundspannung" 
* Angabe des Durchmessers der Bundstelle im Kurzbericht

### Fehlerbehebung
* diverse Fehlerkorrekturen

## Version 3.0 (September 2020)
### Neue Features
* Überarbeitung des Plugins und Ergänzung von zusätzlichen Eingabeparametern
* Erweiterung um manuelle Editiermöglichkeiten der Seillinie
* Übersetzung nach EN, IT, FR

## Version 2.0 (Februar 2018)
Portierung auf QGIS 3

## Version 1.0 (Mai 2015)
Initiale Version
