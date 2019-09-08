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
import numpy as np
from math import floor

from .adjustmentPlot import AdjustmentPlot
from .guiHelperFunctions import MyNavigationToolbar

from qgis.PyQt.QtCore import QSize
from qgis.PyQt.QtWidgets import QDialog, QSizePolicy

from .ui_adjustmentDialog import Ui_Dialog
from .adjustmentDialog_poles import AdjustmentDialogPoles
from .adjustmentDialog_params import AdjustmentDialogParams
from .adjustmentDialog_thresholds import AdjustmentDialogThresholds



class AdjustmentDialog(QDialog, Ui_Dialog):
    """
    Dialog window that is shown after the optimization has successfully run
    through. Users can change the calculated cable layout by changing pole
    position, height, angle and the properties of the cable line. The cable
    line is then recalculated and the new layout is shown in a plot.
    """
    INIT_POLE_HEIGHT = 10
    INIT_POLE_ANGLE = 0
    HORIZONTAL_BUFFER = 10
    POLE_DIST_STEP = 1
    POLE_HEIGHT_STEP = 0.1
    
    def __init__(self, toolWindow, interface):
        QDialog.__init__(self, interface.mainWindow())

        self.iface = interface
        self.canvas = self.iface.mapCanvas()
        self.toolWin = toolWindow

        # Load data
        self.originalData = {}
        self.poles = []
        self.xdata = []
        self.terrain = []
        self.cableLine = {}
        self.cableParams = {}
        self.terrainSpacing = 0
        self.loadData()

        # Setup GUI from UI-file
        self.setupUi(self)

        self.configurationHasChanged = False
        self.mapMarker = None
        self.pointsToDraw = []
        self.mapLines = []
        
        # Create diagram
        self.plot = AdjustmentPlot(self)
        self.plot.setMinimumSize(QSize(600, 400))
        self.plot.setMaximumSize(QSize(600, 400))
        self.plot.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        # Draw profile in diagram
        self.plot.initData(self.xdata, self.terrain)
        self.plot.updatePlot(self.poles, self.cableLine)
        
        # Pan/Zoom tools for diagram
        bar = MyNavigationToolbar(self.plot, self)
        
        self.plotLayout.addWidget(self.plot)
        self.plotLayout.addWidget(bar)

        # Fill tab widget with data
        self.poleLayout = AdjustmentDialogPoles(self, self.poles)
        self.paramLayout = AdjustmentDialogParams(self, self.cableParams)
        self.thresholdLayout = AdjustmentDialogThresholds(self)
    
    def loadData(self):
        # Test data
        storeDump = 'plotData_ergebnisfenster_20190816_L-24m'
        homePath = '/home/pi/Projects/seilaplan/pickle_dumps'
        storefile = os.path.join(homePath, '{}.pckl'.format(storeDump))
        f = open(storefile, 'rb')
        dump = pickle.load(f)
        f.close()
        [disp_data, di, seilDaten, HM, IS, projInfo, resultStatus,
         locPlot] = dump

        data = {
            'poleDist': [IS['Ank'][3][1][0]] + list(HM['idx']) + [
                IS['Ank'][3][1][3]],
            'poleHeight': [False] + list(HM['h']) + [False],
            'terrain': disp_data,
            'anker': None,
            'IS': IS,
            'data': dump
        }
        self.terrainSpacing = int(abs(disp_data[0][0]))
        self.xdata = disp_data[0]
        self.terrain = disp_data[1]
        
        poles = []

        for idx in range(len(data['poleDist'])):
            angle = self.INIT_POLE_ANGLE
            if idx == 0 or idx == len(data['poleDist']) -1:
                angle = False
            poles.append({
                'dist': data['poleDist'][idx],
                'height': data['poleHeight'][idx],
                'angle': angle,
                'terrain': self.getTerrainAtDist(data['poleDist'][idx])
            })
        
        data['poles'] = poles
        self.cableParams = data['IS']
        self.poles = poles
        self.cableLine = {
            'xaxis': seilDaten['l_coord'],
            'empty': seilDaten['z_Leer'],
            'load': seilDaten['z_Zweifel']
        }
        self.originalData = data
    
    def getTerrainAtDist(self, pos):
        # TODO: Was machen wenn Terrain genauer als 1m aufgenommen werden soll?
        return self.terrain[int(np.argmax(self.xdata>=pos))]
    
    def zoomToPole(self, idx):
        self.plot.zoomTo(self.poles[idx])
        self.plot.updatePlot(self.poles, self.cableLine)
    
    def zoomOut(self):
        self.plot.zoomOut()
        self.plot.updatePlot(self.poles, self.cableLine)

    def updatePole(self, idx, fieldType, newVal):
        self.poles[idx][fieldType] = newVal
        if fieldType == 'dist':
            self.poles[idx]['terrain'] = self.getTerrainAtDist(newVal)
        self.plot.zoomTo(self.poles[idx])
        self.plot.updatePlot(self.poles, self.cableLine)
        self.activateRecalcBtn()
    
    def addPole(self, idx):
        newPoleIdx = idx + 1
        oldLeftIdx = idx
        oldRightIdx = idx + 1
        lowerRange = self.poles[oldLeftIdx]['dist'] + self.POLE_DIST_STEP
        upperRange = self.poles[oldRightIdx]['dist'] - self.POLE_DIST_STEP
        rangeDist = upperRange - lowerRange
        dist = floor(lowerRange + 0.5 * rangeDist)
        
        self.poles.insert(newPoleIdx, {
            'dist': dist,
            'height': self.INIT_POLE_HEIGHT,
            'angle': self.INIT_POLE_ANGLE,
            'terrain': self.getTerrainAtDist(dist)
        })
        self.plot.zoomOut()
        self.plot.updatePlot(self.poles, self.cableLine)
        self.activateRecalcBtn()
        
        return newPoleIdx, dist, lowerRange, upperRange, \
               self.INIT_POLE_HEIGHT, self.INIT_POLE_ANGLE

    def deletePole(self, idx):
        self.poles.pop(idx)
        self.plot.zoomOut()
        self.plot.updatePlot(self.poles, self.cableLine)
        self.activateRecalcBtn()
    
    def updateCableParam(self, param, newVal):
        self.cableParams[param] = newVal
        self.activateRecalcBtn()

    def activateRecalcBtn(self):
        self.configurationHasChanged = True
        # Activate recalculation button
    
    def recalculate(self):
        # calculate(this.params, self.fieldComment.getText())
        pass
    
    def Apply(self):
        self.close()
    
    def Reject(self):
        self.close()

