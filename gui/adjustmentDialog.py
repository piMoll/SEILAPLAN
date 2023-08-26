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

from qgis.PyQt.QtCore import QTimer, Qt, QCoreApplication, QSettings
from qgis.PyQt.QtWidgets import QDialog, QMessageBox, QTextEdit
from qgis.PyQt.QtGui import QPixmap

from .ui_adjustmentDialog import Ui_AdjustmentDialogUI
from .adjustmentPlot import AdjustmentPlot, saveImgAsPdfWithMpl, \
    calculatePlotDimensions
from .plotting_tools import MyNavigationToolbar
from .poleWidget import CustomPoleWidget
from .birdViewWidget import BirdViewWidget
from .adjustmentDialog_params import AdjustmentDialogParams
from .adjustmentDialog_thresholds import AdjustmentDialogThresholds
from .saveDialog import DialogOutputOptions
from .guiHelperFunctions import DialogWithImage, addBackgroundMap
from .mapMarker import MapMarkerTool
from ..tools.birdViewMapExtractor import extractMapBackground
from ..core.cablelineFinal import preciseCable, updateWithCableCoordinates
from ..tools.calcThreshold import ThresholdUpdater
from ..tools.outputReport import generateReportText, generateReport, \
    createOutputFolder, generateShortReport
