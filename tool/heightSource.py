import os

import numpy as np
from osgeo import gdal
from qgis.PyQt.QtCore import QCoreApplication
from qgis.core import (QgsCoordinateTransform, QgsRasterLayer, QgsPoint,
                       QgsCoordinateReferenceSystem, QgsProject)
from math import sin, cos, pi
import csv
import copy
# Check if library scipy is present. On linux scipy isn't included in
#  the standard qgis python interpreter
try:
    from scipy import interpolate as ipol
except ModuleNotFoundError:
    # Import error is handled in seilaplanPlugin.py run() function
    pass


class AbstractHeightSource(object):
    
    def __init__(self):
        self.path = None
        self.spatialRef = None
        self.contourLayer = None
        self.extent = []
        self.buffer = (None, None)
    
    def getAsStr(self):
        return self.path or ''
    
    def prepareData(self, *args):
        raise NotImplementedError
    
    def getHeightAtPoints(self, coords):
        raise NotImplementedError
    
    def guessCrs(self):
        if self.extent and -180 <= self.extent[0] <= 180 \
                and -90 <= self.extent[1] <= 90:
            self.spatialRef = QgsCoordinateReferenceSystem('EPSG:4326')
        else:
            self.spatialRef = QgsCoordinateReferenceSystem()

    # noinspection PyMethodMayBeStatic
    def tr(self, message, **kwargs):
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
        return QCoreApplication.translate(type(self).__name__, message)


