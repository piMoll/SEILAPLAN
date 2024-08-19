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
import os
import sys
from qgis.PyQt import uic
from qgis.PyQt.QtCore import QTimer, Qt, QCoreApplication, QSettings
from qgis.PyQt.QtWidgets import QDialog, QMessageBox, QTextEdit
from qgis.PyQt.QtGui import QPixmap
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
from SEILAPLAN.tools.birdViewMapExtractor import extractMapBackground
from SEILAPLAN.core.cablelineFinal import preciseCable, updateWithCableCoordinates
from SEILAPLAN.tools.calcThreshold import ThresholdUpdater
from SEILAPLAN.tools.poles import Poles
from SEILAPLAN.tools.profile import Profile
from SEILAPLAN.tools.outputReport import generateReportText, generateReport, \
    createOutputFolder, generateShortReport
from SEILAPLAN.tools.outputGeo import organizeDataForExport, addToMap, \
    generateCoordTable, writeGeodata
from SEILAPLAN.tools.configHandler import ConfigHandler
from SEILAPLAN.tools.configHandler_params import ParameterConfHandler
from SEILAPLAN.tools.configHandler_project import ProjectConfHandler
from SEILAPLAN.tools.globals import ResultQuality, PolesOrigin
# This loads the .ui file so that PyQt can populate the plugin with the
#  elements from Qt Designer
UI_FILE = os.path.join(os.path.dirname(__file__), 'adjustmentDialog.ui')
FORM_CLASS, _ = uic.loadUiType(UI_FILE)


