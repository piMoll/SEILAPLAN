[**GitHub Repository**](https://github.com/piMoll/SEILAPLAN)

[**Changelog**](https://github.com/piMoll/SEILAPLAN/blob/master/changelog.md)

_[See english version below](#Seilaplan)_

# SEILAPLAN

SEILAPLAN ist ein QGIS Plugin zur Unterstützung der Waldbewirtschaftung und
optimiert das Layout einer Seillinie.


![Seilaplan Bearbeitungsfenster mit Seillinien-Layout](https://github.com/piMoll/SEILAPLAN/raw/master/docs/gui_preview.png)

## [**Docs**](https://github.com/piMoll/SEILAPLAN/tree/master/help)

* [de] Theoretische Dokumentation der
  Berechnungsgrundlagen: [SEILAPLAN_Theoretische_Doku.pdf](https://github.com/piMoll/SEILAPLAN/raw/master/help/SEILAPLAN_Theoretische_Doku.pdf)
* [de] Technische Dokumentation der
  Plugin-Implementation: [SEILAPLAN_QGIS_Plugin_Doku.pdf](https://github.com/piMoll/SEILAPLAN/raw/master/help/SEILAPLAN_QGIS_Plugin_Doku.pdf)

## Installation
Voraussetzung für die Verwendung von SEILAPLAN ist [QGIS](https://qgis.org/), ein frei verfügbares geografisches Informationssystem zur Betrachtung und Analyse von Geodaten.

Es wird empfohlen, eine aktuelle Langzeitversion (LTS) von QGIS zu benutzen und diese regelmässig zu aktualisieren.

1. QGIS [herunterladen](https://www.qgis.org/download/) und installieren
2. In QGIS den Plugin-Manager öffnen: Menü _Erweiterungen > Erweiterungen verwalten und installieren_
3. Im Reiter _Alle_ nach «SEILAPLAN» suchen
4. Eintrag auswählen und _Erweiterung installieren_ klicken
5. Das Seilaplan Icon ![Icon](https://github.com/piMoll/SEILAPLAN/raw/master/docs/seilaplan_icon.png) sollte in der Werkzeugleiste sichtbar werden. Falls nicht, Rechtsklick auf die Werkzeugleiste und Eintrag _Erweiterungswerkzeugleiste_ aktivieren

Weitere Informationen, erste Schritte und Fehlerbehebungen finden sich im PDF: [SEILAPLAN_Installation_und_erste_Schritte.pdf](https://github.com/piMoll/SEILAPLAN/raw/master/help/SEILAPLAN_Installation_und_erste_Schritte.pdf)

## Bezug von Höhendaten für die Schweiz
Seit Frühjahr 2021 stellt das Schweizer Bundesamt für Landestopografie swisstopo sehr genaue Höhendaten zum freien Download zur Verfügung. 
Die Daten können mit dem QGIS Plugin _Swiss Geo Downloader_ bequem in QGIS heruntergeladen werden.  
Die Installation des Plugins wird im Menü _Erweiterungen_ > _Erweiterungen verwalten und installieren_ durchgeführt
(links auf Reiter _Alle_ oder _Nicht installiert_ klicken).
Im Suchfeld _Swiss Geo Downloader_ eingeben und das Plugin auswählen. Rechts unten _Erweiterung installieren_ klicken.  
Das Plugin kann nach erfolgreicher Installation in der Toolbar oder im Menü _Web_ geöffnet werden.

## Optimierungsalgorithmus
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
(Realisierung ab Version 2.x) 

**Beteiligte Personen**  
Leo Bont, Hansrudolf Heinimann (Konzept, Mechanik)  
Patricia Moll (Implementation in Python / QGIS)  
Laura Ramstein (Koordination Weiterentwicklung)

## Kontakt
Für Fragen steht Ihnen Leo Bont zur Verfügung.  
seilaplanplugin@gmail.com


## Zitiervorschlag
Verwendung für wissenschaftliche Zwecke:

```
«Bont, L. G., Moll, P. E., Ramstein, L., Frutig, F., Heinimann, H. R., & Schweier, J. (2022). SEILAPLAN, a QGIS plugin for cable road layout design. Croatian Journal of Forest Engineering: Journal for Theory and Application of Forestry Engineering, 43(2), 241-255.»
```


Zitiervorschlag Quellcode:

```
«Moll, P. E., Bont, L. G., Ramstein, L., Frutig, F., Heinimann, H. R., & Schweier, J. (2022). SEILAPLAN, a QGIS plugin for cable road layout design, version 3.5.0, https://github.com/piMoll/SEILAPLAN»
```

---
_english_

# Seilaplan

SEILAPLAN is a QGIS Plugin to support forest harvest operations by optimizing
the layout of cable roads.

![Seilaplan editing window with cable line layout](https://github.com/piMoll/SEILAPLAN/raw/master/docs/gui_preview.png)

## Installation

To run SEILAPLAN [QGIS](https://qgis.org/) is required, a freely available
geographic information system for viewing and analyzing geodata.

It is recommended to use a current Long Term Support (LTS) version of QGIS and
update it regularly.

1. Download and install QGIS from [here](https://www.qgis.org/download/)
2. Open the Plugin Manager in QGIS: Menu _Plugins > Manage and Install Plugins_
3. In the _All_ tab, search for "SEILAPLAN"
4. Select the entry and click _Install Plugin_
5. The Seilaplan
   icon ![Icon](https://github.com/piMoll/SEILAPLAN/raw/master/docs/seilaplan_icon.png)
   should appear in the toolbar. If not, right-click on the toolbar and
   activate the _Plugins Toolbar_ entry

Further information, first steps, and troubleshooting can be found in the PDF (
german): [SEILAPLAN_Installation_und_erste_Schritte.pdf](https://github.com/piMoll/SEILAPLAN/raw/master/help/SEILAPLAN_Installation_und_erste_Schritte.pdf)

## Obtaining elevation data for Switzerland

Since spring 2021, the Swiss Federal Office of Topography swisstopo has been
providing very accurate elevation data for free download.
The data can be conveniently downloaded in QGIS using the _Swiss Geo
Downloader_ QGIS plugin.  
The plugin can be installed through the menu _Plugins_ > _Manage and Install
Plugins_
(click on the _All_ or _Not Installed_ tab on the left).
Enter _Swiss Geo Downloader_ in the search field and select the plugin. Click
_Install Plugin_ in the bottom right.  
After successful installation, the plugin can be opened from the toolbar or the
_Web_ menu.

## Optimization Algorithm

Based on a digital elevation model, defined start and end coordinates, and
technical parameters, the algorithm calculates the optimal cable line layout.
The position and height of the supports, as well as the most important
characteristics of the cable line, are determined.

The plugin requires the following input data:

1. Elevation model (all raster formats supported by QGIS) or longitudinal
   profile (CSV)
2. Start and end points (can be drawn on the map or specified as coordinate
   pairs)
3. Selection or definition of a cable crane type

## Implementation

**Chair of Forest Engineering**  
ETH Zurich  
8092 Zurich  
(Concept, implementation Version 1.x for QGIS 2)

**Forest Production Systems Group FPS**  
Swiss Federal Research Institute WSL  
8903 Birmensdorf  
(Implementation from Version 2.x)

**Contributing people**  
Leo Bont, Hansrudolf Heinimann (Concept, Mechanics)  
Patricia Moll (Implementation in Python / QGIS)  
Laura Ramstein (Coordination of further development)

## Contact

For questions, please contact Leo Bont.  
seilaplanplugin@gmail.com

## Citation

For scientific purposes:

```
«Bont, L. G., Moll, P. E., Ramstein, L., Frutig, F., Heinimann, H. R., & Schweier, J. (2022). SEILAPLAN, a QGIS plugin for cable road layout design. Croatian Journal of Forest Engineering: Journal for Theory and Application of Forestry Engineering, 43(2), 241-255.»
```

Citation for source code:

```
«Moll, P. E., Bont, L. G., Ramstein, L., Frutig, F., Heinimann, H. R., & Schweier, J. (2022). SEILAPLAN, a QGIS plugin for cable road layout design, version 3.5.0, https://github.com/piMoll/SEILAPLAN»
```
