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
from qgis.PyQt.QtCore import Qt, QSize, QCoreApplication
from qgis.PyQt.QtWidgets import QSizePolicy

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.collections import LineCollection

from .mapMarker import PROFILE_COLOR, POLE_COLOR, SECTION_COLOR
from .plotting_tools import zoom_with_wheel


class ProfilePlot(FigureCanvas):
    
    def __init__(self, parent=None, width=10, height=4, dpi=72):
        self.win = parent
        self.fig = Figure(figsize=(width, height), dpi=dpi, facecolor='#efefef')
        self.axes = self.fig.add_subplot(111)
        
        FigureCanvas.__init__(self, self.fig)
        self.setParent(parent)
        
        self.linePoints = []
        self.line_exists = False
        self.profile = None
        self.labelScale = None
        # Reference to toolbar
        self.tbar = None
        
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
        self.evtMovePole = None
        self.evtPressPole = None
        self.evtMoveSection = None
        self.evtPressSection = None
        
        # Enable zoom with scroll wheel
        zoomFunc = zoom_with_wheel(self, self.axes, zoomScale=1.3)
        
        self.axes.set_aspect('equal', 'datalim')
        self.setFocusPolicy(Qt.ClickFocus)
        FigureCanvas.setSizePolicy(self, QSizePolicy.Expanding,
                                   QSizePolicy.Expanding)
        self.setMinimumSize(QSize(600, 400))
        FigureCanvas.updateGeometry(self)
        
        # Fit plot tightly into window
        self.fig.tight_layout(pad=0.2, w_pad=0.1, h_pad=0.1)
        
    def plotData(self, plotData):
        """
        :type plotData: tool.profile.Profile
        """
        self.axes.clear()
        self.__setupAxes()
        self.profile = plotData
        
        # Set plot extent
        xmin = np.min(self.profile.di_disp)
        ymin = np.min(self.profile.zi_disp)
        xmax = np.max(self.profile.di_disp)
        ymax = np.max(self.profile.zi_disp)
        self.labelScale = 1
        # Data point of profile
        self.x_data = self.profile.di
        self.y_data = self.profile.zi
    
        # Add plot data (whole profile)
        pltSegs = np.column_stack([self.profile.di_disp, self.profile.zi_disp])
        pltSegs = tuple(map(tuple, pltSegs))
        lineColl = LineCollection([pltSegs], linewidths=1, colors='green')
        self.axes.add_collection(lineColl)
        # Add profile section between A and E
        pltSegsAE = np.column_stack([self.x_data, self.y_data])
        pltSegsAE = tuple(map(tuple, pltSegsAE))
        lineCollAE = LineCollection([pltSegsAE], linewidths=2.5, picker=True,
                                  colors=PROFILE_COLOR, label='LBL')
        self.axes.add_collection(lineCollAE)

        # Draw start and end
        self.axes.scatter(self.x_data[[0, -1]], self.y_data[[0, -1]],
                          zorder=100, c=POLE_COLOR, s=80, marker='o')
        # Label
        self.axes.text(self.x_data[0], self.y_data[0] + self.labelScale,
                       'A',  ha='center', fontsize=12)
        self.axes.text(self.x_data[-1], self.y_data[-1] + self.labelScale,
                       'E', ha='center', fontsize=12)
        
        if self.profile.surveyPnts is not None:
            # Add markers for survey points
            for pointX, pointY, idx, notes in zip(self.profile.surveyPnts['d'],
                                                  self.profile.surveyPnts['z'],
                                                  self.profile.surveyPnts['nr'],
                                                  self.profile.surveyPnts['notes']):
                self.axes.plot([pointX, pointX],
                               [pointY, pointY - 5 * self.labelScale],
                               color='green', linewidth=1.5)
                labelText = f"{idx}"
                rot = 0
                ha = 'center'
                va = 'top'
                if notes:
                    labelText = f"{idx}{':' if notes else ''} {notes if len(notes) <= 25 else notes[:22] + '...'}"
                    # For less placement issues, labels are rotated 45°
                    rot = 55
                    ha = 'right'
                    va = 'center'
                    # Label rotation is switched if profile line inclines
                    if self.y_data[0] < self.y_data[-1]:
                        rot = 305
                        ha = 'left'
                self.axes.text(pointX, pointY - 6 * self.labelScale,
                               labelText, ha=ha, va=va, fontsize=12, color='green',
                               rotation=rot, rotation_mode='anchor')

        # Init cursor cross position
        self.xcursor = self.x_data[floor(len(self.x_data) / 2)]
        self.ycursor = self.y_data[floor(len(self.x_data) / 2)]
        self.lx = self.axes.axhline(lw=1.5, ls='dashed', y=self.ycursor)
        self.ly = self.axes.axvline(lw=1.5, ls='dashed', x=self.xcursor)
        self.ly.set_visible(False)
        self.lx.set_visible(False)
        
        self.axes.set_xlim(xmin - 2 * self.labelScale, xmax + 2 * self.labelScale)
        self.axes.set_ylim(ymin - 2 * self.labelScale, ymax + 2 * self.labelScale)
        
        self.draw()
        # Set new plot extent as home extent (for home button)
        self.tbar.update()
        self.tbar.push_current()

    def acitvateCrosshairPole(self):
        self.evtMovePole = self.mpl_connect('motion_notify_event', self.onMouseMoveP)
        self.evtPressPole = self.mpl_connect('button_press_event', self.onMousePressP)
        self.ly.set_color(POLE_COLOR)
        self.lx.set_color(POLE_COLOR)
        self.ly.set_visible(True)
        self.lx.set_visible(True)
        self.win.activateMapCursor(self.xcursor, POLE_COLOR)
        self.draw()

    def deactivateCrosshairPole(self):
        self.mpl_disconnect(self.evtMovePole)
        self.mpl_disconnect(self.evtPressPole)
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
        self.lx.set_ydata([ya])
        self.ly.set_xdata([xa])
        self.xcursor = xa
        self.ycursor = ya
        self.draw()
        # Update cursor on map
        self.win.updateMapCursor(xa, POLE_COLOR)

    def onMousePressP(self, event):
        if not event.inaxes:
            return
        self.deactivateCrosshairPole()
        self.win.deactivateMapCursor()
        posX = int(round(self.xcursor, 0))
        # z Value will be derived from x value
        self.win.addPole(posX, None)

    def createPoint(self, posX, posY):
        scat = self.axes.scatter(posX, posY, zorder=100, c=POLE_COLOR, s=80,
                                 marker='s')
        self.draw()
        return scat

    def deletePoint(self, point):
        point.remove()
        self.draw()

    def activateCrosshairSection(self):
        """ Cursor cross for defining sections without supports."""
        self.evtMoveSection = self.mpl_connect('motion_notify_event', self.onMouseMoveS)
        self.evtPressSection = self.mpl_connect('button_press_event', self.onMousePressS)
        self.ly.set_color(SECTION_COLOR)
        self.lx.set_color(SECTION_COLOR)
        self.win.activateMapCursor(1, SECTION_COLOR)
        self.ly.set_visible(True)
        self.lx.set_visible(True)
        self.draw()

    def deactivateCrosshairSection(self):
        self.mpl_disconnect(self.evtMoveSection)
        self.mpl_disconnect(self.evtPressSection)
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
        self.lx.set_ydata([ya])
        self.ly.set_xdata([xa])
        self.xcursor = xa
        self.ycursor = ya
        # Overdraw profile line
        self.win.updateMapCursor(xa, SECTION_COLOR)
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
            self.drawSection(x, y)
            self.line_exists = True
            self.win.activateMapLine(x)
        elif len(self.linePoints) == 1:
            # Set line
            self.drawSection(x, y)
            self.win.finishLine(x)
            self.deactivateCrosshairSection()
        self.draw()
    
    def drawSection(self, x, y):
        self.linePoints.append([x, y])
        self.axes.vlines(x, y - self.labelScale, y + self.labelScale, lw=2,
                         color=SECTION_COLOR)
        if len(self.linePoints) == 2:
            idxA = np.argmax(self.x_data >= self.linePoints[0][0])
            idxE = np.argmax(self.x_data > self.linePoints[1][0])
            self.axes.plot(self.x_data[idxA:idxE], self.y_data[idxA:idxE],
                           linewidth=2, color=SECTION_COLOR)
            self.linePoints = []

    def __setupAxes(self):
        self.axes.set_xlabel(self.tr("Horizontaldistanz [m]"), fontsize=11)
        self.axes.set_ylabel(self.tr("Hoehe [m.ue.M]"), fontsize=11)
        self.axes.grid(which='major', lw=1)
        self.axes.grid(which='minor', lw=1, linestyle=':')
        self.axes.ticklabel_format(style='plain', useOffset=False)
        self.axes.tick_params(axis="both", which="major", length=5, width=1,
                              bottom=True, top=False, left=True, right=False)
        self.axes.tick_params(axis="both", which="both", direction="in")
        self.axes.minorticks_on()
    
    def setToolbar(self, tbar):
        self.tbar = tbar
    
    def reset(self):
        self.axes.clear()
    
    # noinspection PyMethodMayBeStati
    def tr(self, message, **kwargs):
        """Get the translation for a string using Qt translation API.
        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString

        Parameters
        ----------
        **kwargs
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate(type(self).__name__, message)