class AdjustmentDialog(QDialog, FORM_CLASS):
    """
    Dialog window that is shown after the optimization has successfully run
    through. Users can change the calculated cable layout by changing pole
    position, height, angle and the properties of the cable line. The cable
    line is then recalculated and the new layout is shown in a plot.
    """
    
    def __init__(self, interface, confHandler, onCloseCallback):

        super(AdjustmentDialog, self).__init__(interface.mainWindow())
        
        self.iface = interface
        # Is called when window is closed (necessary for parallel run)
        self.onCloseCallback = onCloseCallback
        # Control variable that gets returned in callback so parent knows how
        # to proceed when this dialog is closed
        self.returnToProjectWindow = None
        
        self.msgBar = self.iface.messageBar()
        
        # Management of Parameters and settings
        self.confHandler: ConfigHandler = confHandler
        self.confHandler.setDialog(self)
        self.paramHandler: ParameterConfHandler = self.confHandler.params
        self.projectHandler: ProjectConfHandler = self.confHandler.project
        self.profile: Profile = self.projectHandler.profile
        self.poles: Poles = self.projectHandler.poles
        # Control variable so parent knows how to proceed when this dialog is closed
        self.returnToProjectWindow = None
        # Max distance the anchors can move away from initial position
        self.anchorBuffer = self.projectHandler.heightSource.buffer
        # Path to plugin root
        self.homePath = os.path.dirname(os.path.dirname(__file__))
        
        # Load data
        self.result = {}
        self.cableline = {}
        
        # Setup GUI from UI-file
        self.setupUi(self)
        self.setDialogTitle()
        # Language
        self.locale = QSettings().value("locale/userLocale")[0:2]
        
        self.drawTool = MapMarkerTool(self.iface.mapCanvas())
        
        # Create plot
        self.plot = AdjustmentPlot(self)
        # Pan/Zoom tools for plot, pan already active
        tbar = MyNavigationToolbar(self.plot, self)
        tbar.pan()
        self.plot.setToolbar(tbar)
        self.plotContainer.addWidget(self.plot)
        self.toolbarContainer.addWidget(tbar, alignment=Qt.AlignLeft | Qt.AlignTop)
        
        # Fill tab widget with data
        self.poleLayout = CustomPoleWidget(self.tabPoles, self.poleGrid, self.poles)
        # self.poleLayout.sig_zoomIn.connect(self.zoomToPole)
        # self.poleLayout.sig_zoomOut.connect(self.zoomOut)
        self.poleLayout.sig_createPole.connect(self.addPole)
        self.poleLayout.sig_updatePole.connect(self.updatePole)
        self.poleLayout.sig_deletePole.connect(self.deletePole)
        
        # Threshold (thd) tab
        self.thdLayout = AdjustmentDialogThresholds(self)
        self.thdLayout.sig_clickedRow.connect(self.onChangeThresholdTopic)
        self.thdUpdater = ThresholdUpdater(self.thdLayout)
        self.selectedPlotTopic = None
        
        # Parameter tab
        self.paramLayout = AdjustmentDialogParams(self, self.paramHandler)
        
        # Fill bird view widget with data
        self.birdViewLayout = BirdViewWidget(self.tabBirdView, self.birdViewGrid, self.poles)
        self.birdViewLayout.sig_updatePole.connect(self.onUpdateBirdViewParams)
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
        self.refreshPoleWidgetRows = False
        self.isRecalculating = False
        self.unsavedChanges = True
        
        # Save dialog
        self.saveDialog = DialogOutputOptions(self, self.confHandler)
        
        # Dialog with explanatory images
        self.imgBox = DialogWithImage()
        
        # Connect signals
        self.btnClose.clicked.connect(self.onClose)
        self.btnSave.clicked.connect(self.onSave)
        self.btnBackToStart.clicked.connect(self.onReturnToProjectWindow)
        for field in self.prHeaderFields.values():
            field.textChanged.connect(self.onPrHeaderChanged)
        self.mapBackgroundButton.clicked.connect(self.onClickMapButton)
        self.infoPlotTopic.clicked.connect(self.onInfo)
        self.infoQ.clicked.connect(self.onInfo)
        self.infoSK.clicked.connect(self.onInfo)
        self.infoSFT.clicked.connect(self.onInfo)
        self.infoBirdViewGeneral.clicked.connect(self.onInfo)
        self.infoBirdViewCategory.clicked.connect(self.onInfo)
        self.infoBirdViewPosition.clicked.connect(self.onInfo)
        self.infoBirdViewAbspann.clicked.connect(self.onInfo)
        
        if 'DARWIN' in sys.platform.upper():
            # Explicitly set the windows flags on macOS so the plugin window
            #  stays on top of QGIS when drawing in the map
            self.setWindowFlags(
                Qt.Window |
                Qt.CustomizeWindowHint |
                Qt.WindowTitleHint |
                Qt.WindowCloseButtonHint |
                Qt.WindowStaysOnTopHint
            )
    
    # noinspection PyMethodMayBeStatic
    def tr(self, message, context='', **kwargs):
        """Get the translation for a string using Qt translation API.
        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString
        
        :param context: String for translation.
        :type context: str, QString

        :returns: Translated version of message.
        :rtype: QString

        Parameters
        ----------
        **kwargs
        """
        if context == '':
            context = type(self).__name__
        return QCoreApplication.translate(context, message)
    
    def loadData(self, pickleFile):
        """ Is used to load testdata from pickl object in debug mode """
        import pickle
        f = open(pickleFile, 'rb')
        dump = pickle.load(f)
        f.close()
        
        self.poles.poles = dump['poles']
        self.initData(dump, ResultQuality.SuccessfulOptimization)
    
    def initData(self, result, resultQuality):
        if not result:
            self.close()
        # result properties: cable line, optSTA, force, optLen, optLen_arr,
        #  duration
        self.result = result
        # If only poles are defined but cable line hasn't been calculated yet,
        #  run the cable calculation now
        if not self.result['cableline']:
            try:
                params = self.paramHandler.getSimpleParameterDict()
                cableline, force, \
                    seil_possible = preciseCable(params, self.poles,
                                                 self.result['optSTA'])
                self.result['cableline'] = cableline
                self.result['force'] = force
            
            except Exception as e:
                QMessageBox.critical(self, self.tr('Unerwarteter Fehler '
                    'bei Berechnung der Seillinie'), str(e), QMessageBox.Ok)
                return
        
        groundClear = self.profile.updateProfileAnalysis(self.result['cableline'])
        self.cableline = {**self.result['cableline'], **groundClear}
        self.result['cableline'] = self.cableline
        
        self.updateRecalcStatus(resultQuality)
        
        # Draw profile in diagram
        self.plot.initData(self.profile.di_disp, self.profile.zi_disp,
                           self.profile.peakLoc_x, self.profile.peakLoc_z,
                           self.profile.surveyPnts)
        self.plot.updatePlot(self.poles.getAsArray(), self.cableline)
        
        # Create layout to modify poles
        self.poleLayout.setInitialGui([self.profile.di_disp[0], self.profile.di_disp[-1]])
        self.birdViewLayout.updateGui()

        # Fill in cable parameters
        self.paramLayout.fillInParams()
        
        # Fill in Threshold data
        self.thdUpdater.update(self.result, self.paramHandler, self.poles,
            self.profile, resultQuality == ResultQuality.SuccessfulOptimization)
        # Add plot topics in drop down
        self.fieldPlotTopic.addItem('-', userData=-1)
        for topic in self.thdUpdater.topics:
            self.fieldPlotTopic.addItem(topic.name, userData=topic.id)
        self.fieldPlotTopic.setCurrentIndex(0)
        self.fieldPlotTopic.currentIndexChanged.connect(self.onChangePlotTopic)
        
        # Mark profile line and poles on map
        self.updateLineOnMap()
        self.addMarkerToMap()
        
        # Fill in project header data
        self.fillInPrHeaderData()
        
        # Start Thread to recalculate cable line every 300 milliseconds
        self.timer.timeout.connect(self.recalculate)
        self.timer.start(300)
        
        self.plot.zoomOut()
        
    def setDialogTitle(self):
        dialogTitle = self.tr('Manuelle Anpassung', 'AdjustmentDialogUI')
        projectTitle = self.projectHandler.getProjectName()
        self.setWindowTitle(f"{dialogTitle} // {projectTitle}")
    
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
        self.updateAnchorMarkerState(prevAnchorA, prevAnchorE)
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
        self.refreshPoleWidgetRows = True
        self.addMarkerToMap(newPoleIdx)
        # self.plot.zoomOut()
        self.plot.updatePlot(self.poles.getAsArray(), self.cableline)
        self.configurationHasChanged = True
    
    def deletePole(self, idx):
        self.poles.delete(idx)
        self.refreshPoleWidgetRows = True
        self.drawTool.removeMarker(idx)
        # self.plot.zoomOut()
        self.plot.updatePlot(self.poles.getAsArray(), self.cableline)
        self.configurationHasChanged = True
    
    def updateAnchorMarkerState(self, prevAnchorA, prevAnchorE):
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

    def onUpdateBirdViewParams(self, idx, property_name, newVal):
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
        if self.sender().objectName() == 'infoSK':
            title = self.tr('Tragseilspannkraft (Anfangspunkt)')
            msg = self.tr('Erklaerung Tragseilspannkraft (Anfangspunkt)')
        if self.sender().objectName() == 'infoSFT':
            title = self.tr('Sicherheitsfaktor Tragseil', 'SeilaplanPluginDialog')
            msg = self.tr('Sicherheitsfaktor Tragseil Erklaerung', 'SeilaplanPluginDialog')
        elif self.sender().objectName() == 'infoBirdViewGeneral':
            title = self.tr('Konfiguration Vogelperspektive')
            msg = self.tr('Erklaerung Vogelperspektive')
        elif self.sender().objectName() == 'infoBirdViewCategory':
            title = self.tr('Stuetzenkategorie')
            imageName = 'Vogelperspektive_Kategorie.png'
        elif self.sender().objectName() == 'infoBirdViewPosition':
            title = self.tr('Stuetzenposition')
            msg = self.tr('Erklaerung Stuetzenposition')
        elif self.sender().objectName() == 'infoBirdViewAbspann':
            title = self.tr('Abspann')
            msg = self.tr('Erklaerung Abspann')
        elif self.sender().objectName() == 'infoPlotTopic':
            plotTopic = self.thdUpdater.getPlotTopicById(self.selectedPlotTopic)
            if plotTopic:
                desc = plotTopic.getDescription()
                title = desc['title']
                msg = desc['message']
        
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
        elif title and msg:
            # Show a simple MessageBox with an info text
            QMessageBox.information(self, title, msg, QMessageBox.Ok)

    def onUpdateCableParam(self):
        # Since user can change entire parameter sets, we prepare params
        #  for recalculation
        self.paramHandler.prepareForCalculation(self.profile.direction)
        self.configurationHasChanged = True
    
    def onPrHeaderChanged(self):
        self.unsavedChanges = True

    def fillInPrHeaderData(self):
        for key, val in self.projectHandler.prHeader.items():
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
        self.projectHandler.setPrHeader(prHeader)
    
    def updateRecalcStatus(self, status):
        color = None
        green = '#b6ddb5'
        yellow = '#f4e27a'
        red = '#e8c4ca'
        ico_path = os.path.join(os.path.dirname(__file__), 'icons')
        if status == ResultQuality.SuccessfulOptimization:
            self.recalcStatus_txt.setText(
                self.tr('Optimierung erfolgreich abgeschlossen'))
            self.recalcStatus_ico.setPixmap(QPixmap(os.path.join(
                ico_path, 'icon_green.png')))
        elif status == ResultQuality.CableLiftsOff:
            self.recalcStatus_txt.setText(
                self.tr('Tragseil hebt bei mindestens einer Stuetze ab'))
            self.recalcStatus_ico.setPixmap(QPixmap(os.path.join(
                ico_path, 'icon_yellow.png')))
            color = yellow
        elif status == ResultQuality.LineNotComplete:
            self.recalcStatus_txt.setText(
                self.tr('Nicht genuegend Stuetzenstandorte bestimmbar'))
            self.recalcStatus_ico.setPixmap(QPixmap(os.path.join(
                ico_path, 'icon_yellow.png')))
            color = yellow
        elif status == PolesOrigin.OnlyStartEnd:
            self.recalcStatus_txt.setText(
                self.tr('Stuetzen manuell platzieren'))
            self.recalcStatus_ico.setPixmap(QPixmap(os.path.join(
                ico_path, 'icon_green.png')))
            color = yellow
        elif status == PolesOrigin.SavedFile:
            self.recalcStatus_txt.setText(
                self.tr('Stuetzen aus Projektdatei geladen'))
            self.recalcStatus_ico.setPixmap(QPixmap(os.path.join(
                ico_path, 'icon_green.png')))
            color = yellow
        elif status == ResultQuality.SuccessfulRerun:
            self.recalcStatus_txt.setText(self.tr('Seillinie neu berechnet.'))
            self.recalcStatus_ico.setPixmap(QPixmap(os.path.join(
                ico_path, 'icon_green.png')))
        elif status == ResultQuality.Error:
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
            params = self.paramHandler.getSimpleParameterDict()
            cableline, force, seil_possible = preciseCable(params, self.poles,
                                                           self.paramHandler.getTensileForce())
        except Exception as e:
            self.updateRecalcStatus(ResultQuality.Error)
            self.isRecalculating = False
            self.configurationHasChanged = False
            return
        
        # Ground clearance
        groundClear = self.profile.updateProfileAnalysis(cableline)
        self.cableline = {**cableline, **groundClear}
        self.result['cableline'] = self.cableline
        self.result['force'] = force

        # Update Plot
        self.plot.updatePlot(self.poles.getAsArray(), self.cableline)
        
        # Update Threshold data
        self.thdUpdater.update(self.result, self.paramHandler, self.poles,
                               self.profile, False)
        self.onRefreshTopicInPlot()
        
        # cable line lifts off of pole
        if not seil_possible:
            self.updateRecalcStatus(ResultQuality.CableLiftsOff)
        else:
            self.updateRecalcStatus(ResultQuality.SuccessfulRerun)
        
        if self.refreshPoleWidgetRows:
            self.refreshPoleWidgetRows = False
            self.poleLayout.refresh()
        self.configurationHasChanged = False
        self.isRecalculating = False
        self.unsavedChanges = True

    def onChangeThresholdTopic(self, row):
        """This function is either called by the Threshold updater when
         the cable has been recalculated or when user clicks on a table row."""
        
        try:
            thItem = self.thdUpdater.getThresholdTopics()[row]
        except IndexError:
            thItem = None
        
        # Click on row was emitted but row is already selected -> deselect
        if thItem is None or thItem.id == self.selectedPlotTopic:
            # Remove markers from plot
            self.plot.removeMarkers()
            # Unselect plot topic
            self.selectedPlotTopic = None
            self.fieldPlotTopic.blockSignals(True)
            self.fieldPlotTopic.setCurrentIndex(0)
            self.fieldPlotTopic.blockSignals(False)
            return

        self.plot.showMarkers(thItem.plotMarkers)
        self.selectedPlotTopic = thItem.id
        
        # Synchronize plot topic dropdown with currently selected threshold topic
        for idx, item in enumerate(self.thdUpdater.topics):
            if self.selectedPlotTopic == item.id:
                self.fieldPlotTopic.blockSignals(True)
                self.fieldPlotTopic.setCurrentIndex(idx+1)
                self.fieldPlotTopic.blockSignals(False)
                break
    
    def onRefreshTopicInPlot(self):
        item = self.thdUpdater.getPlotTopicById(self.selectedPlotTopic)
        if item:
            self.plot.showMarkers(item.plotMarkers)
        else:
            self.plot.removeMarkers()
        
    def onChangePlotTopic(self):
        self.selectedPlotTopic = self.fieldPlotTopic.currentData()
        # Select topic in threshold table
        self.thdLayout.select(self.thdUpdater.getSortIdxByThresholdTopicId(self.selectedPlotTopic))
        # Paint the new topic
        self.onRefreshTopicInPlot()

    def onClose(self):
        self.returnToProjectWindow = False
        self.close()
    
    def onReturnToProjectWindow(self):
        self.readoutPrHeaderData()
        self.returnToProjectWindow = True
        self.close()
    
    def onSave(self):
        self.saveDialog.setConfigData()
        self.saveDialog.exec()
        
        if self.saveDialog.saveSuccessful:
            self.readoutPrHeaderData()
            self.setDialogTitle()
            self.confHandler.updateUserSettings()
            self.createOutput()
            self.unsavedChanges = False
    
    def createOutput(self):
        outputFolder = self.confHandler.getCurrentPath()
        projName = self.projectHandler.getProjectName()
        outputLoc, projName_unique = createOutputFolder(outputFolder, projName)
        
        updateWithCableCoordinates(self.cableline, self.projectHandler.points['A'],
                                   self.projectHandler.azimut)
        poles = [pole for pole in self.poles.poles if pole['active']]
        # Save project file
        self.confHandler.saveSettings(os.path.join(outputLoc,
                                      f"{self.tr('Projekteinstellungen')}.json"))

        # Create short report
        if self.confHandler.getOutputOption('shortReport'):
            generateShortReport(self.confHandler, self.result, projName_unique,
                                outputLoc)

        # Create technical report
        if self.confHandler.getOutputOption('report'):
            reportText = generateReportText(self.confHandler, self.result, projName_unique)
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
            printPlot.layoutDiagrammForPrint(projName_unique, poles, self.poles.direction)
            imgPath = None
            if includingBirdView:
                # Create second plot
                xlim, ylim = printPlot.createBirdView(poles, self.projectHandler.azimut)
                # Extract the map background
                imgPath = extractMapBackground(outputLoc, xlim, ylim,
                            self.projectHandler.points['A'], self.projectHandler.azimut)
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
            epsg = self.projectHandler.heightSource.spatialRef
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
                    addToMap(shapeFiles, projName_unique)
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
    
    def cleanUp(self):
        self.drawTool.reset()
        if self.timer:
            self.timer.stop()
    
    def closeEvent(self, QCloseEvent):
        if self.isRecalculating or self.configurationHasChanged:
            QCloseEvent.ignore()
            return
        
        # Check for unsaved changes before closing
        if self.unsavedChanges:
            msgBox = QMessageBox(self)
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
            msgBox.exec()
            
            if msgBox.clickedButton() == yesBtn:
                self.onSave()
            
            if msgBox.clickedButton() == cancelBtn:
                # Cancel closing
                QCloseEvent.ignore()
                return
            
            if msgBox.clickedButton() == noBtn:
                # Nothing to do
                pass
        
        self.cleanUp()
        self.onCloseCallback(self.returnToProjectWindow)