from ..tools.outputGeo import organizeDataForExport, addToMap, \
    generateCoordTable, writeGeodata


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
        self.msgBar = self.iface.messageBar()
        
        # Management of Parameters and settings
        self.confHandler = confHandler
        self.confHandler.setDialog(self)
        self.profile = self.confHandler.project.profile
        self.poles = self.confHandler.project.poles
        # Max distance the anchors can move away from initial position
        self.anchorBuffer = self.confHandler.project.heightSource.buffer
        # Path to plugin root
        self.homePath = os.path.dirname(os.path.dirname(__file__))
        
        # Load data
        self.originalData = {}
        self.result = {}
        self.cableline = {}
        self.status = None
        self.doReRun = False
        
        # Setup GUI from UI-file
        self.setupUi(self)
        # Language
        self.locale = QSettings().value("locale/userLocale")[0:2]
        
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
        
        # Threshold (thd) tab
        thdTblSize = [5, 6]
        self.thdLayout = AdjustmentDialogThresholds(self, thdTblSize)
        self.thdLayout.sig_clickedRow.connect(self.showThresholdInPlot)
        self.selectedThdRow = None
        self.thdUpdater = ThresholdUpdater(self.thdLayout, thdTblSize,
                                           self.showThresholdInPlot)
        
        self.paramLayout = AdjustmentDialogParams(self, self.confHandler.params)
        
        # Fill bird view widget with data
        self.birdViewLayout = BirdViewWidget(self.tabBirdView, self.birdViewGrid, self.poles)
        self.birdViewLayout.sig_updatePole.connect(self.updateBirdViewParams)
        self.tabWidget.currentChanged.connect(self.onBirdViewVisible)
        
        # Project header
        self.prHeaderFields = {
            'PrVerf': self.fieldPrVerf,
            'PrNr': self.fieldPrNr,
            'PrGmd': self.fieldPrGmd,
            'PrWald': self.fieldPrWald,
            'PrBemerkung': self.fieldPrBemerkung,
        }
        
        # Thread for instant recalculation when poles or parameters are changed
        self.timer = QTimer()
        self.configurationHasChanged = False
        self.isRecalculating = False
        self.unsavedChanges = True
        
        # Save dialog
        self.saveDialog = DialogOutputOptions(self, self.confHandler)
        
        # Dialog with explanatory images
        self.imgBox = DialogWithImage()
        
        # Connect signals
        self.btnClose.clicked.connect(self.onClose)
        self.btnSave.clicked.connect(self.onSave)
        self.btnBackToStart.clicked.connect(self.onReturnToStart)
        for field in self.prHeaderFields.values():
            field.textChanged.connect(self.onPrHeaderChanged)
        self.mapBackgroundButton.clicked.connect(self.onClickMapButton)
        self.infoQ.clicked.connect(self.onInfo)
        self.infoBirdViewGeneral.clicked.connect(self.onInfo)
        self.infoBirdViewCategory.clicked.connect(self.onInfo)
        self.infoBirdViewPosition.clicked.connect(self.onInfo)
        self.infoBirdViewAbspann.clicked.connect(self.onInfo)
    
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
        self.result['maxDistToGround'] = self.cableline['maxDistToGround']
        
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
        self.birdViewLayout.updateGui()

        # Fill in cable parameters
        self.paramLayout.fillInParams()
        
        # Fill in Threshold data
        self.thdUpdater.update([
            self.cableline['groundclear_rel'],  # Distance cable - terrain
            self.result['force']['MaxSeilzugkraft'][0],  # Max force on cable
            self.result['force']['Sattelkraft_Total'][0],  # Max force on pole
            self.result['force']['Lastseilknickwinkel'],  # Cable angle on pole
            self.result['force']['Leerseilknickwinkel']],  # Cable angle on pole
            self.confHandler.params, self.poles,
            (self.status in ['jumpedOver', 'savedFile'])
        )
        
        # Mark profile line and poles on map
        self.updateLineOnMap()
        self.addMarkerToMap()
        
        # Fill in project header data
        self.fillInPrHeaderData()
        
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
        # Save new value to config Handler
        self.confHandler.params.setOptSTA(newVal)
        return str(self.confHandler.params.optSTA)

    def updateBirdViewParams(self, idx, property_name, newVal):
        self.poles.update(idx, property_name, newVal)
    
    def onBirdViewVisible(self, tabIdx):
        if tabIdx == self.tabWidget.indexOf(self.tabBirdView):
            self.birdViewLayout.updateGui()
    
    def onClickMapButton(self):
        statusMsg, severity = addBackgroundMap(self.iface.mapCanvas())
        self.msgBar.pushMessage(self.tr('Hintergrundkarte laden'), statusMsg, severity)
    
    def onInfo(self):
        title = 'info'
        msg = ''
        imageName = None
        if self.sender().objectName() == 'infoQ':
            title = self.tr('Gesamtlast')
            msg = self.tr('Erklaerung Gesamtlast')
        elif self.sender().objectName() == 'infoBirdViewGeneral':
            title = self.tr('Konfiguration Vogelperspektive')
            msg = self.tr('Erklaerung Vogelperspektive')
        elif self.sender().objectName() == 'infoBirdViewCategory':
            title = self.tr('Stuetzenkategorie')
            msg = self.tr('Erklaerung Stuetzenkategorie')
            imageName = 'Vogelperspektive_Kategorie.png'
        elif self.sender().objectName() == 'infoBirdViewPosition':
            title = self.tr('Stuetzenposition')
            msg = self.tr('Erklaerung Stuetzenposition')
        elif self.sender().objectName() == 'infoBirdViewAbspann':
            title = self.tr('Abspann')
            msg = self.tr('Erklaerung Abspann')
        
        if imageName:
            # Show an info image
            imgPath = os.path.join(self.homePath, 'img', f'{self.locale}_{imageName}')
            if not os.path.exists(imgPath):
                imgPath = os.path.join(self.homePath, 'img', f'de_{imageName}')
            self.imgBox.setWindowTitle(title)
            # Load image
            myPixmap = QPixmap(imgPath)
            self.imgBox.label.setPixmap(myPixmap)
            self.imgBox.setLayout(self.imgBox.container)
            self.imgBox.show()
        else:
            # Show a simple MessageBox with an info text
            QMessageBox.information(self, title, msg, QMessageBox.Ok)

    def updateCableParam(self):
        self.configurationHasChanged = True
    
    def onPrHeaderChanged(self):
        self.unsavedChanges = True

    def fillInPrHeaderData(self):
        for key, val in self.confHandler.project.prHeader.items():
            field = self.prHeaderFields[key]
            if isinstance(field, QTextEdit):
                field.setPlainText(val)
            else:
                field.setText(val)

    def readoutPrHeaderData(self):
        prHeader = {}
        for key, field in self.prHeaderFields.items():
            if isinstance(field, QTextEdit):
                prHeader[key] = field.toPlainText()
            else:
                prHeader[key] = field.text()
        self.confHandler.project.setPrHeader(prHeader)
    
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
                                                           self.confHandler.params.optSTA)
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
        self.result['maxDistToGround'] = self.cableline['maxDistToGround']
        
        # Update Plot
        self.plot.updatePlot(self.poles.getAsArray(), self.cableline)
        
        # Update Threshold data
        self.thdUpdater.update([
            self.cableline['groundclear_rel'],  # Distance cable - terrain
            self.result['force']['MaxSeilzugkraft'][0],  # Max force on cable
            self.result['force']['Sattelkraft_Total'][0],  # Max force on pole
            self.result['force']['Lastseilknickwinkel'],  # Cable angle on pole
            self.result['force']['Leerseilknickwinkel']],  # Cable angle on pole
            self.confHandler.params, self.poles,
            (self.status in ['jumpedOver', 'savedFile'])
        )
        
        # cable line lifts off of pole
        if not seil_possible:
            self.updateRecalcStatus('liftsOff')
        else:
            self.updateRecalcStatus('cableSuccess')
        self.configurationHasChanged = False
        self.isRecalculating = False
        self.unsavedChanges = True

    def showThresholdInPlot(self, row=None):
        """This function is ether called by the Threshold updater when
         the cable has been recalculated or when user clicks on a table row."""
        
        # Click on row was emitted but row is already selected -> deselect
        if row is not None and row == self.selectedThdRow:
            # Remove markers from plot
            self.plot.removeMarkers()
            self.selectedThdRow = None
            return
        # There was no new selection but a redraw of the table was done, so
        #  current selection has to be added to the plot again
        if row is None:
            if self.selectedThdRow is not None:
                row = self.selectedThdRow
            # Nothing is selected at the moment
            else:
                return
    
        location = self.thdUpdater.rows[row][5]['loc']
        color = self.thdUpdater.rows[row][5]['color']
        plotLabels = self.thdUpdater.plotLabels[row]
        arrIdx = []
        # Get index of horizontal distance so we know which height value to
        #  chose
        for loc in location:
            arrIdx.append(np.argwhere(self.profile.di_disp == loc)[0][0])
        z = self.profile.zi_disp[arrIdx]
    
        self.plot.showMarkers(location, z, plotLabels, color)
        self.selectedThdRow = row

    def onClose(self):
        self.close()
    
    def onReturnToStart(self):
        self.readoutPrHeaderData()
        self.doReRun = True
        self.close()
    
    def onSave(self):
        self.saveDialog.doSave = False
        self.saveDialog.exec()
        if self.saveDialog.doSave:
            self.readoutPrHeaderData()
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
        poles = [pole for pole in self.poles.poles if pole['active']]
        # Save project file
        self.confHandler.saveSettings(os.path.join(outputLoc,
                                      self.tr('Projekteinstellungen') + '.json'))

        # Create short report
        if self.confHandler.getOutputOption('shortReport'):
            generateShortReport(self.confHandler, self.result, projName,
                                outputLoc)

        # Create technical report
        if self.confHandler.getOutputOption('report'):
            reportText = generateReportText(self.confHandler, self.result, projName)
            generateReport(reportText, outputLoc)
        
        # Create plot
        if self.confHandler.getOutputOption('plot'):
            includingBirdView = self.confHandler.getOutputOption('birdView')
            plotSavePath = os.path.join(outputLoc, self.tr('Diagramm.pdf'))
            width, height, ratio = calculatePlotDimensions(self.profile.di_disp, self.profile.zi_disp)
            
            printPlot = AdjustmentPlot(self, width, height, 150, withBirdView=includingBirdView, profilePlotRatio=ratio)
            printPlot.initData(self.profile.di_disp, self.profile.zi_disp,
                               self.profile.peakLoc_x, self.profile.peakLoc_z,
                               self.profile.surveyPnts)
            printPlot.updatePlot(self.poles.getAsArray(), self.cableline, True)
            printPlot.layoutDiagrammForPrint(projName, poles)
            imgPath = None
            if includingBirdView:
                # Create second plot
                xlim, ylim = printPlot.createBirdView(poles, self.confHandler.project.azimut)
                # Extract the map background
                imgPath = extractMapBackground(outputLoc, xlim, ylim,
                            self.confHandler.project.points['A'], self.confHandler.project.azimut)
                printPlot.addBackgroundMap(imgPath)
            printPlot.exportPdf(plotSavePath)
            # Delete map background
            if imgPath:
                os.remove(imgPath)
        
        if self.confHandler.getOutputOption('birdViewLegend'):
            imageName = 'Vogelperspektive_Kategorie.png'
            imgPath = os.path.join(self.homePath, 'img', f'{self.locale}_{imageName}')
            if not os.path.exists(imgPath):
                imgPath = os.path.join(self.homePath, 'img', f'de_{imageName}')
            saveImgAsPdfWithMpl(imgPath, os.path.join(outputLoc, self.tr('Vogelperspektive Legende') + '.pdf'))
        
        # Generate geo data
        if (self.confHandler.getOutputOption('csv') or
                self.confHandler.outputOptions['shape'] or
                self.confHandler.outputOptions['kml'] or
                self.confHandler.outputOptions['dxf']):
            
            # Put geo data in separate sub folder
            savePath = os.path.join(outputLoc, 'geodata')
            os.makedirs(savePath)
            epsg = project.heightSource.spatialRef
            geodata = organizeDataForExport(poles, self.cableline,
                                            self.profile)

            title = self.tr('Unerwarteter Fehler')
            msg = self.tr('Erstellen der Geodaten nicht moeglich')
        
            if self.confHandler.getOutputOption('csv'):
                try:
                    generateCoordTable(self.cableline, self.profile,
                                       poles, savePath)
                except Exception as e:
                    msg = f'{msg}:\n{e}'
                    self.showMessage(title, msg)
            if self.confHandler.getOutputOption('shape'):
                try:
                    shapeFiles = writeGeodata(geodata, 'SHP', epsg, savePath)
                    addToMap(shapeFiles, projName)
                except Exception as e:
                    msg = f'{msg}:\n{e}'
                    self.showMessage(title, msg)
            if self.confHandler.getOutputOption('kml'):
                try:
                    writeGeodata(geodata, 'KML', epsg, savePath)
                except Exception as e:
                    msg = f'{msg}:\n{e}'
                    self.showMessage(title, msg)
            if self.confHandler.getOutputOption('dxf'):
                try:
                    writeGeodata(geodata, 'DXF', epsg, savePath)
                except Exception as e:
                    msg = f'{msg}:\n{e}'
                    self.showMessage(title, msg)
            
        self.updateRecalcStatus('saveDone')
    
    def showMessage(self, title, message):
        QMessageBox.critical(self, title, message, QMessageBox.Ok)
    
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
