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
from qgis.PyQt.QtCore import Qt

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.patheffects as PathEffects
from matplotlib.font_manager import FontProperties


p = 21

class AdjustmentPlot(FigureCanvas):
    ZOOM_TO_DISTANCE = 20
    
    def __init__(self, parent=None, width=5, height=4, dpi=72):
        self.win = parent
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = self.fig.add_subplot(111)
    
        FigureCanvas.__init__(self, self.fig)
        self.setParent(parent)
        
        self.xdata = None
        self.terrain = None
        self.data_xlow = 0
        self.data_xhi = 0
        self.data_ylow = 0
        self.data_yhi = 0
        self.labelBuffer = 1
        
        self.currentPole = None
        self.isZoomed = False

        self.axes.set_aspect(2, None, 'SW')
        self.__setupAxes(self.axes)
        self.setFocusPolicy(Qt.ClickFocus)
        self.fig.tight_layout(pad=0, w_pad=0.1, h_pad=0.1)

    @staticmethod
    def __setupAxes(axe):
        # axe.set_xlabel("Horizontaldistanz von Startpunkt aus", fontsize=10)
        # axe.set_ylabel("Höhe", verticalalignment='top', fontsize=10,
        #                horizontalalignment='right', labelpad=20)
        axe.set_aspect('equal', 'datalim')
        axe.ticklabel_format(style='plain', useOffset=False)
        axe.tick_params(axis="both", which="major", direction="out",
                        length=5, width=1, bottom=True, top=False,
                        left=True, right=False)
        axe.minorticks_on()
        axe.tick_params(axis="both", which="minor", direction="out", length=5,
                        width=1, bottom=True, top=False, left=True,
                        right=False)
        # TODO: Legend
        
    def initData(self, xdata, terrain):
        self.xdata = xdata
        self.terrain = terrain
        self.data_xlow = np.min(self.xdata)
        self.data_xhi = np.max(self.xdata)
        self.data_ylow = np.min(self.terrain)
        self.data_yhi = np.max(self.terrain) + 25
    
    def setPlotLimits(self):
        if self.isZoomed:
            x = self.currentPole['x']
            y = self.currentPole['y']
            h = self.currentPole['h']
            self.axes.set_xlim(x - AdjustmentPlot.ZOOM_TO_DISTANCE,
                               x + AdjustmentPlot.ZOOM_TO_DISTANCE)
            self.axes.set_ylim(
                (y + 0.5 * h) - AdjustmentPlot.ZOOM_TO_DISTANCE,
                (y + 0.5 * h) + AdjustmentPlot.ZOOM_TO_DISTANCE)
            self.labelBuffer = 0.2

        else:
            self.axes.set_xlim(self.data_xlow, self.data_xhi)
            self.axes.set_ylim(self.data_ylow, self.data_yhi)
            self.labelBuffer = (self.data_yhi - self.data_ylow) / 40
        
    def updatePlot(self, poles, cable):
        self.axes.clear()
        # Terrain
        self.axes.plot(self.xdata, self.terrain, color='#a1d1ab', linewidth=3.5)
        # Cable lines
        self.axes.plot(cable['xaxis'], cable['empty'], color='#4D83B2',
                       linewidth=1.5, label="Leerseil")
        self.axes.plot(cable['xaxis'], cable['load'], color='#FF4D44',
                       linewidth=1.5, label="Lastwegkurve nach Zweifel")
        # Poles
        [pole_x, pole_y, _, pole_yh] = poles
        self.axes.vlines(pole_x, pole_y, pole_yh,
                         colors='#363432', linewidth=3.0)
        # Vertical guide lines
        if self.isZoomed:
            x = self.currentPole['x']
            y = self.currentPole['y']
            yh = self.currentPole['yh']
            self.axes.axvline(lw=1, ls='dotted', color='black', x=x)
            self.axes.axhline(lw=1, ls='dotted', color='black', y=y)
            self.axes.axhline(lw=1, ls='dotted', color='black', y=yh)
        
        # Data limit of axis
        self.setPlotLimits()
        # Add labels
        self.placeLabels(pole_x, pole_yh)

        self.draw()

    def zoomTo(self, pole):
        self.isZoomed = True
        self.currentPole = {
            'x': pole['dist'],
            'y': pole['terrain'],
            'h': pole['height'],
            'yh': pole['terrain'] + pole['height']
        }
        self.setPlotLimits()
    
    def zoomOut(self):
        self.isZoomed = False
        self.currentPole = {}
        self.setPlotLimits()
    
    def placeLabels(self, xdata, ydata):
        if self.isZoomed:
            x = self.currentPole['x']
            y = self.currentPole['y']
            h = self.currentPole['h']
            yh = self.currentPole['yh']
            pos_t_x = self.axes.get_xlim()[0]
            pos_t_y = y + self.labelBuffer
            pox_yp_y = yh + self.labelBuffer
            pos_h_x = x
            pos_h_y = yh + self.labelBuffer * 3
    
            self.axes.text(pos_t_x, pos_t_y, f'{round(y, 1)} m', ha='left')
            self.axes.text(pos_t_x, pox_yp_y, f'{round(yh, 1)} m', ha='left')
            self.axes.text(pos_h_x, pos_h_y, f'{round(h, 1)} m', ha='center')
        else:
            for i in range(len(xdata)):
                self.axes.text(xdata[i], ydata[i] + self.labelBuffer, f'{i + 1}',
                               fontsize=12, ha='center')
