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

from qgis.PyQt.QtCore import QTimer, Qt, QCoreApplication
from qgis.PyQt.QtWidgets import QDialog, QMessageBox
from qgis.PyQt.QtGui import QPixmap

from .ui_adjustmentDialog import Ui_AdjustmentDialogUI
from .adjustmentPlot import AdjustmentPlot
from .plotting_tools import MyNavigationToolbar
from .poleWidget import CustomPoleWidget
from .adjustmentDialog_params import AdjustmentDialogParams
from .adjustmentDialog_thresholds import AdjustmentDialogThresholds
from .saveDialog import DialogOutputOptions
from .mapMarker import MapMarkerTool
from ..tool.cablelineFinal import preciseCable, updateWithCableCoordinates
from ..tool.outputReport import generateReportText, generateReport, createOutputFolder, generateShortReport
from ..tool.outputGeo import organizeDataForExport, addToMap, \
    generateCoordTable, exportToShape, exportToKML


class AdjustmentDialog(QDialog, Ui_AdjustmentDialogUI):
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
        self.thSize = [5, 6]
        self.thData = {}
        self.status = None
        self.doReRun = False
        
        # Setup GUI from UI-file
        self.setupUi(self)
        
        self.drawTool = MapMarkerTool(self.iface.mapCanvas())
        
        # Create plot
        self.plot = AdjustmentPlot(self)
        # Pan/Zoom tools for plot, pan already active
        tbar = MyNavigationToolbar(self.plot, self)
        tbar.pan()
        self.plot.setToolbar(tbar)
        self.plotLayout.addWidget(self.plot)
        self.plotLayout.addWidget(tbar, alignment=Qt.AlignHCenter | Qt.AlignTop)
        
        # Fill tab widget with data
        self.poleLayout = CustomPoleWidget(self.tabPoles, self.poleVGrid, self.poles)
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
    
    # noinspection PyMethodMayBeStatic
    def tr(self, message, **kwargs):
        """Get the translation for a string using Qt translation API.
        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString

        Parameters
        ----------
        **kwargs
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate(type(self).__name__, message)
    
    def loadData(self, pickleFile):
        """ Is used to load testdata from pickl object in debug mode """
        f = open(pickleFile, 'rb')
        dump = pickle.load(f)
        f.close()
        
        self.poles.poles = dump['poles']
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
                QMessageBox.critical(self, self.tr('Unerwarteter Fehler '
                    'bei Berechnung der Seillinie'), str(e), QMessageBox.Ok)
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
        lowerDistRange = floor(-1 * self.anchorBuffer[0])
        upperDistRange = floor(self.profile.profileLength + self.anchorBuffer[1])
        self.poleLayout.setInitialGui([lowerDistRange, upperDistRange])

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
        prevAnchorA = self.poles.hasAnchorA is True
        prevAnchorE = self.poles.hasAnchorE is True
        self.poles.update(idx, property_name, newVal)
        # Update markers on map
        for i, pole in enumerate(self.poles.poles):
            if pole['active']:
                self.updateMarkerOnMap(i)
        self.updateLineOnMap()
        # Update anchors
        self.updateAnchorState(prevAnchorA, prevAnchorE)
        # self.plot.zoomTo(self.poles.poles[idx])
        self.poleLayout.changeRow(idx, property_name, newVal, prevAnchorA, prevAnchorE)
        if property_name == 'name':
            # No redraw when user only changes name
            return
        self.plot.updatePlot(self.poles.getAsArray(), self.cableline)
        self.configurationHasChanged = True
    
    def addPole(self, idx):
        newPoleIdx = idx + 1
        self.poles.add(newPoleIdx, None, manually=True)
        self.poleLayout.addRow(newPoleIdx)
        self.addMarkerToMap(newPoleIdx)
        # self.plot.zoomOut()
        self.plot.updatePlot(self.poles.getAsArray(), self.cableline)
        self.configurationHasChanged = True
    
    def deletePole(self, idx):
        self.poles.delete(idx)
        self.poleLayout.deleteRow(idx)
        self.drawTool.removeMarker(idx)
        # self.plot.zoomOut()
        self.plot.updatePlot(self.poles.getAsArray(), self.cableline)
        self.configurationHasChanged = True
    
    def updateAnchorState(self, prevAnchorA, prevAnchorE):
        """Update anchor markers on map: depending on nature of pole change,
        anchors can be activated or deactivated in self.poles.update."""
        if prevAnchorA is not self.poles.hasAnchorA:
            idxA = 0
            if self.poles.hasAnchorA:
                # Anchor A was activated
                point = [self.poles.poles[0]['coordx'],
                         self.poles.poles[0]['coordy']]
                self.drawTool.showMarker(point, idxA, 'anchor')
            else:
                # Anchor A was deactivated
                self.drawTool.hideMarker(idxA)

        if prevAnchorE is not self.poles.hasAnchorE:
            idxE = len(self.poles.poles)-1
            if self.poles.hasAnchorE:
                # Anchor E was activated
                point = [self.poles.poles[-1]['coordx'],
                         self.poles.poles[-1]['coordy']]
                self.drawTool.showMarker(point, idxE, 'anchor')
            else:
                # Anchor E was deactivated
                self.drawTool.hideMarker(idxE)
    
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
                self.tr('Optimierung erfolgreich abgeschlossen'))
            self.recalcStatus_ico.setPixmap(QPixmap(os.path.join(
                ico_path, 'icon_green.png')))
        elif status == 'liftsOff':
            self.recalcStatus_txt.setText(
                self.tr('Tragseil hebt bei mindestens einer Stuetze ab'))
            self.recalcStatus_ico.setPixmap(QPixmap(os.path.join(
                ico_path, 'icon_yellow.png')))
            color = yellow
        elif status == 'notComplete':
            self.recalcStatus_txt.setText(
                self.tr('Nicht genuegend Stuetzenstandorte bestimmbar'))
            self.recalcStatus_ico.setPixmap(QPixmap(os.path.join(
                ico_path, 'icon_yellow.png')))
            color = yellow
        elif status == 'jumpedOver':
            self.recalcStatus_txt.setText(
                self.tr('Stuetzen manuell platzieren'))
            self.recalcStatus_ico.setPixmap(QPixmap(os.path.join(
                ico_path, 'icon_green.png')))
            color = yellow
        elif status == 'savedFile':
            self.recalcStatus_txt.setText(
                self.tr('Stuetzen aus Projektdatei geladen'))
            self.recalcStatus_ico.setPixmap(QPixmap(os.path.join(
                ico_path, 'icon_green.png')))
            color = yellow
        elif status == 'cableSuccess':
            self.recalcStatus_txt.setText(self.tr('Seillinie neu berechnet.'))
            self.recalcStatus_ico.setPixmap(QPixmap(os.path.join(
                ico_path, 'icon_green.png')))
        elif status == 'cableError':
            self.recalcStatus_txt.setText(
                self.tr('Fehler aufgetreten'))
            self.recalcStatus_ico.setPixmap(QPixmap(os.path.join(
                ico_path, 'icon_yellow.png')))
            color = red
        elif status == 'saveDone':
            self.recalcStatus_txt.setText(self.tr('Ergebnisse gespeichert'))
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
        self.plot.updatePlot(self.poles.getAsArray(), self.cableline)
        
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
            self.result['force']['Lastseilknickwinkel'],  # Cable angle on pole
            self.result['force']['Leerseilknickwinkel'],  # Cable angle on pole
        ]
        
        if not self.thData:
            # Fill table with initial data
            self.initThresholdData(resultData)
        
        else:
            # Cable was recalculated, update threshold values
            self.thData['plotLabels'] = []
            for i in range(len(self.thData['rows'])):
                thresholdData = self.checkThresholdAndLocation(i, resultData[i])
                val = ''
                color = 1
                location = []
                plotLabels = []
                if len(thresholdData) == 4:
                    val, location, color, plotLabels = thresholdData
                self.thresholdLayout.updateData(i, 4, val)
                self.thresholdLayout.updateData(i, 5, {'loc': location, 'color': color})
                self.thData['rows'][i][4] = val
                self.thData['rows'][i][5] = {'loc': location, 'color': color}
                self.thData['plotLabels'].append(plotLabels)
        
        self.showThresholdInPlot()
    
    def initThresholdData(self, resultData):
        params = self.confHandler.params
        rows = [['' for cell in range(self.thSize[1])]
                for row in range(self.thSize[0])]
        header = [
            '',
            self.tr('Kennwert'),
            self.tr('Grenzwert'),
            self.tr('Optimierte Loesung'),
            self.tr('Aktuelle Loesung'),
            self.tr('Wo?')
        ]
        infoText = [
            {
                'title': self.tr('Minimaler Bodenabstand'),
                'message': self.tr('Es wird der im Parameterset definierte minimale Bodenabstand mit einer Aufloesung von 1m getestet.'),
            },
            {
                'title': self.tr('Max. auftretende Seilzugkraft'),
                'message': self.tr('Es wird die maximal auftretende Seilzugkraft am Lastseil mit der Last in Feldmitte berechnet.'),
            },
            {
                'title': self.tr('Max. resultierende Sattelkraft'),
                'message': self.tr('Es wird die maximal resultierende Sattelkraft an befahrbaren Stuetzen mit der Last auf der Stuetze berechnet.'),
            },
            {
                'title': self.tr('Max. Lastseilknickwinkel'),
                'message': self.tr('Groessere Knickwinkel reduzieren die Bruchlast des Tragseils und fuehren zu hoeheren Sattelkraeften.'),
            },
            {
                'title': self.tr('Min. Leerseilknickwinkel'),
                'message': self.tr('Bei Knickwinkeln unter 2 besteht die Gefahr, dass das Tragseil beim Sattel abhebt (rot). Bei Knickwinkeln zwischen 2 und 4 muss das Tragseil mittels Niederhaltelasche gesichert werden (orange).'),
            },
        ]
        
        units = [
            params.params['Bodenabst_min']['unit'],
            params.params['min_SK']['unit'],
            params.params['min_SK']['unit'],
            '°',
            '°'
        ]
        thresholds = [
            params.getParameter('Bodenabst_min'),
            float(params.getParameter('zul_SK')),
            None,
            [30, 60],
            [1, 3],
        ]
        self.thData = {
            'header': header,
            'rows': rows,
            'units': units,
            'thresholds': thresholds,
            'plotLabels': []
        }
        label = [
            self.tr('Minimaler Bodenabstand'),
            self.tr('Max. auftretende Seilzugkraft'),
            self.tr('Max. resultierende Sattelkraft'),
            self.tr('Max. Lastseilknickwinkel'),
            self.tr('Min. Leerseilknickwinkel')
        ]
        thresholdStr = [
            f"{params.getParameterAsStr('Bodenabst_min')} {units[0]}",
            f"{params.getParameter('zul_SK')} {units[1]}",
            '-',
            '30 / 60 °',
            '1 ; 3 °'
        ]
        # Where to put the current threshold values
        valColumn = 3
        emptyColumn = 4
        if self.status in ['jumpedOver', 'savedFile']:
            # No optimization was run, so no optimal solution
            valColumn = 4
            emptyColumn = 3
        
        for i in range(self.thSize[0]):
            thresholdData = self.checkThresholdAndLocation(i, resultData[i])
            val = ''
            color = 1
            location = []
            plotLabels = []
            if len(thresholdData) == 4:
                val, location, color, plotLabels = thresholdData
            self.thData['rows'][i][0] = infoText[i]
            self.thData['rows'][i][1] = label[i]
            self.thData['rows'][i][2] = thresholdStr[i]
            self.thData['rows'][i][valColumn] = val
            self.thData['rows'][i][emptyColumn] = ''
            self.thData['rows'][i][5] = {'loc': location, 'color': color}
            self.thData['plotLabels'].append(plotLabels)
        
        self.thresholdLayout.populate(header, self.thData['rows'], valColumn)
    
    def checkThresholdAndLocation(self, idx, data):
        maxVal = None
        # Formatted value to insert into threshold table
        valStr = ""
        # Location in relation to origin on horizontal axis (needed for
        #  plotting)
        location = []
        # Color of marked threshold
        color = 3   # black
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
                color = 1   # red
        
        # Max force on cable
        elif idx == 1:
            # Replace nan with 0 so that no Runtime Warning is thrown in
            # np.argwhere()
            localCopy = np.nan_to_num(data)
            maxVal = np.max(localCopy)
            location = np.argwhere(localCopy > self.thData['thresholds'][idx])
            if len(location) != 0:
                plotLabel = np.ravel(localCopy[location])
                plotLabel = [self.formatThreshold(l, idx) for l in plotLabel]
                locationIdx = np.ravel(location)
                # Force is calculated in the middle of the field, so
                #  marker should also be in the middle between two poles
                location = []
                for field in locationIdx:
                    leftPole = self.poles.poles[self.poles.idxA + field]['d']
                    rightPole = self.poles.poles[self.poles.idxA + field + 1]['d']
                    location.append(int(leftPole + floor((rightPole - leftPole) / 2)))
                color = 1   # red
        
        elif idx == 2:
            localCopy = np.nan_to_num(data)
            maxVal = np.max(localCopy)
            color = 3   # neutral
            for poleIdx, calcVal in enumerate(data):
                pole = self.poles.poles[self.poles.idxA + poleIdx]
                if not np.isnan(calcVal):
                    location.append(pole['d'])
                    plotLabel.append(self.formatThreshold(calcVal, idx))
        
        # Lastseilknickwinkel
        elif idx == 3 and not np.all(np.isnan(data)):
            maxValArr = [np.nan, np.nan]
            # Loop through all angles and test poles in between start and end
            #   with threshold 1, start and end pole with threshold 2
            for poleIdx, angle in enumerate(data):
                isOverThreshold = False
                # NAN values will be ignored
                if angle == np.nan:
                    continue
                # Test first and last pole of optimization with second threshold
                if poleIdx + self.poles.idxA in [self.poles.idxA, self.poles.idxE]:
                    # Check if current value is new max value
                    maxValArr[1] = np.nanmax([maxValArr[1], angle])
                    # Check if angle is higher than second threshold
                    if angle > self.thData['thresholds'][idx][1]:
                        isOverThreshold = True
                        color = 1   # red
                else:
                    # Check if current value is new max value
                    maxValArr[0] = np.nanmax([maxValArr[0], angle])
                    if angle > self.thData['thresholds'][idx][0]:
                        isOverThreshold = True
                        color = 1   # red
                    
                if isOverThreshold:
                    pole = self.poles.poles[self.poles.idxA + poleIdx]
                    location.append(pole['d'])
                    plotLabel.append(self.formatThreshold(angle, idx))
            # Format the two max values
            valStr = ' / '.join([self.formatThreshold(maxVal, idx) for maxVal in maxValArr])
        
        # Leerseilknickwinkel
        elif idx == 4 and not np.all(np.isnan(data)):
            # Replace nan with 0 so that no Runtime Warning is thrown
            localCopy = np.nan_to_num(data)
            maxVal = np.nanmin(localCopy)
            # Check if values are under defined threshold. Also ignore NAN values
            smallerThan = (localCopy < self.thData['thresholds'][idx][1]) * ~np.isnan(data)
            # Angles between 2 and 4 degrees have error level 'attention'
            if self.thData['thresholds'][idx][0] < maxVal < self.thData['thresholds'][idx][1]:
                color = 2   # orange
            elif maxVal < self.thData['thresholds'][idx][0]:
                color = 1   # red
            # Check which pole is affected
            locationPole = np.ravel(np.argwhere(smallerThan))
            for poleIdx in locationPole:
                pole = self.poles.poles[self.poles.idxA + poleIdx]
                location.append(pole['d'])
                plotLabel.append(self.formatThreshold(localCopy[poleIdx], idx))
        
        if isinstance(maxVal, float) and not np.isnan(maxVal):
            valStr = self.formatThreshold(maxVal, idx)
        
        return valStr, location, color, plotLabel
    
    def formatThreshold(self, val, idx):
        if isinstance(val, float) and not np.isnan(val):
            return f"{round(val, 1)} {self.thData['units'][idx]}"
        else:
            return '-'
    
    def showThresholdInPlot(self, row=None):
        # Click on row was emitted but row is already selected -> deselect
        if row is not None and row == self.selectedThresholdRow:
            # Remove markers from plot
            self.plot.removeMarkers()
            self.selectedThresholdRow = None
            return
        # There was no new selection but a redraw of the table was done, so
        #  current selection has to be added to the plot again
        if row is None:
            if self.selectedThresholdRow is not None:
                row = self.selectedThresholdRow
            # Nothing is selected at the moment
            else:
                return
        
        location = self.thData['rows'][row][5]['loc']
        color = self.thData['rows'][row][5]['color']
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
        self.plot.showMarkers(location, z, self.thData['plotLabels'][row], color)
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
                                    self.tr('Projekteinstellungen.txt')))

        # Create short report
        if self.confHandler.getOutputOption('shortReport'):
            generateShortReport(self.confHandler, self.result,
                                self.fieldComment.toPlainText(), projName,
                                outputLoc)

        # Create technical report
        if self.confHandler.getOutputOption('report'):
            reportText = generateReportText(self.confHandler, self.result,
                                            self.fieldComment.toPlainText(), projName)
            generateReport(reportText, outputLoc)
        
        # Create plot
        if self.confHandler.getOutputOption('plot'):
            plotSavePath = os.path.join(outputLoc, self.tr('Diagramm.pdf'))
            printPlot = AdjustmentPlot(self)
            printPlot.initData(self.profile.di_disp, self.profile.zi_disp,
                               self.profile.peakLoc_x, self.profile.peakLoc_z,
                               self.profile.surveyPnts)
            printPlot.updatePlot(self.poles.getAsArray(), self.cableline, True)
            printPlot.printToPdf(plotSavePath, projName, self.poles.poles)
        
        # Generate geo data
        if self.confHandler.getOutputOption('geodata') \
                or self.confHandler.getOutputOption('kml'):
            # Put geo data in separate sub folder
            savePath = os.path.join(outputLoc, 'geodata')
            os.makedirs(savePath)
            epsg = project.heightSource.spatialRef
            geodata = organizeDataForExport(self.poles.poles, self.cableline)
            
            if self.confHandler.getOutputOption('geodata'):
                shapeFiles = exportToShape(geodata, epsg, savePath)
                addToMap(shapeFiles, projName)
            if self.confHandler.getOutputOption('kml'):
                exportToKML(geodata, epsg, savePath)
        
        # Generate coordinate tables
        if self.confHandler.getOutputOption('coords'):
            generateCoordTable(self.cableline, self.profile, self.poles.poles,
                               outputLoc)
        
        self.updateRecalcStatus('saveDone')
    
    def closeEvent(self, event):
        if self.isRecalculating or self.configurationHasChanged:
            return
        if self.unsavedChanges:
            msgBox = QMessageBox()
            msgBox.setIcon(QMessageBox.Information)
            msgBox.setWindowTitle(self.tr('Nicht gespeicherte Aenderungen'))
            msgBox.setText(self.tr('Moechten Sie die Ergebnisse speichern?'))
            msgBox.setStandardButtons(QMessageBox.Cancel |
                                      QMessageBox.No | QMessageBox.Yes)
            cancelBtn = msgBox.button(QMessageBox.Cancel)
            cancelBtn.setText(self.tr("Abbrechen"))
            noBtn = msgBox.button(QMessageBox.No)
            noBtn.setText(self.tr("Nein"))
            yesBtn = msgBox.button(QMessageBox.Yes)
            yesBtn.setText(self.tr("Ja"))
            msgBox.show()
            msgBox.exec()
            
            if msgBox.clickedButton() == yesBtn:
                self.onSave()
                self.drawTool.reset()
            elif msgBox.clickedButton() == cancelBtn:
                event.ignore()
                return
            elif msgBox.clickedButton() == noBtn:
                self.drawTool.reset()
        else:
            self.drawTool.reset()
        
        self.timer.stop()
