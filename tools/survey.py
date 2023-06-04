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
import copy
from .heightSource import AbstractHeightSource
from .importCsvXyz import CsvXyzReader
from .importCsvVertex import CsvVertexReader
from .importExcelProtocol import ExcelProtocolReader
from .outputGeo import CH_CRS, reprojectToCrs
# Check if library scipy is present. On linux scipy isn't included in
#  the standard qgis python interpreter
try:
    from scipy import interpolate as ipol
except ModuleNotFoundError:
    # Import error is handled in seilaplanPlugin.py run() function
    pass


class SurveyData(AbstractHeightSource):
    BUFFER_DEFAULT = 0
    
    SOURCE_CSV_XYZ = 'csvXyz'
    SOURCE_CSV_VERTEX = 'csvVertex'
    SOURCE_EXCEL_PROTOCOL = 'excelProtocol'
    
    def __init__(self, path, sourceType=None):
        AbstractHeightSource.__init__(self)
        self.path = path
        self.sourceType = None
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
        self.plotNotes = []
        self.origData = {}
        self.valid = False
        self.errorMsg = ''
        self.warnMsg = ''
        self.prHeaderData = {}
        self.openFile(sourceType)
        if self.valid and not self.spatialRef:
            self.guessCrs()
    
    def openFile(self, sourceType):
        success = False

        if not os.path.exists(self.path):
            self.valid = False
            self.errorMsg = self.tr(
                "Datei '_path_' ist nicht vorhanden.")
            self.errorMsg = self.errorMsg.replace('_path_', self.path)
            return
        
        reader = None
        
        if sourceType == self.SOURCE_CSV_XYZ or not sourceType:
            reader = CsvXyzReader(self.path)
            if reader.valid:
                try:
                    success = reader.readOutData()
                    sourceType = self.SOURCE_CSV_XYZ
                except Exception:
                    pass
        
        if sourceType == self.SOURCE_CSV_VERTEX or not sourceType:
            reader = CsvVertexReader(self.path)
            if reader.valid:
                try:
                    success = reader.readOutData()
                    sourceType = self.SOURCE_CSV_VERTEX
                    self.plotNotes = reader.notes
                except Exception:
                    pass
    
        if sourceType == self.SOURCE_EXCEL_PROTOCOL:
            reader = ExcelProtocolReader(self.path)
            if reader.valid:
                try:
                    success = reader.readOutData()
                    self.plotNotes = reader.notes['onPoint']
                except Exception:
                    pass
        
        if reader:
            self.errorMsg = reader.errorMsg
            self.warnMsg = reader.warnMsg
            self.spatialRef = reader.spatialRef
            self.surveyPoints = reader.surveyPoints
            self.nr = reader.nr
            self.sourceType = sourceType
            # Only present in excelProtocol
            self.prHeaderData = reader.prHeaderData
            if not reader.valid and not self.errorMsg:
                self.errorMsg = self.tr("Ungueltiges Format oder fehlende Daten.")

        if success:
            self.projectOnLine()
            self.valid = True
        else:
            if not self.errorMsg:
                self.errorMsg = self.tr("Datei konnte nicht eingelesen werden. Unerwarteter Fehler aufgetreten.")
        
        # If everything went fine but there is a warning, show that one on completion
        if self.warnMsg and not self.errorMsg:
            self.errorMsg = self.warnMsg
    
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
        self.plotNotes = self.plotNotes if len(self.plotNotes) == len(self.x) \
                                else[''] * len(self.x)
        
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
        if ((Ax > Ex and self.x[0] < self.x[-1])
                or (Ax < Ex and self.x[0] > self.x[-1])
                or (Ay > Ey and self.y[0] < self.y[-1])
                or (Ay < Ey and self.y[0] > self.y[-1])):
            # If profile line defined by A and E has the opposite direction
            # than the original survey data, we have to switch the coordinate
            # arrays.
            self.x = self.x[::-1]
            self.y = self.y[::-1]
            self.z = self.z[::-1]
            self.nr = self.nr[::-1]
            self.plotNotes = self.plotNotes[::-1]
        
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
        surveyPnts_z = np.array([]*np.size(surveyPnts_d))
        # surveyPnts_d[1:-1] = np.round(surveyPnts_d[1:-1])
        try:
            surveyPnts_z = self.interpolFunc(surveyPnts_d + distToStart)
            self.plotPoints = {
                'd': surveyPnts_d,
                'z': surveyPnts_z,
                'nr': self.nr,
                'notes': self.plotNotes,
            }
            
        except ValueError:
            self.plotPoints = None
        
        if orig:
            # Save initial profile (full length) so it can be used to calculate
            #  cursor position in function projectPositionOnToLine()
            pointCoords = np.column_stack([surveyPnts_d, surveyPnts_z])
            self.origData = {
                'x': copy.deepcopy(self.x),
                'y': copy.deepcopy(self.y),
                'plotPoints': copy.deepcopy(pointCoords)
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
