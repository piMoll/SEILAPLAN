# -*- coding: utf-8 -*-
"""
/***************************************************************************
 SeilaplanPlugin
                                 A QGIS plugin
 Seilkran-Layoutplaner
                              -------------------
        begin                : 2013
        copyright            : (C) 2015 by ETH Zürich
        email                : mollpa@ethz.ch and bontle@ethz.ch
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
import unicodedata

from PyQt4 import QtCore, QtGui
from qgis.core import QGis, QgsRasterLayer, QgsGeometry, QgsPoint, QgsFeature
from qgis.gui import QgsRubberBand
from ..seilaplanPluginDialog import Raster
from ..bo.createProfile import CreateProfile


class Verlauf():
    def __init__(self, pointA, pointE, mainTool):
        self.mainWin = mainTool
        self.iface = mainTool.iface

        # Koordinateninformation als float
        self.pointAx = pointA[0]
        self.pointAy = pointA[1]
        self.pointEx = pointE[0]
        self.pointEy = pointE[1]
        # Start-/Endkoordinaten als QGIS Punkt-Objekte
        self.qgisPointA = None
        self.qgisPointE = None

        # Linienelement in der Karte
        self.rubberband = QgsRubberBand(self.mainWin.canvas, False)
        self.rubberband.setWidth(2)
        self.rubberband.setColor(QtGui.QColor(QtCore.Qt.red))

        self.drawnLine = None



        self.profile = self.makeProfile()

    def updatePointA(self, point):
        try:
            num = int(point.replace("'", ''))
        except ValueError:
            num = ''
        self.pointAx = point[0]
        self.pointAy = point[1]

        # Reset fixStue
        self.mainWin.fixStue = {}

    def updatePointE(self, point):
        self.pointEx = point[0]
        self.pointEy = point[1]

        # Reset fixStue
        self.mainWin.fixStue = {}

    def checkPoint(self, point):
        state = 'yellow'
        if self.mainWin.dhm != {}:
            extent = self.mainWin.dhm['extent']
            [extLx, extHy, extHx, extLy] = extent
            try:
                [x, y] = point
                if extLx <= float(x) <= extHx and extLy <= float(y) <= extHy:
                    state = 'green'
                else:
                    state = 'red'
            except ValueError:
                state = 'yellow'
        return state

    def updateLine(self):
        # Koordinateninformation als float
        self.createQgisPoint()
        self.createDigiFeature()

    def createQgisPoint(self):
        # Start-/Endkoordinaten als QGIS Punkt-Objekte
        self.qgisPointA = QgsPoint(self.pointAx, self.pointAy)
        self.qgisPointE = QgsPoint(self.pointEx, self.pointEy)

    def createDigiFeature(self):
        line = QgsGeometry.fromPolyline([self.qgisPointA, self.qgisPointE])
        self.drawnLine = QgsFeature()
        self.drawnLine.setGeometry(line)

    def makeProfile(self):
        createProf = CreateProfile(self.iface, self.drawnLine,
                                   self.mainWin.dhm['layer'])
        profile = createProf.create()
        return profile

def resetRubberband(self):
        self.rubberband = QgsRubberBand(self.mainWin.canvas, False)