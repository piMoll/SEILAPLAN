import os

import numpy as np
from osgeo import gdal, osr
from qgis.core import QgsRasterLayer
from scipy import interpolate as ipol
from math import ceil, floor


class AbstractHeightSource(object):
    
    def __init__(self):
        self.path = None
        self.extent = None
        self.buffer = None
    
    def getAsStr(self):
        return self.path or ''
    
    def prepareData(self, *args):
        raise NotImplementedError
    
    def getHeightAtPoints(self, coords):
        raise NotImplementedError
    
    
class Raster(AbstractHeightSource):
    
    RASTER_BUFFER_DEFAULT = 21
    ANCHOR_BUFFER = 5
    
    def __init__(self, layer=None, path=None):
        AbstractHeightSource.__init__(self)
        self.layer = None
        self.name = None
        self.spatialRef = None
        self.contour = None
        self.subraster = None
        self.buffer = self.RASTER_BUFFER_DEFAULT
        self.valid = False
        
        # Get raster info from QGIS layer
        if layer and isinstance(layer, QgsRasterLayer):
            self.layer = layer
            self.name = layer.name()
            self.path = layer.dataProvider().dataSourceUri()
            self.spatialRef = layer.crs().authid()
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
        elif path and os.path.exists(path):
            self.path = path
            ds = gdal.Open(path)
            prj = ds.GetProjection()
            if prj:
                srs = osr.SpatialReference(wkt=prj)
                self.spatialRef = srs.GetAttrValue("AUTHORITY", 0) + ':' \
                                  + srs.GetAttrValue("AUTHORITY", 1)
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
    
    def setContour(self, contourLyr):
        self.contour = contourLyr
    
    def prepareData(self, points, anchorLen):
        self.updateRasterBuffer(anchorLen)
        
        [Ax, Ay] = points['A']
        [Ex, Ey] = points['E']
        [xMin, yMax, xMax, yMin] = self.extent
    
        # Create sub raster to perform faster interpolation
        # raster extent
        pointXmin = min(Ax, Ex) - 2 * self.buffer
        pointXmax = max(Ax, Ex) + 2 * self.buffer
        pointYmin = min(Ay, Ey) - 2 * self.buffer
        pointYmax = max(Ay, Ey) + 2 * self.buffer
    
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

    def updateRasterBuffer(self, anchorLen):
        anchorLen += self.ANCHOR_BUFFER
        self.buffer = max(self.RASTER_BUFFER_DEFAULT, anchorLen)


class SurveyData(AbstractHeightSource):
    
    BUFFER_DEFAULT = 0
    
    def __init__(self, path):
        AbstractHeightSource.__init__(self)
        self.path = path
        self.extent = None
        self.cellsize = 1
        self.buffer = self.BUFFER_DEFAULT
        self.surveyPoints = None
        self.interpolFunc = None
        self.valid = False
        self.readFromFile()
    
    def readFromFile(self):
        try:
            z, x, y = np.genfromtxt(self.path, delimiter=',',
                                    dtype='float64', skip_header=1,
                                    unpack=True)
        except Exception as e:
            # TODO
            return False
    
        self.extent = [floor(np.min(x)), ceil(np.max(y)),
                       ceil(np.max(x)), floor(np.min(y))]
        self.surveyPoints = {
            'x': x,
            'y': y,
            'z': z
        }
        self.valid = True
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
        plane = np.linalg.lstsq(flatpoints, np.ones_like(x), rcond=None)[0]
        # Get coefficients of plane
        a, b, c = plane
    
        # Get normal vector of plane
        vectorNorm = a * a + b * b + c * c
        normalVector = np.array([a, b, c]) / np.sqrt(vectorNorm)
        # Get a sample point in plane
        pointInPlane = np.array([a, b, c]) / vectorNorm
    
        # Restructure survey data
        pointsN = np.column_stack((x, y, z))
        # Projects the points with coordinates x, y, z onto the plane defined
        # by a*x + b*y + c*z = 1
        # Reference all survey points to the sample point in plane
        pointsFromPointInPlane = pointsN - pointInPlane
        # Project these points onto the normal vector
        projOntoNormalVector = np.dot(pointsFromPointInPlane, normalVector)
        # Subtract projection from the points
        projOntoPlane = (pointsFromPointInPlane - projOntoNormalVector[:, None]
                         * normalVector)
        # Reference projected survey points back to the origin by adding sample
        # point in plane
        res = pointInPlane + projOntoPlane

        # Sort coordinates by x
        if np.min(res[:,0]) == np.max(res[:,0]):
            # Special case: coordinates lie perfectly on vertical axis
            sortedCoordinates = res[res[:,1].argsort()]
        else:
            sortedCoordinates = res[res[:,0].argsort()]

        rxx, ryy, rzz = np.column_stack(sortedCoordinates)
        self.surveyPoints = {
            'x': rxx,
            'y': ryy,
            'z': rzz
        }
    
    def prepareData(self):
        # TODO
        # # Calculate distances from every point to first point on profile
        # dist = ((rxx - np.ones_like(x) * Ax) ** 2
        #         + (ryy - np.ones_like(x) * Ay) ** 2) ** 0.5
        # distArr = np.column_stack((dist, rzz))
        # # Sort distances
        # distArr_sort = np.sort(distArr, 0)
        # # Interpolate points on profile
        # self.interpolFunc = ipol.interp1d(distArr_sort[:, 0], distArr_sort[:, 1])
        pass

    def getFirstPoint(self):
        return [self.surveyPoints['x'][0].item(), self.surveyPoints['y'][0].item()]

    def getLastPoint(self):
        return [self.surveyPoints['x'][-1].item(), self.surveyPoints['y'][-1].item()]

    def getHeightAtPoints(self, coords):
        # TODO: Profile could be in opposite direction of survey points
        #  may sort surveyPoints when Start/End coordinate is known
        distToFirst = ((coords[1][0] - self.surveyPoints['x'][0])**2 +
                       (coords[0][0] - self.surveyPoints['y'][0])**2)**0.5
        arr = np.arange(distToFirst, len(coords), 1)
        return self.interpolFunc(arr)

