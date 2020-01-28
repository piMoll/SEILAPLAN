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
from qgis.PyQt.QtCore import Qt, QSize
from qgis.PyQt.QtWidgets import QSizePolicy

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from .plotting_tools import zoom_with_wheel


class AdjustmentPlot(FigureCanvas):
    
    ZOOM_TO_DISTANCE = 20
    
    def __init__(self, parent=None, width=5, height=4, dpi=72):
        self.win = parent
        self.fig = Figure(figsize=(width, height), dpi=dpi, facecolor='#efefef')
        self.axes = self.fig.add_subplot(111)
    
        FigureCanvas.__init__(self, self.fig)
        self.setParent(parent)
        
        self.xdata = None
        self.terrain = None
        self.tPoints = None
        self.peakLoc_x = None
        self.peakLoc_y = None
        self.data_xlow = 0
        self.data_xhi = 0
        self.data_ylow = 0
        self.data_yhi = 0
        self.labelBuffer = 1
        self.arrowMarker = None
        self.arrowLabel = []
        # Reference to navigation toolbar
        self.tbar = None
        
        self.currentPole = None
        self.isZoomed = False

        # Enable zoom with scroll wheel
        zoomFunc = zoom_with_wheel(self, self.axes, zoomScale=1.3)

        self.axes.set_aspect('equal', 'datalim')
        self.setFocusPolicy(Qt.ClickFocus)
        FigureCanvas.setSizePolicy(self, QSizePolicy.Expanding,
                                   QSizePolicy.Expanding)
        self.setMinimumSize(QSize(600, 400))
        FigureCanvas.updateGeometry(self)
        self.fig.tight_layout(pad=0, w_pad=0.1, h_pad=0.1)

    def __setupAxes(self):
        self.axes.ticklabel_format(style='plain', useOffset=False)
        self.axes.tick_params(axis="both", which="major", direction="in",
                              length=5, width=1, bottom=True, top=False,
                              left=True, right=False)
        self.axes.minorticks_on()
        self.axes.tick_params(which="minor", direction="in")
        
    def initData(self, xdata, terrain, peakLocation_x, peakLocation_y,
                 surveyPoints):
        self.xdata = xdata
        self.terrain = terrain
        self.peakLoc_x = peakLocation_x
        self.peakLoc_y = peakLocation_y
        self.data_xlow = np.min(self.xdata)
        self.data_xhi = np.max(self.xdata)
        self.data_ylow = np.min(self.terrain)
        self.data_yhi = np.max(self.terrain) + 25
        self.tPoints = surveyPoints
    
    def setPlotLimits(self):
        if self.isZoomed:
            d = self.currentPole['d']
            z = self.currentPole['z']
            h = self.currentPole['h']
            self.axes.set_xlim(d - AdjustmentPlot.ZOOM_TO_DISTANCE,
                               d + AdjustmentPlot.ZOOM_TO_DISTANCE)
            self.axes.set_ylim(
                (z + 0.5 * h) - AdjustmentPlot.ZOOM_TO_DISTANCE,
                (z + 0.5 * h) + AdjustmentPlot.ZOOM_TO_DISTANCE)
            self.labelBuffer = 0.2

        else:
            self.axes.set_xlim(self.data_xlow, self.data_xhi)
            self.axes.set_ylim(self.data_ylow, self.data_yhi)
            self.labelBuffer = (self.data_yhi - self.data_ylow) / 40
        
    def updatePlot(self, poles, cable, printPdf=False):
        scale = 1
        legendCol = 4
        fontSize = 11
        if printPdf:
            legendCol = 3
            scale = 0.5
            fontSize = 8
        
        # current Zoom
        xlim = self.axes.get_xlim()
        ylim = self.axes.get_ylim()
        
        self.axes.clear()
        self.__setupAxes()
        # Terrain
        self.axes.plot(self.xdata, self.terrain, color='#a1d1ab',
                       linewidth=3.5*scale, zorder=1)
        # Mark survey points when working with CSV height data
        if self.tPoints is not None:
            # Add markers for survey points
            for pointX, pointY, idx in self.tPoints:
                self.axes.plot([pointX, pointX],
                               [pointY, pointY - 6 * self.labelBuffer * scale],
                               color='green', linewidth=1.5 * scale, zorder=2)
                self.axes.text(pointX, pointY - 8 * self.labelBuffer * scale,
                               str(int(idx)), fontsize=fontSize, ha='center',
                               va='top', color='green')
        
        if not printPdf:
            # Well suited locations (peaks) for poles
            self.axes.scatter(self.peakLoc_x, self.peakLoc_y, marker='^',
                              color='#ffaa00', edgecolors='#496b48',
                              label='Günstige\nGeländeform', zorder=3)
        # Cable lines
        self.axes.plot(cable['xaxis'], cable['empty'], color='#4D83B2',
                       linewidth=1.5*scale, label="Leerseil")
        self.axes.plot(cable['xaxis'], cable['load'], color='#FF4D44',
                       linewidth=1.5*scale, label="Lastwegkurve\nnach Zweifel")
        # Anchors
        if cable['anchorA']:
            self.axes.plot(cable['anchorA']['d'], cable['anchorA']['z'],
                           color='#FF4D44', linewidth=1.5*scale)
        if cable['anchorE']:
            self.axes.plot(cable['anchorE']['d'], cable['anchorE']['z'],
                           color='#FF4D44', linewidth=1.5*scale)
        # Ground clearance
        self.axes.plot(cable['groundclear_di'], cable['groundclear'],
                       color='#910000', linewidth=1*scale, linestyle=':',
                       label="Min. Bodenabstand")
        self.axes.plot(cable['groundclear_di'], cable['groundclear_under'],
                       color='#910000', linewidth=1*scale)
            
        # Poles
        [pole_d, pole_z, pole_h, pole_dtop, pole_ztop] = poles
        for i, d in enumerate(pole_d):
            self.axes.plot([pole_d[i], pole_dtop[i]], [pole_z[i], pole_ztop[i]],
                           color='#363432', linewidth=3.0*scale)
        # Vertical guide lines
        if self.isZoomed:
            d = self.currentPole['d']
            z = self.currentPole['z']
            ztop = self.currentPole['ztop']
            self.axes.axvline(lw=1, ls='dotted', color='black', x=d)
            self.axes.axhline(lw=1, ls='dotted', color='black', y=z)
            self.axes.axhline(lw=1, ls='dotted', color='black', y=ztop)
        
        # Data limit of axis
        # self.setPlotLimits()
        # Add labels
        if not printPdf:
            self.placeLabels(pole_dtop, pole_ztop)
        # Legend
        self.axes.legend(loc='lower center', fontsize=fontSize,
                         bbox_to_anchor=(0.5, 0), ncol=legendCol)
        
        self.axes.set_xlim(xlim)
        self.axes.set_ylim(ylim)
        self.draw()
        print(self.axes._get_view())
        # Set new plot extent as home extent (for home button)
        if not printPdf:
            self.tbar.update()
            self.tbar.push_current()
    
    def showMarkers(self, x, y, label):
        # Displays marker for thresholds
        self.removeMarkers()
        y -= self.labelBuffer * 3
        self.arrowMarker = self.axes.scatter(x, y, marker='^', zorder=20,
                                             c='#e06767', s=100)
        # Adds a label underneath marker with threshold value
        self.arrowLabel = []
        for i, txt in enumerate(label):
            self.arrowLabel.append(
                self.axes.text(x[i], y[i] - 2*self.labelBuffer, txt, zorder=30,
                               ha='center', backgroundcolor='white', va='top',
                               color='#e06767'))
        self.draw()
    
    def removeMarkers(self):
        if self.arrowMarker:
            self.arrowMarker.remove()
            [l.remove() for l in self.arrowLabel]
            self.arrowMarker = None
            self.arrowLabel = []
            self.draw()

    def zoomTo(self, pole):
        self.isZoomed = True
        self.currentPole = pole
        self.setPlotLimits()
    
    def zoomOut(self):
        self.isZoomed = False
        self.currentPole = {}
        self.setPlotLimits()
        # Set new plot extent as home extent (for home button)
        self.tbar.update()
        self.tbar.push_current()
    
    def placeLabels(self, xdata, ydata):
        if self.isZoomed:
            d = self.currentPole['d']
            z = self.currentPole['z']
            h = self.currentPole['h']
            ztop = self.currentPole['ztop']
            pos_t_d = self.axes.get_xlim()[0]
            pos_t_z = z + self.labelBuffer
            pox_yp_z = ztop + self.labelBuffer
            pos_h_d = d
            pos_h_z = ztop + self.labelBuffer * 3
    
            self.axes.text(pos_t_d, pos_t_z, f'{round(z, 1)} m', ha='left')
            self.axes.text(pos_t_d, pox_yp_z, f'{round(ztop, 1)} m', ha='left')
            self.axes.text(pos_h_d, pos_h_z, f'{round(h, 1)} m', ha='center')
        else:
            for i in range(len(xdata)):
                self.axes.text(xdata[i], ydata[i] + self.labelBuffer*2,
                               f'{i + 1}', fontsize=12, ha='center')
    
    def printToPdf(self, filelocation, title, poles, dpi=300):
        xlen = 11.69  # 11.69 inch = A4 width
        ylen = 8.27  # 8.27 inch = A4 height
        self.fig.set_size_inches([xlen, ylen])
        self.fig.tight_layout(pad=4, w_pad=1, h_pad=3)
        self.setPlotLimits()
        # Layout plot
        self.axes.set_title(f'Seilaplan Plot  -  {title}', fontsize=10,
                            multialignment='center', y=1.05)
        self.axes.set_xlabel("Horizontaldistanz [m]", fontsize=9)
        self.axes.set_ylabel("Höhe [m.ü.M]", fontsize=9)
        self.axes.tick_params(labelsize=8)
        self.axes.grid(which='major', lw=0.5)
        self.axes.grid(which='minor', lw=0.5, linestyle=':')
        # Label poles
        for pole in poles:
            if pole['poleType'] != 'anchor':
                self.axes.text(pole['dtop'], pole['ztop'] + self.labelBuffer*2,
                               pole['name'], ha='center', fontsize=8)
        self.print_figure(filelocation, dpi)

    def setToolbar(self, tbar):
        self.tbar = tbar