class Raster(AbstractHeightSource):
    
    BUFFER_DEFAULT = 50
    
    def __init__(self, layer=None, path=None):
        AbstractHeightSource.__init__(self)
        self.layer = None
        self.name = None
        self.spatialRef = None
        self.subraster = None
        self.buffer = [None, None]
        self.valid = False
        self.errorMsg = ''
        
        # Get raster info from QGIS layer
        if layer and isinstance(layer, QgsRasterLayer):
            self.layer = layer
            self.name = layer.name()
            self.path = layer.dataProvider().dataSourceUri()
            self.spatialRef = layer.crs()
            ext = layer.extent()
            self.extent = [ext.xMinimum(),
                           ext.yMaximum(),
                           ext.xMaximum(),
                           ext.yMinimum()]
            self.cols = layer.width()
            self.rows = layer.height()
            self.cellsize = float(layer.rasterUnitsPerPixelX())
            self.valid = True
            
        # Get raster info from gdal raster object
        elif path:
            if not os.path.exists(path):
                self.errorMsg = self.tr("Raster-Datei _path_ ist nicht vorhanden, "
                                        "Raster kann nicht geladen werden.")
                self.errorMsg = self.errorMsg.replace('_path_', path)
                return
            self.path = path
            ds = gdal.Open(path)
            prj = ds.GetProjection()
            if prj:
                self.spatialRef = QgsCoordinateReferenceSystem(prj)
            self.cols = ds.RasterXSize
            self.rows = ds.RasterYSize
            upx, xres, xskew, upy, yskew, yres = ds.GetGeoTransform()
            self.cellsize = xres
            xMin = upx + 0 * xres + 0 * xskew
            yMax = upy + 0 * yskew + 0 * yres
            xMax = upx + self.cols * xres + self.rows * xskew
            yMin = upy + self.cols * yskew + self.rows * yres
            self.extent = [xMin, yMax, xMax, yMin]
            if not self.spatialRef:
                self.guessCrs()
            self.valid = True
            del ds
    
    def prepareData(self, points, azimut, anchorLen):
        [Ax, Ay] = points['A']
        [Ex, Ey] = points['E']
        [xMin, yMax, xMax, yMin] = self.extent
        self.buffer = (self.BUFFER_DEFAULT + anchorLen,
                       self.BUFFER_DEFAULT + anchorLen)

        # Extend profile line by buffer length so user can move start and end
        #  point slightly
        reverseAzimut = azimut + pi
        if azimut > pi:
            reverseAzimut = azimut - pi
        AxBuff = Ax + self.buffer[0] * sin(reverseAzimut)
        AyBuff = Ay + self.buffer[0] * cos(reverseAzimut)
        ExBuff = Ex + self.buffer[1] * sin(azimut)
        EyBuff = Ey + self.buffer[1] * cos(azimut)
        
        # Add 5 pixel safety margin
        pointXmin = min(AxBuff, ExBuff) - 5 * self.cellsize
        pointXmax = max(AxBuff, ExBuff) + 5 * self.cellsize
        pointYmin = min(AyBuff, EyBuff) - 5 * self.cellsize
        pointYmax = max(AyBuff, EyBuff) + 5 * self.cellsize
        # Check if extended profile is still fully inside raster
        pointXmin = pointXmin if pointXmin >= xMin else xMin
        pointXmax = pointXmax if pointXmax <= xMax else xMax
        pointYmin = pointYmin if pointYmin >= yMin else yMin
        pointYmax = pointYmax if pointYmax <= yMax else yMax

        # The subraster is being created in memory, not on disk. It has the
        # same cellsize as the original raster. If needed, the coordinates in
        # 'projWin' are shifted so that the raster does not have to be
        # resampled.
        ds = gdal.Open(self.path)
        subraster = gdal.Translate('/vsimem/in_memory_output.tif', ds,
                                   projWin=[pointXmin, pointYmax, pointXmax,
                                            pointYmin])
        z = subraster.ReadAsArray()
        if np.ndim(z) > 2:
            # Assumption: Height information is in first raster band
            z = z[:][:][0]
        z = np.flip(z, 0)
    
        upx, xres, xskew, upy, yskew, yres = subraster.GetGeoTransform()
        # This raster has its origin in the upper left corner, so y axis is
        #  always descending
        cols = subraster.RasterXSize
        rows = subraster.RasterYSize
        cellsize = xres
        xMin_ = upx
        yMax_ = upy
        xMax_ = upx + cols * xres + rows * xskew
        yMin_ = upy + cols * yskew + rows * yres
        
        # Shift coordinates of cell from left upper corner to center of pixel
        xMin_m = xMin_ + 0.5 * cellsize
        xMax_m = xMax_ + 0.5 * cellsize
        yMin_m = yMin_ - 0.5 * cellsize
        yMax_m = yMax_ - 0.5 * cellsize
    
        xaxis = np.arange(xMin_m, xMax_m, cellsize)
        yaxis = np.arange(yMin_m, yMax_m, cellsize)
        # Because of floating point issues there are some rare cases where
        #  numpy.arange() will create one more entry than necessary
        if len(xaxis) != cols:
            xaxis = xaxis[:-1]
        if len(yaxis) != rows:
            yaxis = yaxis[:-1]
        
        extent = [xMin_, xMax_, yMin_, yMax_]

        self.subraster = {
            'xaxis': xaxis,
            'yaxis': yaxis,
            'z': z,
            'extent': extent,
            'cellsize': cellsize
        }
        # Update buffer at start and end point. If profile is near edge of
        #  raster, no buffer is added to the profile (buffer length = 0)
        bufferA = self.buffer[0]
        bufferE = self.buffer[1]
        if not (xMin_m <= AxBuff <= xMax_m - cellsize
                and yMin_m <= AyBuff <= yMax_m - cellsize):
            bufferA = 0
        if not (xMin_m <= ExBuff <= xMax_m-cellsize
                and yMin_m <= EyBuff <= yMax_m-cellsize):
            bufferE = 0
        self.buffer = (bufferA, bufferE)
        
        del ds
        del subraster
    
    def getHeightAtPoints(self, coords):
        x = self.subraster['xaxis']
        y = self.subraster['yaxis']
        z = self.subraster['z']
        # Linear interpolation on subraster
        try:
            points_lin = ipol.interpn((y, x), z, coords)
        except ValueError:
            raise Exception(self.tr('Interpolation auf Raster nicht moeglich.'))
        return points_lin


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
                idxLon = [idx for idx, h in enumerate(row) if formatStr(h) == 'LON']
                idxLat = [idx for idx, h in enumerate(row) if formatStr(h) == 'LAT']
                idxAlt = [idx for idx, h in enumerate(row) if formatStr(h) == 'ALTITUDE']
    
                idxX = [idx for idx, h in enumerate(row) if formatStr(h) == 'X']
                idxY = [idx for idx, h in enumerate(row) if formatStr(h) == 'Y']
                idxZ = [idx for idx, h in enumerate(row) if formatStr(h) == 'Z']
                break

        # Check if data is in vertex format
        if len(idxLat) == 1 and len(idxLon) == 1 and len(idxAlt) == 1:
            success = self.readOutData(idxLon[0], idxLat[0], idxAlt[0], sep)
            self.spatialRef = QgsCoordinateReferenceSystem('EPSG:4326')
        
        # Check if data is in x, y, z format
        elif len(idxX) == 1 and len(idxY) == 1 and len(idxZ) == 1:
            success = self.readOutData(idxX[0], idxY[0], idxZ[0], sep)
        
        if success:
            self.projectOnLine()
            self.valid = True
        else:
            self.errorMsg = self.tr("Daten in CSV-Datei konnten nicht geladen werden.")
        
    def readOutData(self, idxX, idxY, idxZ, sep):
        try:
            x, y, z = np.genfromtxt(self.path, delimiter=sep, dtype='float64',
                                    usecols=(idxX, idxY, idxZ), unpack=True,
                                    skip_header=1)
        except TypeError as e:
            return False
        # Check for missing values
        x_isnan = np.isnan(x)
        y_isnan = np.isnan(y)
        z_isnan = np.isnan(z)
        # Remove whole row
        x = x[~(x_isnan + y_isnan + z_isnan)]
        y = y[~(x_isnan + y_isnan + z_isnan)]
        z = z[~(x_isnan + y_isnan + z_isnan)]
        
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
    
    def reprojectToCrs(self, destinationCrs):
        if isinstance(destinationCrs, str):
            destinationCrs = QgsCoordinateReferenceSystem(destinationCrs)
        if not destinationCrs:
            destinationCrs = QgsCoordinateReferenceSystem('EPSG:2056')
        # Do not reproject if data is already in destinationCrs
        if self.spatialRef == destinationCrs or not destinationCrs.isValid():
            return
        transformer = QgsCoordinateTransform(self.spatialRef, destinationCrs,
                                             QgsProject.instance())

        for i in range(len(self.surveyPoints['x'])):
            point = QgsPoint(self.surveyPoints['x'][i],
                             self.surveyPoints['y'][i])
            point.transform(transformer)
            self.surveyPoints['x'][i] = point.x()
            self.surveyPoints['y'][i] = point.y()
        
        self.spatialRef = destinationCrs
        self.projectOnLine()
    
    def projectOnLine(self):
        # Fit a plane through X/Y coordinates with least squares algorithm
        x = self.surveyPoints['x']
        y = self.surveyPoints['y']
        z = self.surveyPoints['z']
        
        # First, replace Z-coordinate with 0 -> we are working in 2D space and
        # restructure data so that every point is a sub array of 3 coordinates
        flatpoints = np.array([x, y, np.zeros_like(x)])
        flatpoints = np.column_stack(flatpoints)
        # Fit a plane through X/Y coordinates with least squares algorithm
        self.plane = np.linalg.lstsq(flatpoints, np.ones_like(x), rcond=None)[0]
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
        projOntoNormalVector = np.dot(pointsFromPointInPlane, self.normalVector)
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
            self.plotPoints = np.column_stack([surveyPnts_d, surveyPnts_z, self.nr])
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
        x0 = np.array([x0]*len(coords))
        y0 = np.array([y0]*len(coords))
        # Only one point
        if np.shape(coords)[0] == 1:
            dist = np.hypot(coords[0][1] - x0, coords[0][0] - y0)
        # Several points in array
        else:
            dist = np.hypot(coords[:,1] - x0, coords[:,0] - y0)
        return self.interpolFunc(dist)
    
    def projectPositionOnToLine(self, position):
        """ Gets a position on map and transforms it to nearest points on
        survey profile line."""
        point = np.array([[position.x(), position.y(), 0]])
        # Reference point to a sample point in plane
        pointsFromPointInPlane = point - self.pointInPlane
        # Project this point onto the normal vector
        projOntoNormalVector = np.dot(pointsFromPointInPlane, self.normalVector)
        # Subtract projection from the point
        projOntoPlane = (pointsFromPointInPlane - projOntoNormalVector[:, None]
                         * self.normalVector)
        # Reference projected point back to origin by adding sample point in plane
        res = self.pointInPlane + projOntoPlane
        xOnLine = res[0][0]
        yOnLine = res[0][1]
        
        # Check that point never leaves profile between first and last point
        [x0, y0] = [self.origData['x'][0].item(), self.origData['y'][0].item()]
        [x1, y1] = [self.origData['x'][-1].item(), self.origData['y'][-1].item()]
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
            nextIdx = len(self.origData['plotPoints'][:, 0])-1
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
