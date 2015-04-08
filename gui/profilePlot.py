# -*- coding: utf-8 -*-
"""
Nach diesen Beispielen implementiert:
https://github.com/eliben/code-for-blog/blob/master/2009/qt_mpl_bars.py
http://www.technicaljar.com/?p=688
"""

from PyQt4.QtCore import *
import numpy as np

# import matplotlib
# Force matplotlib to not use any Xwindows backend.
# matplotlib.use('Cairo')
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.collections import LineCollection
from ..bo.plotExtent import PlotExtent


class QtMplCanvas(FigureCanvas):
    def __init__(self, interface, profile, profileWin):
        # import pydevd
        # pydevd.settrace('localhost', port=53100,
        #              stdoutToServer=True, stderrToServer=True)
        self.iface = interface
        self.profile = profile
        self.win = profileWin
        self.dpi = 72
        self.fig = Figure(dpi=self.dpi)
        self.fig.set_facecolor([.89,.89,.89])
        self.axes = self.fig.add_subplot(111)
        self.linePoints = []
        self.line_exists = False
        self.noStue = []

        self.pltExt = PlotExtent()
        self.pltExt.union(self.profile.getExtent())
        self.pltExt.expand()
        self.axes.set_xlim(self.pltExt.xmin, self.pltExt.xmax)
        self.axes.set_ylim(self.pltExt.ymin, self.pltExt.ymax)

        pltSegs = self.profile.getPlotSegments()
        self.lineColl = LineCollection(pltSegs, linewidths=2, linestyles='solid',
                                  colors='#E71C23', picker=True, label='LBL')
        self.axes.add_collection(self.lineColl)

        [x_data, y_data] = np.array(pltSegs[0]).T
        self.x_data = x_data
        self.y_data = y_data
        self.yRange = np.max(y_data) - np.min(y_data)
        self.yT = self.yRange * 0.1
        stueH = self.yRange * 0.2
        # Start- und Endstütze einzeichnen
        self.axes.vlines(x_data[[0, -1]], y_data[[0, -1]],
                         y_data[[0, -1]]+stueH, colors='#0101D5', linewidth='2')
        self.xcursor = self.x_data[len(self.x_data)/2]
        self.ycursor = self.y_data[len(self.x_data)/2]
        # Fadenkreuz
        self.lx = self.axes.axhline(lw=2, ls='dashed', y=self.ycursor)
        self.ly = self.axes.axvline(lw=2, ls='dashed', x=self.xcursor)
        # self.horiLine = self.axes.axhline(lw=2, ls='dotted', y=self.ycursor,
        #                                   color='#F4CC13')
        # import pydevd
        # pydevd.settrace('localhost', port=53100,
        #              stdoutToServer=True, stderrToServer=True)
        self.ly.set_visible(False)
        self.lx.set_visible(False)
        # self.horiLine.set_visible(False)

        self.__setupAxes(self.axes)
        FigureCanvas.__init__(self, self.fig)

        self.setFocusPolicy(Qt.ClickFocus)
        self.setFocus()

    def acitvateFadenkreuz(self):
        # Connections
        self.cidMove = self.mpl_connect('motion_notify_event',self.mouse_move)
        self.cidPress = self.mpl_connect('button_press_event',self.mouse_press)
        self.ly.set_color('#4444FF')
        self.lx.set_color('#4444FF')
        self.ly.set_visible(True)
        self.lx.set_visible(True)
        self.win.activateMapMarker(self.xcursor)
        self.fig.canvas.draw()

    def deactivateFadenkreuz(self):
        self.mpl_disconnect(self.cidMove)
        self.mpl_disconnect(self.cidPress)
        self.ly.set_visible(False)
        self.lx.set_visible(False)
        self.fig.canvas.draw()
        self.win.deactivateMapMarker()

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
        self.fig.canvas.draw()
        # Cursor in Karte aktualisieren
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
        self.fig.canvas.draw()
        return scat

    def DeletePoint(self, scatterobjekt):
        scatterobjekt.remove()
        self.fig.canvas.draw()

    def acitvateFadenkreuz2(self):
        # Connections
        self.cidMove2 = self.mpl_connect('motion_notify_event',self.mouse_move2)
        self.cidPress2 = self.mpl_connect('button_press_event',self.mouse_press2)
        self.ly.set_color('#F4CC13')
        self.lx.set_color('#F4CC13')
        self.win.activateMapMarkerLine(1)
        self.ly.set_visible(True)
        self.lx.set_visible(True)
        # self.win.activateMapLine(self.xcursor)
        self.fig.canvas.draw()

    def deactivateFadenkreuz2(self):
        self.mpl_disconnect(self.cidMove2)
        self.mpl_disconnect(self.cidPress2)
        self.ly.set_visible(False)
        self.lx.set_visible(False)
        self.win.deactivateMapMarker()
        self.line_exists = False
        self.linePoints = []
        self.fig.canvas.draw()

    def mouse_move2(self, event):
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
        # Profillinie überzeichnen
        self.win.updateMapMarker(xa)
        if self.line_exists:
            self.win.lineMoved(xa)
        self.fig.canvas.draw()
        # Cursor in Karte aktualisieren
        # self.win.updateMapMarker(xa)

    def mouse_press2(self, event):
        if not event.inaxes:
            return
        x, y = event.xdata, event.ydata
        indx = np.searchsorted(self.x_data, [x])[0]
        xa = self.x_data[indx-1]
        ya = self.y_data[indx-1]

        if len(self.linePoints) == 0:
            # Markierungslinien für Beriche ohne Stützen initialiseren
            self.vLine = self.axes.vlines(xa, ya-self.yT, ya+self.yT, lw=2,
                             color='#F4CC13', label='Start')
            self.linePoints.append(xa)
            self.line_exists = True
            self.win.activateMapLine(xa)
        elif len(self.linePoints) == 1:
            # Linienmarkierung setzten
            self.axes.vlines(xa, ya-self.yT, ya+self.yT, lw=2,
                             color='#F4CC13', label='Ende')
            self.linePoints.append(xa)
            self.win.finishLine(xa)
            self.noStue.append(self.linePoints)
            self.deactivateFadenkreuz2()
        self.fig.canvas.draw()

    def __setupAxes(self, axe1):
        axe1.set_xlabel(u"Horizontaldistanz von Startpunkt aus")
        axe1.set_ylabel(u"Höhe")
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

    def getNoStue(self):
        return self.noStue