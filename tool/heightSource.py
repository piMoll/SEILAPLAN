import os

import numpy as np
from osgeo import gdal
from qgis.core import QgsRasterLayer, QgsCoordinateReferenceSystem
from scipy import interpolate as ipol
from math import floor, sin, cos, pi
import csv


class AbstractHeightSource(object):
    
    def __init__(self):
        self.path = None
        self.extent = []
        self.buffer = (None, None)
    
    def getAsStr(self):
        return self.path or ''
    
    def prepareData(self, *args):
        raise NotImplementedError
    
    def getHeightAtPoints(self, coords):
        raise NotImplementedError
    
    
class Raster(AbstractHeightSource):
    
    BUFFER_DEFAULT = 21
    ANCHOR_BUFFER = 5
    
    def __init__(self, layer=None, path=None):
        AbstractHeightSource.__init__(self)
        self.layer = None
        self.name = None
        self.spatialRef = None
        self.subraster = None
        self.buffer = (self.BUFFER_DEFAULT, self.BUFFER_DEFAULT)
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
                self.errorMsg = f"Raster-Datei {path} ist nicht vorhanden, " \
                                f"Raster kann nicht geladen werden."
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
            self.valid = True
            del ds
    
    def prepareData(self, points, azimut):
        [Ax, Ay] = points['A']
        [Ex, Ey] = points['E']
        [xMin, yMax, xMax, yMin] = self.extent
    
        # Create sub raster to perform faster interpolation
        # raster extent
        pointXmin = min(Ax, Ex) - 2 * self.BUFFER_DEFAULT
        pointXmax = max(Ax, Ex) + 2 * self.BUFFER_DEFAULT
        pointYmin = min(Ay, Ey) - 2 * self.BUFFER_DEFAULT
        pointYmax = max(Ay, Ey) + 2 * self.BUFFER_DEFAULT
    
        # Subraster can not exceed bigger raster extent
        pointXmin = pointXmin if pointXmin >= xMin else xMin
        pointXmax = pointXmax if pointXmax <= xMax else xMax
        pointYmin = pointYmin if pointYmin >= yMin else yMin
        pointYmax = pointYmax if pointYmax <= yMax else yMax
    
        # Generate subraster, save to in memory storage
        ds = gdal.Open(self.path)
        # for band in range(1, ds.RasterCount):
        #     srcband = ds.GetRasterBand(band)
        #     if srcband:
        #         stats = srcband.GetStatistics(True, True)
        #         rstType = srcband.GetUnitType()
        #         rast_array = np.array(ds.GetRasterBand(i+1).ReadAsArray())
        
        # The subraster created has the same cellsize as the original raster.
        # If needed, the coordinates in 'projWin' are shifted so that the
        # raster does not have to be resampled
        subraster = gdal.Translate('/vsimem/in_memory_output.tif', ds,
                                   projWin=[pointXmin, pointYmax, pointXmax,
                                            pointYmin])
        z = subraster.ReadAsArray()  # TODO: z ist momentan in m, bisher dm
    
        if np.ndim(z) > 2:
            # Assumption: Height information is in first raster band
            z = z[:][:][0]
        z = np.flip(z, 0)
    
        upx, xres, xskew, upy, yskew, yres = subraster.GetGeoTransform()
        cols = subraster.RasterXSize
        rows = subraster.RasterYSize
        cellsize = xres
        xMin_ = upx + 0 * xres + 0 * xskew
        yMax_ = upy + 0 * yskew + 0 * yres
        xMax_ = upx + cols * xres + rows * xskew
        yMin_ = upy + cols * yskew + rows * yres
    
        xaxis = np.arange(xMin_, xMax_, cellsize)
        yaxis = np.arange(yMin_, yMax_, cellsize)
        extent = [xMin_, xMax_, yMin_, yMax_]
        
        self.subraster = {
            'xaxis': xaxis,
            'yaxis': yaxis,
            'z': z,
            'extent': extent,
            'cellsize': cellsize
        }
        del ds
        del subraster
    
    def getHeightAtPoints(self, coords):
        x = self.subraster['xaxis']
        y = self.subraster['yaxis']
        z = self.subraster['z']
        # Linear interpolation on subraster
        points_lin = ipol.interpn((y, x), z, coords)
        return points_lin


