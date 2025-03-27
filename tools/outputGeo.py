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

from qgis.PyQt.QtCore import QCoreApplication
from qgis.core import (QgsRasterLayer, QgsProcessing, QgsProcessingException,
                       QgsWkbTypes, QgsFields, QgsField, QgsVectorFileWriter,
                       QgsFeature, QgsGeometry, QgsCoordinateTransform, QgsPoint,
                       QgsCoordinateReferenceSystem, QgsProject,
                       QgsCoordinateTransformContext)
from SEILAPLAN import DEBUG
from SEILAPLAN.gui.guiHelperFunctions import addLayerToQgis

try:
    from processing import run
except ModuleNotFoundError as e:
    if DEBUG:
        pass
    else:
        raise e

# Checking for deprecations needs a deprecation check...
try:
    from qgis.core.Qgis import QGIS_VERSION_INT
except (ImportError, ModuleNotFoundError):
    from qgis.core import Qgis
    QGIS_VERSION_INT = Qgis.QGIS_VERSION_INT


GPS_CRS = 'EPSG:4326'
CH_CRS = 'EPSG:2056'
VIRTUALRASTER = 'SEILAPLAN Virtuelles Raster'


# Defining attribute types: QVariant has been deprecated as of QGIS 3.38
if QGIS_VERSION_INT >= 33800:
    from qgis.PyQt.QtCore import QMetaType
    type_string = QMetaType.Type.QString
    type_double = QMetaType.Type.Double
else:
    from qgis.PyQt.QtCore import QVariant
    type_string = QVariant.String
    type_double = QVariant.Double


def organizeDataForExport(poles, cableline, profile):
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
    terrainLine = np.swapaxes(np.array([profile.xi_disp,
                                        profile.yi_disp,
                                        profile.zi_disp]), 1, 0)
    profile_emptyLine = np.swapaxes(np.array([cableline['xaxis'],
                                               cableline['empty']]), 1, 0)
    profile_loadLine = np.swapaxes(np.array([cableline['xaxis'],
                                               cableline['load']]), 1, 0)
    profile_terrain = np.swapaxes(np.array([profile.di_disp,
                                            profile.zi_disp]), 1, 0)
    profile_data = [profile_emptyLine, profile_loadLine, profile_terrain]
        
    # Pole coordinates
    for pole in poles:
        poleLine = [pole['d'], pole['z']], [pole['dtop'], pole['ztop']]
        profile_data.append(np.array(poleLine))
    
    return {
        'poles': poles,
        'emptyLine': emptyLine,
        'loadLine': loadLine,
        'terrain': terrainLine,
        'profile': profile_data
    }


def writeGeodata(geodata, geoFormat, epsg, savePath):
    # Create sub folder for every format
    savePath = os.path.join(savePath, geoFormat.lower())
    os.makedirs(savePath)
    
    spatialRef = QgsCoordinateReferenceSystem(epsg)
    
    if geoFormat == 'SHP':
        geoFormat = 'ESRI Shapefile'
        stuePath = os.path.join(savePath, tr('stuetzen') + '.shp')
        seilLeerPath = os.path.join(savePath, tr('leerseil') + '.shp')
        seilLastPath = os.path.join(savePath, tr('lastseil') + '.shp')
        terrainPath = os.path.join(savePath, tr('terrain') + '.shp')
        checkShpPath(stuePath)
        checkShpPath(seilLeerPath)
        checkShpPath(seilLastPath)
        checkShpPath(terrainPath)
    
    elif geoFormat == 'KML':
        stuePath = os.path.join(savePath, tr('stuetzen') + '.kml')
        seilLeerPath = os.path.join(savePath, tr('leerseil') + '.kml')
        seilLastPath = os.path.join(savePath, tr('lastseil') + '.kml')
        terrainPath = os.path.join(savePath, tr('terrain') + '.kml')
    
    elif geoFormat == 'DXF':
        stuePath = os.path.join(savePath, tr('stuetzen') + '.dxf')
        seilLeerPath = os.path.join(savePath, tr('leerseil') + '.dxf')
        seilLastPath = os.path.join(savePath, tr('lastseil') + '.dxf')
        terrainPath = os.path.join(savePath, tr('terrain') + '.dxf')
        # For DXF, we create an additional file containing the side view
        #  (dist and height) of the data
        profilePath = os.path.join(savePath, tr('profilansicht') + '.dxf')
    
    else:
        raise Exception(f'Writing to {geoFormat} not implemented')
    
    # Check if qgis supports the requested geodata file type
    isGeoFormatAvailable = False
    for availableFormat in QgsVectorFileWriter.supportedFiltersAndFormats():
        if availableFormat.driverName == geoFormat:
            isGeoFormatAvailable = True
            break
    if not isGeoFormatAvailable:
        errorMsg = tr('Die Ausgabe in _geoFormat_ wird von dieser QGIS-Installation nicht unterstuetzt')
        raise Exception(errorMsg.replace('_geoFormat_', geoFormat))

    # Save pole positions
    savePointGeometry(stuePath, geodata['poles'], spatialRef, geoFormat)
    # Save empty cable line
    saveLineGeometry(seilLeerPath, [geodata['emptyLine']], spatialRef, geoFormat)
    # Save cable line under load
    saveLineGeometry(seilLastPath, [geodata['loadLine']], spatialRef, geoFormat)
    # Save terrain line
    saveLineGeometry(terrainPath, [geodata['terrain']], spatialRef, geoFormat)
    # Side view
    if geoFormat == 'DXF':
        saveLineGeometry(profilePath, geodata['profile'], spatialRef, geoFormat, False)
    
    geoOutput = {'stuetzen': stuePath,
                 'leerseil': seilLeerPath,
                 'lastseil': seilLastPath,
                 'terrain': terrainPath}
    return geoOutput


