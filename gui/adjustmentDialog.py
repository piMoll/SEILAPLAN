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

from qgis.PyQt.QtCore import QTimer, Qt
from qgis.PyQt.QtWidgets import QDialog, QMessageBox
from qgis.PyQt.QtGui import QPixmap

from .ui_adjustmentDialog import Ui_AdjustmenDialog
from .adjustmentPlot import AdjustmentPlot
from .guiHelperFunctions import MyNavigationToolbar
from .customWidgets import CustomPoleWidget
from .adjustmentDialog_params import AdjustmentDialogParams
from .adjustmentDialog_thresholds import AdjustmentDialogThresholds
from .saveDialog import DialogOutputOptions
from .mapMarker import MapMarkerTool
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
        self.status = None
        self.doReRun = False

        # Setup GUI from UI-file
        self.setupUi(self)

        self.drawTool = MapMarkerTool(self.iface.mapCanvas())
        
        # Create plot
        self.plot = AdjustmentPlot(self)
        # Pan/Zoom tools for plot, pan already active
        bar = MyNavigationToolbar(self.plot, self)
        bar.pan()
        self.plotLayout.addWidget(self.plot)
        self.plotLayout.addWidget(bar, alignment=Qt.AlignHCenter | Qt.AlignTop)

        # Fill tab widget with data
        self.poleLayout = CustomPoleWidget(self.tabPoles, self.poleVGrid)
        # self.poleLayout.sig_zoomIn.connect(self.zoomToPole)
        # self.poleLayout.sig_zoomOut.connect(self.zoomOut)
        self.poleLayout.sig_createPole.connect(self.addPole)
        self.poleLayout.sig_updatePole.connect(self.updatePole)
        self.poleLayout.sig_deletePole.connect(self.deletePole)
        
        self.thresholdLayout = AdjustmentDialogThresholds(self, self.thSize)
        self.thresholdLayout.sig_clickedRow.connect(self.showThresholdInPlot)

        self.paramLayout = AdjustmentDialogParams(self, self.confHandler.params)

        # Thread for instant recalculation when poles or parameters are changed
        self.timer = QTimer()
        self.configurationHasChanged = False
        self.isRecalculating = False
        self.unsavedChanges = True

        # Save dialog
        self.saveDialog = DialogOutputOptions(self, self.confHandler)
        
        # Connect signals
        self.btnClose.clicked.connect(self.onClose)
        self.btnSave.clicked.connect(self.onSave)
        self.btnBackToStart.clicked.connect(self.onReturnToStart)
        self.fieldComment.textChanged.connect(self.onCommentChanged)

    def loadData(self, pickleFile):
        """ Is used to load testdata from pickl object in debug mode """
        f = open(pickleFile, 'rb')
        dump = pickle.load(f)
        f.close()

        self.poles.poles = dump['poles']
        self.poles.calculateAnchor()

        self.initData(dump, 'optiSuccess')
        
    def initData(self, result, status):
        if not result:
            self.close()
        # Save original data from optimization
        self.originalData = result
        # Dictionary properties: cableline, optSTA, force, optLen, optLen_arr, duration
        self.result = result
        # Algorithm was skipped, no optimized solution
        if status in ['jumpedOver', 'savedFile']:
            try:
                params = self.confHandler.params.getSimpleParameterDict()
                cableline, force, \
                    seil_possible = preciseCable(params, self.poles,
                                                 self.result['optSTA'])
                self.result['cableline'] = cableline
                self.result['force'] = force

            except Exception as e:
                QMessageBox.critical(self,
                    'Unerwarteter Fehler bei Berechnung der Seillinie',
                                     str(e), QMessageBox.Ok)
                return

        self.cableline = self.result['cableline']
        self.profile.updateProfileAnalysis(self.cableline, self.poles.poles)

        self.updateRecalcStatus(status)

        # Draw profile in diagram
        self.plot.initData(self.profile.di_disp, self.profile.zi_disp,
                           self.profile.peakLoc_x, self.profile.peakLoc_z)
        self.plot.updatePlot(self.poles.getAsArray(), self.cableline)
    
        # Create layout to modify poles
        lowerDistRange = -1*self.anchorBuffer
        upperDistRange = self.poles.poles[-1]['d'] + self.anchorBuffer
        self.poleLayout.setInitialGui(self.poles.poles, [lowerDistRange, upperDistRange])

        # Fill in cable parameters
        self.paramLayout.fillInParams()
        
        # Fill in Threshold data
        self.updateThresholds()
        
        # Mark profile line and poles on map
        self.updateLineOnMap()
        self.addMarkerToMap()

        # Start Thread to recalculate cable line every 300 milliseconds
        self.timer.timeout.connect(self.recalculate)
        self.timer.start(300)
        
        self.plot.zoomOut()
    
    def zoomToPole(self, idx):
        self.plot.zoomTo(self.poles.poles[idx])
        self.plot.updatePlot(self.poles.getAsArray(), self.cableline)
    
    def zoomOut(self):
        self.plot.zoomOut()
        self.plot.updatePlot(self.poles.getAsArray(), self.cableline)

    def updatePole(self, idx, property_name, newVal):
        self.poles.update(idx, property_name, newVal)
       
        # Update pole markers on map except if its an anchor
        if property_name == 'd' and 0 < idx < len(self.poles.poles)-1:
            self.updateMarkerOnMap(idx)
            # If star or end pole have changed, the profile line is also updated
            if idx in [1, len(self.poles.poles) - 2]:
                self.updateLineOnMap()

        # self.plot.zoomTo(self.poles.poles[idx])
        self.poleLayout.changeRow(idx, property_name, newVal)
        self.plot.updatePlot(self.poles.getAsArray(), self.cableline)
        self.configurationHasChanged = True
    
    def addPole(self, idx):
        newPoleIdx = idx + 1
        oldLeftIdx = idx
        oldRightIdx = idx + 1
        lowerRange = self.poles.poles[oldLeftIdx]['d']
        upperRange = self.poles.poles[oldRightIdx]['d']
        rangeDist = upperRange - lowerRange
        d = floor(lowerRange + 0.5 * rangeDist)
        
        self.poles.add(newPoleIdx, d, manually=True)

        self.poleLayout.addRow(
            newPoleIdx, self.poles.poles[newPoleIdx]['name'], d, lowerRange,
            upperRange, self.poles.poles[newPoleIdx]['h'],
            self.poles.poles[newPoleIdx]['angle'])
        self.addMarkerToMap(newPoleIdx)
        # self.plot.zoomOut()
        self.plot.updatePlot(self.poles.getAsArray(), self.cableline)
        self.configurationHasChanged = True

    def deletePole(self, idx):
        self.poles.delete(idx)
        self.poleLayout.deleteRow(idx, self.poles.poles[idx-1]['d'],
                                  self.poles.poles[idx+1]['d'])
        self.drawTool.removeMarker(idx-1)
        # self.plot.zoomOut()
        self.plot.updatePlot(self.poles.getAsArray(), self.cableline)
        self.configurationHasChanged = True
    
    def updateLineOnMap(self):
        startPole = self.poles.poles[1]
        endPole = self.poles.poles[-2]
        self.drawTool.updateLine([
                [startPole['coordx'], startPole['coordy']],
                [endPole['coordx'], endPole['coordy']]], False)
    
    def addMarkerToMap(self, idx=-1):
        # Mark all poles except anchors on map
        if idx == -1:
            for pole in self.poles.poles[1:-1]:
                self.drawTool.drawMarker([pole['coordx'], pole['coordy']])
        else:
            # Add a new pole to the map
            pole = self.poles.poles[idx]
            self.drawTool.drawMarker([pole['coordx'], pole['coordy']], idx-1)
    
    def updateMarkerOnMap(self, idx):
        point = [self.poles.poles[idx]['coordx'],
                 self.poles.poles[idx]['coordy']]
        self.drawTool.updateMarker(point, idx-1)
    
    def updateOptSTA(self, newVal):
        self.result['optSTA'] = float(newVal)
        return str(newVal)
    
    def updateCableParam(self):
        self.configurationHasChanged = True
    
    def onCommentChanged(self):
        self.unsavedChanges = True
    
    def updateRecalcStatus(self, status):
        self.status = status
        ico_path = os.path.join(os.path.dirname(__file__), 'icons')
        if status == 'optiSuccess':
            self.recalcStatus_txt.setText(
                'Optimierung erfolgreich abgeschlossen.')
            self.recalcStatus_ico.setPixmap(QPixmap(os.path.join(
                ico_path, 'icon_green.png')))
        elif status == 'liftsOff':
            self.recalcStatus_txt.setText(
                'Die Seillinie wurde berechnet, das Tragseil hebt jedoch '
                'bei mindestens einer Stütze ab.')
            self.recalcStatus_ico.setPixmap(QPixmap(os.path.join(
                ico_path, 'icon_yellow.png')))
        elif status == 'notComplete':
            self.recalcStatus_txt.setText(
                'Die Seillinie konnte nicht komplett berechnet werden, '
                'es sind nicht genügend\nStützenstandorte bestimmbar.')
            self.recalcStatus_ico.setPixmap(QPixmap(os.path.join(
                ico_path, 'icon_yellow.png')))
        elif status == 'jumpedOver':
            self.recalcStatus_txt.setText(
                'Optimierung wurde übersprungen, Stützen müssen manuell '
                'platziert werden.')
            self.recalcStatus_ico.setPixmap(QPixmap(os.path.join(
                ico_path, 'icon_green.png')))
        elif status == 'savedFile':
            self.recalcStatus_txt.setText(
                'Optimierung wurde übersprungen, Stützen wurden aus '
                'Projektdatei geladen.')
            self.recalcStatus_ico.setPixmap(QPixmap(os.path.join(
                ico_path, 'icon_green.png')))
        elif status == 'cableSuccess':
            self.recalcStatus_txt.setText('Seillinie neu berechnet.')
            self.recalcStatus_ico.setPixmap(QPixmap(os.path.join(
                ico_path, 'icon_green.png')))
        elif status == 'cableError':
            self.recalcStatus_txt.setText('Bei der Berechnung der Seillinie '
                'ist ein Fehler aufgetreten.')
            self.recalcStatus_ico.setPixmap(QPixmap(os.path.join(
                ico_path, 'icon_yellow.png')))
        elif status == 'saveDone':
            self.recalcStatus_txt.setText('Ergebnisse gespeichert.')
            self.recalcStatus_ico.setPixmap(QPixmap(os.path.join(
                ico_path, 'icon_save.png')))
    
    def recalculate(self):
        if not self.configurationHasChanged or self.isRecalculating:
            return
        self.isRecalculating = True
        
        try:
            params = self.confHandler.params.getSimpleParameterDict()
            cableline, force, seil_possible = preciseCable(params, self.poles,
                                                           self.result['optSTA'])
        except Exception as e:
            self.updateRecalcStatus('cableError')
            self.isRecalculating = False
            self.configurationHasChanged = False
            # TODO: Error handling when shape mismach
            # QMessageBox.critical(self, 'Unerwarteter Fehler bei Neuberechnung '
            #     'der Seillinie', str(e), QMessageBox.Ok)
            return

        self.cableline = cableline
        self.result['force'] = force
        
        # Ground clearance
        try:
            self.profile.updateProfileAnalysis(self.cableline, self.poles.poles)
        except ValueError:
            # TODO: Wrong Array lengths, just ignore for the moment because
            #  there has to be some error in cable line function
            # QMessageBox.critical(self, 'Fehler', 'Fehler bei Berechnung des '
            #                      'Bodenabstands', QMessageBox.Ok)
            pass
        
        # Update Plot
        [pole_d, pole_z, pole_h, pole_dtop, pole_ztop] = self.poles.getAsArray()
        self.plot.updatePlot([pole_d, pole_z, pole_h, pole_dtop, pole_ztop],
                             self.cableline)
        
        # Update Threshold data
        self.updateThresholds()

        # cable line lifts off of pole
        if not seil_possible:
            self.updateRecalcStatus('liftsOff')
        else:
            self.updateRecalcStatus('cableSuccess')
        self.configurationHasChanged = False
        self.isRecalculating = False
        self.unsavedChanges = True
    
    def updateThresholds(self):
        params = self.confHandler.params
        resultData = [
            self.cableline['groundclear_rel'],  # Distance cable - terrain
            self.result['force']['MaxSeilzugkraft'][0],  # Max force on cable
            self.result['force']['Sattelkraft_Total'][0],  # Max force on pole
            self.result['force']['Anlegewinkel_Lastseil'],  # Cable angle
            self.result['force']['Nachweis'],  # Prove
        ]
        
        if not self.thData:
            rows = [['' for cell in range(self.thSize[1])]
                    for row in range(self.thSize[0])]
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
                float(params.getParameter('zul_SK')),
                float(params.getParameter('zul_SK')),
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
            # Where to put the current threshold values
            valColumn = 2
            emptyColumn = 3
            if self.status in ['jumpedOver', 'savedFile']:
                # No optimization was run, so no optimal solution
                valColumn = 3
                emptyColumn = 2
            
            for i in range(self.thSize[0]):
                val, location = self.checkThresholdAndLocation(i, resultData[i])
                self.thData['rows'][i][0] = label[i]
                self.thData['rows'][i][1] = thresholdStr[i]
                self.thData['rows'][i][valColumn] = val
                self.thData['rows'][i][emptyColumn] = ''
                self.thData['rows'][i][4] = location
            
            self.thresholdLayout.populate(header, self.thData['rows'], valColumn)
        
        else:
            for i in range(len(self.thData['rows'])):
                val, location = self.checkThresholdAndLocation(i, resultData[i])
                self.thData['rows'][i][3] = val
                self.thData['rows'][i][4] = location

            self.thresholdLayout.updateData(self.thData['rows'])
    
    def checkThresholdAndLocation(self, idx, data):
        val = None
        valStr = ""
        location = []

        # Ground clearance
        if idx == 0:
            if np.isnan(data).all():
                return valStr, location
            val = np.nanmin(data)
            # Check if min value is smaller than ground clearance
            if val < self.thData['thresholds'][idx]:
                # Replace nan so there is no Runtime Warning in np.argwhere()
                localCopy = np.copy(data)
                localCopy[np.isnan(localCopy)] = 100.0
                location = np.ravel(np.argwhere(localCopy == val))
        
        # Max force on cable and on pole
        elif idx in [1, 2]:
            # Replace nan with 0 so that no Runtime Warning is thrown in
            # np.argwhere()
            localCopy = np.nan_to_num(data)
            val = np.max(localCopy)
            location = np.argwhere(localCopy > self.thData['thresholds'][idx])
            if len(location) != 0:
                location = np.ravel(location)
        
        # Cable angle
        elif idx == 3:
            # Replace nan with 0 so that no Runtime Warning is thrown
            localCopy = np.nan_to_num(data)
            # Transform negative values to values over 30, so we have to do
            # only one check
            localCopy[localCopy < 0] -= 30
            localCopy[localCopy < 0] *= -1
            val = np.nanmax(localCopy)
            locationPole = np.unique(np.rollaxis(
                np.argwhere(localCopy > 30), 1)[1])
            for loc in locationPole:
                location.append(int(self.poles.poles[loc+1]['d']))
        
        # Proof: Only test for poles that are not first and last pole
        elif idx == 4:
            valStr = 'Nein' if 'Nein' in data[1:-1] else 'Ja'
            locationPole = [i for i, m in enumerate(data[1:-1]) if m == 'Nein']
            for loc in locationPole:
                location.append(int(self.poles.poles[loc+1]['d']))
        
        if isinstance(val, float) and val is not np.nan:
            valStr = f"{round(val, 1)} {self.thData['units'][idx]}"

        return valStr, location

    def showThresholdInPlot(self, row):
        location = self.thData['rows'][row][4]
        arrIdx = []
        for l in location:
            arrIdx.append(np.argwhere(self.profile.di_disp == l)[0][0])
        z = self.profile.zi_disp[arrIdx]
        self.plot.showArrow(location, z)
    
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
        outputLoc = createOutputFolder(os.path.join(outputFolder, projName))
        updateWithCableCoordinates(self.cableline, project.points['A'],
                                   project.azimut)
        # Save project file
        self.confHandler.saveToFile(os.path.join(outputLoc,
                                                 'Projekteinstellungen.txt'))

        # Create report
        if self.confHandler.getOutputOption('report'):
            reportText = generateReportText(self.confHandler, self.result,
                                            self.fieldComment.toPlainText())
            generateReport(reportText, outputLoc, projName)

        # Create plot
        if self.confHandler.getOutputOption('plot'):
            plotSavePath = os.path.join(outputLoc, 'Diagramm.pdf')
            printPlot = AdjustmentPlot(self)
            printPlot.initData(self.profile.di_disp, self.profile.zi_disp,
                               self.profile.peakLoc_x, self.profile.peakLoc_z)
            printPlot.updatePlot(self.poles.getAsArray(), self.cableline, True)
            printPlot.printToPdf(plotSavePath, projName, self.poles.poles)

        # Generate geo data
        if self.confHandler.getOutputOption('geodata'):
            geodata = generateGeodata(project, self.poles.poles,
                                      self.cableline, outputLoc)
            addToMap(geodata, projName)

        # Generate coordinate tables
        if self.confHandler.getOutputOption('coords'):
            generateCoordTable(self.cableline, self.profile, self.poles.poles,
                               outputLoc)
        
        self.updateRecalcStatus('saveDone')

    def closeEvent(self, event):
        if self.isRecalculating or self.configurationHasChanged:
            return
        if self.unsavedChanges:
            reply = QMessageBox.information(self, 'Nicht gespeicherte Änderungen',
                'Möchten Sie die Ergebnisse speichern?', QMessageBox.Cancel |
                                            QMessageBox.No | QMessageBox.Yes)
            if reply == QMessageBox.Yes:
                self.onSave()
                self.drawTool.reset()
            elif reply == QMessageBox.Cancel:
                event.ignore()
            elif reply == QMessageBox.No:
                self.drawTool.reset()
        else:
            self.drawTool.reset()
