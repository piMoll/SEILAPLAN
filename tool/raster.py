import os

import numpy as np
from osgeo import gdal
from qgis.core import QgsRasterLayer
from scipy import interpolate as ipol


class Raster(object):
    
    RASTER_BUFFER_DEFAULT = 21
    ANCHOR_BUFFER = 5
    
    def __init__(self, layer=None, path=None):
        self.layer = None
        self.name = None
        self.spatialRef = None
        self.contour = None
        self.subraster = None
        self.rasterBuffer = self.RASTER_BUFFER_DEFAULT
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
    
    def setSubraster(self, points, anchorLen):
        self.updateRasterBuffer(anchorLen)
        
        [Ax, Ay] = points['A']
        [Ex, Ey] = points['E']
        [xMin, yMax, xMax, yMin] = self.extent
    
        # Create sub raster to perform faster interpolation
        # raster extent
        pointXmin = min(Ax, Ex) - 2 * self.rasterBuffer
        pointXmax = max(Ax, Ex) + 2 * self.rasterBuffer
        pointYmin = min(Ay, Ey) - 2 * self.rasterBuffer
        pointYmax = max(Ay, Ey) + 2 * self.rasterBuffer
    
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
        z = subraster.ReadAsArray() # TODO: z ist momentan in m, bisher dm
    
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
    
    def getInterpolatedHeightAtPoints(self, coords):
        x = self.subraster['xaxis']
        y = self.subraster['yaxis']
        z = self.subraster['z']
        # Linear interpolation on subraster
        points_lin = ipol.interpn((y, x), z, coords)
        return points_lin

    def updateRasterBuffer(self, anchorLen):
        anchorLen += self.ANCHOR_BUFFER
        self.rasterBuffer = max(self.RASTER_BUFFER_DEFAULT, anchorLen)