def savePointGeometry(filePath, poles, spatialRef, geoFormat):
    """
    :param filePath: Location of shape file
    :param poles: array of poles dictionaries
    :param spatialRef: current spatial reference of qgis project
    :param geoFormat: Geodata export format
    """
    fields = QgsFields()
    headerName = tr('bezeichnung')
    headerCategory = tr('shp_kategorie')
    headerPosition = tr('shp_position')
    headerAbspann = tr('shp_abspann')
    
    if geoFormat != 'DXF':
        # Define fields for feature attributes, DXF-format does not support
        #  fields
        fields.append(QgsField(headerName, type_string, typeName='text', len=254))
        fields.append(QgsField('x', type_double))
        fields.append(QgsField('y', type_double))
        fields.append(QgsField('z', type_double))
        fields.append(QgsField('h', type_double))
        fields.append(QgsField(headerCategory, type_string, typeName='text', len=254))
        fields.append(QgsField(headerPosition, type_string, typeName='text', len=254))
        fields.append(QgsField(headerAbspann, type_string, typeName='text', len=254))

    if QGIS_VERSION_INT >= 31030:
        # Use newer QgsVectorFileWriter.create() function
        options = QgsVectorFileWriter.SaveVectorOptions()
        options.driverName = geoFormat
        options.includeZ = True
        options.fileEncoding = 'UTF-8'
        writer = QgsVectorFileWriter.create(
            filePath, fields, QgsWkbTypes.Type.PointZ, spatialRef,
            QgsCoordinateTransformContext(), options)
    else:
        writer = QgsVectorFileWriter(filePath, 'UTF-8', fields,
            QgsWkbTypes.Type.PointZ, spatialRef, geoFormat)

    if writer.hasError() != QgsVectorFileWriter.NoError:
        raise Exception(f'{writer.errorMessage()} ({geoFormat})')
    
    features = []
    for idx, pole in enumerate(poles):
        feature = QgsFeature()
        feature.setFields(fields)
        feature.setGeometry(QgsPoint(pole['coordx'], pole['coordy'], pole['z']))
        feature.setId(idx)
        if geoFormat != 'DXF':
            # DXF-Format does not support fields / attributes
            feature.setAttribute(headerName, pole['name'])
            feature.setAttribute('x', float(pole['coordx']))
            feature.setAttribute('y', float(pole['coordy']))
            feature.setAttribute('z', float(pole['z']))
            feature.setAttribute('h', float(pole['h']))
            feature.setAttribute(headerCategory, tr(pole['category'], 'BirdViewRow'))
            feature.setAttribute(headerPosition, tr(pole['position'], 'BirdViewRow'))
            feature.setAttribute(headerAbspann, unicode2acii(tr(pole['abspann'], 'BirdViewRow')))
        features.append(feature)

    writer.addFeatures(features)
    # Delete the writer to flush features to disk
    del writer


