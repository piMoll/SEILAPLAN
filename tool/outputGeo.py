#!/usr/bin/env python
#  -*- coding: utf-8 -*-
"""
#------------------------------------------------------------------------------
# Name:        Seiloptimierungstool
# Purpose:
#
# Author:      Patricia Moll
#
# Created:     14.05.2013
# Copyright:   (c) mollpa 2012
# Licence:     <your licence>
#------------------------------------------------------------------------------
"""
import numpy as np
from math import cos, sin, atan, pi
import os
import csv
import osgeo.ogr as ogr
import osgeo.osr as osr



def generateGeodata(projInfo, HM, seilDaten, stueLabel, savePath):
    projName = projInfo['Projektname']
    [Ax, Ay] = projInfo['Anfangspunkt']
    [Ex, Ey] = projInfo['Endpunkt']
    epsg = projInfo['Hoehenmodell']['spatialRef'][5:]
    # spatialRef = projInfo['spatialRef']
    spatialRef = osr.SpatialReference()
    spatialRef.ImportFromEPSG(int(epsg))
    # spatialReference.ImportFromProj4("""
    #     +proj=somerc +lat_0=46.95240555555556 +lon_0=7.439583333333333 +k_0=1
    #     +x_0=600000 +y_0=200000 +ellps=bessel +towgs84=674.4,15.1,405.3,0,0,0,0
    #     +units=m +no_defs""")
    # Seilverlauf
    seilHoriDist = seilDaten['l_coord']
    seilLeerZ = seilDaten['z_Leer']
    seilLastZ = seilDaten['z_Zweifel']

    # X- und Y-Koordinate der Geodaten im Projektionssystem berechnen
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

    # Stützenpunkte abspeichern
    stueName = u'{}_Stuetzen'.format(projName.replace("'", "."))
    stuePath = os.path.join(savePath, stueName + '.shp')
    checkShpPath(stuePath)
    save2PointShape(stuePath, 'Stuetzen', stueGeo, 'StuetzenH',
                    HM['h'], stueLabel, spatialRef)
    # Leerseil abspeichern
    seilLeerName = '{}_Leerseil'.format(projName.replace("'", "."))
    seilLeerPath = os.path.join(savePath, seilLeerName + '.shp')
    checkShpPath(seilLeerPath)
    save2LineShape(seilLeerPath, seilLeerName, seilLeerGeo, spatialRef)

    # Lastseil abspeichern
    seilLastName = '{}_Lastseil'.format(projName)
    seilLastPath = os.path.join(savePath, seilLastName + '.shp')
    checkShpPath(seilLastPath)
    save2LineShape(seilLastPath,seilLastName, seilLastGeo, spatialRef)

    geoOutput = {'stuetzen': stuePath,
                 'leerseil': seilLeerPath,
                 'lastseil': seilLastPath}
    return geoOutput


def save2PointShape(shapePath, layerName, geodata, attribName,
                    attribData, label, spatialRef):
    """
    :param shapePath: Pfad wo Shapefile agespeichert wird
    :param layerName: Name des Layers
    :param geodata: Koordinaten der Punkte
    :param attribName: Attributname (Feldname) von zusätzlichen Werten
    :param attribData: Werte für Attribute
    :param spatialRef: Räumliche Referenz
    """
    # ALS ERKLÄRUNG: osgeo Vektor Hirarchie
    #   Driver-->Datasource-->Layer-->Feature-->Geometry-->Point
    driver = ogr.GetDriverByName('ESRI Shapefile')
    shapeDriver = driver.CreateDataSource(shapePath)
    layer = shapeDriver.CreateLayer(layerName, spatialRef, ogr.wkbPoint)
    # Erzeuge Attributfelder
    layer.CreateField(ogr.FieldDefn('StuetzenNr', ogr.OFTString))
    layer.CreateField(ogr.FieldDefn(attribName, ogr.OFTInteger))
    for idx, (coords, attrib) in enumerate(zip(geodata, attribData)):
        # Erzeuge Punkt
        geometry = ogr.Geometry(ogr.wkbPoint)
        # TODO alles sollte 3D sein!!!
        geometry.SetPoint(0, coords[0], coords[1], coords[2])
        # Erzeuge Feature
        feature = ogr.Feature(layer.GetLayerDefn())
        feature.SetGeometry(geometry)
        feature.SetFID(idx)
        feature.SetField('StuetzenNr', unicode2acii(label[idx]))
        feature.SetField(attribName, attrib)
        # Speichere Feature
        layer.CreateFeature(feature)
        # Cleanup
        geometry.Destroy()
        feature.Destroy()
    # Cleanup
    shapeDriver.Destroy()

