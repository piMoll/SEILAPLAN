"""
/***************************************************************************
 SeilaplanPlugin
                                 A QGIS plugin
 Seilkran-Layoutplaner
                              -------------------
        begin                : 2013
        copyright            : (C) 2015 by ETH Zürich
        email                : seilaplanplugin@gmail.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
import os

from qgis.PyQt.QtCore import QSize, Qt, QFileInfo, QSettings
from qgis.PyQt.QtWidgets import (QDialog, QWidget, QLabel, QDialogButtonBox,
                                 QLayout, QVBoxLayout)
from qgis.core import QgsRasterLayer, QgsVectorLayer, QgsProject
from processing import run

from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT \
    as NavigationToolbar


class DialogWithImage(QDialog):
    def __init__(self, interface):
        QDialog.__init__(self, interface.mainWindow())
        self.iface = interface
        self.main_widget = QWidget(self)
        self.main_widget.setMinimumSize(QSize(100, 100))
        self.label = QLabel()
        self.buttonBox = QDialogButtonBox(self.main_widget)
        self.buttonBox.setStandardButtons(QDialogButtonBox.Ok)
        self.buttonBox.accepted.connect(self.Apply)
        # Access the layout of the MessageBox to add the checkbox
        self.container = QVBoxLayout(self.main_widget)
        self.container.addWidget(self.label)
        self.container.addWidget(self.buttonBox)
        self.container.setAlignment(Qt.AlignCenter)
        self.container.setSizeConstraint(QLayout.SetFixedSize)
        self.setLayout(self.container)

    def Apply(self):
        self.close()


class MyNavigationToolbar(NavigationToolbar):
    # Only display the buttons we need
    toolitems = [t for t in NavigationToolbar.toolitems if
                 t[0] in ('Home', 'Pan', 'Zoom')]

    def __init__(self, *args, **kwargs):
        super(MyNavigationToolbar, self).__init__(*args, **kwargs)
        self.layout().takeAt(3)  # 3 = Amount of tools we need


def createContours(canvas, dhm):
    contourLyr = dhm.contour
    contourName = "Hoehenlinien_" + dhm.name
    
    # Get current CRS of qgis project
    s = QSettings()
    oldValidation = s.value("/Projections/defaultBehaviour")
    crs = canvas.mapSettings().destinationCrs()
    crsEPSG = crs.authid()
    # If project and raster CRS are equal and set correctly
    if crsEPSG == dhm.spatialRef and "USER" not in crsEPSG:
        s.setValue("/Projections/defaultBehaviour", "useProject")
    else:
        crs = dhm.layer.crs()
    
    # If contours exist, remove them
    if contourLyr:
        QgsProject.instance().removeMapLayer(contourLyr.id())
        contourLyr = None
    
    # If no contours exist, create them
    else:
        # TODO: IN MEMORY LAYER
        outputPath = os.path.join(os.path.dirname(dhm.path), contourName + '.shp')
        if os.path.exists(outputPath):
            contourLyr = QgsVectorLayer(outputPath, contourName, "ogr")
        else:
            processingParams = {
                'INPUT': dhm.layer,
                'BAND': 1,
                'INTERVAL': 20,
                'FIELD_NAME': "Hoehe",
                'OUTPUT': outputPath
            }
            algOutput = run("gdal:contour", processingParams)
            contourLyr = QgsVectorLayer(algOutput['OUTPUT'], contourName, "ogr")
        # contourLyr the same CRS as qgis project
        contourLyr.setCrs(crs)
        QgsProject.instance().addMapLayer(contourLyr)
        s.setValue("/Projections/defaultBehaviour", oldValidation)
        
    # More useful stuff
    # uri = "linestring?crs=epsg:{}".format(crsNum)
    # contourName = "Hoehenlinien_" + self.dhm['name']
    # contour = QgsVectorLayer(uri, contourName,  "memory")
    
    return contourLyr


def loadOsmLayer(homePath):
    # TODO: Wird in Karte nicht dargestellt: Wahrsch. Projektionsproblem
    osmLyr = None
    
    for l in QgsProject.instance().layerTreeRoot().findLayers():
        if l.layer().name() == 'OSM_Karte':
            osmLyr = l.layer()
            QgsProject.instance().removeMapLayer(osmLyr.id())
            break
            
    if not osmLyr:
        # Add OSM layer
        xmlPath = os.path.join(homePath, 'config', 'OSM_Karte.xml')
        baseName = QFileInfo(xmlPath).baseName()
        osmLayer = QgsRasterLayer(xmlPath, baseName)
        QgsProject.instance().addMapLayer(osmLayer)
