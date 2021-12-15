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
import numpy as np
from qgis.core import QgsCoordinateReferenceSystem
import csv
import copy
from .heightSource import AbstractHeightSource
from .outputGeo import GPS_CRS, CH_CRS, latLonToUtmCode, reprojectToCrs
# Check if library scipy is present. On linux scipy isn't included in
#  the standard qgis python interpreter
try:
    from scipy import interpolate as ipol
except ModuleNotFoundError:
    # Import error is handled in seilaplanPlugin.py run() function
    pass


class SurveyData(AbstractHeightSource):
    BUFFER_DEFAULT = 0
    
    def __init__(self, path):
        AbstractHeightSource.__init__(self)
        self.path = path
        self.extent = None
        self.cellsize = 1
        self.spatialRef = None
        self.azimut = None
        self.buffer = (self.BUFFER_DEFAULT, self.BUFFER_DEFAULT)
        self.surveyPoints = {}
        self.x = None
        self.y = None
        self.z = None
        self.nr = None
        self.dist = None
        self.plane = None
        self.normalVector = None
        self.pointInPlane = None
        self.interpolFunc = None
        self.plotPoints = None
        self.origData = {}
        self.valid = False
        self.errorMsg = ''
        self.openFile()
        if not self.spatialRef:
            self.guessCrs()
    
    def openFile(self):
        success = False
        
        def formatStr(s):
            return s.strip().upper()

        if not os.path.exists(self.path):
            self.valid = False
            self.errorMsg = self.tr(
                "CSV-Datei '_path_' ist nicht vorhanden.")
            self.errorMsg = self.errorMsg.replace('_path_', self.path)
            return
        
        with open(self.path, newline='') as file:
            reader = csv.reader(file)
            sep = ','
            for row in reader:
                if len(row) == 1:
                    row = row[0].split(';')
                    sep = ';'
                if len(row) == 1:
                    row = row[0].split(',')
                    sep = ','
                # Analyse header line
                
                # Fields of Vertex csv
                idxTYPE = [idx for idx, h in enumerate(row) if
                           formatStr(h) == 'TYPE']
                idxLon = [idx for idx, h in enumerate(row) if
                          formatStr(h) == 'LON']
                idxLat = [idx for idx, h in enumerate(row) if
                          formatStr(h) == 'LAT']
                idxSEQ = [idx for idx, h in enumerate(row) if
                          formatStr(h) == 'SEQ']
                idxAlti = [idx for idx, h in enumerate(row) if
                           formatStr(h) == 'ALTITUDE']
                idxHD = [idx for idx, h in enumerate(row) if
                         formatStr(h) == 'HD']
                idxAz = [idx for idx, h in enumerate(row) if
                         formatStr(h) == 'AZ']
                
                idxX = [idx for idx, h in enumerate(row) if
                        formatStr(h) == 'X']
                idxY = [idx for idx, h in enumerate(row) if
                        formatStr(h) == 'Y']
                idxZ = [idx for idx, h in enumerate(row) if
                        formatStr(h) == 'Z']
                break
        
        # Check if data is in vertex format
        if len(idxTYPE) == 1 and len(idxSEQ) == 1 and len(idxAlti) == 1 \
                and len(idxHD) == 1 and len(idxAz) == 1 \
                and len(idxLat) == 1 and len(idxLon) == 1:
            success = self.readOutVertexData(idxTYPE[0], idxSEQ[0], idxAlti[0],
                        idxHD[0], idxAz[0], idxLon[0], idxLat[0], sep)
        
        # Check if data is in x, y, z format
        elif len(idxX) == 1 and len(idxY) == 1 and len(idxZ) == 1:
            success = self.readOutData(idxX[0], idxY[0], idxZ[0], sep)
        
        if success:
            self.projectOnLine()
            self.valid = True
        else:
            if not self.errorMsg:
                self.errorMsg = self.tr("Daten in CSV-Datei konnten nicht geladen werden.")
    
    def readOutData(self, idxX, idxY, idxZ, sep):
        try:
            x, y, z = np.genfromtxt(self.path, delimiter=sep, dtype='float64',
                                    usecols=(idxX, idxY, idxZ), unpack=True,
                                    skip_header=1)
        except TypeError as e:
            return False
        # Check for missing values and remove whole row
        x = x[~(np.isnan(x) + np.isnan(y) + np.isnan(z))]
        y = y[~(np.isnan(x) + np.isnan(y) + np.isnan(z))]
        z = z[~(np.isnan(x) + np.isnan(y) + np.isnan(z))]
        
        if len(x) < 2:
            return False
        try:
            self.extent = [np.min(x), np.max(y), np.max(x), np.min(y)]
        except TypeError as e:
            return False
        
        self.surveyPoints = {
            'x': x,
            'y': y,
            'z': z
        }
        self.nr = np.arange(len(x)) + 1
        return True
    
    def readOutVertexData(self, idxTYPE, idxSEQ, idxAlti, idxHD, idxAz, idxLon, idxLat, sep):
        try:
            # Readout measuring type separately (because the data is of
            # type string)
            dataType = np.genfromtxt(self.path, delimiter=sep, dtype=str,
                                     usecols=idxTYPE)
            # Analyse when data rows start
            skipHead = np.where(dataType == 'TRAIL')[0][0]
            # Read out numerical values
            seq, alti, hd, az, lon, lat = np.genfromtxt(self.path, delimiter=sep,
                    usecols=(idxSEQ, idxAlti, idxHD, idxAz, idxLon, idxLat),
                    skip_header=skipHead, unpack=True)
        except ValueError:
            return False
        
        # Make sure array dataType has the same size as the numerical data
        #  and check if the readout data has type TRAIL
        trail = dataType[skipHead:] == 'TRAIL'
        
        # See if dimensions of extracted data fit
        if not (trail.size == seq.size == alti.size == hd.size ==
                az.size == lon.size == lat.size):
            return False
        
        # Check for missing values and create array masks to skip them when
        #  processing
        mask_use = np.array([True]*seq.size)
        
        # Check if there are multiple measurement series by searching for
        #  seq = 1. Only take the longest sequence of measurements
        sequence_len = []
        sequence_starts = np.where(seq == 1)[0]
        last_start = 0
        for sequence_start in sequence_starts:
            if sequence_start != 0:
                sequence_len.append(sequence_start - last_start)
            last_start = sequence_start
        sequence_len.append(seq.size - last_start)
        # Find sequence start and end index
        start_of_longest_sequence = sequence_starts[np.argmax(sequence_len)]
        end_of_longest_sequence = sequence_starts[np.argmax(sequence_len)+1] \
            if sequence_len == seq.size else -1
        
        # Update mask by setting every other measurement series to False
        mask_use[:start_of_longest_sequence] = False
        if end_of_longest_sequence != -1:
            mask_use[end_of_longest_sequence:] = False
        
        seq = seq[mask_use]
        alti = alti[mask_use]
        hd = hd[mask_use]
        az = az[mask_use]
        lon = lon[mask_use]
        lat = lat[mask_use]
        # Check if some gps measurements are missing
        mask_gps = ~(np.isnan(lon) + np.isnan(lat))
        
        # Quality checks
        
        # If relative measurements are missing, we cannot create a line
        if np.sum(np.isnan(az)) > 0 \
                or np.sum(np.isnan(hd)) > 0:
            self.errorMsg = self.tr('Die Messdaten sind unvollstaendig, '
                                    'die CSV-Datei kann nicht geladen werden.')
            return False

        # Check if the sequence numbers are in order and that there are no gaps
        if np.sum(np.cumsum(np.array([1] * seq.size)) == seq) != seq.size:
            # Only add a warning, create the profile ether way
            self.errorMsg = self.tr('Die CSV-Datei enthaelt Messluecken, '
                'das erstellte Profil koennte fehlerhaft sein.')
        
        # If there are multiple measurements series (sequence restarts at one),
        # there is most certainly an issue with the CSV data
        if np.sum(seq == 1) > 1:
            # Only add a warning
            self.errorMsg = self.tr('Die CSV-Datei enthaelt mehr als eine '
                'Messreihe. Es wurde nur die laengste Messreihe geladen.')
    
        # Check if at least one pair of absolute coordinates are present to
        #  transform relative measurements into destination coordinate system
        if lon[mask_gps].size == 0 or lat[mask_gps].size == 0:
            self.errorMsg = self.tr('Die CSV-Datei enthaelt keine '
                'GPS-Koordinaten, das Profil kann nicht erstellt werden.')
            return False
    
        # Calculate X/Y coordinate relative to the first point (0, 0)
        #  by adding the distance (horizontalDist * sin(azimuth))
        relCoords = np.array(
            [np.cumsum(hd * np.sin(np.radians(az))),
             np.cumsum(hd * np.cos(np.radians(az)))
            ])
    
        # Guess UTM epsg code by analysing lat, lon values
        try:
            utmEpsg = latLonToUtmCode(lat[mask_gps][0], lon[mask_gps][0])
        except Exception:
            self.errorMsg = self.tr('Die CSV-Datei enthaelt ungueltige GPS-Koordinaten.')
            return False
    
        # Transform GPS coordinates to projected UTM coordinates
        utmx, utmy = reprojectToCrs(lon[mask_gps], lat[mask_gps], GPS_CRS, utmEpsg)
        utmCoords = np.array([utmx, utmy])

        # Calculate mean distance to UTM coords but only on rows where
        #  GPS coords are present
        # TODO: Gewichtung GPS Genauigkeit
        deltaX = utmCoords[0] - relCoords[0][mask_gps]
        deltaY = utmCoords[1] - relCoords[1][mask_gps]
        meanDist = np.mean(np.sqrt(np.square(deltaX) + np.square(deltaY)))
        # Calculate mean azimut to UTM coords
        meanAz = np.mean(np.arctan(deltaX/deltaY))

        # Move relative coordinates to UTM system
        relCoordsNew = np.array([
            relCoords[0] + meanDist * np.sin(meanAz),
            relCoords[1] + meanDist * np.cos(meanAz)
        ])
        # Translate back to WGS84
        gpsx, gpsy = reprojectToCrs(relCoordsNew[0], relCoordsNew[1], utmEpsg, GPS_CRS)
        self.surveyPoints = {
            'x': gpsx,
            'y': gpsy,
            'z': alti
        }
        self.spatialRef = QgsCoordinateReferenceSystem(GPS_CRS)
        self.nr = np.arange(len(gpsx)) + 1

        # TODO: Remove
        self.addToMap(GPS_CRS, lon, lat, 'gps')
        # self.addToMap(utmEpsg, relCoordsNew[0], relCoordsNew[1], 'rel')
        # self.addToMap(GPS_CRS, gpsx, gpsy, 'rel2gps')

        return True
    
    def reprojectToCrs(self, destinationCrs):
        if isinstance(destinationCrs, str):
            destinationCrs = QgsCoordinateReferenceSystem(destinationCrs)
        if not destinationCrs:
            destinationCrs = QgsCoordinateReferenceSystem(CH_CRS)
        # Do not reproject if data is already in destinationCrs
        if self.spatialRef == destinationCrs or not destinationCrs.isValid():
            return
        
        # If original spatial ref was not valid (empty), set the destination
        #  CRS as new spatial reference
        if not self.spatialRef.isValid():
            self.spatialRef = destinationCrs
            return

        xnew, ynew = reprojectToCrs(self.surveyPoints['x'],
                                    self.surveyPoints['y'],
                                    self.spatialRef, destinationCrs)
        self.surveyPoints['x'] = xnew
        self.surveyPoints['y'] = ynew
        self.spatialRef = destinationCrs
        
        self.projectOnLine()
    
    def projectOnLine(self):
        """ Interpolate points so they lay on a line. This does not make much
        sense for geographical GPS coordinates, but this function will run
        again after points have been projected onto a planar coordinate system.
        """
        
        # Fit a plane through X/Y coordinates with least squares algorithm
        x = self.surveyPoints['x']
        y = self.surveyPoints['y']
        z = self.surveyPoints['z']
        
        # First, replace Z-coordinate with 0 -> we are working in 2D space and
        # restructure data so that every point is a sub array of 3 coordinates
        flatpoints = np.array([x, y, np.zeros_like(x)])
        flatpoints = np.column_stack(flatpoints)
        # Fit a plane through X/Y coordinates with least squares algorithm
        self.plane = np.linalg.lstsq(flatpoints, np.ones_like(x), rcond=None)[
            0]
        # Get coefficients of plane
        a, b, c = self.plane
        
        # Get normal vector of plane
        vectorNorm = a * a + b * b + c * c
        self.normalVector = np.array([a, b, c]) / np.sqrt(vectorNorm)
        # Get a sample point in plane
        self.pointInPlane = np.array([a, b, c]) / vectorNorm
        
        # Restructure survey data
        pointsN = np.column_stack((x, y, z))
        # Projects the points with coordinates x, y, z onto the plane defined
        # by a*x + b*y + c*z = 1
        # Reference all survey points to the sample point in plane
        pointsFromPointInPlane = pointsN - self.pointInPlane
        # Project these points onto the normal vector
        projOntoNormalVector = np.dot(pointsFromPointInPlane,
                                      self.normalVector)
        # Subtract projection from the points
        projOntoPlane = (pointsFromPointInPlane - projOntoNormalVector[:, None]
                         * self.normalVector)
        # Reference projected survey points back to the origin by adding sample
        # point in plane
        res = self.pointInPlane + projOntoPlane
        self.x, self.y, self.z = np.column_stack(res)
        # Update extent with projected coordinates
        self.extent = [np.min(self.x), np.max(self.y),
                       np.max(self.x), np.min(self.y)]
        points = {
            'A': self.getFirstPoint(),
            'E': self.getLastPoint()
        }
        self.prepareData(points, orig=True)
    
    def prepareData(self, points, azimut=None, anchorLen=None, orig=False):
        [Ax, Ay] = points['A']
        [Ex, Ey] = points['E']
        # Switch sorting of points if cable line goes in opposite direction
        if (Ax > Ex and self.x[0] < self.x[-1]) \
                or (Ax < Ex and self.x[0] > self.x[-1]):
            # If profile line defined by A and E has the opposite direction
            # than the original survey data, we have to switch the coordinate
            # arrays.
            self.x = self.x[::-1]
            self.y = self.y[::-1]
            self.z = self.z[::-1]
            self.nr = self.nr[::-1]
        
        [x0, y0] = self.getFirstPoint()
        [x1, y1] = self.getLastPoint()
        # Calculate distances from every point to first point on profile
        self.dist = np.hypot(self.x - np.ones_like(self.x) * x0,
                             self.y - np.ones_like(self.y) * y0)
        
        # Interpolate distance-height points on profile
        self.interpolFunc = ipol.interp1d(self.dist, self.z)
        
        # Update buffer: If user defined other start/end points than first and
        # last point of profile, define distances to ends as buffer
        distToStart = np.hypot(x0 - Ax, y0 - Ay)
        distToEnd = np.hypot(x1 - Ex, y1 - Ey)
        self.buffer = (distToStart, distToEnd)
        
        # For display in plot survey points are being rounded to the nearest
        #  meter and numbered
        surveyPnts_d = self.dist - distToStart
        # surveyPnts_d[1:-1] = np.round(surveyPnts_d[1:-1])
        try:
            surveyPnts_z = self.interpolFunc(surveyPnts_d + distToStart)
            self.plotPoints = np.column_stack(
                [surveyPnts_d, surveyPnts_z, self.nr])
        except ValueError:
            self.plotPoints = None
        
        if orig:
            # Save initial profile (full length) so it can be used to calculate
            #  cursor position in function projectPositionOnToLine()
            self.origData = {
                'x': copy.deepcopy(self.x),
                'y': copy.deepcopy(self.y),
                'plotPoints': copy.deepcopy(self.plotPoints)
            }
    
    def getFirstPoint(self):
        return [self.x[0].item(), self.y[0].item()]
    
    def getLastPoint(self):
        return [self.x[-1].item(), self.y[-1].item()]
    
    def getHeightAtPoints(self, coords):
        [x0, y0] = self.getFirstPoint()
        x0 = np.array([x0] * len(coords))
        y0 = np.array([y0] * len(coords))
        # Only one point
        if np.shape(coords)[0] == 1:
            dist = np.hypot(coords[0][1] - x0, coords[0][0] - y0)
        # Several points in array
        else:
            dist = np.hypot(coords[:, 1] - x0, coords[:, 0] - y0)
        return self.interpolFunc(dist)
    
    def projectPositionOnToLine(self, position):
        """ Gets a position on map and transforms it to nearest points on
        survey profile line."""
        point = np.array([[position.x(), position.y(), 0]])
        # Reference point to a sample point in plane
        pointsFromPointInPlane = point - self.pointInPlane
        # Project this point onto the normal vector
        projOntoNormalVector = np.dot(pointsFromPointInPlane,
                                      self.normalVector)
        # Subtract projection from the point
        projOntoPlane = (pointsFromPointInPlane - projOntoNormalVector[:, None]
                         * self.normalVector)
        # Reference projected point back to origin by adding sample point in plane
        res = self.pointInPlane + projOntoPlane
        xOnLine = res[0][0]
        yOnLine = res[0][1]
        
        # Check that point never leaves profile between first and last point
        [x0, y0] = [self.origData['x'][0].item(), self.origData['y'][0].item()]
        [x1, y1] = [self.origData['x'][-1].item(),
                    self.origData['y'][-1].item()]
        if xOnLine < x0 < x1 or xOnLine > x0 > x1:
            xOnLine = x0
        if xOnLine < x1 < x0 or xOnLine > x1 > x0:
            xOnLine = x1
        if yOnLine < y0 < y1 or yOnLine > y0 > y1:
            yOnLine = y0
        if yOnLine < y1 < y0 or yOnLine > y1 > y0:
            yOnLine = y1
        
        # Cursor snapping to survey points
        snapDist = 2
        distToFirst = np.hypot(x0 - xOnLine, y0 - yOnLine)
        # Get neighbouring survey points
        idx = np.argwhere(self.origData['plotPoints'][:, 0] > distToFirst)
        if len(idx > 0):
            nextIdx = idx[0][0]
        else:
            nextIdx = len(self.origData['plotPoints'][:, 0]) - 1
        lastIdx = nextIdx - 1
        distNext = self.origData['plotPoints'][:, 0][nextIdx] - distToFirst
        distLast = distToFirst - self.origData['plotPoints'][:, 0][lastIdx]
        # Check if cursor is near a survey point
        if distNext < snapDist and distNext < distLast:
            xOnLine = self.origData['x'][nextIdx]
            yOnLine = self.origData['y'][nextIdx]
        elif distLast < snapDist and distLast < distNext:
            xOnLine = self.origData['x'][lastIdx]
            yOnLine = self.origData['y'][lastIdx]
        
        return [xOnLine, yOnLine]


    # TODO remove
    def addToMap(self, lyrCrs, x, y, lyrname):
        from qgis.core import (QgsPointXY, QgsProject,
                               QgsFeature, QgsGeometry, QgsVectorLayer,
                               QgsField)
        from qgis.PyQt.QtCore import QVariant
        # Create survey point layer
        surveyPointLayer = QgsVectorLayer('Point?crs=' + lyrCrs,
                                          lyrname, 'memory')
        pr = surveyPointLayer.dataProvider()
        pr.addAttributes([QgsField("nr", QVariant.Int)])
        surveyPointLayer.updateFields()
        features = []
        idx = 1
        for x, y in np.column_stack([x, y]):
            feature = QgsFeature()
            feature.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(x, y)))
            feature.setId(idx)
            feature.setAttributes([idx])
            features.append(feature)
            idx += 1
        pr.addFeatures(features)
        surveyPointLayer.updateExtents()
        QgsProject.instance().addMapLayers([surveyPointLayer])
