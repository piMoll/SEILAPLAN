# Seilaplan Changelog

## Version 3.6.0 (Juli 2024)
### Neue Features
* Seilaplan kann mehrfach gestartet werden, um Projekte (bzw. Varianten) parallel zu bearbeiten
* Neue Parameter um Grenzwerte für Leer- und Lastseilknickwinkel zu definieren (bisher fix 1/3° und 30/60°)
* Neuer Parameter um die Höhe der Bundstelle über der Sattelleiste zu definieren (bisher fix 1.5 m)
* Bearbeitungsfenster:
  * Über eine Auswahlliste KÖNNEN zusätzliche Informationen (BHD, Durchhang, Knickwinkel, etc.) im Diagramm angezeigt werden
  * Im neuen Tab "Parameter" kann das verwendete Parameterset ausgetauscht werden
  * Im Diagramm wird der Seildurchhang statt einmal für die gesamte Seillinie, neu für jedes Seilfeld einzeln ausgegeben
  * Pro Stütze wird der Bundstellendurchmesser angegeben
  * Stützenbezeichnungen können neu 42 statt 22 Zeichen lang sein. Im Diagramm-PDF wurde die Lesbarkeit der Bezeichnungen verbessert
* Vogelperspektive: Angepasstes Symbol für Mehrbaumanker; Abspannseile enden am Anfangs- / Endpunkt der Seillinie, nicht dahinter
* Exportierte PDFs (Diagramm, Berichte) enthalten den eindeutigen Namen des Projektordners
* Automatisch erzeugte Projektbezeichnung enthält Jahresangabe und ist ISO-ähnlich formatiert
* Diverse Verbesserung der Benutzerführung: Anpassung von Bezeichnungen und Ergänzen von Hinweisen

### Fehlerbehebung
* Kurzbericht: Korrektur der Angriffswinkel-Berechnung für befahrbare Endstützen
* Bundstelle ist neu 3.0 m statt bisher 1.5 m über Sattelleiste, Wert ist anpassbar
* Behebe Problem beim Erzeugen des Diagramm-PDFs, das ältere QGIS-Versionen zum Absturz bringt

## Version 3.5.3 (Mai 2024)
### Fehlerbehebung
* Fehler beim Start des Plugins auf Windows mit QGIS Version 3.36, weil eine scipy-Bibliothek fehlt
  * 
## Version 3.5.2 (März 2024)
### Fehlerbehebung
* Vogelperspektive
  * Korrigiere Stützensymbole, wenn sie rechts des Seils und in Richtung des Anfangspunkts orientiert sein sollten
  * Passe Reihenfolge von Stützentypen in Auswahlliste an; erst Stützen-, dann Ankertypen

## Version 3.5.1 (Januar 2024)
### Fehlerbehebung
* Vogelperspektive: Überarbeite Stützensymbole, passe Länge der Abspannseile an
* Ergänze Kennwerte im Bearbeitungsfenster: Zeige die max. Seilzugkraft am höchsten Punkt im Diagramm an
* Fehler: Verschieben der Stütze ans Ende oder Anfang des Profils verursacht Plugin-Absturz

## Version 3.5.0 (August 2023)
### Neue Features
* Vogelperspektive: Darstellung der Seillinie, Stützen und Abspannseile aus der Vogelperspektive
  * Konfiguriere Stützenkategorie und -position, sowie Ausrichtung der Abspannseile in einem neuen Tab
  * Exportiere Vogelperspektive als Diagramm unterhalb des Seitenprofils
  * Ergänzung der Stützeneigenschaften in Berichten und Geodaten-Export
* Hintergrundkarte darstellen: Bei QGIS-Projekten im CH-Koordinatensystem wird neu die Schweizer Landeskarte statt der OSM-Karte geladen

## Version 3.4.2 (Juni 2023)
### Fehlerbehebung
* Geländeprofil aus Haglöf Vertex: Ergänze Standort der ersten Messung (Punkt Nr. 0)
* Korrigiere die Darstellung des Durchmesser-Symbols in Berichten
* Problembehebung bei der Erstellung von Profillinien bei Seillinien in Richtung 0, 100, 200 oder 300 Gon
* Beim Laden von reportlab (Bibliothek für Berichterstellung) wird die im System installierte Version bevorzugt

