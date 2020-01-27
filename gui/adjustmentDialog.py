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
        self.anchorBuffer = self.confHandler.project.heightSource.buffer

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
        self.selectedThresholdRow = None

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
        self.poles.calculateAnchorLength()

        self.initData(dump, 'optiSuccess')
        
    def initData(self, result, status):
        if not result:
            self.close()
        # Save original data from optimization
        self.originalData = result
        # result properties: cable line, optSTA, force, optLen, optLen_arr,
        #  duration
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
        self.profile.updateProfileAnalysis(self.cableline)

        self.updateRecalcStatus(status)

        # Draw profile in diagram
        self.plot.initData(self.profile.di_disp, self.profile.zi_disp,
                           self.profile.peakLoc_x, self.profile.peakLoc_z,
                           self.profile.surveyPnts)
        self.plot.updatePlot(self.poles.getAsArray(), self.cableline)
    
        # Create layout to modify poles
        lowerDistRange = floor(-1*self.anchorBuffer[0])
        upperDistRange = floor(self.poles.lastPole['d'] + self.anchorBuffer[1])
        self.poleLayout.setInitialGui([lowerDistRange, upperDistRange], self.poles)

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
       
        # Update markers on map
        if property_name == 'd':
            self.updateMarkerOnMap(idx)
            if idx in [self.poles.idxA, self.poles.idxE]:
                self.updateLineOnMap()
        
        # Anchor was deactivated
        elif property_name == 'active' and newVal is False:
            # Update range of neighbouring pole
            lowerRange = None
            upperRange = None
            if idx > 0:
                lowerRange = self.poles.poles[idx - 1]['d']
            if idx < len(self.poles.poles) - 1:
                upperRange = self.poles.poles[idx + 1]['d']
            self.poleLayout.deactivateRow(idx, lowerRange, upperRange)
            self.drawTool.hideMarker(idx)
            
        # Anchor was activated
        elif property_name == 'active' and newVal is True:
            # Update new distance ranges of neighbouring poles
            if idx == 0:
                if self.poles.poles[0]['d'] < self.poles.firstPole['d']:
                    dist = self.poles.poles[0]['d']
                else:
                    dist = self.poles.firstPole['d'] - self.poles.POLE_DIST_STEP
            else:
                if self.poles.poles[-1]['d'] > self.poles.lastPole['d']:
                    dist = self.poles.poles[-1]['d']
                else:
                    dist = self.poles.lastPole['d'] + self.poles.POLE_DIST_STEP
            # Update new distance value in Poles class
            self.poles.update(idx, 'd', dist)
            # Update distance of anchor in gui (and distance range of neighbours)
            self.poleLayout.changeRow(idx, 'd', dist)
            # Activate input fields
            self.poleLayout.activateRow(idx, dist)
            point = [self.poles.poles[idx]['coordx'],
                    self.poles.poles[idx]['coordy']]
            self.drawTool.showMarker(point, idx, 'anchor')

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
        lowerRange = None
        upperRange = None
        if idx > 0:
            lowerRange = self.poles.poles[idx-1]['d']
        if idx < len(self.poles.poles)-1:
            upperRange = self.poles.poles[idx+1]['d']
        self.poleLayout.deleteRow(idx, lowerRange, upperRange)
        self.drawTool.removeMarker(idx)
        # self.plot.zoomOut()
        self.plot.updatePlot(self.poles.getAsArray(), self.cableline)
        self.configurationHasChanged = True
    
    def updateLineOnMap(self):
        self.drawTool.updateLine(
            [[self.poles.firstPole['coordx'], self.poles.firstPole['coordy']],
             [self.poles.lastPole['coordx'], self.poles.lastPole['coordy']]],
            drawMarker=False)
    
    def addMarkerToMap(self, idx=-1):
        # Mark all poles except anchors on map
        if idx == -1:
            for idx, pole in enumerate(self.poles.poles):
                self.drawTool.drawMarker([pole['coordx'], pole['coordy']],
                                         idx, pointType=pole['poleType'],
                                         firstPoint=(idx == self.poles.idxA))
                if not pole['active']:
                    self.drawTool.hideMarker(idx)
        else:
            # Add a new pole to the map
            pole = self.poles.poles[idx]
            self.drawTool.drawMarker([pole['coordx'], pole['coordy']], idx,
                                     pointType=pole['poleType'])
    
    def updateMarkerOnMap(self, idx):
        point = [self.poles.poles[idx]['coordx'],
                 self.poles.poles[idx]['coordy']]
        self.drawTool.updateMarker(point, idx)
    
    def updateOptSTA(self, newVal):
        self.result['optSTA'] = float(newVal)
        return str(newVal)
    
    def updateCableParam(self):
        self.configurationHasChanged = True
    
    def onCommentChanged(self):
        self.unsavedChanges = True
    
    def updateRecalcStatus(self, status):
        self.status = status
        color = None
        green = '#b6ddb5'
        yellow = '#f4e27a'
        red = '#e8c4ca'
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
            color = yellow
        elif status == 'notComplete':
            self.recalcStatus_txt.setText(
                'Die Seillinie konnte nicht komplett berechnet werden, '
                'es sind nicht genügend\nStützenstandorte bestimmbar.')
            self.recalcStatus_ico.setPixmap(QPixmap(os.path.join(
                ico_path, 'icon_yellow.png')))
            color = yellow
        elif status == 'jumpedOver':
            self.recalcStatus_txt.setText(
                'Optimierung wurde übersprungen, Stützen müssen manuell '
                'platziert werden.')
            self.recalcStatus_ico.setPixmap(QPixmap(os.path.join(
                ico_path, 'icon_green.png')))
            color = yellow
        elif status == 'savedFile':
            self.recalcStatus_txt.setText(
                'Optimierung wurde übersprungen, Stützen wurden aus '
                'Projektdatei geladen.')
            self.recalcStatus_ico.setPixmap(QPixmap(os.path.join(
                ico_path, 'icon_green.png')))
            color = yellow
        elif status == 'cableSuccess':
            self.recalcStatus_txt.setText('Seillinie neu berechnet.')
            self.recalcStatus_ico.setPixmap(QPixmap(os.path.join(
                ico_path, 'icon_green.png')))
        elif status == 'cableError':
            self.recalcStatus_txt.setText('Bei der Berechnung der Seillinie '
                'ist ein Fehler aufgetreten.')
            self.recalcStatus_ico.setPixmap(QPixmap(os.path.join(
                ico_path, 'icon_yellow.png')))
            color = red
        elif status == 'saveDone':
            self.recalcStatus_txt.setText('Ergebnisse gespeichert.')
            self.recalcStatus_ico.setPixmap(QPixmap(os.path.join(
                ico_path, 'icon_save.png')))
            color = green
        stylesheet = ''
        if color:
            stylesheet = f"background-color:{color};"
        self.recalcStatus_txt.setStyleSheet(stylesheet)
    
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
        self.profile.updateProfileAnalysis(self.cableline)
        
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
        resultData = [
            self.cableline['groundclear_rel'],  # Distance cable - terrain
            self.result['force']['MaxSeilzugkraft'][0],  # Max force on cable
            self.result['force']['Sattelkraft_Total'][0],  # Max force on pole
            self.result['force']['Anlegewinkel_Lastseil'],  # Cable angle
            self.result['force']['Nachweis'],  # Prove
        ]
        
        if not self.thData:
            # Fill table with initial data
            self.initThresholdData(resultData)
        
        else:
            # Cable was recalculated, update threshold values
            self.thData['plotLabels'] = []
            for i in range(len(self.thData['rows'])):
                val, location, \
                    plotLabels = self.checkThresholdAndLocation(i, resultData[i])
                self.thresholdLayout.updateData(i, 3, val)
                self.thresholdLayout.updateData(i, 4, location)
                self.thData['rows'][i][3] = val
                self.thData['rows'][i][4] = location
                self.thData['plotLabels'].append(plotLabels)
        
        self.showThresholdInPlot()
    
    def initThresholdData(self, resultData):
        params = self.confHandler.params
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
            params.params['min_SK']['unit'],
            params.params['min_SK']['unit'],
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
            'thresholds': thresholds,
            'plotLabels': []
        }
        label = [
            'Minimaler Bodenabstand',
            'Max. auftretende Seilzugkraft\n(am Lastseil, Last in Feldmitte)',
            'Max. resultierende Sattelkraft\n(an befahrbarer Stütze, Last auf Stütze)',
            'Seilwinkel am Lastseil\n(eingehend / ausgehend)',
            'Nachweis erbracht, dass Seil nicht vom Sattel abhebt',
        ]
        thresholdStr = [
            f"{params.getParameterAsStr('Bodenabst_min')} {units[0]}",
            f"{params.getParameter('zul_SK')} {units[1]}",
            f"{params.getParameter('zul_SK')} {units[2]}",
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
            val, location, \
                plotLabels = self.checkThresholdAndLocation(i, resultData[i])
            self.thData['rows'][i][0] = label[i]
            self.thData['rows'][i][1] = thresholdStr[i]
            self.thData['rows'][i][valColumn] = val
            self.thData['rows'][i][emptyColumn] = ''
            self.thData['rows'][i][4] = location
            self.thData['plotLabels'].append(plotLabels)
    
        self.thresholdLayout.populate(header, self.thData['rows'], valColumn)
    
    def checkThresholdAndLocation(self, idx, data):
        maxVal = None
        # Formatted value to insert into threshold table
        valStr = ""
        # Location in relation to origin on horizontal axis (needed for
        #  plotting)
        location = []
        # Formatted threshold value to show in plot
        plotLabel = []

        # Ground clearance
        if idx == 0:
            if np.isnan(data).all():
                return valStr, location
            maxVal = np.nanmin(data)
            # Check if min value is smaller than ground clearance
            if maxVal < self.thData['thresholds'][idx]:
                # Replace nan so there is no Runtime Warning in np.argwhere()
                localCopy = np.copy(data)
                localCopy[np.isnan(localCopy)] = 100.0
                # Check where the minimal ground clearance is located
                location = np.ravel(np.argwhere(localCopy == maxVal))
                if location:
                    plotLabel = [self.formatThreshold(l, idx) for l in localCopy[location]]
                location = [int(l + self.poles.firstPole['d']) for l in location]
        
        # Max force on cable and on pole
        elif idx in [1, 2]:
            # Replace nan with 0 so that no Runtime Warning is thrown in
            # np.argwhere()
            localCopy = np.nan_to_num(data)
            maxVal = np.max(localCopy)
            location = np.argwhere(localCopy > self.thData['thresholds'][idx])
            if len(location) != 0:
                plotLabel = np.ravel(localCopy[location])
                plotLabel = [self.formatThreshold(l, idx) for l in plotLabel]
                locationIdx = np.ravel(location)
                if idx == 1:
                    # Force is calculated in the middle of the field, so
                    #  marker should also be in the middle between two poles
                    location = []
                    for field in locationIdx:
                        leftPole = self.poles.poles[self.poles.idxA + field]['d']
                        rightPole = self.poles.poles[self.poles.idxA + field + 1]['d']
                        location.append(int(leftPole + floor((rightPole - leftPole) / 2)))
                elif idx == 2:
                    # Force is located at pole, so we need horizontal distance
                    #  of poles
                    location = [int(self.poles.poles[self.poles.idxA + l]['d']) for l in locationIdx]
        
        # Cable angle
        elif idx == 3:
            # Replace nan with 0 so that no Runtime Warning is thrown
            localCopy = np.nan_to_num(data)
            # Transform negative values to values over 30, so we have to do
            #  only do one check
            localCopy[localCopy < 0] -= 30
            localCopy[localCopy < 0] *= -1
            maxVal = np.nanmax(localCopy)
            greaterThan = localCopy > 30
            # Check which pole is affected
            locationPole = np.ravel(np.argwhere(np.any(greaterThan, 0)))
            # Generate labels: For every pole, there is an incoming and
            #  outgoing angle which has to be extracted and correctly formatted
            if len(locationPole) != 0:
                # Transpose arrays to get incoming / outgoing angle pairwise
                dataT = data.T
                greaterThanT = greaterThan.T
                for i, gT in enumerate(greaterThanT):
                    if not np.any(gT):
                        continue
                    txt = ''
                    if gT[0]:       # incoming angle
                        txt += f'ein: {self.formatThreshold(dataT[i][0], idx)}\n'
                    elif gT[1]:     # outgoing angle
                        txt += f'aus: {self.formatThreshold(dataT[i][1], idx)}'
                    plotLabel.append(txt)
                for loc in locationPole:
                    # Get horizontal distance of affected poles
                    location.append(int(self.poles.poles[loc + self.poles.idxA]['d']))
        
        # Proof: Only test for poles that are not first and last pole
        elif idx == 4:
            valStr = 'Nein' if 'Nein' in data[1:-1] else 'Ja'
            # Without first and last pole!
            locationPole = [i for i, m in enumerate(data[1:-1]) if m == 'Nein']
            for loc in locationPole:
                location.append(int(self.poles.poles[loc + self.poles.idxA + 1]['d']))
        
        if isinstance(maxVal, float) and maxVal is not np.nan:
            valStr = self.formatThreshold(maxVal, idx)

        return valStr, location, plotLabel

    def formatThreshold(self, val, idx):
        if isinstance(val, float) and val is not np.nan:
            return f"{round(val, 1)} {self.thData['units'][idx]}"

    def showThresholdInPlot(self, row=None):
        # Click on row was emitted but row is already selected -> deselect
        if row is not None and row == self.selectedThresholdRow:
            # Remove markers from plot
            self.plot.removeMarkers()
            self.selectedThresholdRow = None
            return
        # There was no new selection but a redraw of the table was done, so
        #  current selection has be added to the plot again
        if row is None:
            if self.selectedThresholdRow is not None:
                row = self.selectedThresholdRow
            # Nothing is selected at the moment
            else:
                return
        
        location = self.thData['rows'][row][4]
        arrIdx = []
        # Get index of horizontal distance so we know which height value to
        #  chose
        if row in [2, 3, 4]:
            # For thresholds that correspond to a pole
            for loc in location:
                arrIdx.append(np.argwhere(self.profile.di_disp == loc)[0][0])
            z = self.profile.zi_disp[arrIdx]
        else:  # row in [0, 1]
            # For thresholds that correspond to cable
            z = self.cableline['groundclear'][location]
        self.plot.showMarkers(location, z, self.thData['plotLabels'][row])
        self.selectedThresholdRow = row
    
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
                               self.profile.peakLoc_x, self.profile.peakLoc_z,
                               self.profile.surveyPnts)
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

        self.timer.stop()
