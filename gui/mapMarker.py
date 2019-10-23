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
    sig_createProfile = pyqtSignal()
    sig_changeCoord = pyqtSignal(QgsPointXY, str)

    def __init__(self, canvas, drawLineButton, showProfileButton):
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
        
        # Buttons from main dialog
        self.drawLineButton = drawLineButton
        self.buttonShowProf = showProfileButton

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
        self.canvas.setCursor(self.cursor)

    def deactivate(self):
        self.canvas.setCursor(QCursor(Qt.OpenHandCursor))
        self.linePoints = []
        # Stop pressing down button
        self.drawLineButton.setChecked(False)

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
                self.sig_changeCoord.emit(self.linePoints[0], 'A')
                self.sig_changeCoord.emit(self.linePoints[1], 'E')
                self.canvas.setMapTool(self.savedTool)      # self.deactivate()

    def setCursor(self, cursor):
        self.cursor = cursor

    def updateLine(self, points):
        self.rubberband.setToGeometry(QgsGeometry.fromPolylineXY(points), None)
        self.lineFeature = self.createLineFeature(points)
        self.drawMarker(points[0])
        self.drawMarker(points[1])
    
    def activateSectionLine(self, initPoint):
        rubberbandS = QgsRubberBand(self.canvas)
        rubberbandS.setWidth(3)
        rubberbandS.setColor(QColor(SECTION_COLOR))
        self.lineFeatureS.append(rubberbandS)
        self.linePointsS = [initPoint, None]
    
    def updateSectionLine(self, point):
        self.linePointsS[1] = point
        self.lineFeatureS[-1].setToGeometry(
            QgsGeometry.fromPolylineXY(self.linePointsS), None)
    
    def clearUnfinishedLines(self):
        if len(self.linePointsS) == 1:
            self.lineFeatureS[-1].reset(False)
            self.lineFeatureS[-1].deleteLater()
            self.lineFeatureS.pop(-1)
            self.linePointsS = []

    def drawMarker(self, point):
        marker = QgsPoleMarker(self.canvas)
        marker.setCenter(point)
        self.markers.append(marker)
        self.canvas.refresh()

    def removeMarker(self, position=-1):
        if position >= 0:
            marker = self.markers[position]
            self.canvas.scene().removeItem(marker)
            self.markers.pop(position)
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
        if not self.poleCursor:
            self.poleCursor = QgsMovingCross(self.canvas, color)
        self.poleCursor.setCenter(point)
        self.canvas.refresh()

    @staticmethod
    def createLineFeature(pnts):
        line = QgsGeometry.fromPolylineXY(pnts)
        qgFeat = QgsFeature()
        qgFeat.setGeometry(line)
        return qgFeat


class QgsPoleMarker(QgsVertexMarker):
    def __init__(self, canvas, color=POLE_COLOR):
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
