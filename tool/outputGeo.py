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
import numpy as np
import os
import csv

from qgis.PyQt.QtCore import QVariant, QCoreApplication
from qgis.core import QgsWkbTypes, QgsFields, QgsField, QgsVectorFileWriter, \
    QgsFeature, QgsGeometry, QgsPoint, QgsCoordinateReferenceSystem


def organizeDataForExport(poles, cableline):
    """Creates 3D shapefiles containing the pole positions, the empty cable
    line and the cable line under load.
    """
    # Calculate x and y coordinate in reference system
    emptyLine = np.swapaxes(np.array([cableline['coordx'],
                                      cableline['coordy'],
                                      cableline['empty']]), 1, 0)
    loadLine = np.swapaxes(np.array([cableline['coordx'],
                                        cableline['coordy'],
                                        cableline['load']]), 1, 0)
    
    # Pole coordinates
    poleGeo = []
    poleName = []
    for pole in poles:
        if pole['active']:
            poleGeo.append([pole['coordx'], pole['coordy'], pole['z'], pole['h']])
            poleName.append(pole['name'])
    
    return {
        'poleGeo': poleGeo,
        'poleName': poleName,
        'emptyLine': emptyLine,
        'loadLine': loadLine
    }


def exportToShape(geodata, epsg, savePath):
    spatialRef = QgsCoordinateReferenceSystem(epsg)
    geoFormat = 'ESRI Shapefile'

    # Save pole positions
    stuePath = os.path.join(savePath, tr('stuetzen') + '.shp')
    checkShpPath(stuePath)
    savePointGeometry(stuePath, geodata['poleGeo'], geodata['poleName'],
                      spatialRef, geoFormat)
    
    # Save empty cable line
    seilLeerPath = os.path.join(savePath, tr('leerseil') + '.shp')
    checkShpPath(seilLeerPath)
    saveLineGeometry(seilLeerPath, geodata['emptyLine'], spatialRef, geoFormat)

    # Save cable line under load
    seilLastPath = os.path.join(savePath, tr('lastseil') + '.shp')
    checkShpPath(seilLastPath)
    saveLineGeometry(seilLastPath, geodata['loadLine'], spatialRef, geoFormat)

    geoOutput = {'stuetzen': stuePath,
                 'leerseil': seilLeerPath,
                 'lastseil': seilLastPath}
    return geoOutput


def exportToKML(geodata, epsg, savePath):
    spatialRef = QgsCoordinateReferenceSystem(epsg)
    geoFormat = 'KML'
    
    # Save pole positions
    stuePath = os.path.join(savePath, 'kml_' + tr('stuetzen') + '.kml')
    savePointGeometry(stuePath, geodata['poleGeo'], geodata['poleName'],
                      spatialRef, geoFormat)
    
    # Save empty cable line
    seilLeerPath = os.path.join(savePath, 'kml_' + tr('leerseil') + '.kml')
    saveLineGeometry(seilLeerPath, geodata['emptyLine'], spatialRef, geoFormat)
    
    # Save cable line under load
    seilLastPath = os.path.join(savePath, 'kml_' + tr('lastseil') + '.kml')
    saveLineGeometry(seilLastPath, geodata['loadLine'], spatialRef, geoFormat)


def savePointGeometry(path, geodata, label, spatialRef, geoFormat):
    """
    :param label: Name of poles
    :param path: Location of shape file
    :param geodata: x, y and z coordinate of poles
    :param spatialRef: current spatial reference of qgis project
    :param geoFormat: Geodata export format
    """

    # Define fields for feature attributes. A QgsFields object is needed
    stueNrName = tr('bezeichnung')
    fields = QgsFields()
    fields.append(QgsField(stueNrName, QVariant.String, 'text', 254))
    fields.append(QgsField('x', QVariant.Double))
    fields.append(QgsField('y', QVariant.Double))
    fields.append(QgsField('z', QVariant.Double))
    fields.append(QgsField('h', QVariant.Double))
    writer = QgsVectorFileWriter(path, 'UTF-8', fields, QgsWkbTypes.PointZ,
                                 spatialRef, geoFormat)

    if writer.hasError() != QgsVectorFileWriter.NoError:
        # TODO
        raise Exception('Vector Writer')
    
    features = []
    for idx, coords in enumerate(geodata):
        feature = QgsFeature()
        feature.setFields(fields)
        feature.setGeometry(QgsPoint(coords[0], coords[1], coords[2]))
        feature.setId(idx)
        feature.setAttribute(stueNrName, label[idx])
        feature.setAttribute('x', float(coords[0]))
        feature.setAttribute('y', float(coords[1]))
        feature.setAttribute('z', float(coords[2]))
        feature.setAttribute('h', float(coords[3]))
        features.append(feature)

    writer.addFeatures(features)
    # Delete the writer to flush features to disk
    del writer


