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
    def __init__(self, parent=None, width=5, height=4, dpi=72):
        # self.iface = interface
        self.win = parent
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = self.fig.add_subplot(111)
    
        FigureCanvas.__init__(self, self.fig)
        self.setParent(parent)
        # self.fig.set_facecolor([.89, .89, .89])

        # Mouse position
        self.x_data = None
        self.y_data = None
        self.data_xlow = 0
        self.data_xhi = 0
        self.data_ylow = 0
        self.data_yhi = 0
        self.yT = None

        # Zoom View
        self.isZoomed = False
        self.zoom_vline = self.axes.axvline(lw=1, ls='dotted', color='black', x=0)
        self.zoom_hline_low = self.axes.axhline(lw=1, ls='dotted', color='black', y=0)
        self.zoom_hline_high = self.axes.axhline(lw=1, ls='dotted', color='black', y=0)
        # self.zoom_hline = self.axes.axhline(lw=1, ls='dotted', y=self.zoom_yhigh)

        self.zoom_vline.set_visible(False)
        self.zoom_hline_low.set_visible(False)
        self.zoom_hline_high.set_visible(False)

        self.axes.set_aspect(2, None, 'SW')
        self.__setupAxes(self.axes)
        self.setFocusPolicy(Qt.ClickFocus)
        # self.setFocus()

    def plotData(self, plotData):
        [disp_data, di, seilDaten, HM, IS, projInfo, resultStatus, locPlot] = plotData

        self.x_data = disp_data[0]
        self.y_data = disp_data[1]
        seillinieLeer = seilDaten['z_Leer']
        seillinieZweifel = seilDaten['z_Zweifel']
        seil_di = seilDaten['l_coord']
        di = np.int32(di)
        hoeheStue = HM['h']
        zStue = HM['z']
        idxStue = HM['idx']
        # Erstelle Figure
        # Höhe der Figur angepasst an Höhendistanz der Seillinie (verzerrungsfrei)
        self.data_xlow = np.min(self.x_data)
        self.data_xhi = np.max(self.x_data)
        self.data_ylow = np.min(self.y_data)
        self.data_yhi = max([np.max(self.y_data), np.max(zStue) + 5])
        data_ylen = self.data_yhi - self.data_ylow
        # Anker
        [zAnkerseil, xAnkerseil] = IS['Ank'][3]
        # Markierungen für fixe Stützen
        [findFixStueX, findFixStueZ] = IS['HM_fix_marker']
        # scaleFactor = 1.5  # Um Liniendicke und Schrift zu skalieren
        # dpi = 100 / scaleFactor  # Ausgabequalität
        # max_xlen = 10.10  # 11.69 inch = A4 Breite
        # max_ylen = 7.07  # 8.27 inch = A4 Höhe
        # fig_xlen = max_xlen * scaleFactor
        # fig_ylen = max_ylen * scaleFactor
        
        self.axes.plot(seil_di, seillinieLeer, color='#4D83B2', linewidth=1.5,
                  label="Leerseil")
        self.axes.plot(seil_di, seillinieZweifel, color='#FF4D44', linewidth=1.5,
                  label="Lastwegkurve nach Zweifel")
        # Gelände
        self.axes.plot(self.x_data, self.y_data, color='#a1d1ab', linewidth=3.5)
        # self.axes.plot(HM['poss_x'], HM['poss_y'], 'o', markersize=3.5,
        #           color='#F3FF3E',
        #           label="Mögliche Stützenstandorte")

        # Ankerfelder
        if xAnkerseil[0] != xAnkerseil[
            1]:  # Falls Anker vom Benutzer definiert wurden
            self.axes.plot(xAnkerseil[:2], zAnkerseil[:2], color='#FF4D44',
                      linewidth=1.8)
        if xAnkerseil[2] != xAnkerseil[3] and resultStatus != 3:
            # Falls Anker vom Benutzer definiert wurden
            self.axes.plot(xAnkerseil[2:], zAnkerseil[2:], color='#FF4D44',
                      linewidth=1.8)
        # Stützen
        self.axes.vlines(idxStue.astype(float),
                         self.y_data[idxStue + p].astype(float),
                         zStue.astype(float), colors='#363432', linewidth=3.0)


        # Annotations
        for i in range(len(idxStue)):
            marker = ''
            if findFixStueX[i] > 0:
                marker = '°'
                if findFixStueZ[i] > 0:
                    marker = '°*'

            self.axes.annotate(
                f"{i+1}. Stütze{marker}",
                xy=(idxStue[i], zStue[i]),
                xycoords='data', xytext=(-25, 20),
                textcoords='offset points', size=12,
                path_effects=[PathEffects.withStroke(linewidth=3, foreground="w")])

        # Axis range
        self.axes.set_xlim(self.data_xlow, self.data_xhi)
        self.axes.set_ylim(self.data_ylow, self.data_yhi)
        # TODO: mit margins arbeiten: self.axes.margin(2, 2)

        self.draw()
        
        # TODO: Funktioniert unter Windows nicht
        # self.fig.tight_layout()

    @staticmethod
    def __setupAxes(axe):
        # axe1.set_xlabel("Horizontaldistanz von Startpunkt aus", fontsize=12)
        axe.set_ylabel("Höhe", verticalalignment='top', fontsize=12,
                       horizontalalignment='center', labelpad=20)
        # axe.grid()
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

    def zoomTo(self, event):
        if self.isZoomed:
            self.zoomOut()
            return
        
        x = 50
        y_low = 633.2
        y_heigh = 641.2
        buffer = 10
        self.isZoomed = True

        self.axes.set_xlim(x - buffer, x + buffer)
        self.axes.set_ylim(y_low - buffer/2, y_heigh + buffer/2)

        self.zoom_vline.set_xdata(x)
        self.zoom_hline_low.set_ydata(y_low)
        self.zoom_hline_high.set_ydata(y_heigh)

        self.axes.text(x, y_low - 1, f'{x} m')
        self.axes.text(x - buffer / 2, y_low + 0.1, f'{y_low} m')
        self.axes.text(x - buffer / 2, y_heigh + 0.1, f'{y_heigh} m')
        self.axes.text(x + 0.5, 637, f'10 m')
        
        self.zoom_vline.set_visible(True)
        self.zoom_hline_low.set_visible(True)
        self.zoom_hline_high.set_visible(True)

        self.draw()
    
    def zoomOut(self):
        self.axes.set_xlim(self.data_xlow, self.data_xhi)
        self.axes.set_ylim(self.data_ylow, self.data_yhi)
        self.zoom_vline.set_visible(False)
        self.zoom_hline_low.set_visible(False)
        self.zoom_hline_high.set_visible(False)

        for txt in self.axes.texts:
            txt.set_visible(False)

        self.draw()
