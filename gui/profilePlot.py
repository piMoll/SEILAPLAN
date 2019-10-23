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

import numpy as np
from math import floor
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QSizePolicy

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.collections import LineCollection

from .mapMarker import PROFILE_COLOR, POLE_COLOR, SECTION_COLOR


class ProfilePlot(FigureCanvas):
    
    POLE_H = 12.0
    
    def __init__(self, parent=None, width=5, height=4, dpi=72):
        self.win = parent
        self.fig = Figure(figsize=(width, height), dpi=dpi, facecolor='#efefef')
        self.axes = self.fig.add_subplot(111)
        
        FigureCanvas.__init__(self, self.fig)
        self.setParent(parent)
        
        self.linePoints = []
        self.line_exists = False
        self.noStue = []
        self.profileObj = None
        
        # Mouse position
        self.x_data = None
        self.y_data = None
        # Cursor cross position
        self.xcursor = 0
        self.ycursor = 0
        # Cursor cross
        self.lx = None
        self.ly = None
        # Listener for canvas events
        self.cidMove = None
        self.cidPress = None
        self.cidMove2 = None
        self.cidPress2 = None
        self.vLine = None

        self.updateMarkerThread = None
        
        self.axes.set_aspect('equal', 'datalim')
        self.setFocusPolicy(Qt.ClickFocus)
        FigureCanvas.setSizePolicy(self, QSizePolicy.Expanding,
                                   QSizePolicy.Expanding)
        FigureCanvas.updateGeometry(self)
        self.fig.tight_layout(pad=0.2, w_pad=0.1, h_pad=0.1)
        
    def plotData(self, plotData):
        """
        :type plotData: gui.profileCreation.PreviewProfile
        """
        self.axes.clear()
        self.__setupAxes()
        self.profileObj = plotData
        
        # Set plot extent
        self.axes.set_xlim(self.profileObj.xmin, self.profileObj.xmax)
        self.axes.set_ylim(self.profileObj.ymin,
                           self.profileObj.ymax + self.POLE_H)
    
        # Add plot data
        pltSegs = self.profileObj.profile
        lineColl = LineCollection([pltSegs], linewidths=2.5, picker=True,
                                  colors=PROFILE_COLOR, label='LBL')
        self.axes.add_collection(lineColl)
        
        # Data point of profile
        self.x_data = self.profileObj.xaxis
        self.y_data = self.profileObj.yaxis

        # Draw start and end pole
        self.axes.vlines(self.x_data[[0, -1]], self.y_data[[0, -1]],
                         self.y_data[[0, -1]] + self.POLE_H)
        # Label
        self.axes.text(self.x_data[0], self.y_data[0] + self.POLE_H + 4,
                       'A', ha='center', fontsize=12)
        self.axes.text(self.x_data[-1], self.y_data[-1] + self.POLE_H + 4,
                       'E', ha='center', fontsize=12)

        # Init cursor cross position
        self.xcursor = self.x_data[floor(len(self.x_data) / 2)]
        self.ycursor = self.y_data[floor(len(self.x_data) / 2)]
        self.lx = self.axes.axhline(lw=1.5, ls='dashed', y=self.ycursor)
        self.ly = self.axes.axvline(lw=1.5, ls='dashed', x=self.xcursor)
        self.ly.set_visible(False)
        self.lx.set_visible(False)
        
        self.draw()

    def acitvateCrosshairPole(self):
        self.cidMove = self.mpl_connect('motion_notify_event', self.onMouseMoveP)
        self.cidPress = self.mpl_connect('button_press_event', self.onMousePressP)
        self.ly.set_color(POLE_COLOR)
        self.lx.set_color(POLE_COLOR)
        self.ly.set_visible(True)
        self.lx.set_visible(True)
        self.win.activateMapCursor(self.xcursor, POLE_COLOR)
        self.draw()

    def deactivateCrosshairPole(self):
        self.mpl_disconnect(self.cidMove)
        self.mpl_disconnect(self.cidPress)
        self.ly.set_visible(False)
        self.lx.set_visible(False)
        self.draw()

    def onMouseMoveP(self, event):
        if not event.inaxes:
            return
        x, y = event.xdata, event.ydata
        indx = np.argmax(self.x_data >= x)
        if indx == 0:
            # Cursor outside of profile
            return
        xa = self.x_data[indx]
        ya = self.y_data[indx]
        # Update the line positions
        self.lx.set_ydata(ya)
        self.ly.set_xdata(xa)
        self.xcursor = xa
        self.ycursor = ya
        self.draw()
        # Update cursor on map
        self.win.updateMapMarker(xa, POLE_COLOR)

    def onMousePressP(self, event):
        if not event.inaxes:
            return
        self.deactivateCrosshairPole()
        self.win.deactivateMapCursor()
        posX = str(int(self.xcursor))
        posY = str(int(self.ycursor))
        drawnPoint = self.CreatePoint(self.xcursor, self.ycursor)
        self.win.CreateFixStue(posX, posY, drawnPoint)

    def CreatePoint(self, posX, posY):
        scat = self.axes.scatter(posX, posY, zorder=100, c=POLE_COLOR, s=40)
        self.draw()
        return scat

    def DeletePoint(self, point):
        point.remove()
        self.draw()

    def activateCrosshairSection(self):
        """ Cursor cross for defining sections without supports."""
        self.cidMove2 = self.mpl_connect('motion_notify_event', self.onMouseMoveS)
        self.cidPress2 = self.mpl_connect('button_press_event', self.onMousePressS)
        self.ly.set_color(SECTION_COLOR)
        self.lx.set_color(SECTION_COLOR)
        self.win.activateMapCursor(1, SECTION_COLOR)
        self.ly.set_visible(True)
        self.lx.set_visible(True)
        self.draw()

    def deactivateCrosshairSection(self):
        self.mpl_disconnect(self.cidMove2)
        self.mpl_disconnect(self.cidPress2)
        self.ly.set_visible(False)
        self.lx.set_visible(False)
        self.line_exists = False
        self.linePoints = []
        self.draw()

    def onMouseMoveS(self, event):
        if not event.inaxes:
            return
        x, y = event.xdata, event.ydata
        indx = np.argmax(self.x_data >= x)
        if indx == 0:
            # Cursor outside of profile
            return
        xa = self.x_data[indx]
        ya = self.y_data[indx]
        # Update the line positions
        self.lx.set_ydata(ya)
        self.ly.set_xdata(xa)
        self.xcursor = xa
        self.ycursor = ya
        # Overdraw profile line
        self.win.updateMapMarker(xa, SECTION_COLOR)
        if self.line_exists:
            self.win.lineMoved(xa)
        self.draw()

    def onMousePressS(self, event):
        if not event.inaxes:
            return
        x, y = event.xdata, event.ydata
        indx = np.argmax(self.x_data >= x)
        x = self.x_data[indx]
        y = self.y_data[indx]

        if len(self.linePoints) == 0:
            # Initialize marker lines for sections without supports
            self.drawSectionPoint(x, y)
            self.linePoints.append(x)
            self.line_exists = True
            self.win.activateMapLine(x)
        elif len(self.linePoints) == 1:
            # Set line
            self.linePoints.append(x)
            self.drawSectionPoint(x, y)
            self.drawSectionLine()
            self.win.finishLine(x)
            self.noStue.append(self.linePoints)
            self.deactivateCrosshairSection()
        self.draw()
    
    def drawSectionPoint(self, x, y):
        self.vLine = self.axes.vlines(x, y - 4, y + 4, lw=2, color=SECTION_COLOR)
    
    def drawSectionLine(self):
        idxA = np.argmax(self.x_data >= self.linePoints[0])
        idxE = np.argmax(self.x_data > self.linePoints[1])
        self.axes.plot(self.x_data[idxA:idxE], self.y_data[idxA:idxE],
                       linewidth=2, color=SECTION_COLOR)

    def __setupAxes(self):
        self.axes.set_xlabel("Horizontaldistanz [m]", fontsize=11)
        self.axes.set_ylabel("Höhe [M.ü.M]", fontsize=11)
        self.axes.grid(which='major', lw=1)
        self.axes.grid(which='minor', lw=1, linestyle=':')
        self.axes.ticklabel_format(style='plain', useOffset=False)
        self.axes.tick_params(axis="both", which="major", length=5, width=1,
                              bottom=True, top=False, left=True, right=False)
        self.axes.tick_params(axis="both", which="both", direction="in")
        self.axes.minorticks_on()
