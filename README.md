SEILAPLAN Seilkran-Layoutplaner
===============================

SEILAPLAN is a QGIS Plugin to support forest harvest operations by optimizing the layout of cable roads. The Plugin is available only in german.

SEILAPLAN ist ein QGIS Plugin zur Unterstützung der Waldberwirtschaftung und optimiert das Layout einer Seillinie. Das Plugin ist nur in deutsch vorhanden.

Algorithmus
-----------

Der Algorithmus berechnet auf Basis eines digitalen Höhenmodells zwischen definierten Anfangs- und Endkoordinaten sowie technischen Parametern das optimale Seillinienlayout. Es werden Position und Höhe der Stützen, sowie die wichtigsten Kennwerte der Seillinie bestimmt.

Das Plugin benötigt folgende Input-Daten:

0. Höhenmodell (alle von QGIS unterstützen Formate)
0. Anfangs- und Endpunkt (können in die Karte gezeichnet oder als Koordinatenpaare angegeben werdne)
0. Auswahl oder Definition eines Seilkran-Typs

Installation
------------

Das Plugin kann direkt über GitHub in QGIS eingebunden werden. Dazu muss unter Plugin-Management -> Einstellungen eine neue Online-Quelle hinzugefügt werden:
    https://raw.githubusercontent.com/piMoll/SEILAPLAN/master/plugin.xml


Update
------

Ist eine neue Version des Plugins vorhanden, wird das am unteren Rand der QGIS-Benutzeroberfläche angezeigt. Durch Klick auf den Link wird die aktuelle Version heruntergeladen.