def saveLineGeometry(filePath, geodata, spatialRef, geoFormat, is3D=True):
    """
    :param filePath: Location of shape file
    :param geodata: x, y and z coordinate of line
    :param spatialRef: current spatial reference of qgis project
    :param geoFormat: Geodata export format
    :param is3D: Geodata in 3D, else 2D
    """
    # Define fields for feature attributes. A QgsFields object is needed
    fields = QgsFields()
    geomType = QgsWkbTypes.Type.LineStringZ
    if not is3D:
        geomType = QgsWkbTypes.Type.LineString
    if QGIS_VERSION_INT >= 31030:
        # Use newer QgsVectorFileWriter.create() function
        options = QgsVectorFileWriter.SaveVectorOptions()
        options.driverName = geoFormat
        options.includeZ = True
        options.fileEncoding = 'UTF-8'
        writer = QgsVectorFileWriter.create(
            filePath, fields, geomType, spatialRef,
            QgsCoordinateTransformContext(), options)
    else:
        writer = QgsVectorFileWriter(filePath, 'UTF-8', fields,
                                     geomType, spatialRef, geoFormat)

    if writer.hasError() != QgsVectorFileWriter.NoError:
        raise Exception(f'{writer.errorMessage()} ({geoFormat})')

    features = []
    for idx, line in enumerate(geodata):
        lineVertices = []
        for coords in line:
            if len(coords) == 3:
                lineVertices.append(QgsPoint(coords[0], coords[1], coords[2]))
            elif len(coords) == 2:
                lineVertices.append(QgsPoint(coords[0], coords[1]))
        
        feature = QgsFeature()
        feature.setGeometry(QgsGeometry.fromPolyline(lineVertices))
        feature.setId(idx + 1)
        features.append(feature)
    writer.addFeatures(features)
    for featureToDel in features:
        del featureToDel
    # Delete the writer to flush features to disk
    del writer


def checkShpPath(path):
    """Deletes remains of earlier shapefiles. Otherwise, these files can
    interact with new shapefiles (e.g. old indexes)."""
    fileEndings = ['.shp', '.dbf', '.prj', '.shx']
    path = path.replace('.shp', '')
    for ending in fileEndings:
        if os.path.exists(path+ending):
            os.remove(path+ending)


def addToMap(geodata, projName):
    """ Adds the shape file to the qgis project."""
    from qgis.core import QgsVectorLayer
    
    polesLyr = QgsVectorLayer(geodata['stuetzen'], tr('stuetzen'), 'ogr')
    emptyLineLyr = QgsVectorLayer(geodata['leerseil'], tr('leerseil'), 'ogr')
    loadLineLyr = QgsVectorLayer(geodata['lastseil'], tr('lastseil'), 'ogr')
    terrainLyr = QgsVectorLayer(geodata['terrain'], tr('terrain'), 'ogr')
    
    for layer in [polesLyr, emptyLineLyr, loadLineLyr, terrainLyr]:
        layer.setProviderEncoding('UTF-8')
        layer.dataProvider().setEncoding('UTF-8')

        # Add layer to map
        addLayerToQgis(layer, '', projName)


def createVirtualRaster(rasterList):
    """If more than one raster is selected, they are combined to a virtual raster."""
    try:
        output = QgsProcessing.TEMPORARY_OUTPUT
    except AttributeError:
        # For QGIS < 3.6
        output = 'memory:virtRaster'
    
    # Create a new virtual raster
    processingParams = {
        'ADD_ALPHA': False,
        'ASSIGN_CRS': None,
        'EXTRA': '',
        'INPUT': rasterList,
        'OUTPUT': output,
        'PROJ_DIFFERENCE': False,
        'RESAMPLING': 0,
        'RESOLUTION': 0,
        'SEPARATE': False,
        'SRC_NODATA': ''
    }
    try:
        algOutput = run("gdal:buildvirtualraster", processingParams)
    except (RuntimeError, QgsProcessingException) as e:
        raise RuntimeError
    else:
        rasterLyr = QgsRasterLayer(algOutput['OUTPUT'], VIRTUALRASTER)
        if rasterLyr.isValid():
            return rasterLyr
        else:
            return None


