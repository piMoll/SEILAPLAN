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
import pickle
import os

from .adjustmentPlot import AdjustmentPlot
from .guiHelperFunctions import MyNavigationToolbar

from qgis.PyQt.QtCore import QSize, Qt
from qgis.PyQt.QtWidgets import (QDialog, QSizePolicy, QDoubleSpinBox,
                                 QSpinBox, QPushButton, QLineEdit, QHBoxLayout,
                                 QSpacerItem)
from qgis.PyQt.QtGui import QIcon, QPixmap

from .ui_adjustmentDialog import Ui_Dialog

from .adjustmentDialog_poles import AdjustmentDialogPoles



class AdjustmentDialog(QDialog, Ui_Dialog):
    def __init__(self, toolWindow, interface):
        QDialog.__init__(self, interface.mainWindow())

        self.iface = interface
        self.canvas = self.iface.mapCanvas()
        self.toolWin = toolWindow
        
        self.data = self.loadData()

        # Setup GUI from UI-file
        self.setupUi(self)
        
        self.dataIsPlotted = False
        
        self.mapMarker = None
        self.pointsToDraw = []
        self.mapLines = []
        
        # Matplotlib diagram
        self.sc = AdjustmentPlot(self)
        self.sc.setMinimumSize(QSize(600, 400))
        self.sc.setMaximumSize(QSize(600, 400))
        self.sc.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # Pan/Zoom Tools for diagram
        bar = MyNavigationToolbar(self.sc, self)
        
        self.plotLayout.addWidget(self.sc)
        self.plotLayout.addWidget(bar)

        poles = AdjustmentDialogPoles(self)

    
    def plotData(self):
        if self.dataIsPlotted:
            return
        # Draw plofile in diagram
        self.sc.plotData(self.data['data'])
        self.sc.updateGeometry()
        
        self.dataIsPlotted = True
    
    @staticmethod
    def loadData():
        # Testdata
        storeDump = 'plotData_ergebnisfenster_20190816_L-24m'
        homePath = '/home/pi/Projects/seilaplan/pickle_dumps'
        storefile = os.path.join(homePath, '{}.pckl'.format(storeDump))
        f = open(storefile, 'rb')
        dump = pickle.load(f)
        f.close()
        [disp_data, di, seilDaten, HM, IS, projInfo, resultStatus,
         locPlot] = dump
        
        return {
            'poleDist': HM['idx'],
            'poleHeight': HM['h'],
            'anker': None,
            'data': dump
        }
    
    def Apply(self):
        self.close()
    
    def Reject(self):
        self.close()

