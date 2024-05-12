# -*- coding: utf-8 -*-
"""
/***************************************************************************
 SeilaplanPluginDialog
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

# GUI and QGIS libraries
from qgis.PyQt.QtCore import QFileInfo, QCoreApplication, QSettings, Qt
from qgis.PyQt.QtWidgets import (QDialog, QMessageBox, QFileDialog, QComboBox,
                                 QTextEdit)
from qgis.PyQt.QtGui import QPixmap
from qgis.core import (QgsRasterLayer, QgsPointXY, QgsProject,
                       QgsCoordinateReferenceSystem)
from processing.core.Processing import Processing

# Further GUI modules for functionality
from .guiHelperFunctions import (DialogWithImage, createContours,
                                 addBackgroundMap, createProfileLayers)
from .surveyImportDialog import SurveyImportDialog
from ..tools.outputGeo import CH_CRS
from ..tools.configHandler import ConfigHandler
from ..tools.configHandler_project import castToNum
# GUI elements
from .checkableComboBoxOwn import QgsCheckableComboBoxOwn
from .saveDialog import DialogSaveParamset
from .mapMarker import MapMarkerTool
from .ui_seilaplanDialog import Ui_SeilaplanDialogUI
from .profileDialog import ProfileDialog


class SeilaplanPluginDialog(QDialog, Ui_SeilaplanDialogUI):
    def __init__(self, interface, confHandler):
        """

        :type confHandler: ConfigHandler
        """
        QDialog.__init__(self, interface.mainWindow())
        
        # QGIS interface
        self.iface = interface
        # QGIS map canvas
        self.canvas = self.iface.mapCanvas()
        # Management of Parameters and settings
        self.confHandler = confHandler
        self.confHandler.setDialog(self)
        self.paramHandler = confHandler.params
        self.projectHandler = confHandler.project
        self.startAlgorithm = False
        self.goToAdjustment = False
        # Path to plugin root
        self.homePath = os.path.dirname(os.path.dirname(__file__))
        
        # Setup GUI of SEILAPLAN (import from ui_seilaplanDialog.py)
        self.setupUi(self)
        
        # Add a special QGIS type drop down with checkboxes to select raster layer
        self.rasterField = QgsCheckableComboBoxOwn(self.groupBox_2)
        self.rasterField.setObjectName("rasterField2")
        self.gridLayout_15.addWidget(self.rasterField, 0, 2, 1, 1)
        self.virtRaster = None
        
        # Language
        self.locale = QSettings().value("locale/userLocale")[0:2]
        
        # Interaction with canvas, is used to draw onto map canvas
        self.drawTool = MapMarkerTool(self.canvas)
        # Connect emitted signals
        self.drawTool.sig_lineFinished.connect(self.onFinishedLineDraw)
        # Survey data line layer
        self.surveyLineLayer = None
        self.surveyPointLayer = None
        
        # Dictionary of all GUI setting fields
        self.parameterFields = {}
        self.prHeaderFields = {}
        
        # GUI fields and variables handling coordinate information
        self.coordFields = {}
        self.linePoints = {
            'A': QgsPointXY(-100, -100),
            'E': QgsPointXY(-100, -100)
        }
        
        # Organize parameter GUI fields in dictionary
        self.groupFields()
        
        # Dialog to import survey data
        self.surveyImportDialog = SurveyImportDialog(self, self.confHandler)
        
        # Dialog with explanatory images
        self.imgBox = DialogWithImage()
        # MessageBar
        self.msgBar = self.iface.messageBar()
        
        # Additional GIS-Layers
        self.osmLyrButton.setEnabled(False)
        self.contourLyrButton.setEnabled(False)
        
        # Connect GUI elements from dialog window with functions
        self.connectGuiElements()
        
        # Dialog window with height profile
        self.profileWin = ProfileDialog(self, self.iface, self.drawTool,
                                        self.projectHandler)

        # Dialog windows for saving parameter and cable sets
        self.paramSetWindow = DialogSaveParamset(self)

        # Set initial state of terrain data group
        self.enableRasterHeightSource()
        
        Processing.initialize()
    
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
        return QCoreApplication.translate(context, message, **kwargs)
    
    def connectGuiElements(self):
        """Connect GUI elements with functions.
        """
        self.buttonCancel.clicked.connect(self.cancel)
        self.buttonRun.clicked.connect(self.apply)
        self.btnAdjustment.clicked.connect(self.goToAdjustmentWindow)
        self.buttonOpenPr.clicked.connect(self.onLoadProjects)
        self.buttonSavePr.clicked.connect(self.onSaveProject)
        self.rasterField.selectedItemsChanged.connect(self.onChangeRaster)
        self.buttonRefreshRa.clicked.connect(self.updateRasterList)
        self.buttonInfo.clicked.connect(self.onInfo)

        self.radioRaster.toggled.connect(self.onToggleHeightSource)
        # self.radioSurveyData.toggled.connect(self.onToggleHeightSource) # Second trigger not necessary
        self.buttonLoadSurveyData.clicked.connect(self.onLoadSurveyData)
        
        self.fieldTypeA.currentTextChanged.connect(self.onTypeAChange)
        self.fieldTypeE.currentTextChanged.connect(self.onTypeEChange)
        
        # Info buttons
        self.infoRasterlayer.clicked.connect(self.onInfo)
        self.infoSurveyData.clicked.connect(self.onInfo)
        self.infoPointA.clicked.connect(self.onInfo)
        self.infoPointE.clicked.connect(self.onInfo)
        self.infoBodenabstand.clicked.connect(self.onInfo)
        self.infoStuetzen.clicked.connect(self.onInfo)
        self.infoQ.clicked.connect(self.onInfo)
        self.infoSK.clicked.connect(self.onInfo)
        self.infoFieldE.clicked.connect(self.onInfo)
        self.infoFieldFuellF.clicked.connect(self.onInfo)
        self.infoFieldSFT.clicked.connect(self.onInfo)
        self.infoBerechnung.clicked.connect(self.onInfo)
        
        # OSM map and contour buttons
        self.osmLyrButton.clicked.connect(self.onClickOsmButton)
        self.contourLyrButton.clicked.connect(self.onClickContourButton)
        
        # Filed that contains project names
        self.fieldProjName.textChanged.connect(self.setProjName)
        # Button starts map drawing
        self.draw.clicked.connect(self.drawLine)
        # Button shows profile window
        self.buttonShowProf.clicked.connect(self.onShowProfile)
        # Drop down field for parameter set choices
        self.fieldParamSet.currentIndexChanged.connect(self.setParameterSet)
        self.buttonSaveParamset.clicked.connect(self.onSaveParameterSet)
        self.buttonRemoveParamset.clicked.connect(self.onRemoveParameterSet)
        
        # Action for changed Coordinates (when coordinate is changed by hand)
        self.coordAx.editingFinished.connect(
            lambda: self.onCoordFieldChange('A'))
        self.coordAy.editingFinished.connect(
            lambda: self.onCoordFieldChange('A'))
        self.coordEx.editingFinished.connect(
            lambda: self.onCoordFieldChange('E'))
        self.coordEy.editingFinished.connect(
            lambda: self.onCoordFieldChange('E'))
        
        for name, inputField in self.parameterFields.items():
            # lambda definition is put in its own function "getListener" to
            # preserve scope, otherwise var "name" gets overwritten in every
            # iteration of this loop
            if isinstance(inputField, QComboBox) and name == 'Seilsys':
                inputField.currentIndexChanged.connect(
                    self.getListenerComboBox(name))
            else:
                inputField.editingFinished.connect(
                    self.getListenerLineEdit(name))
    
    def groupFields(self):
        """Combine all GUI fields in dictionary for faster access.
        """
        self.parameterFields = {
            'Seilsys': self.fieldSeilsys,
            'HM_Kran': self.fieldHMKran,
            'Befahr_A': self.fieldBefA,
            'Befahr_E': self.fieldBefE,
            'Bodenabst_min': self.fieldBabstMin,
            'Bodenabst_A': self.fieldBabstA,
            'Bodenabst_E': self.fieldBabstE,
            
            'Q': self.fieldQ,
            'qT': self.fieldQt,
            'D': self.fieldD,
            'MBK': self.fieldMBK,
            'qZ': self.fieldqZ,
            'qR': self.fieldqR,
            'SK': self.fieldSK,
            'Anlagetyp': self.fieldAnlagetyp,
            
            'Min_Dist_Mast': self.fieldMinDist,
            'L_Delta': self.fieldLdelta,
            'HM_min': self.fieldHMmin,
            'HM_max': self.fieldHMmax,
            'HM_Delta': self.fieldHMdelta,
            'HM_nat': self.fieldHMnat,
            
            'E': self.fieldE,
            'FuellF': self.fieldFuellF,
            'SF_T': self.fieldSFT
        }
        self.coordFields = {
            'Ax': self.coordAx,
            'Ay': self.coordAy,
            'Ex': self.coordEx,
            'Ey': self.coordEy
        }
        self.prHeaderFields = {
            'PrVerf': self.fieldPrVerf,
            'PrNr': self.fieldPrNr,
            'PrGmd': self.fieldPrGmd,
            'PrWald': self.fieldPrWald,
            'PrBemerkung': self.fieldPrBemerkung,
        }
    
    def onToggleHeightSource(self):
        if self.radioRaster.isChecked():
            self.enableRasterHeightSource()
        else:
            self.enableSurveyDataHeightSource()
        # Reset profile data
        self.projectHandler.resetHeightSource()
        self.projectHandler.resetProfile()
        self.drawTool.surveyDataMode = False
        self.removeSurveyDataLayer()
        self.checkPoints()
    
    def enableRasterHeightSource(self):
        if not self.radioRaster.isChecked():
            self.radioRaster.blockSignals(True)
            self.radioSurveyData.blockSignals(True)
            self.radioRaster.setChecked(True)
            self.radioRaster.blockSignals(False)
            self.radioSurveyData.blockSignals(False)
        self.fieldSurveyDataPath.setText('')
        self.rasterField.blockSignals(True)
        self.rasterField.setEnabled(True)
        self.rasterField.blockSignals(False)
        self.buttonRefreshRa.setEnabled(True)
        self.buttonLoadSurveyData.setEnabled(False)
        # Enable coordinate fields
        for field in self.coordFields.values():
            self.setFieldReadOnly(field, False)
        # Change label next to draw button
        self.labelDraw.setText(self.tr("Seillinie in Karte einzeichnen", "SeilaplanDialogUI"))
        self.labelCoords.setText(self.tr("oder Koordinaten der Seillinie manuell angeben:", "SeilaplanDialogUI"))
        # Deactivate ui elements in group cableline
        self.toggleCableLineUI(False)

    def enableSurveyDataHeightSource(self):
        if not self.radioSurveyData.isChecked():
            self.radioRaster.blockSignals(True)
            self.radioSurveyData.blockSignals(True)
            self.radioSurveyData.setChecked(True)
            self.radioRaster.blockSignals(False)
            self.radioSurveyData.blockSignals(False)
        self.rasterField.blockSignals(True)
        self.rasterField.deselectAllOptions()
        self.rasterField.setEnabled(False)
        self.rasterField.blockSignals(False)
        self.buttonRefreshRa.setEnabled(False)
        self.buttonLoadSurveyData.setEnabled(True)
        # Disable coordinate fields
        for field in self.coordFields.values():
            self.setFieldReadOnly(field, True)
        # Change label next to draw button
        self.labelDraw.setText(self.tr('Start- Endpunkt auf dem Gelaendeprofil definieren'))
        self.labelCoords.setText("")
        # Deactivate ui elements in group cableline
        self.toggleCableLineUI(False)
    
    
    def setFieldReadOnly(self, field, readonly):
        field.setReadOnly(readonly)
        field.blockSignals(readonly)
        if readonly:
            field.setStyleSheet("color: rgb(136, 138, 133);")
            field.setToolTip(self.tr('Koordinate kann nicht manuell veraendert werden, benutzen Sie die Schaltflaeche zeichnen'))
        else:
            field.setStyleSheet("")
            field.setToolTip("")
    
    def getListenerLineEdit(self, property_name):
        return lambda: self.parameterChangedLineEdit(property_name)
    
    def getListenerComboBox(self, property_name):
        return lambda: self.parameterChangedComboBox(property_name)
    
    def parameterChangedLineEdit(self, property_name):
        # Deactivate editFinished signal so it is not fired twice when
        # setParameter() shows a QMessageBox
        self.parameterFields[property_name].blockSignals(True)
        newVal = self.parameterFields[property_name].text()
        newValAsStr = self.paramHandler.setParameter(property_name, newVal)
        if newValAsStr is not False:
            self.updateParametersetField()
            # Insert correctly formatted value
            self.parameterFields[property_name].setText(newValAsStr)
        self.parameterFields[property_name].blockSignals(False)
    
    def parameterChangedComboBox(self, property_name):
        newVal = self.parameterFields[property_name].currentIndex()
        newValAsIdx = self.paramHandler.setParameter(property_name, newVal)
        if newValAsIdx is not False:
            self.updateParametersetField()
    
    def updateParametersetField(self):
        # Change current parameter set name
        if self.paramHandler.currentSetName:
            self.fieldParamSet.setCurrentText(self.paramHandler.currentSetName)
        else:
            self.fieldParamSet.setCurrentIndex(-1)
    
    def setupContentForFirstRun(self):
        # Generate project name
        self.fieldProjName.setText(self.projectHandler.generateProjectName())
        # Check QGIS table of content for raster layer
        self.updateRasterList()
        # Load all predefined and user-defined parameter sets from the
        # config folder
        self.paramHandler.setParameterSet(self.paramHandler.defaultSet)
        self.fillParametersetList()
        
        self.fillInValues()
        
        # Set point types
        self.fieldTypeA.setCurrentIndex(
            self.projectHandler.getPointTypeAsIdx('A'))
        self.fieldTypeE.setCurrentIndex(
            self.projectHandler.getPointTypeAsIdx('E'))
    
    def setupContent(self):
        self.startAlgorithm = False
        self.goToAdjustment = False
        # Generate project name
        self.fieldProjName.setText(self.projectHandler.getProjectName())
        
        if self.projectHandler.heightSourceType in ['dhm', 'dhm_list']:
            # Enable gui elements
            self.enableRasterHeightSource()
            # Search raster and if necessary load from disk
            rasternames = self.searchForRaster(
                self.projectHandler.getHeightSourceAsStr(source=True))
            self.setRaster(rasternames)
    
        elif self.projectHandler.heightSourceType == 'survey':
            # Enable gui elements
            self.enableSurveyDataHeightSource()
            # Show data on map and in gui
            self.loadSurveyData()
        
        else:
            # Raster could not be loaded correctly
            self.rasterField.blockSignals(True)
            self.rasterField.deselectAllOptions()
            self.rasterField.blockSignals(False)
            self.fieldSurveyDataPath.setText('')
        
        # Update start and end point
        self.checkPoints()
        
        # Load all predefined and user-defined parameter sets from the
        # config folder (maybe a new set was added when project was opened)
        self.fillParametersetList()
        # Fill in parameter values
        self.fillInValues()
        # Deactivate / Activate status of field HMKran depending on
        #  point type of start point
        self.updateHMKran(self.projectHandler.A_type)
        # Fill in project header data (if present)
        self.fillInPrHeaderData()

        # Set point types
        self.fieldTypeA.setCurrentIndex(
            self.projectHandler.getPointTypeAsIdx('A'))
        self.fieldTypeE.setCurrentIndex(
            self.projectHandler.getPointTypeAsIdx('E'))
    
    def fillParametersetList(self):
        self.fieldParamSet.blockSignals(True)
        self.fieldParamSet.clear()
        self.fieldParamSet.addItems(self.paramHandler.getParametersetNames())
        if self.paramHandler.currentSetName:
            self.fieldParamSet.setCurrentText(self.paramHandler.currentSetName)
        else:
            self.fieldParamSet.setCurrentIndex(-1)
        self.fieldParamSet.blockSignals(False)
    
    def setParameterSet(self):
        name = self.fieldParamSet.currentText()
        if name:
            self.paramHandler.setParameterSet(name)
            # Fill in values of parameter set
            self.fillInValues()
            # Deactivate / Activate status of field HMKran depending on
            #  point type of start point
            self.updateHMKran(self.projectHandler.A_type)
    
    def fillInValues(self):
        """Fills parameter values into GUI fields."""
        for field_name, field in self.parameterFields.items():
            val = self.paramHandler.getParameterAsStr(field_name)
            if val is not None:
                if isinstance(field, QComboBox):
                    val = self.paramHandler.getParameter(field_name)
                    field.setCurrentIndex(val)
                    continue
                
                field.setText(val)
    
    def onSaveParameterSet(self):
        if not self.paramHandler.checkValidState():
            return
        self.paramSetWindow.setData(self.paramHandler.getParametersetNames(),
                                    self.paramHandler.SETS_PATH)
        self.paramSetWindow.exec()
        setname = self.paramSetWindow.getNewSetname()
        if setname:
            self.paramHandler.saveParameterSet(setname)
            self.fieldParamSet.addItem(setname)
            self.fieldParamSet.setCurrentText(setname)
    
    def onRemoveParameterSet(self):
        currParamset = self.fieldParamSet.currentText()
        # No action if there is no parameter set specified
        if currParamset == '':
            return
        # Standard set cannot be deleted
        if currParamset == self.paramHandler.defaultSet:
            QMessageBox.critical(self, self.tr('Parameterset loeschen'),
                self.tr('Standardparameterset kann nicht geloescht werden.'), QMessageBox.Ok)
            return
        
        # Ask before removing
        msgBox = QMessageBox()
        msgBox.setIcon(QMessageBox.Information)
        msgBox.setWindowTitle(self.tr('Parameterset loeschen'))
        msgBox.setText(self.tr('Moechten Sie das Parameterset wirklich loeschen?'))
        msgBox.setStandardButtons(QMessageBox.No | QMessageBox.Yes)
        noBtn = msgBox.button(QMessageBox.No)
        noBtn.setText(self.tr("Nein"))
        yesBtn = msgBox.button(QMessageBox.Yes)
        yesBtn.setText(self.tr("Ja"))
        msgBox.show()
        msgBox.exec()
        
        if msgBox.clickedButton() == yesBtn:
            success = self.paramHandler.removeParameterSet(currParamset)
            if not success:
                QMessageBox.critical(self, self.tr('Parameterset loeschen'),
                    self.tr('Ein Fehler ist aufgetreten. Parameterset kann nicht geloescht werden.'), QMessageBox.Ok)
            else:
                # Set default set
                self.paramHandler.setParameterSet(self.paramHandler.defaultSet)
                # Update drop down list to remove set
                self.fillParametersetList()
                # Fill in values of default set
                self.fillInValues()
                # Deactivate / Activate status of field HMKran depending on
                #  point type of start point
                self.updateHMKran(self.projectHandler.A_type)
            
    def updateRasterList(self):
        rasterlist = self.getAvailableRaster()
        self.addRastersToDropdown([lyr['name'] for lyr in rasterlist])
        return rasterlist
    
    def getAvailableRaster(self):
        """Go trough table of content and collect all raster layers.
        """
        rColl = []
        for item in QgsProject.instance().layerTreeRoot().findLayers():
            lyr = item.layer()
            if lyr.type() == 1 and lyr.providerType() not in ['wms', 'wmts']:
                lyrName = lyr.name()
                r = {
                    'lyr': lyr,
                    'name': lyrName
                }
                rColl.append(r)
        return rColl
    
    def addRastersToDropdown(self, rasterList):
        """Put list of raster layers into drop down menu of self.rasterField.
        If raster name contains some kind of "DHM", select it."""
        self.rasterField.blockSignals(True)
        selectedRasters = self.rasterField.checkedItems()
        self.rasterField.clear()
        self.rasterField.addItems(rasterList)
        selectedRastersNew = [r for r in selectedRasters if r in rasterList]
        self.rasterField.setCheckedItems(selectedRastersNew)
        self.rasterField.blockSignals(False)
    
    def onChangeRaster(self):
        """Triggered by choosing a raster from the drop down menu."""
        self.setRaster()
        # Update start and end point
        self.checkPoints()
    
    def setRaster(self, selectedRasters: list = None):
        """Sets selected raster in project handler"""
        if not selectedRasters:
            selectedRasters = self.rasterField.checkedItems()
        rasterlist = self.getAvailableRaster()
        rasterLyrList = []
        singleRasterLayer = None
        
        for rlyr in rasterlist:
            if rlyr['name'] in selectedRasters:
                rasterLyrList.append(rlyr['lyr'])

        if len(rasterLyrList) == 1:
            singleRasterLayer = rasterLyrList[0]
            self.projectHandler.setHeightSource(rasterLyrList[0], 'dhm')
            rasterValid = True
        elif len(rasterLyrList) > 1:
            self.projectHandler.setHeightSource(rasterLyrList, 'dhm_list')
            rasterValid = True
        else:
            rasterValid = False

        # Check spatial reference of raster and show message
        if not rasterValid or not self.checkEqualSpatialRef():
            # Unset raster
            self.projectHandler.resetHeightSource()
            # Remove raster selection
            self.rasterField.blockSignals(True)
            self.rasterField.deselectAllOptions()
            self.rasterField.blockSignals(False)
            rasterValid = False

        # Select layer in panel if it's only one
        if rasterValid and singleRasterLayer:
            self.iface.setActiveLayer(singleRasterLayer)
            
        # If a raster was selected, a contour layer can be generated
        self.contourLyrButton.setEnabled(rasterValid)
        # Activate/Deactivate other ui elements
        self.toggleCableLineUI(rasterValid)
    
    def searchForRaster(self, rasterpaths):
        """ Checks if a raster from a saved project is present in the table
        of content or exists at the given location (path).
        """
        if isinstance(rasterpaths, str):
            rasterpaths = [rasterpaths]
            
        availRaster = self.getAvailableRaster()
        rasterNameList = []
        self.rasterField.blockSignals(True)
        for path in rasterpaths:
            rasterinQGIS = False
            for i, rlyr in enumerate(availRaster):
                lyrPath = rlyr['lyr'].dataProvider().dataSourceUri()
                # Raster has been loaded in QGIS project already
                if lyrPath == path:
                    # Sets the dhm name in the drop down
                    self.rasterField.setItemCheckState(i, Qt.Checked)
                    rasterNameList.append(rlyr['name'])
                    rasterinQGIS = True
                    break
            if not rasterinQGIS:
                # Raster is still at same location in file system
                if os.path.exists(path):
                    # Load raster
                    newRaster = QFileInfo(path).baseName()
                    rasterLyr = QgsRasterLayer(path, newRaster)
                    QgsProject.instance().addMapLayer(rasterLyr)
                    # Update drop down menu
                    
                    dropdownItems = self.updateRasterList()
                    for idx, item in enumerate(dropdownItems):
                        if item['name'] == newRaster:
                            self.rasterField.setItemCheckState(idx, Qt.Checked)
                            break
                    rasterNameList.append(newRaster)
        if not rasterNameList:
            self.rasterField.deselectAllOptions()
            txt = self.tr("Raster '{}' nicht vorhanden".format(', '.join(rasterpaths)))
            title = self.tr("Fehler beim Laden des Rasters")
            QMessageBox.information(self, title, txt)
        self.rasterField.blockSignals(False)
        return rasterNameList
    
    def checkEqualSpatialRef(self):
        # Check spatial reference of newly added raster
        heightSource = self.projectHandler.heightSource
        if not heightSource:
            return False
        hsType = self.projectHandler.heightSourceType
        mapCrs = QgsProject.instance().crs()
        lyrCrs = heightSource.spatialRef
        title = self.tr('Fehler Koordinatenbezugssystem (KBS)')
        msg = ''
        success = True
        
        # Height source has a different crs than map --> map crs is changed
        if lyrCrs.isValid() and not lyrCrs.isGeographic() and lyrCrs != mapCrs:
            QgsProject.instance().setCrs(lyrCrs)
            self.canvas.refresh()
            return True
        
        # Height source is in a geographic crs
        elif lyrCrs.isValid() and lyrCrs.isGeographic():
            # Raster is in geographic coordinates --> automatic transformation
            # not possible
            if hsType in ['dhm', 'dhm_list']:
                msg = self.tr('KBS-Fehler - Raster kann nicht verarbeitet werden')\
                    .format(lyrCrs.description(), lyrCrs.authid())
                success = False
            # Survey data can be transformed to map crs
            elif hsType == 'survey' and not mapCrs.isGeographic():
                # Survey data is transformed to map reference system
                heightSource.reprojectToCrs(mapCrs)
                success = True
            
            elif hsType == 'survey' and mapCrs.isGeographic():
                # Transform to LV95 by default
                heightSource.reprojectToCrs(None)
                msg = self.tr('KBS-Fehler - Felddaten und QGIS in geografischem KBS')
                QgsProject.instance().setCrs(lyrCrs)
                self.canvas.refresh()
                success = True
        
        elif not lyrCrs.isValid():
            if mapCrs.isGeographic():
                msg = self.tr('KBS-Fehler - Bezugssystem des Rasters unbekannt')
                heightSource.spatialRef = QgsCoordinateReferenceSystem(CH_CRS)
                QgsProject.instance().setCrs(lyrCrs)
                self.canvas.refresh()
                success = True
            else:
                # Reference system of survey data not valid or unknown. We use
                #  refsys of map
                heightSource.spatialRef = mapCrs
                success = True
        
        if msg:
            QMessageBox.information(self, title, msg)
        return success
    
    def onLoadSurveyData(self):
        self.surveyImportDialog.exec()
        if self.surveyImportDialog.doImport:
            self.projectHandler.resetProfile()
            # Load data from csv file
            self.projectHandler.setHeightSource(None, 'survey',
                self.surveyImportDialog.filePath,
                self.surveyImportDialog.surveyType)
            self.loadSurveyData()
            self.checkPoints()
            # Excel protocol can include project header data
            self.fillInPrHeaderData()
            self.fillInValues()
    
    def loadSurveyData(self):
        # Remove earlier survey data layer
        self.removeSurveyDataLayer()

        # Check the spatial reference and inform user if necessary
        if not self.checkEqualSpatialRef():
            self.projectHandler.resetHeightSource()
            self.projectHandler.resetProfile()
        
        heightSource = self.projectHandler.heightSource
        if heightSource and heightSource.valid:
            # Create and add QGS layers of data to the map
            self.surveyLineLayer, \
                self.surveyPointLayer = createProfileLayers(heightSource)
            # Zoom to layer
            self.iface.setActiveLayer(self.surveyPointLayer)
            self.iface.zoomToActiveLayer()

            # Set path to csv in read only lineEdit
            self.fieldSurveyDataPath.setText(self.projectHandler.getHeightSourceAsStr())
            # Activate draw tool
            self.drawTool.surveyDataMode = True
            
            # Activate ui elements
            self.toggleCableLineUI(True)
            highlightButton(self.draw)
        else:
            self.fieldSurveyDataPath.setText('')
            self.drawTool.surveyDataMode = False
            self.toggleCableLineUI(False)
    
    def removeSurveyDataLayer(self):
        try:
            if self.surveyLineLayer:
                QgsProject.instance().removeMapLayer(self.surveyLineLayer.id())
                self.surveyLineLayer = None
            if self.surveyPointLayer:
                QgsProject.instance().removeMapLayer(self.surveyPointLayer.id())
                self.surveyPointLayer = None
        except RuntimeError:
            return
    
    def setProjName(self, projname):
        self.projectHandler.setProjectName(projname)
    
    # TODO Unset Focus of field when clicking on something else, doesnt work yet
    # def mousePressEvent(self, event):
    #     focused_widget = QtGui.QApplication.focusWidget()
    #     if isinstance(focused_widget, QtGui.QLineEdit):
    #         focused_widget.clearFocus()
    #     QtGui.QDialog.mousePressEvent(self, event)
    
    def toggleCableLineUI(self, isEnabled):
        # Activate draw button
        self.draw.setEnabled(isEnabled)
        if not isEnabled:
            self.draw.setToolTip(self.tr('Bitte erst Terraindaten definieren'))
            unHighlightButton(self.draw)
        else:
            self.draw.setToolTip('')
        self.osmLyrButton.setEnabled(isEnabled)
        # Enable coordinate fields
        for field in self.coordFields.values():
            field.setEnabled(isEnabled)

    def drawLine(self):
        if self.drawTool.isActive:
            self.drawTool.reset()
            return
        if self.projectHandler.heightSourceType in ['dhm', 'dhm_list']:
            self.drawTool.drawLine()
        elif self.projectHandler.heightSourceType == 'survey':
            self.drawTool.drawLine(self.projectToProfileLine)
    
    def projectToProfileLine(self, mapPosition):
        point = self.projectHandler.heightSource.projectPositionOnToLine(mapPosition)
        return QgsPointXY(point[0], point[1])
    
    def onCoordFieldChange(self, pointType):
        x = castToNum(self.coordFields[pointType + 'x'].text())
        y = castToNum(self.coordFields[pointType + 'y'].text())
        [x, y], coordState, hasChanged = self.projectHandler.setPoint(
            pointType, [x, y])
        if hasChanged:
            self.changePoint(pointType, [x, y], coordState)
            self.updateLineByCoordFields()
    
    def changePoint(self, pointType, coords, coordState):
        x = coords[0]
        y = coords[1]
        # Update profile line geometry
        if x and y:
            self.linePoints[pointType] = QgsPointXY(x, y)
        else:
            self.linePoints[pointType] = QgsPointXY(-100, -100)
        
        # Update coordinate state icon
        self.changePointSym(coordState[pointType], pointType)
        
        # Update coordinate field (formatted string)
        [xStr, yStr] = self.projectHandler.getPointAsStr(pointType)
        self.coordFields[pointType + 'x'].blockSignals(True)
        self.coordFields[pointType + 'y'].blockSignals(True)
        self.coordFields[pointType + 'x'].setText(xStr)
        self.coordFields[pointType + 'y'].setText(yStr)
        self.coordFields[pointType + 'x'].blockSignals(False)
        self.coordFields[pointType + 'y'].blockSignals(False)
        
        # Update profile button and profile length
        self.buttonShowProf.setEnabled(self.projectHandler.profileIsValid())
        self.laenge.setText(self.projectHandler.getProfileLenAsStr())
    
    def checkPoints(self):
        [Ax, Ay], coordState = self.projectHandler.getPoint('A')
        [Ex, Ey], coordState = self.projectHandler.getPoint('E')
        self.changePoint('A', [Ax, Ay], coordState)
        self.changePoint('E', [Ex, Ey], coordState)
        # Draw line
        self.updateLineByCoordFields()
    
    def updateLineByCoordFields(self):
        self.drawTool.reset()
        if self.projectHandler.profileIsValid():
            self.drawTool.updateLine(list(self.linePoints.values()))
    
    def updateLineByMapDraw(self, newpoint, pointType):
        [x, y], coordState, hasChanged = self.projectHandler.setPoint(
            pointType, [newpoint.x(), newpoint.y()])
        self.changePoint(pointType, [x, y], coordState)
    
    def changePointSym(self, state, point):
        iPath = '<html><head/><body><p><img src=":/plugins/SeilaplanPlugin/' \
                'gui/icons/icon_{}.png"/></p></body></html>'
        greenTxt = ''
        yellowTxt = self.tr('zu definieren')
        redTxt = self.tr('ausserhalb Raster')
        
        if point == 'A':
            if state == 'green':
                self.symA.setText(iPath.format('green'))
                self.symA.setToolTip(greenTxt)
            if state == 'yellow':
                self.symA.setText(iPath.format('yellow'))
                self.symA.setToolTip(yellowTxt)
            if state == 'red':
                self.symA.setText(iPath.format('red'))
                self.symA.setToolTip(redTxt)
        if point == 'E':
            if state == 'green':
                self.symE.setText(iPath.format('green'))
                self.symE.setToolTip(greenTxt)
            if state == 'yellow':
                self.symE.setText(iPath.format('yellow'))
                self.symE.setToolTip(yellowTxt)
            if state == 'red':
                self.symE.setText(iPath.format('red'))
                self.symE.setToolTip(redTxt)
    
    def onClickOsmButton(self):
        """Add a Background layer."""
        statusMsg, severity = addBackgroundMap(self.canvas)
        self.msgBar.pushMessage(self.tr('Hintergrundkarte laden'), statusMsg, severity)
    
    def onClickContourButton(self):
        """Calcluate contour lines from currently selected dhm and add them to
        as a layer."""
        if self.projectHandler.heightSource.contourLayer is None:
            createContours(self.canvas, self.projectHandler.heightSource)
    
    def onFinishedLineDraw(self, linecoord):
        self.projectHandler.resetProfile()
        self.updateLineByMapDraw(linecoord[0], 'A')
        self.updateLineByMapDraw(linecoord[1], 'E')
        # Stop pressing button down
        self.draw.setChecked(False)
        unHighlightButton(self.draw)
    
    def onShowProfile(self):
        try:
            profile = self.projectHandler.preparePreviewProfile()
        except Exception:
            QMessageBox.critical(self, self.tr('Fehler'),
                self.tr('Unerwarteter Fehler bei Erstellung des Profils'))
            return
        if profile:
            self.profileWin.setProfile(profile)
            self.profileWin.setPoleData(
                self.projectHandler.fixedPoles['poles'],
                self.projectHandler.noPoleSection)
            self.profileWin.exec()
    
    def onLoadProjects(self):
        title = self.tr('Projekt laden')
        fFilter = self.tr('Json- oder Text-Datei') + ' (*.json *.txt)'
        filename, _ = QFileDialog.getOpenFileName(self, title,
                                                  self.confHandler.getCurrentPath(),
                                                  fFilter)
        if filename:
            self.confHandler.reset()
            success = self.confHandler.loadSettings(filename)
            if success:
                self.setupContent()
            else:
                QMessageBox.critical(self, self.tr('Fehler beim Laden'),
                    self.tr('Projektdatei konnte nicht geladen werden.'))
        else:
            return False
    
    def onSaveProject(self):
        title = self.tr('Projekt speichern')
        fFilter = self.tr('Json (*.json)')
        self.readoutPrHeaderData()
        if not self.confHandler.checkValidState():
            return
        filename, _ = QFileDialog.getSaveFileName(self, title,
                        os.path.join(self.confHandler.getCurrentPath(),
                                     self.projectHandler.getProjectName() + '.json'), fFilter)
        
        if filename:
            if filename[-5:] != '.json':
                filename += '.json'
            self.confHandler.saveSettings(filename)
        else:
            return False
    
    def onTypeAChange(self):
        idx = self.fieldTypeA.currentIndex()
        if idx == -1:
            return
        self.projectHandler.setPointType('A', idx)
        self.updateHMKran(self.projectHandler.A_type)
    
    def onTypeEChange(self):
        idx = self.fieldTypeE.currentIndex()
        self.projectHandler.setPointType('E', idx)
    
    def updateHMKran(self, poleType):
        # Update GUI: fieldHMKran
        if poleType in ['pole', 'pole_anchor']:
            self.fieldHMKran.setEnabled(False)
            self.fieldHMKran.setText('')
        elif poleType == 'crane':
            paramVal = self.paramHandler.getParameterAsStr('HM_Kran')
            self.fieldHMKran.setText(paramVal)
            self.fieldHMKran.setEnabled(True)
        
    def onInfo(self):
        title = 'info'
        msg = ''
        imageName = None
        
        if self.sender().objectName() == 'buttonInfo':
            title = 'SEILAPLAN Info'
            msg = self.tr('Infotext').format(os.path.join(os.path.dirname(
                os.path.dirname(__file__)), 'help', 'docs'))
        
        elif self.sender().objectName() == 'infoRasterlayer':
            title = self.tr('Hoeheninformationen laden')
            msg = self.tr('Hoeheninformation - Erklaerung Raster')
        elif self.sender().objectName() == 'infoSurveyData':
            title = self.tr('Hoeheninformationen laden')
            msg = self.tr('Hoeheninformation - Erklaerung Felddaten')
        
        elif self.sender().objectName() == 'infoPointA':
            title = self.tr('Anfangspunkt')
            imageName = 'Anfangspunkt.png'
        elif self.sender().objectName() == 'infoPointE':
            title = self.tr('Endpunkt')
            imageName = 'Endpunkt.png'
        
        elif self.sender().objectName() == 'infoBodenabstand':
            title = self.tr('Erklaerungen zum Bodenabstand')
            imageName = 'Bodenabstand.png'
        elif self.sender().objectName() == 'infoStuetzen':
            title = self.tr('Erklaerungen zu den Zwischenstuetzen')
            imageName = 'Stuetzen.png'
        
        elif self.sender().objectName() == 'infoQ':
            title = self.tr("Gesamtlast")
            msg = self.tr('Erklaerung Gesamtlast')
        elif self.sender().objectName() == 'infoSK':
            self.tr("Grundspannung"),
            msg = self.tr('Erklaerung Grundspannung')
        elif self.sender().objectName() == 'infoFieldE':
            title = self.tr("Elastizitaetsmodul Tragseil")
            msg = self.tr('Elastizitaetsmodul Tragseil Erklaerung')
        elif self.sender().objectName() == 'infoFieldFuellF':
            title = self.tr("Fuellfaktor")
            msg = self.tr('Fuellfaktor Erklaerung')
        elif self.sender().objectName() == 'infoFieldSFT':
            title = self.tr("Sicherheitsfaktor Tragseil")
            msg = self.tr('Europaweit wird ein Sicherheitsfaktor von 3.0 fuer das '
                          'Tragseil verwendet.')
        
        elif self.sender().objectName() == 'infoBerechnung':
            title = self.tr("Naechste Schritte")
            msg = self.tr('Erklaerungen Berechnungsbuttons')
        
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
        
    def goToAdjustmentWindow(self):
        if self.confHandler.checkValidState() \
                and self.checkEqualSpatialRef \
                and self.confHandler.prepareForCalculation():
            self.readoutPrHeaderData()
            self.startAlgorithm = False
            self.goToAdjustment = True
            self.close()
        else:
            return False
    
    def apply(self):
        if self.confHandler.checkValidState() \
                and self.checkEqualSpatialRef \
                and self.paramHandler.checkBodenabstand() \
                and self.confHandler.prepareForCalculation():
            self.readoutPrHeaderData()
            self.startAlgorithm = True
            self.goToAdjustment = False
            self.close()
        else:
            # If project info or parameter are missing or wrong, algorithm
            # can not start
            return False
    
    def cancel(self):
        """ Called when 'Cancel' is pressed."""
        self.close()
    
    def cleanUp(self):
        # Save user settings
        self.confHandler.updateUserSettings()
        # Clean markers and lines from map canvas
        self.drawTool.reset()
        # Remove survey line
        self.removeSurveyDataLayer()
    
    def closeEvent(self, QCloseEvent):
        """Last method that is called before main window is closed."""
        # Close additional dialogs
        self.imgBox.close()
        if self.profileWin.isVisible():
            self.profileWin.close()
        
        if self.startAlgorithm or self.goToAdjustment:
            self.drawTool.reset()
        else:
            self.cleanUp()




def highlightButton(button):
    button.setStyleSheet("QPushButton { padding: 3px; border: 2px solid; border-radius: 4px; border-color: red }")


def unHighlightButton(button):
    button.setStyleSheet("")


    
