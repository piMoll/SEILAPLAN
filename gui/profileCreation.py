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
from math import cos, sin
import numpy as np
from qgis.core import QgsPointXY


class PreviewProfile(object):
    """Creates a profile from a given start and end point on a raster using
    the QGIS identify() tool. The profile resolution depends on the raster
    resolution. This Profile is only used to be plotted in the profile window
    and differs from the one created in tool -> profile.py (resolution,
    interpolation method, etc.)."""
    
    def __init__(self, projectHandler):
        """
        :type projectHandler: configHandler.ProjectConfHandler
        """
        coordsA, _ = projectHandler.getPoint('A')
        coordsE, _ = projectHandler.getPoint('E')
        self.pointA = QgsPointXY(*tuple(coordsA))
        self.pointE = QgsPointXY(*tuple(coordsE))
        self.length = projectHandler.getProfileLen()
        self.res = min(1, projectHandler.dhm.cellsize)
        self.azimut = projectHandler.getAzimut()
        self.rasterlyr = projectHandler.dhm.layer.dataProvider()
        
        self.profile = []
        self.xaxis = None
        self.yaxis = None
        self.xmin = None
        self.ymin = None
        self.xmax = None
        self.ymax = None
    
    def create(self):
        """Extracts the raster values and saves them to a collection."""
        if self.length == 0:
            return False
        stepsAlongLine = np.arange(0, self.length, self.res)

        for step in stepsAlongLine:
            newx = self.pointA.x() + step * cos(self.azimut)
            newy = self.pointA.y() + step * sin(self.azimut)
            newPoint = QgsPointXY(newx, newy)
            self.profile.append((step, self.extractRasterVal(newPoint)))
        # Last Point
        if self.length % self.res != 0:
            lastStep = stepsAlongLine[-1] + self.res
            self.profile.append((lastStep, self.extractRasterVal(self.pointE)))
        
        # Axis data
        nparr = np.asarray(self.profile)
        self.xaxis = nparr[:, 0]
        self.yaxis = nparr[:, 1]

        # Min and max values for diagram extent
        self.xmin = np.min(self.xaxis)
        self.ymin = np.min(self.yaxis)
        self.xmax = np.max(self.xaxis)
        self.ymax = np.max(self.yaxis)

        return self.profile
    
    def extractRasterVal(self, point):
        """Extracts the raster value at a point."""
        identifyResult = self.rasterlyr.identify(point, 1)
        rasterVal = -9999
        for bndNr, pixVal in identifyResult.results().items():
            if 1 == bndNr:
                try:
                    rasterVal = float(pixVal)
                except ValueError:
                    rasterVal = -9999
                    pass
        return rasterVal
    
    def expand(self, distance=10):
        """Expands the extent of the raster. Used for plotting the data."""
        if not self.profile:
            return
        self.xmin -= distance
        self.ymin -= distance
        self.xmax += distance
        self.ymax += distance