class SurveyData(AbstractHeightSource):
    
    BUFFER_DEFAULT = 0
    ANCHOR_BUFFER = 5
    
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
        self.plane = None
        self.normalVector = None
        self.pointInPlane = None
        self.interpolFunc = None
        self.valid = False
        self.errorMsg = ''
        self.openFile()
    
    def openFile(self):
        success = False
        
        def formatStr(s):
            return s.strip().upper()
        
        with open(self.path) as file:
            reader = csv.reader(file, delimiter=',')
            for row in reader:
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
            success = self.readOutData(idxLon[0], idxLat[0], idxAlt[0])
            self.spatialRef = QgsCoordinateReferenceSystem('EPSG:4326')
        
        # Check if data is in x, y, z format
        elif len(idxX) == 1 and len(idxY) == 1 and len(idxZ) == 1:
            success = self.readOutData(idxX[0], idxY[0], idxZ[0])
            # TODO: Maybe inform that project coordinate system has to be set correctly
        
        if success:
            self.projectOnLine()
            self.valid = True
        else:
            # TODO: Text anpassen
            self.errorMsg = ("csv-Datei konnte nicht geladen werden. Stellen "
                    "Sie sicher, dass die Datei die drei Spalten 'x', 'y' und "
                    "'z' besitzt und ausser den Überschriften keine Texte "
                    "enthält.")
        
    def readOutData(self, idxX, idxY, idxZ):
        try:
            x, y, z = np.genfromtxt(self.path, delimiter=',', dtype='float64',
                                    usecols=(idxX, idxY, idxZ), unpack=True,
                                    skip_header=1)
        except Exception as e:
            # TODO
            return False
        self.extent = [np.min(x), np.max(y), np.max(x), np.min(y)]
        self.surveyPoints = {
            'x': x,
            'y': y,
            'z': z
        }
        return True
    
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

        # Sort coordinates by x
        if np.min(res[:,0]) == np.max(res[:,0]):
            # Special case: coordinates lie perfectly on vertical axis
            sortedCoordinates = res[res[:,1].argsort()]
        else:
            sortedCoordinates = res[res[:,0].argsort()]
        self.x, self.y, self.z = np.column_stack(sortedCoordinates)

    def prepareData(self, points, azimut):
        [Ax, Ay] = points['A']
        [Ex, Ey] = points['E']
        # Switch sorting of points if cable line goes in opposite direction
        if Ax > Ex or (Ay > Ey and Ax == Ex):
            # By default points are sorted by x coordinate in ascending order.
            # If profile line defined by A and E has descending x-coordinates
            # we have to switch the coordinate arrays.
            # Special case: If all points lie perfectly on a vertical (map)
            # axis (all points have same x-coord), wen have to check if
            # y-coord is descending.
            self.x = self.x[::-1]
            self.y = self.y[::-1]
            self.z = self.z[::-1]
            
        [x0, y0] = self.getFirstPoint()
        [x1, y1] = self.getLastPoint()
        # Calculate distances from every point to first point on profile
        dist = ((self.x - np.ones_like(self.x) * x0) ** 2
                + (self.y - np.ones_like(self.x) * y0) ** 2) ** 0.5
        # distArr = np.column_stack((dist, self.z))
        # Interpolate distance-height points on profile
        self.interpolFunc = ipol.interp1d(dist, self.z)
        
        # Update buffer: If user defined other start/end points than first and
        # last point of profile, define distances to ends as buffer
        distToStart = ((x0 - Ax) ** 2 + (y0 - Ay) ** 2) ** 0.5
        distToEnd = ((x1 - Ex) ** 2 + (y1 - Ey) ** 2) ** 0.5
        self.buffer = (distToStart, distToEnd)

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
            dist = ((coords[0][1] - x0)**2 + (coords[0][0] - y0)**2)**0.5
        # Several points in array
        else:
            dist = ((coords[:,1] - x0)**2 + (coords[:,0] - y0)**2)**0.5
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
        [x0, y0] = self.getFirstPoint()
        [x1, y1] = self.getLastPoint()
        if xOnLine < x0 and (yOnLine > y0 > y1 or yOnLine < y0 < y1):
            xOnLine = x0
            yOnLine = y0
        elif xOnLine > x1 and (yOnLine > y1 > y0 or yOnLine < y1 < y0):
            xOnLine = x1
            yOnLine = y1

        return [xOnLine, yOnLine]
