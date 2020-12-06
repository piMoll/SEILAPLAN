![Seilaplan Bearbeitungsfenster mit Seillinien-Layout](https://github.com/piMoll/SEILAPLAN/raw/master/docs/gui_preview.png)

## Installation
Voraussetzung für die Installation von Seilaplan ist QGIS ab Version 3.0: [QGIS herunterladen](https://www.qgis.org/de/site/forusers/download.html).

Das Plugin kann direkt im QGIS Plugin-Manager eingebunden werden: Dazu im Menü unter _Erweiterungen > Erweiterungen verwalten > Einstellungen_ eine neue Online-Quelle (Reositorium) mit folgender Adresse hinzufügen:
```
https://raw.githubusercontent.com/piMoll/SEILAPLAN/master/plugin.xml
```

Seilaplan kann anschliessend über die Suchfunktion aufgerufen und installiert werden.

Detailiert Installationsanleitung, Erste Schritte und Fehlerbehebungen finden sich im PDF: [SEILAPLAN_Installation_und_erste_Schritte.pdf](https://github.com/piMoll/SEILAPLAN/raw/master/help/docs/SEILAPLAN_Installation_und_erste_Schritte.pdf)


## Dokumentation
* Theoretische Dokumentation der Berechnungsgrundlagen: [SEILAPLAN_Theoretische_Doku.pdf](https://github.com/piMoll/SEILAPLAN/raw/master/help/docs/SEILAPLAN_Theoretische_Doku.pdf)
* Technische Dokumentation der Plugin-Implementation: [SEILAPLAN_QGIS_Plugin_Doku.pdf](https://github.com/piMoll/SEILAPLAN/raw/master/help/docs/SEILAPLAN_QGIS_Plugin_Doku.pdf)


## Algorithmus
Der Algorithmus berechnet auf Basis eines digitalen Höhenmodells zwischen definierten Anfangs- und Endkoordinaten sowie technischen Parametern das optimale Seillinienlayout. Es werden Position und Höhe der Stützen, sowie die wichtigsten Kennwerte der Seillinie bestimmt.

Das Plugin benötigt folgende Input-Daten:  

1. Höhenmodell (alle von QGIS unterstützen Raster-Formate) oder Längsprofil (CSV)
2. Anfangs- und Endpunkt (können in die Karte gezeichnet oder als Koordinatenpaare angegeben werden)
3. Auswahl oder Definition eines Seilkran-Typs 

## Realisierung
**Professur für Forstliches Ingenieurwesen**  
ETH Zürich  
8092 Zürich  
(Konzept, Realisierung Version 1.x für QGIS 2) 

**Gruppe Forstliche Produktionssysteme FPS**  
Eidgenössische Forschungsanstalt WSL  
8903 Birmensdorf  
(Realisierung Version 2.x für QGIS 3) 

**Beteiligte Personen**  
Leo Bont, Hansrudolf Heinimann (Konzept, Mechanik)  
Patricia Moll (Implementation in Python / QGIS)  
Laura Rammstein (Koordination Weiterentwicklung)

## Kontakt
Für Fragen steht Ihnen Leo Bont zur Verfügung.  
seilaplanplugin@gmail.com
