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

from qgis.PyQt.QtCore import Qt, pyqtSignal
from qgis.PyQt.QtGui import QCursor, QColor
from qgis.gui import QgsMapTool, QgsRubberBand, QgsVertexMarker
from qgis.core import QgsGeometry, QgsFeature, QgsPointXY


# Colors
CURSOR_COLOR = '#00000'
PROFILE_COLOR = '#de0d15'
POLE_COLOR = '#0055ff'
SECTION_COLOR = '#ff9900'


class MapMarkerTool(QgsMapTool):
    
    # Signals
    sig_lineFinished = pyqtSignal(list)

    def __init__(self, canvas):
        QgsMapTool.__init__(self, canvas)
        self.canvas = canvas
        
        # Cross hair when drawing profile line
        self.cursor = QCursor(Qt.CrossCursor)
        # Cross hair when creating new fixed poles in profile window
        self.poleCursor = None

        # Red line for profile drawing
        self.rubberband = QgsRubberBand(self.canvas)
        self.rubberband.setWidth(3)
        self.rubberband.setColor(QColor(PROFILE_COLOR))

        # Coordinates of drawn line points
        self.linePoints = []
        # Drawn line geometry
        self.lineFeature = None
        # Point markers for poles
        self.markers = []

        # Line for section marking (sections without poles)
        self.linePointsS = []
        self.lineFeatureS = []

        # Temporary save double clicks
        self.dblclktemp = None
        
        # Backup the last active Tool before the profile tool became active
        self.savedTool = self.canvas.mapTool()

    def drawLine(self):
        self.reset()
        self.canvas.setMapTool(self)        # runs function self.activate()

    def activate(self):
        self.removeMarker()
        self.canvas.setCursor(self.cursor)

    def deactivate(self):
        self.canvas.setCursor(QCursor(Qt.OpenHandCursor))
        self.linePoints = []

    def reset(self):
        self.removeMarker()
        self.canvas.setMapTool(self.savedTool)
        self.rubberband.reset()
        self.linePoints = []
        self.dblclktemp = None
        self.lineFeature = None
        for line in self.lineFeatureS:
            line.reset()
            line.deleteLater()
        self.lineFeatureS = []
        self.deactivateCursor()

    def canvasMoveEvent(self, event):
        if len(self.linePoints) > 0:
            self.rubberband.reset()
            line = [self.linePoints[0], event.mapPoint()]
            self.rubberband.setToGeometry(QgsGeometry.fromPolylineXY(line), None)

    def canvasReleaseEvent(self, event):
        mapPos = event.mapPoint()
        if mapPos == self.dblclktemp:
            self.dblclktemp = None
            return
        else:
            # Mark point with marker symbol
            self.drawMarker(mapPos)
            
            # Click ist first point of line
            if len(self.linePoints) == 0:
                self.rubberband.reset()
                self.linePoints.append(mapPos)
            
            # Click is second point of line
            elif len(self.linePoints) == 1:
                self.linePoints.append(mapPos)
                # self.removePoleMarker()
                self.dblclktemp = mapPos
                self.lineFeature = self.createLineFeature(self.linePoints)
                self.sig_lineFinished.emit(self.linePoints)
                self.canvas.setMapTool(self.savedTool)      # self.deactivate()

    def updateLine(self, points, drawMarker=True):
        qgsPoints = [self.convertToQgsPoint(p) for p in points]
        self.rubberband.setToGeometry(QgsGeometry.fromPolylineXY(qgsPoints), None)
        self.lineFeature = self.createLineFeature(qgsPoints)
        if drawMarker:
            self.drawMarker(qgsPoints[0])
            self.drawMarker(qgsPoints[1])
    
    def activateSectionLine(self, initPoint):
        qgsPoint = self.convertToQgsPoint(initPoint)
        rubberbandS = QgsRubberBand(self.canvas)
        rubberbandS.setWidth(3)
        rubberbandS.setColor(QColor(SECTION_COLOR))
        self.lineFeatureS.append(rubberbandS)
        self.linePointsS = [qgsPoint, None]
    
    def updateSectionLine(self, point):
        qgsPoint = self.convertToQgsPoint(point)
        self.linePointsS[1] = qgsPoint
        self.lineFeatureS[-1].setToGeometry(
            QgsGeometry.fromPolylineXY(self.linePointsS), None)
    
    def deleteSectionLines(self):
        for line in self.lineFeatureS:
            line.reset(False)
            line.deleteLater()
            self.linePoints = []
        self.lineFeatureS = []
    
    def clearUnfinishedLines(self):
        if len(self.linePointsS) == 1:
            self.lineFeatureS[-1].reset(False)
            self.lineFeatureS[-1].deleteLater()
            self.lineFeatureS.pop(-1)
            self.linePointsS = []

    def drawMarker(self, point, idx=None, color=POLE_COLOR):
        qgsPoint = self.convertToQgsPoint(point)
        marker = QgsPoleMarker(self.canvas, color)
        marker.setCenter(qgsPoint)
        if not idx:
            self.markers.append(marker)
        else:
            self.markers.insert(idx, marker)
        self.canvas.refresh()
    
    def updateMarker(self, point, idx):
        qgsPoint = self.convertToQgsPoint(point)
        self.markers[idx].setCenter(qgsPoint)
        self.canvas.refresh()

    def removeMarker(self, idx=-1):
        if idx >= 0:
            marker = self.markers[idx]
            self.canvas.scene().removeItem(marker)
            self.markers.pop(idx)
        else:
            for marker in self.markers:
                self.canvas.scene().removeItem(marker)
            self.markers = []
        self.canvas.refresh()
    
    def deactivateCursor(self):
        if self.poleCursor:
            self.canvas.scene().removeItem(self.poleCursor)
        self.poleCursor = None
    
    def updateCursor(self, point, color=POLE_COLOR):
        qgsPoint = self.convertToQgsPoint(point)
        if not self.poleCursor:
            self.poleCursor = QgsMovingCross(self.canvas, color)
        self.poleCursor.setCenter(qgsPoint)
        self.canvas.refresh()

    @staticmethod
    def createLineFeature(pnts):
        line = QgsGeometry.fromPolylineXY(pnts)
        qgFeat = QgsFeature()
        qgFeat.setGeometry(line)
        return qgFeat
    
    @staticmethod
    def convertToQgsPoint(point):
        qgsPoint = None
        if isinstance(point, QgsPointXY):
            qgsPoint = point
        elif isinstance(point, list):
            qgsPoint = QgsPointXY(point[0], point[1])
        return qgsPoint


class QgsPoleMarker(QgsVertexMarker):
    def __init__(self, canvas, color):
        QgsVertexMarker.__init__(self, canvas)
        self.setColor(QColor(color))
        self.setIconType(QgsVertexMarker.ICON_BOX)
        self.setIconSize(11)
        self.setPenWidth(3)


class QgsMovingCross(QgsVertexMarker):
    def __init__(self, canvas, color=CURSOR_COLOR):
        QgsVertexMarker.__init__(self, canvas)
        self.setColor(QColor(color))
        self.setIconType(QgsVertexMarker.ICON_CROSS)
        self.setIconSize(20)
        self.setPenWidth(3)
