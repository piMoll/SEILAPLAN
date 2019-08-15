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
from qgis.PyQt.QtCore import Qt, pyqtSignal
from qgis.PyQt.QtGui import QCursor, QColor
from qgis.gui import QgsMapTool, QgsRubberBand
from qgis.core import QgsGeometry, QgsFeature, QgsPointXY
# GUI helper modules for functionality
from .guiHelperFunctions import QgsStueMarker

class ProfiletoolMapTool(QgsMapTool):
    
    # Signals
    sig_clearMap = pyqtSignal()
    sig_createProfile = pyqtSignal()
    sig_changeCoord = pyqtSignal(QgsPointXY, str)


    def __init__(self, canvas, drawLineButton, showProfileButton): #buttonShowProf
        QgsMapTool.__init__(self, canvas)
        self.canvas = canvas
        
        self.cursor = QCursor(Qt.CrossCursor)

        # Red line
        self.rubberband = QgsRubberBand(self.canvas)
        self.rubberband.setWidth(3)
        self.rubberband.setColor(QColor(231, 28, 35))
    
        # Buttons from main dialog
        self.drawLineButton = drawLineButton
        self.buttonShowProf = showProfileButton

        # Coordinates of drawn line points
        self.pointsToDraw = []
        # Temporary save double clicks
        self.dblclktemp = None
        # Drawn line geometry
        self.drawnLine = None
        # Point markers on each end of the line
        self.markers = []
        
        # Backup the last active Tool before the pofile tool became active
        self.savedTool = self.canvas.mapTool()


    def drawLine(self):
        # Emit signal that clears map and deletes profile
        self.sig_clearMap.emit()
        self.reset()
        self.canvas.setMapTool(self)        # runs function self.activate()


    def activate(self):
        self.canvas.setCursor(self.cursor)


    def deactivate(self):
        self.canvas.setCursor(QCursor(Qt.OpenHandCursor))
        self.pointsToDraw = []
        # Stop pressing down button
        self.drawLineButton.setChecked(False)


    def reset(self):
        self.removeStueMarker()
        self.canvas.setMapTool(self.savedTool)
        self.rubberband.reset()
        self.pointsToDraw = []
        self.dblclktemp = None
        self.drawnLine = None
        
        
    def canvasMoveEvent(self, event):
        if len(self.pointsToDraw) > 0:
            self.rubberband.reset()
            line = [self.pointsToDraw[0], event.mapPoint()]
            self.rubberband.setToGeometry(QgsGeometry.fromPolylineXY(line), None)
 

    def canvasReleaseEvent(self, event):
        mapPos = event.mapPoint()
        if mapPos == self.dblclktemp:
            self.dblclktemp = None
            return
        else:
            # Mark point with marker symbol
            self.drawStueMarker(mapPos)
            
            # Klick ist first point of line
            if len(self.pointsToDraw) == 0:
                self.rubberband.reset()
                self.pointsToDraw.append(mapPos)
                return
            
            # Klick is second point of line
            elif len(self.pointsToDraw) == 1:
                self.pointsToDraw.append(mapPos)
                self.removeStueMarker()
                self.dblclktemp = mapPos
                self.drawnLine = self.createDigiFeature(self.pointsToDraw)
                self.sig_changeCoord.emit(self.pointsToDraw[0], 'A')
                self.sig_changeCoord.emit(self.pointsToDraw[1], 'E')
                self.canvas.setMapTool(self.savedTool)      # self.deactivate()


    def setCursor(self, cursor):
        self.cursor = cursor


    def updateLine(self, points):
        self.rubberband.setToGeometry(QgsGeometry.fromPolylineXY(points), None)
        self.drawnLine = self.createDigiFeature(points)
        self.drawStueMarker(points[0])
        self.drawStueMarker(points[1])


    def drawStueMarker(self, point):
        marker = QgsStueMarker(self.canvas)
        marker.setCenter(point)
        self.markers.append(marker)
        self.canvas.refresh()


    def removeStueMarker(self, position=-1):
        if position >= 0:
            marker = self.markers[position]
            self.canvas.scene().removeItem(marker)
            self.markers.pop(position)
        else:
            for marker in self.markers:
                self.canvas.scene().removeItem(marker)
            self.markers = []
        self.canvas.refresh()


    @staticmethod
    def createDigiFeature(pnts):
        line = QgsGeometry.fromPolylineXY(pnts)
        qgFeat = QgsFeature()
        qgFeat.setGeometry(line)
        return qgFeat