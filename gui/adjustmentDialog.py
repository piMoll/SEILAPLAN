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

from qgis.PyQt.QtCore import QSize, QTimer
from qgis.PyQt.QtWidgets import QDialog, QSizePolicy
from qgis.PyQt.QtGui import QPixmap

from .ui_adjustmentDialog import Ui_AdjustmenDialog
from .adjustmentPlot import AdjustmentPlot
from .guiHelperFunctions import MyNavigationToolbar
from .adjustmentDialog_poles import AdjustmentDialogPoles
from .adjustmentDialog_params import AdjustmentDialogParams
from .adjustmentDialog_thresholds import AdjustmentDialogThresholds
from .saveDialog import DialogOutputOptions
from ..tool.cablelineFinal import preciseCable


class AdjustmentDialog(QDialog, Ui_AdjustmenDialog):
    """
    Dialog window that is shown after the optimization has successfully run
    through. Users can change the calculated cable layout by changing pole
    position, height, angle and the properties of the cable line. The cable
    line is then recalculated and the new layout is shown in a plot.
    """

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
        self.profile = self.confHandler.project.profile
        self.poles = self.confHandler.project.poles
        # Max distance the anchors can move away from initial position
        self.anchorBuffer = self.confHandler.project.dhm.rasterBuffer

        # Load data
        self.originalData = {}
        self.result = {}
        self.cableline = {}
        self.thSize = [5, 5]
        self.thData = {}
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
        self.updateRecalcStatus('ready')

    def loadData(self, pickleFile):
        # Test data
        f = open(pickleFile, 'rb')
        dump = pickle.load(f)
        f.close()

        self.poles.poles = dump['poles']
        self.poles.calculateAnchor()

        self.initData(dump)
        
    def initData(self, result):
        if not result:
            self.close()

        # Save original data from optimization
        self.originalData = result
        
        self.result = result
        # Structure:
        # cableline
        # optSTA
        # force
        # optLen
        # duration
        self.result['optSTA_arr'] = self.result['optSTA']
        self.result['optSTA'] = self.result['optSTA_arr'][0]
        self.cableline = self.result['cableline']
        self.profile.updateProfileAnalysis(self.cableline, self.poles.poles)

        # Draw profile in diagram
        self.plot.initData(self.profile.di_disp, self.profile.zi_disp)
        self.plot.updatePlot(self.poles.getAsArray(), self.cableline)
    
        # Create layout to modify poles
        self.poleLayout.addPolesToGui(self.poles.poles)

        # Fill in cable parameters
        self.paramLayout.fillInParams()

        # Start Thread to recalculate cable line every 300 milliseconds
        self.timer.timeout.connect(self.recalculate)
        self.timer.start(300)
    
    def zoomToPole(self, idx):
        self.plot.zoomTo(self.poles.poles[idx])
        self.plot.updatePlot(self.poles.getAsArray(), self.cableline)
    
    def zoomOut(self):
        self.plot.zoomOut()
        self.plot.updatePlot(self.poles.getAsArray(), self.cableline)

    def updatePole(self, idx, property_name, newVal):
        self.poles.update(idx, property_name, newVal)
        self.plot.zoomTo(self.poles.poles[idx])
        self.plot.updatePlot(self.poles.getAsArray(), self.cableline)
        self.configurationHasChanged = True
    
    def addPole(self, idx):
        newPoleIdx = idx + 1
        oldLeftIdx = idx
        oldRightIdx = idx + 1
        lowerRange = self.poles.poles[oldLeftIdx]['d'] + self.poles.POLE_DIST_STEP
        upperRange = self.poles.poles[oldRightIdx]['d'] - self.poles.POLE_DIST_STEP
        rangeDist = upperRange - lowerRange
        d = floor(lowerRange + 0.5 * rangeDist)
        
        self.poles.add(newPoleIdx, d)
        
        self.plot.zoomOut()
        self.plot.updatePlot(self.poles.getAsArray(), self.cableline)
        self.configurationHasChanged = True
        
        return newPoleIdx, self.poles.poles[newPoleIdx]['name'], d, \
               lowerRange, upperRange, self.poles.poles[newPoleIdx]['h'], \
               self.poles.poles[newPoleIdx]['angle']

    def deletePole(self, idx):
        self.poles.delete(idx)
        self.plot.zoomOut()
        self.plot.updatePlot(self.poles.getAsArray(), self.cableline)
        self.configurationHasChanged = True
    
    def updateCableParam(self):
        self.configurationHasChanged = True
    
    def updateRecalcStatus(self, status):
        ico_path = os.path.join(__file__, 'icons')
        # if self.recalcStatus_ico.isHidden():
        #     self.recalcStatus_ico.show()
        #     self.recalcStatus_txt.show()
        # if status == 'start':
        #     self.recalcStatus_txt.setText('Neuberechnung...')
        #     self.recalcStatus_ico.setPixmap(QPixmap(os.path.join(
        #         ico_path, 'icon_reload.png')))
        if status == 'ready':
            self.recalcStatus_ico.show()
            self.recalcStatus_txt.show()
            self.recalcStatus_txt.setText('Optimierung erfolgreich abgeschlossen.')
            self.recalcStatus_ico.setPixmap(QPixmap(os.path.join(
                ico_path, 'icon_green.png')))
        if status == 'success':
            self.recalcStatus_ico.show()
            self.recalcStatus_txt.show()
            self.recalcStatus_txt.setText('Seillinie neu berechnet')
            self.recalcStatus_ico.setPixmap(QPixmap(os.path.join(
                ico_path, 'icon_green.png')))
        elif status == 'error':
            self.recalcStatus_ico.show()
            self.recalcStatus_txt.show()
            self.recalcStatus_txt.setText('Es ist ein Fehler aufgetreten')
            self.recalcStatus_ico.setPixmap(QPixmap(os.path.join(
                ico_path, 'icon_yellow.png')))
    
    def recalculate(self):
        if not self.configurationHasChanged or self.isRecalculating:
            return
        self.isRecalculating = True
        
        try:
            params = self.confHandler.params.getSimpleParameterDict()
            cableline, kraft, seil_possible = preciseCable(params,
                                                           self.poles,
                                                           self.result['optSTA'])
        except Exception as e:
            # TODO: Index Errors for certain angles still there
            self.updateRecalcStatus('error')
            self.isRecalculating = False
            self.configurationHasChanged = False
            # TODO: Message
            return

        self.cableline = cableline
        self.result['force'] = kraft
        
        # Ground clearance
        self.profile.updateProfileAnalysis(self.cableline, self.poles.poles)
        
        # Update Plot
        [pole_d, pole_z, pole_h, pole_dtop, pole_ztop] = self.poles.getAsArray()
        self.plot.updatePlot([pole_d, pole_z, pole_h, pole_dtop, pole_ztop],
                             self.cableline)
        
        # Update Threshold data
        self.updateThresholds()
        
        self.updateRecalcStatus('success')
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
        self.saveDialog.doSave = False
        self.saveDialog.exec()
        if self.saveDialog.doSave:
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

