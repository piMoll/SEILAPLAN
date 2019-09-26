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
from math import floor, sin, cos, radians

from .adjustmentPlot import AdjustmentPlot
from .guiHelperFunctions import MyNavigationToolbar

from qgis.PyQt.QtCore import QSize, QTimer
from qgis.PyQt.QtWidgets import QDialog, QSizePolicy

from .ui_adjustmentDialog import Ui_AdjustmenDialog
from .adjustmentDialog_poles import AdjustmentDialogPoles
from .adjustmentDialog_params import AdjustmentDialogParams
from .adjustmentDialog_thresholds import AdjustmentDialogThresholds
from .saveDialog import DialogOutputOptions

from ..tool.cablelineFinal import preciseCable
from ..tool.geoExtract import updateAnker


class AdjustmentDialog(QDialog, Ui_AdjustmenDialog):
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
    
    def __init__(self, interface, confHandler):
        """
        :type confHandler: configHandler.ConfigHandler
        """
        QDialog.__init__(self, interface.mainWindow())

        self.iface = interface
        self.canvas = self.iface.mapCanvas()
        
        # Management of Parameters and settings
        self.confHandler = confHandler
        self.confHandler.setDialog(self)

        # Load data
        self.originalData = {}
        self.poles = []
        self.xdata = []
        self.terrain = []
        self.cableLine = {}
        self.anchor = []
        self.cableParams = {}
        self.gp = {}
        self.terrainSpacing = 0
        self.doReRun = False

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
        self.paramLayout = AdjustmentDialogParams(self, self.confHandler.params)
        self.thresholdLayout = AdjustmentDialogThresholds(self)

        # Thread for instant recalculation when poles or parameters are changed
        self.timer = QTimer()
        self.configurationHasChanged = False
        self.isRecalculating = False

        # Save dialog
        self.saveDialog = DialogOutputOptions(self.iface, self, self.confHandler)
        
        self.btnCancel.clicked.connect(self.Reject)
        self.btnSave.clicked.connect(self.save)
        self.btnBackToStart.clicked.connect(self.goBackToStart)

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
        if not result:
            self.close()
        [disp_data, gp, HM, IS, cableline] = result
        self.xdata = disp_data[0]
        self.terrain = disp_data[1]
        self.gp = gp
        self.terrainSpacing = int(abs(disp_data[0][0]))
        self.cableParams = IS
        self.anchor = IS['Ank']
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
                'x': poleDist[idx],
                'y': self.getTerrainAtDist(poleDist[idx]),
                'h': poleHeight[idx],
                'angle': angle,
                'xtop': poleDist[idx],
                'ytop': self.getTerrainAtDist(poleDist[idx]) + poleHeight[idx],
            })

        # Draw profile in diagram
        self.plot.initData(self.xdata, self.terrain)
        self.plot.updatePlot(self.poleDataToArray(False), self.cableLine)
    
        # Create layout to modify poles
        self.poleLayout.addPolesToGui(self.poles)

        # Fill in cable parameters
        self.paramLayout.fillInParams()

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
        if fieldType != 'name':
            self.poles[idx]['y'] = self.getTerrainAtDist(self.poles[idx]['x'])
            self.calculateTopPoint(idx)
        
        self.plot.zoomTo(self.poles[idx])
        self.plot.updatePlot(self.poleDataToArray(False), self.cableLine)
        self.configurationHasChanged = True
    
    def addPole(self, idx):
        newPoleIdx = idx + 1
        oldLeftIdx = idx
        oldRightIdx = idx + 1
        lowerRange = self.poles[oldLeftIdx]['x'] + self.POLE_DIST_STEP
        upperRange = self.poles[oldRightIdx]['x'] - self.POLE_DIST_STEP
        rangeDist = upperRange - lowerRange
        x = floor(lowerRange + 0.5 * rangeDist)
        y = self.getTerrainAtDist(x)
        
        self.poles.insert(newPoleIdx, {
            'x': x,
            'y': y,
            'h': self.INIT_POLE_HEIGHT,
            'angle': self.INIT_POLE_ANGLE
        })
        self.calculateTopPoint(newPoleIdx)
        
        self.plot.zoomOut()
        self.plot.updatePlot(self.poleDataToArray(False), self.cableLine)
        self.configurationHasChanged = True
        
        return newPoleIdx, x, lowerRange, upperRange, \
               self.INIT_POLE_HEIGHT, self.INIT_POLE_ANGLE

    def deletePole(self, idx):
        self.poles.pop(idx)
        self.plot.zoomOut()
        self.plot.updatePlot(self.poleDataToArray(False), self.cableLine)
        self.configurationHasChanged = True
    
    def updateCableParam(self):
        self.configurationHasChanged = True
    
    def recalculate(self):
        if not self.configurationHasChanged or self.isRecalculating:
            return
        self.isRecalculating = True
        [pole_x, pole_y, pole_h, pole_xtop, pole_ytop] = self.poleDataToArray(False)

        pole_x = np.array(pole_x)
        pole_y = np.array(pole_y)
        pole_h = np.array(pole_h)
        pole_xtop = np.array(pole_xtop)
        pole_ytop = np.array(pole_ytop)
        
        b = pole_xtop[1:] - pole_xtop[:-1]
        h = pole_ytop[1:] - pole_ytop[:-1]
        
        try:
            # TODO anchor data will change when start and end point are changed
            seil, kraft, seil_possible = preciseCable(b, h, self.cableParams, self.anchor)
        except Exception:
            # TODO: Index Errors for certain angles still there
            self.isRecalculating = False
            return
        
        self.cableLine = {
            'xaxis': seil[2] + pole_x[0],   # X-data starts at first pole
            'empty': seil[0] + pole_ytop[0],  # Y-data is calculated relative
            'load': seil[1] + pole_ytop[0]
        }
        # TODO: Recaluclate anchor data
        # pole_anchor = 0
        # anchorCable = updateAnker(pole_anchor, pole_h, pole_x)
        
        self.plot.updatePlot([pole_x, pole_y, pole_h, pole_xtop, pole_ytop], self.cableLine)

        # Deactivate button
        self.configurationHasChanged = False
        self.isRecalculating = False
    
    def poleDataToArray(self, withAnchor=True):
        x = []
        y = []
        h = []
        xtop = []
        ytop = []
        # TODO: Berücksichtigen wenn keine Anker vorhanden
        for pole in self.poles:
            if withAnchor or pole['h']:
                x.append(int(pole['x']))
                y.append(pole['y'])
                h.append(pole['h'])
                xtop.append(pole['xtop'])
                ytop.append(pole['ytop'])
        return [x, y, h, xtop, ytop]
    
    def calculateTopPoint(self, idx):
        x = float(self.poles[idx]['x'])
        y = self.poles[idx]['y']
        h = float(self.poles[idx]['h'])
        angle = -1 * radians(self.poles[idx]['angle'])

        self.poles[idx]['xtop'] = x - round(h * sin(angle), 1)
        self.poles[idx]['ytop'] = y + round(h * cos(angle), 1)
    
    def Apply(self):
        self.close()
    
    def goBackToStart(self):
        self.doReRun = True
        self.Reject()
    
    def save(self):
        self.saveDialog.exec()
        self.confHandler.updateUserSettings()
        self.createOutput()
    
    def createOutput(self):
        pass
        # from .tool.outputReport import getTimestamp, plotData, \
        #     generateReportText, \
        #     generateReport, createOutputFolder
        # from .tool.outputGeo import generateGeodata, addToMap, \
        #     generateCoordTable
        #

        # outputFolder = self.projInfo['outputOpt']['outputPath']
        # outputName = self.projInfo['Projektname']
        # outputLoc = createOutputFolder(outputFolder, outputName)
        # # Move saved project file to output folder
        # if os.path.exists(self.projInfo['projFile']):
        #     newpath = os.path.join(outputLoc,
        #                            os.path.basename(self.projInfo['projFile']))
        #     os.rename(self.projInfo['projFile'], newpath)
        #     self.projInfo['projFile'] = newpath
        # # Generate plot
        # plotSavePath = os.path.join(outputLoc,
        #                             "{}_Diagramm.pdf".format(outputName))
        # plotImage, labelTxt = plotData(disp_data, gp["di"], seilDaten, HM,
        #                                self.confHandler.params.params,
        #                                self.projInfo,
        #                                resultStatus, plotSavePath)
        # self.sig_value.emit(optiLen * 1.015)
        # # Calculate duration and generate time stamp
        # duration, timestamp1, timestamp2 = getTimestamp(t_start)
        #
        # # Create report
        # if self.projInfo['outputOpt']['report']:
        #     reportSavePath = os.path.join(outputLoc,
        #                                   "{}_Bericht.pdf".format(outputName))
        #     reportText = generateReportText(IS, self.projInfo, HM,
        #                                     kraft, optSTA, duration,
        #                                     timestamp2, labelTxt)
        #     generateReport(reportText, reportSavePath, outputName)
        #
        # # Create plot
        # if not self.projInfo['outputOpt']['plot']:
        #     # was already created before and gets deleted if not used
        #     if os.path.exists(plotImage):
        #         os.remove(plotImage)
        #
        # # Generate geo data
        # if self.projInfo['outputOpt']['geodata']:
        #     geodata = generateGeodata(self.projInfo, HM, seilDaten,
        #                               labelTxt[0], outputLoc)
        #     addToMap(geodata, outputName)
        #
        # # Generate coordinate tables
        # if self.projInfo['outputOpt']['coords']:
        #     table1SavePath = os.path.join(outputLoc,
        #                                   outputName + '_KoordStuetzen.csv')
        #     table2SavePath = os.path.join(outputLoc,
        #                                   outputName + '_KoordSeil.csv')
        #     generateCoordTable(seilDaten, gp["zi"], HM,
        #                        [table1SavePath, table2SavePath], labelTxt[0])

    def Reject(self):
        # TODO: Nachfrage
        self.close()

