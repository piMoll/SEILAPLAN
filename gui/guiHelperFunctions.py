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

from qgis.PyQt.QtGui import QFont, QColor
from qgis.PyQt.QtCore import QSize, Qt, QFileInfo, QCoreApplication
from qgis.PyQt.QtWidgets import (QDialog, QWidget, QLabel, QDialogButtonBox,
    QLayout, QVBoxLayout)
from qgis.core import (QgsRasterLayer, QgsPointXY, QgsProject, QgsPoint,
    QgsFeature, QgsGeometry, QgsVectorLayer, QgsPalLayerSettings,
    QgsTextFormat, QgsTextBufferSettings,  QgsVectorLayerSimpleLabeling, Qgis)
from SEILAPLAN import DEBUG

try:
    from processing import run
except ModuleNotFoundError as e:
    if DEBUG:
        pass
    else:
        raise e

# Path to plugin root
HOMEPATH = os.path.dirname(os.path.dirname(__file__))
SWISSTOPO_WMS_URL = 'https://wmts.geo.admin.ch/EPSG/2056/1.0.0/WMTSCapabilities.xml?lang=de'
OVERVIEW_MAP = 'ch.swisstopo.pixelkarte-farbe'
SWISS_CRS = ['EPSG:2056', 'EPSG:21781']


def tr(message, **kwargs):
    """Get the translation for a string using Qt translation API.
    We implement this ourselves since we do not inherit QObject.

    :param message: String for translation.
    :type message: str, QString

    :returns: Translated version of message.
    :rtype: QString

    Parameters
    ----------
    **kwargs
    """
    return QCoreApplication.translate('@default', message)


class DialogWithImage(QDialog):
    def __init__(self):
        QDialog.__init__(self)
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


def createContours(canvas, heightSource):
    contourName = tr("Hoehenlinien_") + heightSource.name
    crs = heightSource.spatialRef
    outputPath = os.path.join(os.path.dirname(heightSource.path),
                              contourName + '.shp')
    if os.path.exists(outputPath):
        contourLyr = QgsVectorLayer(outputPath, contourName, "ogr")
    else:
        processingParams = {
            'INPUT': heightSource.layer,
            'BAND': 1,
            'INTERVAL': 20,
            'FIELD_NAME': "Hoehe",
            'OUTPUT': outputPath
        }
        algOutput = run("gdal:contour", processingParams)
        contourLyr = QgsVectorLayer(algOutput['OUTPUT'], contourName, "ogr")
    
    # contourLyr the same CRS as qgis project
    contourLyr.setCrs(crs)
    addLayerToQgis(contourLyr, 'top')
    canvas.refresh()
    heightSource.contourLyr = contourLyr


def inSwitzerland():
    crs = QgsProject.instance().crs()
    if crs.authid() in SWISS_CRS:
        return True
    else:
        return False


def addBackgroundMap(canvas):
    if inSwitzerland():
        layer: QgsRasterLayer = addSwissBackgroundMap(QgsProject.instance().crs().authid())
    else:
        layer: QgsRasterLayer = addOsmBackgroundMap()
    
    if not layer:
        return tr("Layer bereits in Karte"), Qgis.Info
    
    if layer.isValid():
        addLayerToQgis(layer, 'bottom')
        canvas.refresh()
        return tr("Layer '{}' zur Karte hinzugefügt").format(
            layer.name()), Qgis.Success
    else:
        return tr("Fehler beim Hinzufügen des Layers '{}'").format(
            layer.name()), Qgis.Warning


def addOsmBackgroundMap():
    osmLyr = None
    layerName = tr('OSM_Karte')
    
    already_added = [lyr.name() for lyr in QgsProject.instance().mapLayers().values()]
    
    if layerName not in already_added:
        # Add OSM layer
        xmlPath = os.path.join(HOMEPATH, 'config', 'OSM_Karte.xml')
        baseName = QFileInfo(xmlPath).baseName()
        osmLyr = QgsRasterLayer(xmlPath, baseName)
    return osmLyr