def saveLineGeometry(shapePath, geodata, spatialRef, geoFormat):
    """
    :param shapePath: Location of shape file
    :param geodata: x, y and z coordinate of line
    :param spatialRef: current spatial reference of qgis project
    :param geoFormat: Geodata export format
    """
    # Define fields for feature attributes. A QgsFields object is needed
    fields = QgsFields()
    writer = QgsVectorFileWriter(shapePath, 'UTF-8', fields, QgsWkbTypes.LineStringZ,
                                 spatialRef, geoFormat)

    if writer.hasError() != QgsVectorFileWriter.NoError:
        # TODO
        raise Exception('Vector Writer')

    lineVertices = []
    for coords in geodata:
        lineVertices.append(QgsPoint(coords[0], coords[1], coords[2]))
        
    feature = QgsFeature()
    feature.setGeometry(QgsGeometry.fromPolyline(lineVertices))
    feature.setId(1)
    writer.addFeatures([feature])
    del feature
    # Delete the writer to flush features to disk
    del writer


def checkShpPath(path):
    """Deletes remains of earlier shapefiles. Otherwise these files can
    interact with new shapefiles (e.g. old indexes)."""
    fileEndings = ['.shp', '.dbf', '.prj', '.shx']
    path = path.replace('.shp', '')
    for ending in fileEndings:
        if os.path.exists(path+ending):
            os.remove(path+ending)


def addToMap(geodata, projName):
    """ Adds the shape file to the qgis project."""
    from qgis.core import QgsVectorLayer, QgsProject

    # Create new layer group in table of content
    root = QgsProject.instance().layerTreeRoot()
    projGroup = root.insertGroup(0, projName)
    
    polesLyr = QgsVectorLayer(geodata['stuetzen'], tr('stuetzen'), 'ogr')
    emptyLineLyr = QgsVectorLayer(geodata['leerseil'], tr('leerseil'), 'ogr')
    loadLineLyar = QgsVectorLayer(geodata['lastseil'], tr('lastseil'), 'ogr')
    
    for layer in [polesLyr, emptyLineLyr, loadLineLyar]:
        layer.setProviderEncoding('UTF-8')
        layer.dataProvider().setEncoding('UTF-8')

        # Add layer to map
        QgsProject.instance().addMapLayer(layer, False)
        
        # Add to group
        projGroup.addLayer(layer)


def generateCoordTable(cableline, profile, poles, outputLoc):
    """Creates csv files with the corse of the cable line."""
    savePathStue = os.path.join(outputLoc, tr('Koordinaten Stuetzen.csv'))
    savePathSeil = os.path.join(outputLoc, tr('Koordinaten Seil.csv'))

    # Combine cable data into matrix
    seilDataMatrix = np.array(
        [cableline['xaxis'][::10], cableline['coordx'][::10],
         cableline['coordy'][::10], cableline['load'][::10],
         cableline['empty'][::10], profile.zi,
         cableline['load'][::10] - profile.zi])
    seilDataMatrix = seilDataMatrix.transpose()

    # Txt header
    header = [tr('Horizontaldistanz'), 'X', 'Y', tr('Z Lastseil'),
              tr('Z Leerseil'), tr('Z Gelaende'), tr('Abstand Lastseil-Boden')]
    
    # Write to file
    with open(savePathSeil, 'w') as f:
        fi = csv.writer(f, delimiter=';', dialect='excel', lineterminator='\n')
        fi.writerow(header)
        for row in seilDataMatrix:
            fi.writerow(np.round(row, 1))

    # Pole data
    with open(savePathStue, 'w') as f:
        fi = csv.writer(f, delimiter=';', dialect='excel', lineterminator='\n')
        fi.writerow([tr('Stuetze'), 'X', 'Y', tr('Z Stuetze Boden'),
                     tr('Z Stuetze Spitze'), tr('Stuetzenhoehe'), tr('Neigung')])
        for pole in poles:
            name = [unicode2acii(pole['name'])]
            coords = ([round(e, 3) for e in [pole['coordx'], pole['coordy'],
                                             pole['z'], pole['ztop'],
                                             pole['h'], pole['angle']]])
            row = name + coords
            fi.writerow(row)


def unicode2acii(text):
    """Csv write can not handle utf-8, so most common utf-8 strings are
    converted. This should be fixed in the future."""
    translation = {0xe4: 'ae',
                   0xf6: 'oe',
                   0xfc: 'ue'}
    return text.translate(translation)


# noinspection PyMethodMayBeStatic
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
    # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
    return QCoreApplication.translate('@default', message)
