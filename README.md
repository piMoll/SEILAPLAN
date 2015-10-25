SEILAPLAN Seilkran-Layoutplaner
===============================

Eng: SEILAPLAN is a QGIS Plugin to support forest harvest operations by optimizing the layout of cable roads. At the moment the plugin is available only in german.
De: SEILAPLAN ist ein QGIS Plugin zur Unterstützung der Waldberwirtschaftung und optimiert das Layout einer Seillinie. Das Plugin ist nur in deutscher Sprache vorhanden.

Algorithmus
-----------

Der Algorithmus berechnet auf Basis eines digitalen Höhenmodells zwischen definierten Anfangs- und Endkoordinaten sowie technischen Parametern das optimale Seillinienlayout. Es werden Position und Höhe der Stützen, sowie die wichtigsten Kennwerte der Seillinie bestimmt.

Das Plugin benötigt folgende Input-Daten:
0. Höhenmodell (alle von QGIS unterstützen Formate)
0. Anfangs- und Endpunkt (können in die Karte gezeichnet oder als Koordinatenpaare angegeben werden)
0. Auswahl oder Definition eines Seilkran-Typs

Installation
------------

Das Plugin kann in QGIS direkt eingebunden werden. Dazu muss unter Plugin-Management -> Einstellungen eine neue Online-Quelle (Repository) mit folgender Adresse hinzugefügt werden:
    https://raw.githubusercontent.com/piMoll/SEILAPLAN/master/plugin.xml


Update
------

Ist eine neue Version des Plugins vorhanden, wird das am unteren Rand der QGIS-Benutzeroberfläche angezeigt. Durch Klick auf den Link wird die aktuelle Version heruntergeladen.


Kontakt
-------

Das Plugin wurde an der Professur für Land Use Engineering (LUE) an der ETH Zürich entwickelt. Für Fragen kontaktieren Sie bitte Jochen Breschan, jochen.breschan@usys.ethz.ch.


