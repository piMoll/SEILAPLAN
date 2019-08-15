# -*- coding: utf-8 -*-
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

from math import cos, sin, ceil, floor
import numpy as np
from qgis.core import QgsPointXY

class Profile(object):
    def __init__(self, pointA, pointE, length, azimut, raster):
        """Creates a profile from a given start and end point on a raster."""
        self.pointA = pointA
        self.pointE = pointE
        self.length = length
        self.azimut = azimut
        self.raster = raster
        self.rasterlyr = self.raster.dataProvider()
        
        self.profile = []
        self.xaxis = None
        self.yaxis = None
        self.xmin = None
        self.ymin = None
        self.xmax = None
        self.ymax = None
    
    def create(self):
        """Extracts the raster values and saves them to a collection."""
        for step in range(floor(self.length)+1):
            newx = self.pointA.x() + step * cos(self.azimut)
            newy = self.pointA.y() + step * sin(self.azimut)
            newPoint = QgsPointXY(newx, newy)
            self.profile.append((step, self.extractRasterVal(newPoint)))

        # Last point
        if floor(self.length) != ceil(self.length):
            self.profile.append((self.length, self.extractRasterVal(self.pointE)))
        
        # Axis data
        nparr = np.asarray(self.profile)
        self.xaxis = nparr[:, 0]
        self.yaxis = nparr[:, 1]

        # Min and max values for diagramm extent
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
        