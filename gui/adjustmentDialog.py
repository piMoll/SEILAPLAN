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
from qgis.PyQt.QtWidgets import QDialog, QSizePolicy, QMessageBox
from qgis.PyQt.QtGui import QPixmap

from .ui_adjustmentDialog import Ui_AdjustmenDialog
from .adjustmentPlot import AdjustmentPlot
from .guiHelperFunctions import MyNavigationToolbar
from .adjustmentDialog_poles import AdjustmentDialogPoles
from .adjustmentDialog_params import AdjustmentDialogParams
from .adjustmentDialog_thresholds import AdjustmentDialogThresholds
from .saveDialog import DialogOutputOptions
from ..tool.cablelineFinal import preciseCable, updateWithCableCoordinates
from ..tool.outputReport import generateReportText, generateReport, createOutputFolder
from ..tool.outputGeo import generateGeodata, addToMap, generateCoordTable


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
        self.thresholdLayout = AdjustmentDialogThresholds(self, self.thSize)

        # Thread for instant recalculation when poles or parameters are changed
        self.timer = QTimer()
        self.configurationHasChanged = False
        self.isRecalculating = False
        self.unsavedChanges = True

        # Save dialog
        self.saveDialog = DialogOutputOptions(self.iface, self, self.confHandler)
        
        # Connect signals
        self.btnClose.clicked.connect(self.onClose)
        self.btnSave.clicked.connect(self.onSave)
        self.btnBackToStart.clicked.connect(self.onReturnToStart)
        self.fieldComment.textChanged.connect(self.onCommentChanged)

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
        # Dictionary properties: resultStatus, cableline, optSTA, force, optLen, optLen_arr, duration
        self.result = result
        self.cableline = self.result['cableline']
        self.profile.updateProfileAnalysis(self.cableline, self.poles.poles)

        self.updateRecalcStatus(self.result['resultStatus'])

        # Draw profile in diagram
        self.plot.initData(self.profile.di_disp, self.profile.zi_disp)
        self.plot.updatePlot(self.poles.getAsArray(), self.cableline)
    
        # Create layout to modify poles
        self.poleLayout.addPolesToGui(self.poles.poles)

        # Fill in cable parameters
        self.paramLayout.fillInParams()
        
        # Fill in Threshold data
        self.updateThresholds()

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
    
    def updateOptSTA(self, newVal):
        self.result['optSTA'] = float(newVal)
        return str(newVal)
    
    def updateCableParam(self):
        self.configurationHasChanged = True
    
    def onCommentChanged(self):
        self.unsavedChanges = True
    
    def updateRecalcStatus(self, status):
        ico_path = os.path.join(os.path.dirname(__file__), 'icons')
        if status == '1':
            self.recalcStatus_txt.setText(
                'Optimierung erfolgreich abgeschlossen.')
            self.recalcStatus_ico.setPixmap(QPixmap(os.path.join(
                ico_path, 'icon_green.png')))
        elif status == '2':
            self.recalcStatus_txt.setText(
                'Die Seillinie wurde berechnet, das Tragseil hebt jedoch '
                'bei mindestens einer Stütze ab.')
            self.recalcStatus_ico.setPixmap(QPixmap(os.path.join(
                ico_path, 'icon_yellow.png')))
        elif status == '3':
            self.recalcStatus_txt.setText(
                'Die Seillinie konnte nicht komplett berechnet werden, '
                'es sind nicht genügend\nStützenstandorte bestimmbar.')
            self.recalcStatus_ico.setPixmap(QPixmap(os.path.join(
                ico_path, 'icon_yellow.png')))
        elif status == 'start':
            self.recalcStatus_txt.setText('Neuberechnung...')
            self.recalcStatus_ico.setPixmap(QPixmap(os.path.join(
                ico_path, 'icon_reload.png')))
        elif status == 'success':
            self.recalcStatus_txt.setText('Seillinie neu berechnet')
            self.recalcStatus_ico.setPixmap(QPixmap(os.path.join(
                ico_path, 'icon_green.png')))
        elif status == 'error':
            self.recalcStatus_txt.setText('Es ist ein Fehler aufgetreten')
            self.recalcStatus_ico.setPixmap(QPixmap(os.path.join(
                ico_path, 'icon_yellow.png')))
        elif status == 'saveDone':
            self.recalcStatus_txt.setText('Ergebnisse gespeichert')
            self.recalcStatus_ico.setPixmap(QPixmap(os.path.join(
                ico_path, 'icon_save.png')))
    
    def recalculate(self):
        if not self.configurationHasChanged or self.isRecalculating:
            return
        self.isRecalculating = True
        
        try:
            params = self.confHandler.params.getSimpleParameterDict()
            cableline, kraft, seil_possible = preciseCable(params, self.poles,
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
        self.unsavedChanges = True
    
    def updateThresholds(self):
        params = self.confHandler.params
        
        if not self.thData:
            rows = [['' for cell in range(self.thSize[0])] for row in range(self.thSize[1])]
            header = [
                'Kennwert',
                'Definierter\nGrenzwert',
                'Optimierte\nLösung',
                'Aktuelle\nLösung',
                'Wo?'
            ]
            units = [
                params.params['Bodenabst_min']['unit'],
                params.params['zul_SK']['unit'],
                params.params['zul_SK']['unit'],
                '°',
                ''
            ]
            thresholds = [
                params.getParameter('Bodenabst_min'),
                params.getParameter('zul_SK'),
                params.getParameter('zul_SK'),
                None,
                None
            ]
            self.thData = {
                'header': header,
                'rows': rows,
                'units': units,
                'thresholds': thresholds
            }
            label = [
                'Minimaler Bodenabstand',
                'Max. auftretende Seilzugkraft (am Lastseil, Last in Feldmitte des längsten Seilfeldes)',
                'Max. resultierende Sattelkraft (an befahrbarer Stütze, Last auf Stütze)',
                'Seilwinkel am Lastseil',
                'Nachweis erbracht, dass Seil nicht vom Sattel abhebt',
            ]
            thresholdStr = [
                f"{params.getParameterAsStr('Bodenabst_min')} {units[0]}",
                f"{params.getParameterAsStr('zul_SK')} {units[1]}",
                f"{params.getParameterAsStr('zul_SK')} {units[2]}",
                '0 ° - 30 °',
                '-'
            ]
            for i in range(self.thSize[0]):
                val, location = self.getThresholdFromResult(i)
                self.thData['rows'][i][0] = label[i]
                self.thData['rows'][i][1] = thresholdStr[i]
                self.thData['rows'][i][2] = val
                self.thData['rows'][i][3] = ''
                self.thData['rows'][i][4] = None

            self.thresholdLayout.populate(header, self.thData['rows'])
        
        else:
            for i in range(len(self.thData['rows'])):
                val, location = self.getThresholdFromResult(i)
                self.thData['rows'][i][3] = val
                self.thData['rows'][i][4] = location

        self.thresholdLayout.updateData(self.thData['rows'])
    
    def getThresholdFromResult(self, idx):
        arr = [
            self.profile.gclear_rel,                        # Ground clearance
            self.result['force']['MaxSeilzugkraft'][0],     # Max force on cable
            self.result['force']['Sattelkraft_Total'][0],   # Max force on pole
            self.result['force']['Anlegewinkel_Lastseil'],  # Cable angle
            self.result['force']['Nachweis'],               # Prove
        ]
        val = None
        valStr = ""
        location = []

        if idx == 0:
            # Ground clearance
            val = np.nanmin(arr[idx])
            location = np.ravel(
                np.argwhere(arr[idx] < self.thData['thresholds'][idx]))
        elif idx in [1, 2]:
            # Max force on cable and on pole
            val = np.nanmax(arr[idx])
            location = np.ravel(
                np.argwhere(arr[idx] > self.thData['thresholds'][idx]))
        elif idx == 3:
            # Cable angle
            val = np.nanmax(arr[idx])
            location = np.unique(np.concatenate((
                np.rollaxis(np.argwhere(arr[idx] > 30), 1)[1],
                np.rollaxis(np.argwhere(arr[idx] < 0), 1)[1])
            ))
        elif idx == 4:
            # Prove
            valStr = 'nein' if 'nein' in arr[idx] else 'ja'
            location = [i for i, m in enumerate(arr[idx]) if m == 'nein']
        
        if isinstance(val, float) and val is not np.nan:
            valStr = f"{round(val, 1)} {self.thData['units'][idx]}"

        return valStr, location
    
    def onClose(self):
        self.close()
    
    def onReturnToStart(self):
        self.doReRun = True
        self.close()
    
    def onSave(self):
        self.saveDialog.doSave = False
        self.saveDialog.exec()
        if self.saveDialog.doSave:
            self.confHandler.updateUserSettings()
            self.createOutput()
            self.unsavedChanges = False
    
    def createOutput(self):
        outputFolder = self.confHandler.getCurrentPath()
        project = self.confHandler.project
        projName = project.getProjectName()
        outputLoc = createOutputFolder(outputFolder, projName)
        updateWithCableCoordinates(self.cableline, project.points['A'],
                                   project.azimut)
        # Save project file
        self.confHandler.saveToFile(os.path.join(outputLoc,  outputLoc + '_projectfile.txt'))

        # Create report
        if self.confHandler.getOutputOption('report'):
            reportSavePath = os.path.join(outputLoc, f"{projName}_Bericht.pdf")
            reportText = generateReportText(self.confHandler, self.result,
                                            self.fieldComment.toPlainText())
            generateReport(reportText, reportSavePath, projName)

        # Create plot
        if self.confHandler.getOutputOption('plot'):
            plotSavePath = os.path.join(outputLoc, f'{projName}_Diagramm.pdf')
            printPlot = AdjustmentPlot(self)
            printPlot.initData(self.profile.di_disp, self.profile.zi_disp)
            printPlot.updatePlot(self.poles.getAsArray(), self.cableline, True)
            printPlot.printToPdf(plotSavePath, projName, self.poles.poles)

        # Generate geo data
        if self.confHandler.getOutputOption('geodata'):
            geodata = generateGeodata(project, self.poles.poles,
                                      self.cableline, outputLoc)
            addToMap(geodata, projName)

        # Generate coordinate tables
        if self.confHandler.getOutputOption('coords'):
            table1SavePath = os.path.join(outputLoc, f'{projName}_KoordStuetzen.csv')
            table2SavePath = os.path.join(outputLoc, f'{projName}_KoordSeil.csv')
            generateCoordTable(self.cableline, self.profile, self.poles.poles,
                               [table1SavePath, table2SavePath])
        
        self.updateRecalcStatus('saveDone')

    def closeEvent(self, event):
        if self.isRecalculating or self.configurationHasChanged:
            return
        if self.unsavedChanges:
            reply = QMessageBox.information(self, 'Nicht gespeicherte Änderungen',
                'Möchten Sie die Ergebnisse speichern?', QMessageBox.No | QMessageBox.Yes)
            if reply == QMessageBox.Yes:
                self.onSave()