## Version 3.4.1 (Dezember 2022)
### Neue Features
* Geländelinie als DXF, KML und Shapefile exportieren
* Profilansicht (Seitenansicht) als DXF exportieren
* Überarbeitung des Speichern-Dialogfensters
* Geodaten in separate Ordner abspeichern

### Fehlerbehebung
* Kurzbericht: Wert für maximalen Abstand Seil - Boden korrigiert
* Haglöf Vertex CSV Import: Nur Messungen vom Typ "TRAIL" berücksichtigen, "3P" Messungen als Zusatzinformation im Geländeprofil anzeigen
* Fehlermeldung beim Erstellen von QGIS Layern behoben

## Version 3.4.0 (Mai 2022)
### Neue Features
* Profil-Import aus Feldaufnahmeprotokoll, inkl. Protokoll-Vorlage im Excel-Format
* Auswahl und Import des Geländeprofils in einem separaten Dialogfenster
* Vorlage für Profile im CSV Format mit X-, Y-, Z-Koordinaten
* Erhöhung der max. zulässigen Werte für: Gewicht Last (neu 250 kN), Mindestbruchlast Tragseil (neu 5000 kN), Tragseilspannkraft am Anfangspunkt (neu 1000 kN)

### Fehlerbehebung
* Besseres Abfangen von Fehlern beim Import von Geländeprofilen
* Auswahlliste für Raster zeigt keine WMS-Layer mehr
* Besseres Abfangen von Fehlern beim Aufbereiten von Rasterdaten
* Verbesserung der Formatierung von Koordinaten-Werte für internationale Benutzer
* Karten-Markierungen für fixe Stützen verschwinden nach dem Löschen zuverlässig

## Version 3.3.0 (Januar 2022)
### Neue Features
* Erfassen und Speichern von Projekt-Metadaten wie Autor, Projektnummer, Waldort, etc. Projekt-Metadaten werden in den Berichten aufgelistet
* Projekteinstellungen werden neu im JSON-Format anstatt Textformat abgespeichert (alte Projekteinstellungen im Textformat werden weiterhin unterstützt)
* Überarbeitung und Vereinheitlichung diverser Fachbegriffe in der deutschen Version
* Anzeige von Kennwerten im Diagramm des Überarbeitungsfensters: Neu werden Kennwerte immer angezeigt, egal ob der Grenzwert überschritten wurde
* Die Standardeinstellung für Anfangs- und Endpunkt der Seillinie ist neu eine Verankerung anstatt eine Stütze

### Fehlerbehebung
* Der Berichtinhalt ist nur teilweise sichtbar, bzw. verschoben, wenn eine Seillinie ohne Zwischenstützen oder nur mit Verankerungen erstellt wird
* Der Berichtinhalt ist nur teilweise sichtbar, bzw. verschoben, wenn mehr als 7 Stützen aufgelistet werden
* Im Parameterset "MSK 3t 20/11/8mm" wurde der Seildurchmesser von 22 auf 20 mm korrigiert
* Der Stützentyp (Verankerung, Stütze, Seilkran) wird korrekt aus den Projekteinstellungen ausgelesen
* Bei der Erstellung von Geländeprofilen aus Vertex-Dateien werden neu die relativen Distanz- und Winkelmessungen anstatt die GPS-Messungen für die Berechnung verwendet. Die GPS-Messungen werden nur für die Georeferenzierung des Profils benutzt.
* Beim Öffnen des Geländelinien-Fensters wurde ein leeres Diagramm dargestellt
* Parametersets verschwinden nach Plugin-Update. Dieses Problem tritt einmalig bei der Aktualisierung auf die aktuelle Version 3.3.0 auf, zukünftig nicht mehr.
  * Hinweis: Verschwundene Prametersets können Sie wiederherstellen, indem Sie alte Projektdateien laden, die mit dem Parameterset berechnet wurden.

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