def save2LineShape(shapePath, layerName, geodata, spatialRef):
    driver = ogr.GetDriverByName('ESRI Shapefile')
    shapeDriver = driver.CreateDataSource(shapePath)
    layer = shapeDriver.CreateLayer(layerName, spatialRef, ogr.wkbLineString)
    layerDefinition = layer.GetLayerDefn()
    # Erzeuge Linie
    geometry = ogr.Geometry(ogr.wkbLineString)
    for idx, coords in enumerate(geodata):
        # Füge Punkt Eckpunkt hinzu
        geometry.AddPoint(coords[0], coords[1], coords[2])
    # Erzeuge Feature
    feature = ogr.Feature(layerDefinition)
    feature.SetGeometry(geometry)
    feature.SetFID(1)
    # Speichere Feature
    layer.CreateFeature(feature)
    # Cleanup
    geometry.Destroy()
    feature.Destroy()
    # Cleanup
    shapeDriver.Destroy()

def checkShpPath(path):
    fileEndings = ['.shp', '.dbf', '.prj', '.shx']
    path = path.replace('.shp', '')
    for ending in fileEndings:
        if os.path.exists(path+ending):
            os.remove(path+ending)

def addToMap(iface, geodata, projName):
    from qgis.core import QgsVectorLayer, QgsProject
    stue = QgsVectorLayer(geodata['stuetzen'], u"Stützen", "ogr")
    leerseil = QgsVectorLayer(geodata['leerseil'], u"Leerseil", "ogr")
    lastseil = QgsVectorLayer(geodata['lastseil'], u"Lastseil", "ogr")

    # Map Layer erstellen
    QgsProject.instance().addMapLayer(stue, False)
    QgsProject.instance().addMapLayer(leerseil, False)
    QgsProject.instance().addMapLayer(lastseil, False)

    # Neue Layer-Gruppe im TOC erstellen und Layer hinzufügen
    root = QgsProject.instance().layerTreeRoot()
    projGroup = root.insertGroup(0, projName)
    projGroup.addLayer(stue)
    projGroup.addLayer(leerseil)
    projGroup.addLayer(lastseil)

    # Symbolisierung anpassen
    # Use the currently selected layer

    # from qgis.core import QgsSymbolLayerV2Registry
    # registry = QgsSymbolLayerV2Registry.instance()
    # pointMeta = registry.symbolLayerMetadata("SimpleMarker")
    # lineMeta = registry.symbolLayerMetadata("SimpleLine")
    #
    # # pntSymbol = QgsSymbolV2.defaultSymbol(stue.geometryType())
    #
    # # Line layer
    # lineLayer = lineMeta.createSymbolLayer({'width': '0.26',
    #                                         'color': '255,0,0',
    #                                         'offset': '-1.0',
    #                                         'penstyle': 'solid',
    #                                         'use_custom_dash': '0',
    #                                         'joinstyle': 'bevel',
    #                                         'capstyle': 'square'})
    #
    #
    # # Replace the default layer with our own SimpleMarker
    # # subSymbol.deleteSymbolLayer(0)
    #
    #
    # # Replace the default layer with our two custom layers
    # symbol.deleteSymbolLayer(0)
    # symbol.appendSymbolLayer(lineLayer)
    # symbol.appendSymbolLayer(markerLayer)
    #
    # # Replace the renderer of the current layer
    # # renderer = QgsSingleSymbolRendererV2(symbol)
    # lastseil.setRendererV2(QgsSingleSymbolRendererV2(pntSymbol))

def generateCoordTable(seil, zi, HM, savePath, labelTxt):
    savePathStue = savePath[0]
    savePathSeil = savePath[1]

    # Seildaten (in Meter-Auflösung)
    # -----------------------------
    count = seil["l_coord"].shape[0]        # Grösse des Datensatzes
    # Verwendete Datenreihen
    horiDist = seil['Laengsprofil_di']
    x = seil['x']
    y = seil['y']*-1
    z_last = seil['z_Zweifel'][::10]
    z_leer = seil['z_Leer'][::10]
    gelaende = zi / 10
    # Seildaten zu Matrix zusammenfassen
    seilDataMatrix = np.array([horiDist, x, y, z_last, z_leer, gelaende])
    seilDataMatrix = seilDataMatrix.transpose()

    # Header für txt File schreiben
    header = ["Horizontaldistanz", "X", "Y", "Z Lastseil", "Z Leerseil",
              "Z Gelaende"]
    # Schreibe Seildaten in txt File
    with open(savePathSeil, 'w') as f:
        fi = csv.writer(f, delimiter=';', dialect='excel', lineterminator='\n')
        fi.writerow(header)
        for row in seilDataMatrix:
            fi.writerow(np.round(row, 1))

    # Stützendaten
    # ------------
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
    translation = {0xe4: u'ae',
                   0xf6: u'oe',
                   0xfc: u'ue'}
    return text.translate(translation).encode('ascii', 'ignore')

