SEILAPLAN Seilkran-Layoutplaner
===============================

De: SEILAPLAN ist ein QGIS Plugin zur Unterstützung der Waldberwirtschaftung und optimiert das Layout einer Seillinie. Das Plugin ist nur in deutscher Sprache vorhanden.

En: SEILAPLAN is a QGIS Plugin to support forest harvest operations by optimizing the layout of cable roads. At the moment the plugin is only available in german.

Algorithmus
-----------

Der Algorithmus berechnet auf Basis eines digitalen Höhenmodells zwischen definierten Anfangs- und Endkoordinaten sowie technischen Parametern das optimale Seillinienlayout. Es werden Position und Höhe der Stützen, sowie die wichtigsten Kennwerte der Seillinie bestimmt.

Das Plugin benötigt folgende Input-Daten:  

0. Höhenmodell (alle von QGIS unterstützen Raster-Formate)
0. Anfangs- und Endpunkt (können in die Karte gezeichnet oder als Koordinatenpaare angegeben werden)
0. Auswahl oder Definition eines Seilkran-Typs

Installation
------------

Das Plugin kann in QGIS direkt eingebunden werden. Dazu muss unter Plugin-Management -> Einstellungen eine neue Online-Quelle (Repository) mit folgender Adresse hinzugefügt werden:
    https://raw.githubusercontent.com/piMoll/SEILAPLAN/master/plugin.xml


Update
------

Ist eine neue Version des Plugins vorhanden, wird das am unteren Rand der QGIS-Benutzeroberfläche angezeigt. Durch Klick auf den Link wird die aktuelle Version heruntergeladen.


Realisierung
------------

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

Kontakt
-------

Für Fragen kontaktieren Sie bitte Leo Bont.  
seilaplanplugin@gmail.com