def addSwissBackgroundMap(crs=SWISS_CRS[0]):
    layer = None
    layerName = tr('Landeskarten (farbig)')
    wmsUrl = (f'contextualWMSLegend=0&crs={crs}&dpiMode=7'
              f'&featureCount=10&format=image/jpeg'
              f'&layers={OVERVIEW_MAP}'
              f'&styles={OVERVIEW_MAP}'
              f'&tileDimensions=Time%3Dcurrent'
              f'&url={SWISSTOPO_WMS_URL}')
    
    already_added = [lyr.source() for lyr in QgsProject.instance().mapLayers().values()]
    
    if wmsUrl not in already_added:
        layer = QgsRasterLayer(wmsUrl, layerName, 'wms')
    return layer


def createProfileLayers(heightSource):
    lyrCrs = heightSource.spatialRef.authid()
    pointA = heightSource.getFirstPoint()
    pointE = heightSource.getLastPoint()
    
    # Create profile layer
    surveyLineLayer = QgsVectorLayer('Linestring?crs=' + lyrCrs,
                                     tr('Felddaten-Profil'), 'memory')
    pr = surveyLineLayer.dataProvider()
    feature = QgsFeature()
    feature.setGeometry(QgsGeometry.fromPolyline(
        [QgsPoint(*tuple(pointA)), QgsPoint(*tuple(pointE))]))
    pr.addFeatures([feature])
    surveyLineLayer.updateExtents()
    # Add at the top of the layer tree
    addLayerToQgis(surveyLineLayer, 'top')

    # Create survey point layer
    surveyPointLayer = QgsVectorLayer(f'Point?crs={lyrCrs}&field=id:integer&field=nr:string(30)',
                                      tr('Felddaten-Messpunkte'), 'memory')
    pr = surveyPointLayer.dataProvider()
    features = []
    # TODO: Survey points are NOT rounded
    for x, y, nr, notes in zip(heightSource.x, heightSource.y, heightSource.nr, heightSource.plotNotes):
        feature = QgsFeature()
        feature.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(x, y)))
        labelText = f"{nr}{':' if notes else ''} {notes if len(notes) <= 25 else notes[:22] + '...'}"
        feature.setAttributes([int(nr+1), labelText])
        features.append(feature)
    pr.addFeatures(features)
    surveyPointLayer.updateExtents()
    # Add at the top of the layer tree
    addLayerToQgis(surveyPointLayer, 'top')
    
    # Add Labels for point layer
    layer_settings = QgsPalLayerSettings()
    text_format = QgsTextFormat()
    text_format.setFont(QFont("Arial", 12))
    text_format.setSize(12)
    buffer_settings = QgsTextBufferSettings()
    buffer_settings.setEnabled(True)
    buffer_settings.setSize(1)
    buffer_settings.setColor(QColor("white"))
    text_format.setBuffer(buffer_settings)
    layer_settings.setFormat(text_format)
    layer_settings.fieldName = "nr"
    layer_settings.Placement = 2
    layer_settings.enabled = True
    layer_settings = QgsVectorLayerSimpleLabeling(layer_settings)
    surveyPointLayer.setLabelsEnabled(True)
    surveyPointLayer.setLabeling(layer_settings)
    surveyPointLayer.triggerRepaint()
    
    return surveyLineLayer, surveyPointLayer


def sanitizeFilename(name):
    """ Replace all prohibited chars with underline."""
    invalid_chars = ['/', '\\']
    return ''.join('_' if c in invalid_chars else c for c in name)


def addLayerToQgis(layer, position: str = '', layerGroupName: str = ''):
    layerTree = QgsProject.instance().layerTreeRoot()
    QgsProject.instance().addMapLayer(layer, False)
    
    if layerGroupName:
        layerGroup = layerTree.findGroup(layerGroupName)
        if not layerGroup:
            layerGroup = layerTree.insertGroup(0, layerGroupName)
        layerGroup.addLayer(layer)

    else:
        if position == 'top':
            layerTree.insertLayer(0, layer)
        elif position == 'bottom':
            layerTree.insertLayer(-1, layer)
        
