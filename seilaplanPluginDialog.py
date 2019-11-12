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
from qgis.PyQt.QtCore import QFileInfo, QCoreApplication
from qgis.PyQt.QtWidgets import QDialog, QMessageBox, QFileDialog, QComboBox
from qgis.PyQt.QtGui import QPixmap
from qgis.core import QgsRasterLayer, QgsPointXY, QgsProject
from processing.core.Processing import Processing

# Further GUI modules for functionality
from .gui.guiHelperFunctions import (DialogWithImage, createContours,
                                     loadOsmLayer)
from .configHandler import ConfigHandler, formatNum
# GUI elements
from .gui.saveDialog import DialogSaveParamset
from .gui.mapMarker import MapMarkerTool
from .gui.ui_seilaplanDialog import Ui_SeilaplanDialog
from .gui.profileDialog import ProfileDialog
from .gui.profileCreation import PreviewProfile

# OS dependent line break
nl = os.linesep

# Source of icons in GUI
greenIcon = '<html><head/><body><p><img src=":/plugins/SeilaplanPlugin/' \
            'gui/icons/icon_green.png"/></p></body></html>'
yellowIcon = '<html><head/><body><p><img src=":/plugins/SeilaplanPlugin/' \
             'gui/icons/icon_yellow.png"/></p></body></html>'
redIcon = '<html><head/><body><p><img src=":/plugins/SeilaplanPlugin/' \
          'gui/icons/icon_red.png"/></p></body></html>'
# Text next to coord status
greenTxt = ''
yellowTxt = 'zu definieren'
redTxt = 'ausserhalb Raster'

# Titles of info images
infImg = {'Bodenabstand': 'Erklärungen zum Bodenabstand',
          'VerankerungA': 'Erklärungen zur Verankerung am Anfangspunkt',
          'VerankerungE': 'Erklärungen zur Verankerung am Anfangspunkt',
          'Stuetzen': 'Erklärungen zu den Zwischenstützen'}

# Info button text
infoTxt = ("SEILAPLAN - Seilkran-Layoutplaner\n\n"
           "SEILAPLAN berechnet auf Grund eines digitalen Höhenmodells zwischen "
           "definierten Anfangs- und Endkoordinaten sowie technischen Parametern das "
           "optimale Seillinienlayout. Es werden Position und Höhe der Stütze,"
           "sowie die wichtigsten Kennwerte der Seillinie bestimmt.\n\n"
           "Realisierung:\n\nProfessur für forstliches Ingenieurwesen\n"
           "ETH Zürich\n8092 Zürich\n(Konzept, Realisierung Version 1.x für QGIS 2)\n\n"
           "Gruppe Forstliche Produktionssysteme FPS\n"
           "Eidgenössische Forschungsanstalt WSL\n"
           "8903 Birmensdorf\n(Realisierung Version 2.x für QGIS 3)\n\n"
           "\nBeteiligte Personen:\n\n"
           "Leo Bont, Hans Rudolf Heinimann (Konzept, Mechanik)\nPatricia Moll "
           "(Implementation in Python / QGIS)\n\n\n"
           "SEILAPLAN ist freie Software: Sie können sie unter den Bedingungen "
           "der GNU General Public License, wie von der Free Software Foundation, "
           "Version 2 der Lizenz oder (nach Ihrer Wahl) jeder neueren "
           "veröffentlichten Version, weiterverbreiten und/oder modifizieren.\n")