def generateCoordTable(cableline, profile, poles, outputLoc):
    """Creates csv files with the corse of the cable line."""
    savePath = os.path.join(outputLoc, 'csv')
    os.makedirs(savePath)
    
    savePathStue = os.path.join(savePath, tr('Koordinaten Stuetzen.csv'))
    savePathSeil = os.path.join(savePath, tr('Koordinaten Seil.csv'))

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
        fi.writerow([unicode2acii(col) for col in header])
        for row in seilDataMatrix:
            fi.writerow(np.round(row, 1))

    # Pole data
    header = [tr('Stuetze'), tr('Horizontaldistanz'), 'X', 'Y',
              tr('Z Stuetze Boden'), tr('Z Stuetze Spitze'),
              tr('Stuetzenhoehe'), tr('Neigung'), tr('Kategorie'),
              tr('Position Stuetze'), tr('Ausrichtung Abspannseile')]
    
    with open(savePathStue, 'w') as f:
        fi = csv.writer(f, delimiter=';', dialect='excel', lineterminator='\n')
        fi.writerow([unicode2acii(col) for col in header])
        for pole in poles:
            name = [unicode2acii(pole['name'])]
            coords = ([round(e, 3) for e in [
                pole['d'], pole['coordx'], pole['coordy'], pole['z'],
                pole['ztop'], pole['h'], pole['angle']]])
            birdViewProps = [unicode2acii(tr(prop, 'BirdViewRow')) for prop in [
                pole['category'], pole['position'], pole['abspann']]]
            row = name + coords + birdViewProps
            fi.writerow(row)


def unicode2acii(text):
    """Csv write can not handle utf-8, so most common utf-8 strings are
    converted. This should be fixed in the future."""
    translation = {0xe4: 'ae',
                   0xc4: 'Ae',
                   0xf6: 'oe',
                   0xd6: 'Oe',
                   0xfc: 'ue',
                   0xdc: 'Ue',
                   0xe9: 'e',  # é
                   0xc9: 'E',  # é
                   0xe8: 'e',  # è
                   0xc8: 'E',  # è
                   0xea: 'e',  # ê
                   0xca: 'E',  # ê
                   0xe2: 'a',  # â
                   0xc2: 'A',  # â
                   0xf8: 'O',  # ø
                   0xd8: 'O',  # Ø
                   0x2300: 'O',     # Diameter
                   0x2192: '',   # Unicode Arrow
                   }
    return text.translate(translation)


def latLonToUtmCode(latitude, longitude):
    """Returns corresponding UTM or UPS EPSG code from WGS84 coordinates
    @param latitude - latitude value
    @param longitude - longitude value
    @returns - EPSG code string
    
    Source: https://github.com/All4Gis/QGISFMV/blob/master/code/geo/QgsMgrs.py
    """

    if abs(latitude) > 90:
        raise Exception("Latitude outside of valid range (-90 to 90 degrees).")

    if longitude < -180 or longitude > 360:
        raise Exception("Longitude outside of valid range (-180 to 360 degrees).")

    # UTM zone
    if latitude <= -80 or latitude >= 84:
        # Coordinates falls under UPS system
        zone = 61
    else:
        # Coordinates falls under UTM system
        if longitude < 180:
            zone = int(31 + (longitude / 6.0))
        else:
            zone = int((longitude / 6) - 29)

        if zone > 60:
            zone = 1

        # Handle UTM special cases
        if 56.0 <= latitude < 64.0 and 3.0 <= longitude < 12.0:
            zone = 32

        if 72.0 <= latitude < 84.0:
            if 0.0 <= longitude < 9.0:
                zone = 31
            elif 9.0 <= longitude < 21.0:
                zone = 33
            elif 21.0 <= longitude < 33.0:
                zone = 35
            elif 33.0 <= longitude < 42.0:
                zone = 37

    # North or South hemisphere
    if latitude >= 0:
        ns = 600
    else:
        ns = 700

    return f'EPSG:{32000 + ns + zone}'


def reprojectToCrs(x, y, sourceCrs, destinationCrs=CH_CRS):
    if isinstance(sourceCrs, str):
        sourceCrs = QgsCoordinateReferenceSystem(sourceCrs)
    if isinstance(destinationCrs, str):
        destinationCrs = QgsCoordinateReferenceSystem(destinationCrs)
    
    # Do not reproject if data is already in destinationCrs
    if sourceCrs == destinationCrs or not destinationCrs.isValid():
        return
    transformer = QgsCoordinateTransform(sourceCrs, destinationCrs,
                                         QgsProject.instance())
    xnew = np.copy(x)
    ynew = np.copy(y)
    for i in range(len(x)):
        point = QgsPoint(x[i], y[i])
        point.transform(transformer)
        xnew[i] = point.x()
        ynew[i] = point.y()
    
    return xnew, ynew


def tr(message, context='@default', **kwargs):
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
    return QCoreApplication.translate(context, message)
