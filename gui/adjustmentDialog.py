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

        # Ankerfeld start
        self.addAnker(0, -7.0, [-1 * rangeBuffer, 0])

        # Poles
        for idx in range(poleCount):
            delBtn = False
            addBtn = False
            lowerRange = hDist[idx - 1] if idx > 0 else 0
            upperRange = hDist[idx + 1] if idx < poleCount - 1 else hDist[idx] + rangeBuffer

            # Delete Buttons vor all but the first and last pole
            if idx != 0 and idx != poleCount - 1:
                delBtn = True
            # Add Button for all but the last pole
            if idx != poleCount - 1:
                addBtn = True

            self.addPole(idx + 1, hDist[idx], [lowerRange, upperRange],
                         HM['h'][idx], delBtn, addBtn)

        # Ankerfeld end
        self.addAnker(poleCount + 1, 327.0, [327.0, 327.0 + rangeBuffer])

    def addRow(self, idx):
        rowLayout = QHBoxLayout()
        rowLayout.setAlignment(Qt.AlignLeft)
        # if last position in grid addLayout, else insertLayout
        if self.poleVGrid.count() == idx + 1:
            self.poleVGrid.addLayout(rowLayout)
        else:
            self.poleVGrid.insertLayout(idx, rowLayout)

        self.poleListing[idx] = {}
        return rowLayout

    def addAnker(self, idx, dist, distRange):
        row = self.addRow(idx)
        self.addPoleAddBtn(False)
        self.addPoleName(row, idx, 'Verankerung')
        self.addPoleHDist(row, idx, dist, distRange)  # TODO: Wert aus IS auslesen

    def addPole(self, poleNr, dist, distRange, height, delBtn, addBtn):
        row = self.addRow(poleNr)
        self.addPoleName(row, poleNr, f'{poleNr}. Stütze')
        self.addPoleHDist(row, poleNr, dist, distRange)
        self.addPoleHeight(row, poleNr, height)
        self.addPoleAngle(row, poleNr, 0)

        if delBtn:
            self.addPoleDel(row, poleNr)
        if addBtn:
            self.addPoleAddBtn(poleNr)

    def addPoleAddBtn(self, idx):
        # Placeholder for add Button
        if not idx:
            placeholder = QSpacerItem(5, 31+20, QSizePolicy.Fixed,
                                      QSizePolicy.Fixed)
            self.addBtnVGrid.addItem(placeholder)
            return

        btn = QPushButton(self.tabPoles)
        btn.setMaximumSize(QSize(19, 19))
        btn.setText("")
        icon = QIcon()
        icon.addPixmap(
            QPixmap(":/plugins/SeilaplanPlugin/gui/icons/icon_plus.png"),
            QIcon.Normal, QIcon.Off)
        btn.setIcon(icon)
        btn.setIconSize(QSize(16, 16))
        self.addBtnVGrid.addWidget(btn)
        margin = QSpacerItem(5, 6, QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.addBtnVGrid.addItem(margin)
        self.poleListing[idx]['add'] = btn

    def addPoleName(self, row, idx, value):
        field = QLineEdit(self.tabPoles)
        field.setFixedWidth(180)        # TODO: Soltle wachsen können
        field.setText(value)
        self.poleListing[idx]['name'] = field
        row.addWidget(field)

    def addPoleHDist(self, row, idx, value, valRange):
        field = QDoubleSpinBox(self.tabPoles)
        field.setDecimals(1)
        field.setSingleStep(0.5)
        field.setSuffix(" m")
        field.setFixedWidth(95)
        field.setRange(float(valRange[0]), float(valRange[1]))  # TODO Range ist von der vorherigen und nachherigen Stütze abhängig
        field.setValue(float(value))
        row.addWidget(field)
        self.poleListing[idx]['dist'] = field

    def addPoleHeight(self, row, idx, value):
        field = QDoubleSpinBox(self.tabPoles)
        field.setDecimals(1)
        field.setSingleStep(0.1)
        field.setSuffix(" m")
        field.setFixedWidth(85)
        field.setRange(0.0, 50.0)
        field.setValue(float(value))
        row.addWidget(field)
        self.poleListing[idx]['height'] = field

    def addPoleAngle(self, row, idx, value):
        field = QSpinBox(self.tabPoles)
        field.setSuffix(" °")
        field.setFixedWidth(60)
        field.setRange(-180, 180)
        field.setValue(value)
        row.addWidget(field)
        self.poleListing[idx]['angle'] = field

    def addPoleDel(self, row, idx):
        btn = QPushButton(self.tabPoles)
        btn.setMaximumSize(QSize(27, 27))
        icon = QIcon()
        icon.addPixmap(
            QPixmap(":/plugins/SeilaplanPlugin/gui/icons/icon_bin.png"),
            QIcon.Normal, QIcon.Off)
        btn.setIcon(icon)
        btn.setIconSize(QSize(16, 16))
        row.addWidget(btn)
        self.poleListing[idx]['del'] = btn
    
    def Apply(self):
        self.close()
    
    def Reject(self):
        self.close()

