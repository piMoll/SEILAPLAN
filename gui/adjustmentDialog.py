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
from qgis.PyQt.QtWidgets import QDialog, QSizePolicy, QDoubleSpinBox, QSpinBox, QPushButton, QLineEdit
from qgis.PyQt.QtGui import QIcon, QPixmap

from .ui_adjustmentDialog import Ui_Dialog



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
        
        # Pole Input fields
        self.poleListing = {}
        self.addPolesToGui()

    
    def plotData(self):
        if self.dataIsPlotted:
            return
        # Draw plofile in diagram
        self.sc.plotData(self.data)
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
        return dump
    
    def addPolesToGui(self):
        [disp_data, di, seilDaten, HM, IS, projInfo, resultStatus, locPlot] = self.data
        
        rangeBuffer = 10
        hDist = HM['idx']
        poleCount = len(hDist)
        
        # Ankerfeld links
        self.poleListing[0] = {}
        self.addPoleName(0, 'Verankerung')
        self.addPoleHDist(0, -7.0, [-1 * rangeBuffer, 0])  # TODO: Wert aus IS auslesen

        # Stützen
        for idx in range(poleCount):
            # Create new Row and add gui elements
            poleNr = idx + 1
            self.poleListing[poleNr] = {}
            
            self.addPoleName(poleNr, f'{poleNr}. Stütze')
            lowerRange = hDist[idx - 1] if idx > 0 else 0
            upperRange = hDist[idx + 1] if idx < poleCount - 1 else hDist[idx] + rangeBuffer
            self.addPoleHDist(poleNr, hDist[idx], [lowerRange, upperRange])
            self.addPoleHeight(poleNr, HM['h'][idx])
            self.addPoleAngle(poleNr, 0)
            if idx != 0 and idx != poleCount - 1:
                self.addPoleDel(poleNr)
            
        # Ankerfeld rechts
        self.poleListing[poleCount + 1] = {}
        self.addPoleName(poleCount + 1, 'Verankerung')
        self.addPoleHDist(poleCount + 1, 327.0, [327.0, 327.0 + rangeBuffer]) # TODO


    def addPoleAddBtn(self):
        pass
    
    def addPoleName(self, idx, value):
        field = QLineEdit(self.tabPoles)
        field.setMinimumSize(QSize(170, 0))
        self.gridPoles.addWidget(field, idx + 1, 0, 1, 1)
        field.setText(value)
        self.poleListing[idx]['name'] = field
    
    def addPoleHDist(self, idx, value, valRange):
        field = QDoubleSpinBox(self.tabPoles)
        field.setDecimals(1)
        field.setSingleStep(0.5)
        field.setSuffix(" m")
        field.setMinimumSize(QSize(100, 0))
        self.gridPoles.addWidget(field, idx + 1, 1, 1, 1)
        field.setRange(float(valRange[0]), float(valRange[1]))  # TODO Range ist von der vorherigen und nachherigen Stütze abhängig
        field.setValue(float(value))
        self.poleListing[idx]['dist'] = field
    
    def addPoleHeight(self, idx, value):
        field = QDoubleSpinBox(self.tabPoles)
        field.setDecimals(1)
        field.setSingleStep(0.1)
        field.setSuffix(" m")
        field.setMinimumSize(QSize(100, 0))
        self.gridPoles.addWidget(field, idx + 1, 2, 1, 1)
        field.setRange(0.0, 50.0)
        field.setValue(float(value))
        self.poleListing[idx]['height'] = field
    
    def addPoleAngle(self, idx, value):
        field = QSpinBox(self.tabPoles)
        field.setSuffix(" °")
        field.setMinimumSize(QSize(79, 0))
        self.gridPoles.addWidget(field, idx + 1, 3, 1, 1)
        field.setRange(-180, 180)
        field.setValue(value)
        self.poleListing[idx]['angle'] = field
    
    def addPoleDel(self, idx):
        field = QPushButton(self.tabPoles)
        field.setMaximumSize(QSize(27, 27))
        icon1 = QIcon()
        icon1.addPixmap(
            QPixmap(":/plugins/SeilaplanPlugin/gui/icons/icon_bin.png"),
            QIcon.Normal, QIcon.Off)
        field.setIcon(icon1)
        field.setIconSize(QSize(16, 16))
        self.gridPoles.addWidget(field, idx + 1, 4, 1, 1)
        self.poleListing[idx]['del'] = field
    
    def Apply(self):
        self.close()
    
    def Reject(self):
        self.close()

