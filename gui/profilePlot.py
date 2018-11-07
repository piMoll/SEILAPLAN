# -*- coding: utf-8 -*-
"""
/***************************************************************************
 SeilaplanPlugin
                                 A QGIS plugin
 Seilkran-Layoutplaner
                              -------------------
        begin                : 2013
        copyright            : (C) 2015 by ETH Zürich
        email                : pi1402@gmail.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/

 Code is based on these two examples:
 https://github.com/eliben/code-for-blog/blob/master/2009/qt_mpl_bars.py
 http://www.technicaljar.com/?p=688
"""

import numpy as np
from qgis.PyQt.QtCore import Qt
from math import floor

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.collections import LineCollection
from ..bo.plotExtent import PlotExtent


class QtMplCanvas(FigureCanvas):
    def __init__(self, parent=None, width=5, height=4, dpi=72):
        # self.iface = interface
        self.win = parent
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = self.fig.add_subplot(111)
        
        FigureCanvas.__init__(self, self.fig)
        self.setParent(parent)
        
        self.fig.set_facecolor([.89,.89,.89])
        
        self.linePoints = []
        self.line_exists = False
        self.noStue = []

        self.pltExt = PlotExtent()
        # Mouse position
        self.x_data = None
        self.y_data = None
        self.yT = None
        # Cursor cross position
        self.xcursor = 0
        self.ycursor = 0
        # Cursor cross
        self.lx = 0
        self.ly = 0
        self.lx = self.axes.axhline(lw=2, ls='dashed', y=self.ycursor)
        self.ly = self.axes.axvline(lw=2, ls='dashed', x=self.xcursor)
        self.ly.set_visible(False)
        self.lx.set_visible(False)

        # Listener for canvas events
        self.cidMove = None
        self.cidPress = None
        self.cidMove2 = None
        self.cidPress2 = None
        self.vLine = None

        self.updateMarkerThread = None
        
        self.axes.set_aspect(2, None, 'SW')
        
        self.__setupAxes(self.axes)
        self.setFocusPolicy(Qt.ClickFocus)
        # self.setFocus()
        
        
    def plotData(self, plotData):
        # Set plot extent
        self.pltExt.union(plotData.getExtent())
        self.pltExt.expand()
        self.axes.set_xlim(self.pltExt.xmin, self.pltExt.xmax)
        self.axes.set_ylim(self.pltExt.ymin, self.pltExt.ymax)
    
        # Add plot data
        pltSegs = plotData.getPlotSegments()
        lineColl = LineCollection(pltSegs, linewidths=2, linestyles='solid',
                                  colors='#E71C23', picker=True, label='LBL')
        self.axes.add_collection(lineColl)
        
        # Data points
        [x_data, y_data] = np.array(pltSegs[0]).T
        self.x_data = x_data
        self.y_data = y_data
    
        # Calculate length of markers
        yRange = np.max(y_data) - np.min(y_data)
        self.yT = yRange * 0.1
        stueH = yRange * 0.2

        # Draw start and end point
        self.axes.vlines(x_data[[0, -1]], y_data[[0, -1]],
                         y_data[[0, -1]] + stueH) #, colors='k', linewidth='2')

        # Init cursor cross position
        self.xcursor = self.x_data[floor(len(self.x_data) / 2)]
        self.ycursor = self.y_data[floor(len(self.x_data) / 2)]
        
        self.draw()
        

    def acitvateFadenkreuz(self):
        self.cidMove = self.mpl_connect('motion_notify_event',self.mouse_move)
        self.cidPress = self.mpl_connect('button_press_event',self.mouse_press)
        self.ly.set_color('#4444FF')
        self.lx.set_color('#4444FF')
        self.ly.set_visible(True)
        self.lx.set_visible(True)
        self.win.activateMapMarker(self.xcursor)
        self.draw()

    def deactivateFadenkreuz(self):
        self.mpl_disconnect(self.cidMove)
        self.mpl_disconnect(self.cidPress)
        self.ly.set_visible(False)
        self.lx.set_visible(False)
        self.draw()
        self.win.deactivateMapMarker()

    # TODO: Dies könnte eine Alternative zu searchsorted sein, evtl. schneller?
    @staticmethod
    def find_nearest(array, value):
        idx = (np.abs(array - value)).argmin()
        return array[idx]

    def mouse_move(self, event):
        if not event.inaxes:
            return
        x, y = event.xdata, event.ydata

        indx = np.searchsorted(self.x_data, [x])[0]
        xa = self.x_data[indx-1]
        ya = self.y_data[indx-1]
        # update the line positions
        self.lx.set_ydata(ya)
        self.ly.set_xdata(xa)
        self.xcursor = xa
        self.ycursor = ya
        self.draw()
        # Update cursor on map
        self.win.updateMapMarker(xa)

    def mouse_press(self, event):
        if not event.inaxes:
            return
        self.deactivateFadenkreuz()
        posX = str(int(self.xcursor))
        posY = str(int(self.ycursor))
        drawnPoint = self.CreatePoint(self.xcursor, self.ycursor)
        self.win.CreateFixStue(posX, posY, drawnPoint)

    def CreatePoint(self, posX, posY):
        scat = self.axes.scatter(posX, posY, zorder=100, c='#0101D5', s=40)
        self.draw()
        return scat

    def DeletePoint(self, scatterobjekt):
        scatterobjekt.remove()
        self.draw()

    def acitvateFadenkreuz2(self):
        """ Cursor cross for defining sections without supports.
        """
        self.cidMove2 = self.mpl_connect('motion_notify_event',self.mouse_move2)
        self.cidPress2 = self.mpl_connect('button_press_event',self.mouse_press2)
        self.ly.set_color('#F4CC13')
        self.lx.set_color('#F4CC13')
        self.win.activateMapMarkerLine(1)
        self.ly.set_visible(True)
        self.lx.set_visible(True)
        self.draw()

    def deactivateFadenkreuz2(self):
        self.mpl_disconnect(self.cidMove2)
        self.mpl_disconnect(self.cidPress2)
        self.ly.set_visible(False)
        self.lx.set_visible(False)
        self.win.deactivateMapMarker()
        self.line_exists = False
        self.linePoints = []
        self.draw()

    def mouse_move2(self, event):
        if not event.inaxes:
            return
        x, y = event.xdata, event.ydata

        indx = np.searchsorted(self.x_data, [x])[0]
        xa = self.x_data[indx-1]
        ya = self.y_data[indx-1]
        # Update the line positions
        self.lx.set_ydata(ya)
        self.ly.set_xdata(xa)
        self.xcursor = xa
        self.ycursor = ya
        # Overdraw profile line
        self.win.updateMapMarker(xa)
        if self.line_exists:
            self.win.lineMoved(xa)
        self.draw()

    def mouse_press2(self, event):
        if not event.inaxes:
            return
        x, y = event.xdata, event.ydata
        indx = np.searchsorted(self.x_data, [x])[0]
        xa = self.x_data[indx-1]
        ya = self.y_data[indx-1]

        if len(self.linePoints) == 0:
            # Initialize marker lines for sections without supports
            self.vLine = self.axes.vlines(xa, ya-self.yT, ya+self.yT, lw=2,
                             color='#F4CC13', label='Start')
            self.linePoints.append(xa)
            self.line_exists = True
            self.win.activateMapLine(xa)
        elif len(self.linePoints) == 1:
            # Set line
            self.axes.vlines(xa, ya-self.yT, ya+self.yT, lw=2,
                             color='#F4CC13', label='Ende')
            self.linePoints.append(xa)
            self.win.finishLine(xa)
            self.noStue.append(self.linePoints)
            self.deactivateFadenkreuz2()
        self.draw()

    @staticmethod
    def __setupAxes(axe1):
        axe1.set_xlabel("Horizontaldistanz von Startpunkt aus")
        axe1.set_ylabel("Höhe")
        axe1.grid()
        axe1.set_aspect('equal', 'datalim')
        axe1.ticklabel_format(style='plain', useOffset=False)
        axe1.tick_params(axis="both", which="major", direction="out",
                         length=5,  width=1, bottom=True, top=False,
                         left=True, right=False )
        axe1.minorticks_on()
        axe1.tick_params(axis="both", which="minor", direction="out", length=5,
                         width=1, bottom=True, top=False, left=True,
                         right=False)
