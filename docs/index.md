[**GitHub Repository**](https://github.com/piMoll/SEILAPLAN)

[**Changelog**](https://github.com/piMoll/SEILAPLAN/blob/master/changelog.md)


![Seilaplan Bearbeitungsfenster mit Seillinien-Layout](https://github.com/piMoll/SEILAPLAN/raw/master/docs/gui_preview.png)

## Installation
Voraussetzung für die Installation von Seilaplan ist QGIS ab Version 3.6: [QGIS herunterladen](https://www.qgis.org/de/site/forusers/download.html).

Es wird emfohlen eine aktuelle Langzeitversion (LTS) von QGIS zu benutzen.
Aufgrund von internen Fehlern in QGIS, kann das Plugin in folgenden QGIS-Versionen nicht ausgeführt werden:
* 3.10.9
* 3.14.15
* 3.16.12
* 3.16.13

Das Plugin kann direkt im QGIS Plugin-Manager eingebunden werden. Dazu im Menü unter _Erweiterungen > Erweiterungen verwalten > Einstellungen_ eine neue Online-Quelle (Repositorium) mit folgender Adresse hinzufügen:
```
https://raw.githubusercontent.com/piMoll/SEILAPLAN/master/plugin.xml
```

Seilaplan kann anschliessend über die Suchfunktion aufgerufen und installiert werden.

Eine detaillierte Installationsanleitung, Erste Schritte und Fehlerbehebungen finden sich im PDF: [SEILAPLAN_Installation_und_erste_Schritte.pdf](https://github.com/piMoll/SEILAPLAN/raw/master/help/SEILAPLAN_Installation_und_erste_Schritte.pdf)


## Dokumentation
* Theoretische Dokumentation der Berechnungsgrundlagen: [SEILAPLAN_Theoretische_Doku.pdf](https://github.com/piMoll/SEILAPLAN/raw/master/help/SEILAPLAN_Theoretische_Doku.pdf)
* Technische Dokumentation der Plugin-Implementation: [SEILAPLAN_QGIS_Plugin_Doku.pdf](https://github.com/piMoll/SEILAPLAN/raw/master/help/SEILAPLAN_QGIS_Plugin_Doku.pdf)

## Bezug von Höhendaten für die Schweiz
Seit Frühjahr 2021 stellt das Schweizer Bundesamt für Landestopografie swisstopo sehr genaue Höhendaten zum freien Download zur Verfügung. 
Die Daten können mit dem QGIS Plugin _Swiss Geo Downloader_ bequem in QGIS heruntergeladen werden.  
Die Installation des Plugins wird im Menü _Erweiterungen_ > _Erweiterungen verwalten und installieren_ durchgeführt
(links auf Reiter _Alle_ oder _Nicht installiert_ klicken).
Im Suchfeld _Swiss Geo Downloader_ eingeben und das Plugin auswählen. Rechts unten _Erweiterung installieren_ klicken.  
Das Plugin kann nach erfolgreicher Installation in der Toolbar oder im Menü _Web_ geöffnet werden.

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
Laura Ramstein (Koordination Weiterentwicklung)

## Kontakt
Für Fragen steht Ihnen Leo Bont zur Verfügung.  
seilaplanplugin@gmail.com


## Zitiervorschlag
Verwendung für wissenschaftliche Zwecke:

«Bont, L. G., Moll, P. E., Ramstein, L., Frutig, F., Heinimann, H. R., & Schweier, J. (2022). SEILAPLAN, a QGIS plugin for cable road layout design. Croatian Journal of Forest Engineering: Journal for Theory and Application of Forestry Engineering, 43(2), 241-255.»


Zitiervorschlag Quellcode:

«Moll, P. E., Bont, L. G., Ramstein, L., Frutig, F., Heinimann, H. R., & Schweier, J. (2022). SEILAPLAN, a QGIS plugin for cable road layout design, version 3.5.0, https://github.com/piMoll/SEILAPLAN»
