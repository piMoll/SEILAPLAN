# -*- coding: utf-8 -*-
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
from math import cos, sin, atan, pi
import os
import csv

from qgis.PyQt.QtCore import QVariant
from qgis.core import QgsWkbTypes, QgsFields, QgsField, QgsVectorFileWriter, \
    QgsFeature, QgsGeometry, QgsPoint, QgsCoordinateReferenceSystem


def generateGeodata(projInfo, HM, seilDaten, stueLabel, savePath):
    """Creates 3D shapefiles containing the pole positions, the empty cable
    line and the cable line under load."""
    projName = projInfo['Projektname']
    [Ax, Ay] = projInfo['Anfangspunkt']
    [Ex, Ey] = projInfo['Endpunkt']
    epsg = projInfo['Hoehenmodell']['spatialRef']
    spatialRef = QgsCoordinateReferenceSystem(epsg)

    # Cable line
    seilHoriDist = seilDaten['l_coord']
    seilLeerZ = seilDaten['z_Leer']
    seilLastZ = seilDaten['z_Zweifel']

    # Calculate x and y coordinate in reference system
    dx = float(Ex - Ax)
    dy = float(Ey - Ay)
    if dx == 0:
        dx = 0.0001
    azimut = atan(dy/dx)
    if dx > 0:
        azimut += 2 * pi
    else:
        azimut += pi
    seilX = Ax + seilHoriDist * cos(azimut)
    seilY = Ay + seilHoriDist * sin(azimut)

    stueGeo = np.swapaxes(np.array([HM['x'], HM['y'], HM['z']]), 1, 0)
    seilLeerGeo = np.swapaxes(np.array([seilX, seilY, seilLeerZ]), 1, 0)
    seilLastGeo = np.swapaxes(np.array([seilX, seilY, seilLastZ]), 1, 0)

    # Save pole positions
    stueName = '{}_Stuetzen'.format(projName.replace("'", "."))
    stuePath = os.path.join(savePath, stueName + '.shp')
    checkShpPath(stuePath)
    save2PointShape(stuePath, stueGeo, stueLabel, spatialRef)
    
    # Save empty cable line
    seilLeerName = '{}_Leerseil'.format(projName.replace("'", "."))
    seilLeerPath = os.path.join(savePath, seilLeerName + '.shp')
    checkShpPath(seilLeerPath)
    save2LineShape(seilLeerPath, seilLeerGeo, spatialRef)

    # Save cable line under load
    seilLastName = '{}_Lastseil'.format(projName)
    seilLastPath = os.path.join(savePath, seilLastName + '.shp')
    checkShpPath(seilLastPath)
    save2LineShape(seilLastPath, seilLastGeo, spatialRef)

    geoOutput = {'stuetzen': stuePath,
                 'leerseil': seilLeerPath,
                 'lastseil': seilLastPath}
    return geoOutput

def save2PointShape(shapePath, geodata, label, spatialRef):
    """
    :param label:
    :param shapePath: Location of shape file
    :param geodata: x, y and z coordinate of poles
    :param spatialRef: current spatial reference of qgis project
    """

    # Define fields for feature attributes. A QgsFields object is needed
    fields = QgsFields()
    fields.append(QgsField("StuetzenNr", QVariant.String, 'text', 254))
    fields.append(QgsField("x", QVariant.Double))
    fields.append(QgsField("y", QVariant.Double))
    fields.append(QgsField("h", QVariant.Double))
    writer = QgsVectorFileWriter(shapePath, "UTF-8", fields, QgsWkbTypes.PointZ,
                                 spatialRef, "ESRI Shapefile")

    if writer.hasError() != QgsVectorFileWriter.NoError:
        # TODO
        raise Exception("Vector Writer")
    
    features = []
    for idx, coords in enumerate(geodata):
        feature = QgsFeature()
        feature.setFields(fields)
        feature.setGeometry(QgsPoint(coords[0], coords[1], coords[2]))
        feature.setId(idx)
        feature.setAttribute("StuetzenNr", label[idx])
        feature.setAttribute("x", float(coords[0]))
        feature.setAttribute("y", float(coords[1]))
        feature.setAttribute("h", float(coords[2]))
        features.append(feature)

    writer.addFeatures(features)
    # Delete the writer to flush features to disk
    del writer

def save2LineShape(shapePath, geodata, spatialRef):
    """
    :param shapePath: Location of shape file
    :param geodata: x, y and z coordinate of line
    :param spatialRef: current spatial reference of qgis project
    """
    # Define fields for feature attributes. A QgsFields object is needed
    fields = QgsFields()
    writer = QgsVectorFileWriter(shapePath, "UTF-8", fields, QgsWkbTypes.LineStringZ,
                                 spatialRef, "ESRI Shapefile")

    if writer.hasError() != QgsVectorFileWriter.NoError:
        # TODO
        raise Exception("Vector Writer")

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
    
    stue = QgsVectorLayer(geodata['stuetzen'], "Stützen", "ogr")
    leerseil = QgsVectorLayer(geodata['leerseil'], "Leerseil", "ogr")
    lastseil = QgsVectorLayer(geodata['lastseil'], "Lastseil", "ogr")
    
    for layer in [stue, leerseil, lastseil]:
        layer.setProviderEncoding('UTF-8')
        layer.dataProvider().setEncoding('UTF-8')

        # Map Layer erstellen
        QgsProject.instance().addMapLayer(layer, False)
        
        # Add to group
        projGroup.addLayer(layer)

def generateCoordTable(seil, zi, HM, savePath, labelTxt):
    """Creates csv files with the corse of the cable line."""
    savePathStue = savePath[0]
    savePathSeil = savePath[1]

    horiDist = seil['Laengsprofil_di']
    x = seil['x']
    y = seil['y']*-1
    z_last = seil['z_Zweifel'][::10]
    z_leer = seil['z_Leer'][::10]
    gelaende = zi / 10
    
    # Combine cable data into matrix
    seilDataMatrix = np.array([horiDist, x, y, z_last, z_leer, gelaende])
    seilDataMatrix = seilDataMatrix.transpose()

    # Txt header
    header = ["Horizontaldistanz", "X", "Y", "Z Lastseil", "Z Leerseil",
              "Z Gelaende"]
    
    # Write out data to file
    with open(savePathSeil, 'w') as f:
        fi = csv.writer(f, delimiter=';', dialect='excel', lineterminator='\n')
        fi.writerow(header)
        for row in seilDataMatrix:
            fi.writerow(np.round(row, 1))

    # Pole data
    with open(savePathStue, 'w') as f:
        fi = csv.writer(f, delimiter=';', dialect='excel', lineterminator='\n')
        fi.writerow(["Stuetze", "X", "Y", "Z Boden", "Z Stuetze", "Stuetzenhoehe"])
        for i in range(len(HM['h'])):
            name = [unicode2acii(labelTxt[i])]
            coords = ([round(e, 1) for e in [HM['x'][i], HM['y'][i],
                                             HM['z'][i] - HM['h'][i], HM['z'][i],
                                             HM['h'][i]]])
            row = name + coords
            fi.writerow(row)

def unicode2acii(text):
    # Tabelle mit HEX Codes der Umlaute
    translation = {0xe4: 'ae',
                   0xf6: 'oe',
                   0xfc: 'ue'}
    return text.translate(translation).encode('ascii', 'ignore')

