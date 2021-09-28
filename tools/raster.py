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
from osgeo import gdal
from qgis.core import QgsRasterLayer, QgsCoordinateReferenceSystem
from math import sin, cos, pi
from .heightSource import AbstractHeightSource

# Check if library scipy is present. On linux scipy isn't included in
#  the standard qgis python interpreter
try:
    from scipy import interpolate as ipol
except ModuleNotFoundError:
    # Import error is handled in seilaplanPlugin.py run() function
    pass


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
        self.noDataValue = None
        
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
                self.errorMsg = self.tr(
                    "Raster-Datei _path_ ist nicht vorhanden, "
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
        
        try:
            self.noDataValue = ds.GetRasterBand(1).GetNoDataValue()
        except Exception:
            pass
        
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
        if not (xMin_m <= ExBuff <= xMax_m - cellsize
                and yMin_m <= EyBuff <= yMax_m - cellsize):
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
            raise Exception(
                self.tr('Interpolation auf Raster nicht moeglich.'))
        # Check if z values contain NoData
        noDataCount = np.count_nonzero(points_lin == self.noDataValue)
        if noDataCount > 0:
            self.errorMsg = self.tr(
                'Profillinie enthaelt Datenluecken, bitte Start-/ Endpunkt anpassen.')
        return points_lin
