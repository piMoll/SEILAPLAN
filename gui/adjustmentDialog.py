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

from qgis.PyQt.QtCore import QSize, QTimer
from qgis.PyQt.QtWidgets import QDialog, QSizePolicy

from .ui_adjustmentDialog import Ui_Dialog
from .adjustmentDialog_poles import AdjustmentDialogPoles
from .adjustmentDialog_params import AdjustmentDialogParams
from .adjustmentDialog_thresholds import AdjustmentDialogThresholds

from ..tool.cablelineFinal import preciseCable
from ..tool.geoExtract import updateAnker


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
        self.gp = {}
        self.terrainSpacing = 0

        # Setup GUI from UI-file
        self.setupUi(self)

        self.mapMarker = None
        self.pointsToDraw = []
        self.mapLines = []
        
        # Create diagram
        self.plot = AdjustmentPlot(self)
        self.plot.setMinimumSize(QSize(600, 400))
        self.plot.setMaximumSize(QSize(600, 400))
        self.plot.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # Pan/Zoom tools for diagram
        bar = MyNavigationToolbar(self.plot, self)
        
        self.plotLayout.addWidget(self.plot)
        self.plotLayout.addWidget(bar)

        # Fill tab widget with data
        self.poleLayout = AdjustmentDialogPoles(self)
        self.paramLayout = AdjustmentDialogParams(self)
        self.thresholdLayout = AdjustmentDialogThresholds(self)
        
        # Disable button for recalculating cable line
        self.btnRunCalc.setEnabled(False)
        self.btnRunCalc.clicked.connect(self.recalculate)

        # Thread for instant recalculation when poles or parameters are changed
        self.timer = QTimer()
        self.configurationHasChanged = False
        self.isRecalculating = False

    def loadData(self):
        # Test data
        storeDump = 'plotData_ergebnisfenster_20190911'
        homePath = '/home/pi/Projects/seilaplan/pickle_dumps'
        storefile = os.path.join(homePath, '{}.pckl'.format(storeDump))
        f = open(storefile, 'rb')
        dump = pickle.load(f)
        f.close()
        self.initData(dump)
        
    def initData(self, result):
        [disp_data, gp, HM, IS, cableline] = result
        self.xdata = disp_data[0]
        self.terrain = disp_data[1]
        self.gp = gp
        self.terrainSpacing = int(abs(disp_data[0][0]))
        self.cableParams = IS
        self.cableLine = {
            'xaxis': cableline['l_coord'],
            'empty': cableline['z_Leer'],
            'load': cableline['z_Zweifel']
        }
        # TODO Anchor data

        poleDist = [IS['Ank'][3][1][0]] + list(HM['idx']) + [
            IS['Ank'][3][1][3]]
        poleHeight = [False] + list(HM['h']) + [False]

        for idx in range(len(poleDist)):
            angle = self.INIT_POLE_ANGLE
            if idx == 0 or idx == len(poleDist) - 1:
                angle = False
            self.poles.append({
                'dist': poleDist[idx],
                'height': poleHeight[idx],
                'angle': angle,
                'terrain': self.getTerrainAtDist(poleDist[idx])
            })

        # Draw profile in diagram
        self.plot.initData(self.xdata, self.terrain)
        self.plot.updatePlot(self.poleDataToArray(False), self.cableLine)
    
        # Create layout to modify poles
        self.poleLayout.addPolesToGui(self.poles)

        # Fill in cable parameters
        self.paramLayout.fillInParams(self.cableParams)

        # Start Thread to recalculate cable line every 300 milliseconds
        self.timer.timeout.connect(self.recalculate)
        self.timer.start(300)
        
    def getTerrainAtDist(self, pos):
        # TODO: Was machen wenn Terrain genauer als 1m aufgenommen werden soll?
        return self.terrain[int(np.argmax(self.xdata>=pos))]
    
    def zoomToPole(self, idx):
        self.plot.zoomTo(self.poles[idx])
        self.plot.updatePlot(self.poleDataToArray(False), self.cableLine)
    
    def zoomOut(self):
        self.plot.zoomOut()
        self.plot.updatePlot(self.poleDataToArray(False), self.cableLine)

    def updatePole(self, idx, fieldType, newVal):
        self.poles[idx][fieldType] = newVal
        if fieldType == 'dist':
            self.poles[idx]['terrain'] = self.getTerrainAtDist(newVal)
        self.plot.zoomTo(self.poles[idx])
        self.plot.updatePlot(self.poleDataToArray(False), self.cableLine)
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
        self.plot.updatePlot(self.poleDataToArray(False), self.cableLine)
        self.activateRecalcBtn()
        
        return newPoleIdx, dist, lowerRange, upperRange, \
               self.INIT_POLE_HEIGHT, self.INIT_POLE_ANGLE

    def deletePole(self, idx):
        self.poles.pop(idx)
        self.plot.zoomOut()
        self.plot.updatePlot(self.poleDataToArray(False), self.cableLine)
        self.activateRecalcBtn()
    
    def updateCableParam(self, param, newVal):
        self.cableParams[param] = newVal
        self.activateRecalcBtn()

    def activateRecalcBtn(self):
        self.configurationHasChanged = True
        self.btnRunCalc.setEnabled(True)
    
    def recalculate(self):
        if not self.configurationHasChanged or self.isRecalculating:
            return
        self.isRecalculating = True
        [pole_x, pole_y, pole_h, pole_yh] = self.poleDataToArray(False)

        pole_x = np.array(pole_x)
        pole_y = np.array(pole_y)
        pole_h = np.array(pole_h)
        pole_yh = np.array(pole_yh)
        
        b = pole_x[1:] - pole_x[:-1]
        h = pole_yh[1:] - pole_yh[:-1]
        
        seil, kraft, seil_possible = preciseCable(b, h, self.cableParams)
        
        self.cableLine = {
            'xaxis': seil[2] + pole_x[0],   # X-data starts at first pole
            'empty': seil[0] + pole_yh[0],  # Y-data is calculated relative
            'load': seil[1] + pole_yh[0]
        }
        # TODO: Recaluclate anchor data
        # pole_anchor = 0
        # anchorCable = updateAnker(pole_anchor, pole_h, pole_x)
        
        self.plot.updatePlot([pole_x, pole_y, pole_h, pole_yh], self.cableLine)

        # Deactivate button
        self.btnRunCalc.setEnabled(False)
        self.configurationHasChanged = False
        self.isRecalculating = False
    
    def poleDataToArray(self, withAnchor=True):
        x = []
        y = []
        h = []
        yh = []
        # TODO: Berücksichtigen wenn keine Anker vorhanden
        for pole in self.poles:
            if withAnchor or pole['height']:
                x.append(int(pole['dist']))
                y.append(pole['terrain'])
                h.append(pole['height'])
                yh.append(pole['terrain'] + pole['height'])
        return [x, y, h, yh]
    
    def Apply(self):
        self.close()
    
    def Reject(self):
        self.close()

