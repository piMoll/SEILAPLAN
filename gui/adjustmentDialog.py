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

from qgis.PyQt.QtCore import QSize
from qgis.PyQt.QtWidgets import (QDialog, QWidget, QDialogButtonBox,
                                 QVBoxLayout, QGridLayout, QSizePolicy,
                                 QPushButton, QHBoxLayout, QFrame)



class AdjustmentDialog(QDialog):
    def __init__(self, toolWindow, interface):
        QDialog.__init__(self, interface.mainWindow())
        # super().__init__()
        self.setWindowTitle("Resultat")
        self.iface = interface
        self.canvas = self.iface.mapCanvas()
        self.toolWin = toolWindow
        main_widget = QWidget(self)
        
        self.dataIsPlotted = False
        
        self.mapMarker = None
        self.pointsToDraw = []
        self.mapLines = []
        
        # Matplotlib diagrm
        self.sc = AdjustmentPlot(self)
        self.sc.setMinimumSize(QSize(600, 400))
        self.sc.setMaximumSize(QSize(600, 400))
        self.sc.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.sc.updateGeometry()
        
        # Pan/Zoom Tools for diagram
        bar = MyNavigationToolbar(self.sc, self)
        
        self.gridM = QGridLayout()
        self.grid = QGridLayout()
        self.gridM.addLayout(self.grid, 0, 0, 1, 1)
        
        # Zoom Button
        hbox = QHBoxLayout()
        line1 = QFrame()
        line1.setFrameShape(QFrame.HLine)
        line1.setFrameShadow(QFrame.Sunken)
        self.zoomBtn = QPushButton("Stütze")
        hbox.addWidget(self.zoomBtn)
        # Connect signals
        self.zoomBtn.clicked.connect(self.sc.zoomTo)
        
        self.buttonBox = QDialogButtonBox(main_widget)
        self.buttonBox.setStandardButtons(QDialogButtonBox.Cancel |
                                          QDialogButtonBox.Ok)
        # Build up GUI
        self.container = QVBoxLayout(main_widget)
        self.container.addWidget(self.sc)
        self.container.addWidget(bar)
        self.container.addLayout(hbox)
        self.container.addLayout(self.gridM)
        self.container.addWidget(self.buttonBox)
        
        # Connect signals
        self.buttonBox.rejected.connect(self.Reject)
        self.buttonBox.accepted.connect(self.Apply)
        self.setLayout(self.container)
        self.menu = False
    
    def plotData(self):
        if self.dataIsPlotted:
            return
        # Draw plofile in diagram
        self.sc.plotData(self.loadData())
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
        return dump
    
    def Apply(self):
        self.close()
    
    def Reject(self):
        self.close()