class SeilaplanPluginDialog(QDialog, Ui_SeilaplanDialog):
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
        self.homePath = os.path.dirname(__file__)
        
        # Setup GUI of SEILAPLAN (import from ui_seilaplanDialog.py)
        self.setupUi(self)
        
        # Interaction with canvas, is used to draw onto map canvas
        self.drawTool = MapMarkerTool(self.canvas)
        # Connect emitted signals
        self.drawTool.sig_lineFinished.connect(self.onFinishedLineDraw)
        
        # Dictionary of all GUI setting fields
        self.parameterFields = {}
        
        # GUI fields and variables handling coordinate information
        self.coordFields = {}
        self.linePoints = {
            'A': QgsPointXY(-100, -100),
            'E': QgsPointXY(-100, -100)
        }
        
        # Organize parameter GUI fields in dictionary
        self.groupFields()
        self.enableToolTips()
        
        # Dialog with explanatory images
        self.imgBox = DialogWithImage()
        
        # Additional GIS-Layers
        self.osmLyrButton.setEnabled(False)
        self.contourLyrButton.setEnabled(False)
        
        # Connect GUI elements from dialog window with functions
        self.connectGuiElements()
        
        # Set initial sate of some buttons
        # Button to show profile
        self.buttonShowProf.setEnabled(False)
        # Button that activates drawing on map
        self.draw.setEnabled(False)
        # Button stays down when pressed
        self.draw.setCheckable(True)
        
        # Dialog window with height profile
        self.profileWin = ProfileDialog(self, self.iface, self.drawTool,
                                        self.projectHandler)

        # Dialog windows for saving parameter and cable sets
        self.paramSetWindow = DialogSaveParamset(self)
        
        Processing.initialize()
    
    def connectGuiElements(self):
        """Connect GUI elements with functions.
        """
        self.buttonCancel.clicked.connect(self.cancel)
        self.buttonRun.clicked.connect(self.apply)
        self.btnAdjustment.clicked.connect(self.goToAdjustmentWindow)
        self.buttonOpenPr.clicked.connect(self.onLoadProjects)
        self.buttonSavePr.clicked.connect(self.onSaveProject)
        self.rasterField.currentTextChanged.connect(self.onChangeRaster)
        self.buttonRefreshRa.clicked.connect(self.updateRasterList)
        self.buttonInfo.clicked.connect(self.onInfo)
        
        # Info buttons
        self.infoBodenabstand.clicked.connect(self.onShowInfoImg)
        self.infoVerankerungA.clicked.connect(self.onShowInfoImg)
        self.infoVerankerungE.clicked.connect(self.onShowInfoImg)
        self.infoStuetzen.clicked.connect(self.onShowInfoImg)
        
        # OSM map and contour buttons
        self.osmLyrButton.clicked.connect(self.onClickOsmButton)
        self.contourLyrButton.clicked.connect(self.onClickContourButton)
        
        # Filed that contains project names
        self.fieldProjName.textChanged.connect(self.setProjName)
        # Button starts map drawing
        self.draw.clicked.connect(self.drawTool.drawLine)
        # Button shows profile window
        self.buttonShowProf.clicked.connect(self.onShowProfile)
        # Drop down field for parameter set choices
        self.fieldParamSet.currentIndexChanged.connect(self.setParameterSet)
        self.buttonSaveParamset.clicked.connect(self.onSaveParameterSet)
        
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
            if isinstance(inputField, QComboBox) and name == 'GravSK':
                inputField.currentTextChanged.connect(
                    lambda newVal: self.getListenerComboBox('GravSK', newVal))
            else:
                inputField.editingFinished.connect(
                    self.getListenerLineEdit(name))
    
    def groupFields(self):
        """Combine all GUI fields in dictionary for faster access.
        """
        self.parameterFields = {
            'Q': self.fieldQ,
            'qT': self.fieldQt,
            'A': self.fieldA,
            'E': self.fieldE,
            'zul_SK': self.fieldzulSK,
            'min_SK': self.fieldminSK,
            'qz1': self.fieldqz1,
            'qz2': self.fieldqz2,
            'Bodenabst_min': self.fieldBabstMin,
            'Bodenabst_A': self.fieldBabstA,
            'Bodenabst_E': self.fieldBabstE,
            'GravSK': self.fieldGravSK,
            'Befahr_A': self.fieldBefA,
            'Befahr_E': self.fieldBefE,
            'HM_Anfang': self.fieldHManf,
            'd_Anker_A': self.fieldDAnkA,
            'HM_Ende_min': self.fieldHMeMin,
            'HM_Ende_max': self.fieldHMeMax,
            'd_Anker_E': self.fieldDAnkE,
            'Min_Dist_Mast': self.fieldMinDist,
            'L_Delta': self.fieldLdelta,
            'N_Zw_Mast_max': self.fieldNzwSt,
            'HM_min': self.fieldHMmin,
            'HM_max': self.fieldHMmax,
            'HM_Delta': self.fieldHMdelta,
            'HM_nat': self.fieldHMnat
        }
        self.coordFields = {
            'Ax': self.coordAx,
            'Ay': self.coordAy,
            'Ex': self.coordEx,
            'Ey': self.coordEy
        }
    
    def getListenerLineEdit(self, property_name):
        return lambda: self.parameterChangedLineEdit(property_name)
    
    def getListenerComboBox(self, property_name, newVal):
        return self.paramHandler.setParameter(property_name, newVal)
    
    def parameterChangedLineEdit(self, property_name):
        # Deactivate editFinished signal so it is not fired twice when
        # setParameter() shows a QMessageBox
        self.parameterFields[property_name].blockSignals(True)
        newVal = self.parameterFields[property_name].text()
        newValAsStr = self.paramHandler.setParameter(property_name, newVal)
        if newValAsStr is not False:
            # Change current parameter set name
            if self.paramHandler.currentSetName:
                self.fieldParamSet.setCurrentText(self.paramHandler.currentSetName)
            else:
                self.fieldParamSet.setCurrentIndex(-1)
            # Insert correctly formatted value
            self.parameterFields[property_name].setText(newValAsStr)
        self.parameterFields[property_name].blockSignals(False)
    
    def setupContentForFirstRun(self):
        # Generate project name
        self.fieldProjName.setText(self.projectHandler.generateProjectName())
        # Check QGIS table of content for raster layer
        rasterlist = self.updateRasterList()
        # Select first raster that has the word "dhm" in it, else select first
        # layer
        dhm = self.searchForDhm(rasterlist)
        if dhm:
            self.setRaster(dhm)
            self.checkPoints()
        
        # Load all predefined and user-defined parameter sets from the
        # config folder
        parameterSetNames = self.paramHandler.getParametersetNames()
        # Add set names to drop down
        self.fieldParamSet.addItems(parameterSetNames)
        # Set standard parameter set and associated parameters
        self.paramHandler.setParameterSet('Standardwerte')
        self.fieldParamSet.setCurrentText('Standardwerte')
    
    def setupContent(self):
        self.startAlgorithm = False
        self.goToAdjustment = False
        # Generate project name
        self.fieldProjName.setText(self.projectHandler.getProjectName())
        
        rasterLyr = self.searchForRaster(self.projectHandler.getDhmAsStr())
        # Update raster object with qgs raster layer
        self.projectHandler.setDhm(rasterLyr)
        # Update start and end point
        self.checkPoints()
        
        # Tell profile window to update its content on next show
        self.updateProfileWinContent()
        
        # Set parameter set
        if self.paramHandler.currentSetName:
            self.fieldParamSet.setCurrentText(self.paramHandler.currentSetName)
        else:
            self.fieldParamSet.setCurrentIndex(-1)
        # Fill in parameter values
        self.fillInValues()
    
    def enableToolTips(self):
        for field_name, field in list(self.parameterFields.items()):
            field.setToolTip(self.paramHandler.getParameterTooltip(field_name))
    
    def setParameterSet(self):
        name = self.fieldParamSet.currentText()
        if name:
            self.paramHandler.setParameterSet(name)
            # Fill in values of parameter set
            self.fillInValues()
    
    def fillInValues(self):
        """Fills parameter values into GUI fields."""
        for field_name, field in self.parameterFields.items():
            val = self.paramHandler.getParameterAsStr(field_name)
            if val:
                if isinstance(field, QComboBox):
                    field.setCurrentText(val)
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
    
    def updateRasterList(self):
        rasterlist = self.getAvailableRaster()
        self.addRastersToDropDown(rasterlist)
        return rasterlist
    
    @staticmethod
    def getAvailableRaster():
        """Go trough table of content and collect all raster layers.
        """
        rColl = []
        for l in QgsProject.instance().layerTreeRoot().findLayers():
            lyr = l.layer()
            if lyr.type() == 1 and lyr.name() != 'OSM_Karte':  # = raster
                lyrName = lyr.name()
                r = {
                    'lyr': lyr,
                    'name': lyrName
                }
                rColl.append(r)
        return rColl
    
    def addRastersToDropDown(self, rasterList):
        """Put list of raster layers into drop down menu of self.rasterField.
        If raster name contains some kind of "DHM", select it.
        """
        self.rasterField.blockSignals(True)
        selectedRaster = self.rasterField.currentText()
        for i in reversed(list(range(self.rasterField.count()))):
            self.rasterField.removeItem(i)
        for rLyr in rasterList:
            self.rasterField.addItem(rLyr['name'])
        if selectedRaster != '':
            self.rasterField.setCurrentText(selectedRaster)
        self.rasterField.blockSignals(False)
    
    def searchForDhm(self, rasterlist):
        """ Search for a dhm to set as initial raster when the plugin is
        opened."""
        self.rasterField.blockSignals(True)
        dhmName = ''
        searchStr = ['dhm', 'Dhm', 'DHM', 'dtm', 'DTM', 'Dtm']
        for rLyr in rasterlist:
            if sum([item in rLyr['name'] for item in searchStr]) > 0:
                dhmName = rLyr['name']
                self.rasterField.setCurrentText(dhmName)
                break
        if not dhmName and len(rasterlist) > 0:
            dhmName = rasterlist[0]['name']
            self.rasterField.setCurrentText(dhmName)
        self.rasterField.blockSignals(False)
        return dhmName
    
    def onChangeRaster(self, rastername):
        self.setRaster(rastername)
        # Update start and end point
        self.checkPoints()
    
    def setRaster(self, rastername):
        """Get the current selected Raster in self.rasterField and collect
        useful information about it.
        """
        rasterFound = False
        if isinstance(rastername, int):
            rastername = self.rasterField.currentText()
        rasterlist = self.getAvailableRaster()
        for rlyr in rasterlist:
            if rlyr['name'] == rastername:
                self.projectHandler.setDhm(rlyr['lyr'])
                # Check spatial reference of newly added raster
                mapCrs = self.canvas.mapSettings().destinationCrs().authid()
                lyrCrs = self.projectHandler.dhm.spatialRef
                if lyrCrs and mapCrs != lyrCrs:
                    txt = (f'Das Raster in der Projektdatei liegt in KBS '
                           f'{lyrCrs} vor, das aktuelle QGIS-Projekt jedoch '
                           f'in {mapCrs}. Bitte passen Sie das QGIS-KBS an.')
                    title = "Falsches Koordinatenbezugssystem (KBS)"
                    QMessageBox.information(self, title, txt)

                rasterFound = True
                break
        if not rasterFound:
            self.projectHandler.setDhm(False)
        
        # If a raster was selected, OSM and Contour Layers can be generated
        self.osmLyrButton.setEnabled(rasterFound)
        self.contourLyrButton.setEnabled(rasterFound)
        self.draw.setEnabled(rasterFound)
    
    def searchForRaster(self, path):
        """ Checks if a raster from a saved project is present in the table
        of content or exists at the given location (path).
        """
        availRaster = self.getAvailableRaster()
        rasterLyr = None
        for rlyr in availRaster:
            lyrPath = rlyr['lyr'].dataProvider().dataSourceUri()
            if lyrPath == path:
                # Sets the dhm name in the drop down and triggers self.setRaster()
                self.rasterField.setCurrentText(rlyr['name'])
                rasterLyr = rlyr['lyr']
                break
        if not rasterLyr:
            if os.path.exists(path):
                baseName = QFileInfo(path).baseName()
                rasterLyr = QgsRasterLayer(path, baseName)
                QgsProject.instance().addMapLayer(rasterLyr)
                self.updateRasterList()
                # Sets the dhm name in the drop down and triggers self.setRaster()
                self.rasterField.setCurrentText(baseName)
            else:
                txt = f"Raster {path} nicht vorhanden"
                title = "Fehler beim Laden des Rasters"
                QMessageBox.information(self, title, txt)
        return rasterLyr
    
    def setProjName(self, projname):
        self.projectHandler.setProjectName(projname)
    
    # TODO Unset Focus of field when clicking on something else, doesnt work yet
    # def mousePressEvent(self, event):
    #     focused_widget = QtGui.QApplication.focusWidget()
    #     if isinstance(focused_widget, QtGui.QLineEdit):
    #         focused_widget.clearFocus()
    #     QtGui.QDialog.mousePressEvent(self, event)
    
    def onCoordFieldChange(self, pointType):
        x = self.coordFields[pointType + 'x'].text()
        y = self.coordFields[pointType + 'y'].text()
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
        self.coordFields[pointType + 'x'].setText(formatNum(x))
        self.coordFields[pointType + 'y'].setText(formatNum(y))
        
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
        self.profileWin.doReset = True
        if self.projectHandler.profileIsValid():
            self.drawTool.updateLine(list(self.linePoints.values()))
    
    def updateLineByMapDraw(self, newpoint, pointType):
        [x, y], coordState, hasChanged = self.projectHandler.setPoint(
            pointType, [newpoint.x(), newpoint.y()])
        self.changePoint(pointType, [x, y], coordState)
    
    def changePointSym(self, state, point):
        if point == 'A':
            if state == 'green':
                self.symA.setText(greenIcon)
                self.symTxtA.setText(greenTxt)
            if state == 'yellow':
                self.symA.setText(yellowIcon)
                self.symTxtA.setText(yellowTxt)
            if state == 'red':
                self.symA.setText(redIcon)
                self.symTxtA.setText(redTxt)
        if point == 'E':
            if state == 'green':
                self.symE.setText(greenIcon)
                self.symTxtE.setText(greenTxt)
            if state == 'yellow':
                self.symE.setText(yellowIcon)
                self.symTxtE.setText(yellowTxt)
            if state == 'red':
                self.symE.setText(redIcon)
                self.symTxtE.setText(redTxt)
    
    def onClickOsmButton(self):
        """Add a OpenStreetMap layer."""
        loadOsmLayer(self.homePath)
        self.canvas.refresh()
    
    def onClickContourButton(self):
        """Calcluate contour lines from currently selected dhm and add them to
        as a layer."""
        self.projectHandler.dhm.contour = createContours(self.canvas,
                                                         self.projectHandler.dhm)
        self.canvas.refresh()
    
    def onFinishedLineDraw(self, linecoord):
        self.updateLineByMapDraw(linecoord[0], 'A')
        self.updateLineByMapDraw(linecoord[1], 'E')
        # Stop pressing down button
        self.draw.setChecked(False)
    
    def updateProfileWinContent(self):
        profile = PreviewProfile(self.projectHandler)
        profile.create()
        self.profileWin.setProfile(profile)
        self.profileWin.setPoleData(self.projectHandler.fixedPoles['poles'],
                                    self.projectHandler.noPoleSection)
    
    def onShowProfile(self):
        if not self.profileWin.dataSet:
            self.updateProfileWinContent()
        self.profileWin.exec()
    
    def onLoadProjects(self):
        title = 'Projekt laden'
        fFilter = 'Txt Dateien (*.txt)'
        filename, _ = QFileDialog.getOpenFileName(self, title,
                                                  self.confHandler.getCurrentPath(),
                                                  fFilter)
        if filename:
            success = self.confHandler.loadFromFile(filename)
            if success:
                self.setupContent()
            else:
                QMessageBox.critical(self, 'Fehler beim Laden',
                                'Projektdatei konnte nicht geladen werden.')
        else:
            return False
    
    def onSaveProject(self):
        title = 'Projekt speichern'
        fFilter = 'TXT (*.txt)'
        if not self.confHandler.checkValidState():
            return
        projname = self.projectHandler.getProjectName()
        defaultFilename = f'{projname}.txt'
        filename, _ = QFileDialog.getSaveFileName(self, title,
                        os.path.join(self.confHandler.getCurrentPath(),
                                     defaultFilename), fFilter)
        
        if filename:
            fileExtention = '.txt'
            if filename[-4:] != fileExtention:
                filename += fileExtention
            self.confHandler.saveToFile(filename)
        else:
            return False
    
    def onInfo(self):
        QMessageBox.information(self, "SEILAPLAN Info", infoTxt,
                                QMessageBox.Ok)
    
    def onShowInfoImg(self):
        sender = self.sender().objectName()
        infoType = sender[4:]
        infoTitle = infImg[infoType]
        imgPath = os.path.join(self.homePath, 'img', infoType + '.png')
        self.imgBox.setWindowTitle(infoTitle)
        # Load image
        myPixmap = QPixmap(imgPath)
        self.imgBox.label.setPixmap(myPixmap)
        self.imgBox.setLayout(self.imgBox.container)
        self.imgBox.show()
    
    def goToAdjustmentWindow(self):
        if self.confHandler.checkValidState():
            self.startAlgorithm = False
            self.goToAdjustment = True
            self.close()
        else:
            return False
    
    def apply(self):
        if self.confHandler.checkValidState():
            self.startAlgorithm = True
        else:
            # If project info or parameter are missing or wrong, algorithm
            # can not start
            return False
        self.close()
    
    def cancel(self):
        """ Called when 'Cancel' is pressed."""
        self.close()
    
    def cleanUp(self):
        # Save user settings
        self.confHandler.updateUserSettings()
        # Clean markers and lines from map canvas
        self.drawTool.reset()
    
    def closeEvent(self, QCloseEvent):
        """Last method that is called before main window is closed."""
        # Close additional dialogs
        self.imgBox.close()
        if self.profileWin:
            self.profileWin.close()
        
        if not self.startAlgorithm:
            self.cleanUp()
