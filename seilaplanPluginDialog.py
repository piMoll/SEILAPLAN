# -*- coding: utf-8 -*-
"""
/***************************************************************************
 SeilaplanPluginDialog
                                 A QGIS plugin
 Seilkran-Layoutplaner
                             -------------------
        begin                : 2013
        copyright            : (C) 2015 by ETH Zürich
        email                : pi1402@gmail.com
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
import io
import re
from operator import itemgetter
import unicodedata

# GUI and QGIS libraries
from PyQt4 import QtCore, QtGui
from PyQt4.QtCore import QObject, SIGNAL, QFileInfo
from qgis.core import QGis, QgsRasterLayer, QgsVectorLayer, QgsGeometry, \
    QgsPoint, QgsFeature, QgsMapLayerRegistry
from qgis.gui import QgsRubberBand
import processing

# Further GUI modules for functionality
from gui.guiHelperFunctions import Raster, valueToIdx, QgsStueMarker, \
    strToNum, DialogOutputOptions, generateName, DialogWithImage, formatNum, \
    readFromTxt, castToNumber
from bo.ptmaptool import ProfiletoolMapTool
from bo.createProfile import CreateProfile
# GUI elements
from gui.ui_seilaplanDialog import Ui_Dialog
from gui.profileDialog import ProfileWindow


# UTF-8 coding
try:
    utf8 = QtCore.QString.fromUtf8
except AttributeError:
    utf8 = lambda s: s

# OS dependent line break
nl = unicode(os.linesep)

# Source of icons in GUI
greenIcon = '<html><head/><body><p><img src=":/plugins/SeilaplanPlugin/' \
            'icons/icon_green.png"/></p></body></html>'
yellowIcon = '<html><head/><body><p><img src=":/plugins/SeilaplanPlugin/' \
             'icons/icon_yellow.png"/></p></body></html>'
redIcon = '<html><head/><body><p><img src=":/plugins/SeilaplanPlugin/' \
          'icons/icon_red.png"/></p></body></html>'
# Text next to coord status
greenTxt = ''
yellowTxt = 'zu definieren'
redTxt = 'ausserhalb Raster'

# Titles of info images
infImg = {'Bodenabstand': u'Erklärungen zum Bodenabstand',
          'VerankerungA': u'Erklärungen zur Verankerung am Anfangspunkt',
          'VerankerungE': u'Erklärungen zur Verankerung am Anfangspunkt',
          'Stuetzen': u'Erklärungen zu den Zwischenstützen'}

# TODO: add license and disclaimer
# Info button text
infoTxt = (u"SEILAPLAN - Seilkran-Layoutplaner\n\n"
    u"SEILAPLAN berechnet auf Grund eines digitalen Höhenmodells zwischen "
    u"definierten Anfangs- und Endkoordinaten sowie technischer Parameter das "
    u"optimale Seillinienlayout, d.h. Position und Höhe der Stützen und "
    u"schreibt die wichtigsten Kennwerte dieser Seillinie heraus.\n\n"
    u"Realisierung:\nProfessur für forstliches Ingenieurwesen\n"
    u"ETH Zürich\n8092 Zürich\n\nBeteiligte Personen:\n"
    u"Leo Bont (Konzept, Mechanik)\nPatricia Moll "
    u"(Implementation in Python / QGIS)")



class SeilaplanPluginDialog(QtGui.QDialog, Ui_Dialog):
    def __init__(self, interface, helper):
        QtGui.QDialog.__init__(self, interface.mainWindow())
        # import pydevd
        # pydevd.settrace('localhost', port=53100,
        #             stdoutToServer=True, stderrToServer=True)

        # QGIS interface
        self.iface = interface
        # QGIS map canvas
        self.canvas = self.iface.mapCanvas()
        self.action = QtGui.QAction(
            QtGui.QIcon(":/plugins/SeilaplanPlugin/icons/icon_app.png"),
            u"SEILAPLAN", self.iface.mainWindow())
        self.action.setWhatsThis("SEILAPLAN")
        # Separate class to start algorithm
        self.threadingControl = helper
        # Interaction with canvas, is used to draw onto map canvas
        self.tool = ProfiletoolMapTool(self.canvas, self.action)
        self.savedTool = self.canvas.mapTool()
        # Setup GUI of SEILAPLAN (import from ui_seilaplanDialog.py)
        self.setupUi(self)

        # Define some important paths and locations
        self.userHomePath = os.path.join(os.path.expanduser('~'))
        self.homePath = os.path.dirname(__file__)
        # Config file 'params.txt' stores parameters of cable types
        self.paramPath = os.path.join(self.homePath, 'config', 'params.txt')
        # Config file 'commonPaths.txt' stores previous output folders
        self.commonPathsFile = os.path.join(self.homePath, 'config',
                                            'commonPaths.txt')
        self.commonPaths, outputOpt = self.createCommonPathList()
        # Get the preferences for output options
        self.outputOpt = {'outputPath': self.commonPaths[-1],   # last used output path
                          'report': outputOpt[0],
                          'plot': outputOpt[1],
                          'geodata': outputOpt[2],
                          'coords': outputOpt[3]}

        # Initialize cable parameters
        self.param = None               # All parameters of a certain cable type
        self.paramOrder = None          # Order of parameters
        self.header = None
        self.paramSet = None            # Name of cable type
        self.settingFields = {}         # Dictionary of all GUI setting fields

        # GUI fields and variables handling coordinate information
        self.coordFields = {}
        self.pointA = [-100, -100]
        self.pointE = [-100, -100]
        self.azimut = 0
        self.coordStateA = 'yellow'
        self.coordStateE = 'yellow'
        self.groupFields()

        # Dictionary containing information about selected elevation model
        self.dhm = {}
        # User defined fixed intermediate support
        self.fixStue = {}

        # Dialog with explanatory images
        self.imgBox = DialogWithImage(self.iface)

        # Variables handling additional GIS-Layers
        self.osmLayer = None            # OpenStreetMap Layer (TileMapService)
        self.osmLyrOn = False
        self.osmLyrButton.setEnabled(False)
        self.contourLyrButton.setEnabled(False)     # Contour Layer
        self.contourLyr = None
        self.contourLyrOn = False

        # Connect signals and slots
        self.connectFields()
        self.buttonShowProf.setEnabled(False)

        # Initialize variables handling drawing on map
        self.draw.setEnabled(False)
        self.polygon = False
        # Drawn line
        self.rubberband = QgsRubberBand(self.canvas, self.polygon)
        self.rubberband.setWidth(3)
        self.rubberband.setColor(QtGui.QColor(231, 28, 35))
        self.markers = []           # Point markers on each end of the line
        self.pointsToDraw = []
        self.dblclktemp = None
        self.drawnLine = None
        self.line = False
        self.lineLyr = None
        self.vl = None
        self.lineID = None

        # Dialog window with height profile
        self.profileWin = None
        # Dialog windows with output options
        self.optionWin = DialogOutputOptions(self.iface, self)
        self.optionWin.fillInDropDown(self.commonPaths)


    def connectFields(self):
        """Connect GUI fields.
        """
        QObject.connect(self.buttonOkCancel,
            SIGNAL(utf8("rejected()")), self.Reject)
        QObject.connect(self.buttonOkCancel,
            SIGNAL(utf8("accepted()")), self.apply)
        QObject.connect(self.buttonOpenPr,
            SIGNAL(utf8("clicked()")), self.onLoadProjects)
        QObject.connect(self.buttonSavePr,
            SIGNAL(utf8("clicked()")), self.onSaveProjects)
        QObject.connect(self.rasterField,
            SIGNAL(utf8("currentIndexChanged(const QString&)")), self.setRaster)
        QObject.connect(self.buttonRefreshRa,
            SIGNAL(utf8("clicked()")), self.updateRasterList)
        QObject.connect(self.buttonInfo,
            SIGNAL(utf8("clicked()")), self.onInfo)
        QObject.connect(self.buttonOptionen,
            SIGNAL(utf8("clicked()")), self.onShowOutputOpt)
        # Info buttons
        QObject.connect(self.infoBodenabstand,
            SIGNAL(utf8("clicked()")), self.onShowInfoImg)
        QObject.connect(self.infoVerankerungA,
            SIGNAL(utf8("clicked()")), self.onShowInfoImg)
        QObject.connect(self.infoVerankerungE,
            SIGNAL(utf8("clicked()")), self.onShowInfoImg)
        QObject.connect(self.infoStuetzen,
            SIGNAL(utf8("clicked()")), self.onShowInfoImg)
        # OSM map and contour buttons
        QObject.connect(self.osmLyrButton,
            SIGNAL(utf8("clicked()")), self.onClickOsmButton)
        QObject.connect(self.contourLyrButton,
            SIGNAL(utf8("clicked()")), self.onClickContourButton)

        QObject.connect(self.fieldProjName,
            SIGNAL(utf8("textChanged (const QString&)")), self.setProjName)
        QObject.connect(self.draw,
            SIGNAL(utf8("clicked()")), self.drawLine)
        QObject.connect(self.buttonShowProf,
            SIGNAL(utf8("clicked()")), self.onShowProfile)
        QObject.connect(self.fieldParamSet,
            SIGNAL(utf8("currentIndexChanged(const QString&)")), self.setParamSet)
        # Action for changed Coordinates (when coordinate is changed by hand)
        QObject.connect(self.coordAx,
            SIGNAL(utf8("editingFinished()")), self.changedPointAField)
        QObject.connect(self.coordAy,
            SIGNAL(utf8("editingFinished()")), self.changedPointAField)
        QObject.connect(self.coordEx,
            SIGNAL(utf8("editingFinished()")), self.changedPointEField)
        QObject.connect(self.coordEy,
            SIGNAL(utf8("editingFinished()")), self.changedPointEField)


    def groupFields(self):
        """Combine all GUI fields in dictionary for faster access.
        """
        self.settingFields = {'Q': self.fieldQ,
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
                              'HM_nat': self.fieldHMnat}
        self.coordFields = {'Ax': self.coordAx,
                            'Ay': self.coordAy,
                            'Ex': self.coordEx,
                            'Ey': self.coordEy}

    def loadInitialVals(self):
        """Some initial values are filled into the GUI fields.
        """
        # Load existing parameter sets of cable types
        [self.param, self.header] = readFromTxt(self.paramPath)
        avaSets = []
        for item in self.header:
            if item[:4] == 'set_':
                avaSets.append(item.replace('set_', '', 1))
        self.fieldParamSet.blockSignals(True)
        for i in range(self.fieldParamSet.count()):
            self.fieldParamSet.removeItem(i)
        self.fieldParamSet.addItems(avaSets)
        self.fieldParamSet.setCurrentIndex(-1)
        self.fieldParamSet.blockSignals(False)
        # Generate project name
        self.fieldProjName.setText(generateName())
        self.enableToolTips()

    def enableToolTips(self):
        for [name, field] in self.settingFields.items():
            field.setToolTip(self.param[name]['tooltip'])

    def setParamSet(self, setName):
        self.paramSet = 'set_' + setName
        # Fill in values of parameter set
        self.fillInValues(self.param, self.paramSet)

    def fillInValues(self, data, datafield):
        """Fills in GUI fields with parameters of a certain cable type.
        """
        for name, field in self.settingFields.items():
            val = data[name][datafield]
            if self.param[name]['ftype'] == 'drop_field':
                field.setCurrentIndex(valueToIdx(val))
                continue
            # Float values without decimal places are converted: 10.0 --> 10
            if val[-2:] == '.0':
                val = val[:-2]
            if val == '-':
                val = ''
            field.setText(val)

    def updateRasterList(self):
        rasterlist = self.getAvailableRaster()
        self.addRastersToGui(rasterlist)

    def getAvailableRaster(self):
        """Go trough table of content and collect all raster layers.
        """
        legend = self.iface.legendInterface()
        availLayers = legend.layers()
        rColl = []

        for lyr in availLayers:
            if legend.isLayerVisible(lyr):
                lyrType = lyr.type()
                lyrName = unicodedata.normalize('NFKD',
                                 unicode(lyr.name())).encode('ascii', 'ignore')
                if lyrType == 1:        # = raster
                    r = Raster(lyr.id(), lyrName, lyr)
                    rColl.append(r)
        return rColl

    def addRastersToGui(self, rasterList):
        """Put list of raster layers into drop down menu of self.rasterField.
        If raster name contains some kind of "DHM", select it.
        """
        for i in range(self.rasterField.count()):
            self.rasterField.removeItem(i)
        idx = None
        searchStr = ['dhm', 'Dhm', 'DHM', 'dtm', 'DTM', 'Dtm']
        for i, rLyr in enumerate(rasterList):
            self.rasterField.addItem(rLyr.name)
            if not idx and sum([item in rLyr.name for item in searchStr]) > 0:
                idx = i
        if idx:
            self.rasterField.setCurrentIndex(idx)
        if not self.rasterField.currentText() == '':
            self.setRaster(self.rasterField.currentText())
            self.draw.setEnabled(True)

    def setRaster(self, rastername):
        """Get the current selected Raster in self.rasterField and collect
        useful information about it.
        """
        rasterlist = self.getAvailableRaster()
        for rlyr in rasterlist:
            if rlyr.name == rastername:
                path = rlyr.grid.dataProvider().dataSourceUri()
                spatialRef = rlyr.grid.crs().authid()
                ext = rlyr.grid.extent()
                self.dhm['name'] = rastername
                self.dhm['path'] = path
                self.dhm['layer'] = rlyr.grid
                self.dhm['ncols'] = rlyr.grid.width()
                self.dhm['nrows'] = rlyr.grid.height()
                self.dhm['cellsize'] = float(rlyr.grid.rasterUnitsPerPixelX())
                self.dhm['spatialRef'] = spatialRef
                self.dhm['extent'] = [ext.xMinimum(),
                                      ext.yMaximum(),
                                      ext.xMaximum(),
                                      ext.yMinimum()]
                # Contour Layer is calculated on demand
                self.dhm['contour'] = None
        # If a raster was selected, OSM and Contour Layers can be generated
        self.osmLyrButton.setEnabled(True)
        self.contourLyrButton.setEnabled(True)

    def searchForRaster(self, path):
        """ Checks if a raster from a saved project is present in the table
        of content or exists at the given location (path).
        """
        rasterFound = False
        availRaster = self.getAvailableRaster()
        for rlyr in availRaster:
            lyrPath = rlyr.grid.dataProvider().dataSourceUri()
            if lyrPath == path:
                self.setRaster(rlyr.name)
                rasterFound = True
                self.setCorrectRasterInField(rlyr.name)
                break
        if not rasterFound:
            if os.path.exists(path):
                baseName = QtCore.QFileInfo(path).baseName()
                rlayer = QgsRasterLayer(path, baseName)
                QgsMapLayerRegistry.instance().addMapLayer(rlayer)
                self.updateRasterList()
                self.setCorrectRasterInField(baseName)
                self.setRaster(baseName)
                self.draw.setEnabled(True)
            else:
                txt = u"Raster mit dem Pfad {} ist " \
                      u"nicht vorhanden".format(path)
                title = u"Fehler beim Laden des Rasters"
                QtGui.QMessageBox.information(self, title, txt)

    def setCorrectRasterInField(self, rasterName):
        for idx in range(self.rasterField.count()):
            if rasterName == self.rasterField.itemText(idx):
                self.rasterField.setCurrentIndex(idx)
                self.draw.setEnabled(True)
                break

    def createCommonPathList(self):
        """Gets the output options and earlier used output paths from the file
        'commonPaths.txt' an returns them.
        """
        commonPaths = []
        homePathPresent = False
        # Standard values for when the file is defect or no file is present
        #   [report, plot, shape-files, coordinate tables]
        outputOpt = [1, 1, 0, 0]
        # Output is  saved in home directory when output path is not defined
        userPath = os.path.join(self.userHomePath, 'Seilaplan')

        if os.path.exists(self.commonPathsFile):
            with io.open(self.commonPathsFile, encoding='utf-8') as f:
                lines = f.read().splitlines()
                # First line contains output options
                try:
                    outputOpt = lines[0].split()
                    outputOpt = [int(x) for x in outputOpt]
                except IndexError:    # if file/fist line is empty
                    pass
                except ValueError:    # if there are letters instead of numbers
                    pass
                # Go through paths from most recent to oldest
                for path in lines[1:]:
                    try:
                        if path == '': continue
                        if os.path.exists(path):   # If path still exists
                            if path == userPath:
                                homePathPresent = True
                            commonPaths.append(path)
                    except:
                        continue

        if not homePathPresent:  # If current user path is not present
            if not os.path.exists(userPath):
                os.mkdir(userPath)
            commonPaths.append(userPath)
        # Maximum length of drop down menu
        if len(commonPaths) > 12:
            del commonPaths[0]      # Delete oldest entry
        return commonPaths, outputOpt

    def updateCommonPathFile(self):
        """File 'commonPaths.txt' gets updated.
        """
        if os.path.exists(self.commonPathsFile):
            os.remove(self.commonPathsFile)
        with io.open(self.commonPathsFile, encoding='utf-8', mode='w+') as f:
            f.writelines(u"{} {} {} {} {}".format(self.outputOpt['report'],
                    self.outputOpt['plot'], self.outputOpt['geodata'],
                    self.outputOpt['coords'], nl))
            for path in self.commonPaths:
                f.writelines(path.encode('utf-8') + nl)

    def setProjName(self, projname):
        self.projName = projname

    # TODO Unset Focus of field when clicking on something else, doesnt work yet
    # def mousePressEvent(self, event):
    #     focused_widget = QtGui.QApplication.focusWidget()
    #     if isinstance(focused_widget, QtGui.QLineEdit):
    #         focused_widget.clearFocus()
    #     QtGui.QDialog.mousePressEvent(self, event)


    ###########################################################################
    ### Methods for drawing line on map canvas
    ###########################################################################

    def drawLine(self):
        self.dblclktemp = None
        self.clearMap()
        self.rubberband.reset(self.polygon)
        self.cleanDigi()
        self.activateDigiTool()
        self.canvas.setMapTool(self.tool)

    def clearMap(self):
        if self.profileWin:
            self.profileWin.deactivateMapMarker()
            self.profileWin.removeLines()
            del self.profileWin
            self.profileWin = None
        self.removeStueMarker()

    def createDigiFeature(self, pnts):
        line = QgsGeometry.fromPolyline(pnts)
        qgFeat = QgsFeature()
        qgFeat.setGeometry(line)
        return qgFeat

    def lineFinished(self):
        lastPoint = self.pointsToDraw[-1]
        if len(self.pointsToDraw) < 2:
            self.removeStueMarker()
            self.cleanDigi()
            self.pointsToDraw = []
            self.dblclktemp = lastPoint
            self.drawnLine = None
            self.buttonShowProf.setEnabled(False)
        self.drawnLine = self.createDigiFeature(self.pointsToDraw)
        self.changeCoordA(self.pointsToDraw[0])
        self.changeCoordE(self.pointsToDraw[1])
        self.createProfile()
        self.cleanDigi()
        self.dblclktemp = lastPoint

    def lineFromFields(self):
        self.dblclktemp = None
        self.rubberband.reset(self.polygon)
        lastPoint = self.pointsToDraw[-1]
        if self.coordStateA == self.coordStateE == 'green':
            self.buttonShowProf.setEnabled(True)
        else:
            self.buttonShowProf.setEnabled(False)
        self.pointsToDraw = []
        self.dblclktemp = lastPoint

    def drawStueMarker(self, point):
        marker = QgsStueMarker(self.canvas)
        marker.setCenter(point)
        self.markers.append(marker)
        self.canvas.refresh()

    def removeStueMarker(self, position=None):
        if position:
            marker = self.markers[position]
            self.canvas.scene().removeItem(marker)
            self.markers.pop(position)
        else:
            for marker in self.markers:
                self.canvas.scene().removeItem(marker)
            self.markers = []
        self.canvas.refresh()

    def cleanDigi(self):
        self.pointsToDraw = []
        self.canvas.unsetMapTool(self.tool)     # Signal DEACTIVATE is sent
        self.canvas.setMapTool(self.savedTool)

    def activateDigiTool(self):
        QObject.connect(self.tool, SIGNAL("moved"), self.moved)
        QObject.connect(self.tool, SIGNAL("rightClicked"), self.rightClicked)
        QObject.connect(self.tool, SIGNAL("leftClicked"), self.leftClicked)
        QObject.connect(self.tool, SIGNAL("doubleClicked"), self.doubleClicked)
        QObject.connect(self.tool, SIGNAL("deactivate"), self.deactivateDigiTool)

    def deactivateDigiTool(self):
        QObject.disconnect(self.tool, SIGNAL("moved"), self.moved)
        QObject.disconnect(self.tool, SIGNAL("leftClicked"), self.leftClicked)
        QObject.disconnect(self.tool, SIGNAL("rightClicked"), self.rightClicked)
        QObject.disconnect(self.tool, SIGNAL("doubleClicked"), self.doubleClicked)

    def moved(self, position):
        if len(self.pointsToDraw) > 0:
            mapPos = self.canvas.getCoordinateTransform().\
                toMapCoordinates(position["x"], position["y"])
            self.rubberband.reset(self.polygon)
            newPnt = QgsPoint(mapPos.x(), mapPos.y())
            if QGis.QGIS_VERSION_INT < 10900:
                for i in range(0, len(self.pointsToDraw)):
                    self.rubberband.addPoint(self.pointsToDraw[i])
                self.rubberband.addPoint(newPnt)
            else:
                pnts = self.pointsToDraw + [newPnt]
                self.rubberband.setToGeometry(QgsGeometry.fromPolyline(pnts),
                                              None)

    def rightClicked(self, position):
        # Reroute signal, it doesn't matter which mouse button is clicked
        self.leftClicked(position)

    def leftClicked(self, position):
        mapPos = self.canvas.getCoordinateTransform().\
            toMapCoordinates(position["x"], position["y"])
        newPoint = QgsPoint(mapPos.x(), mapPos.y())
        if newPoint == self.dblclktemp:
            self.dblclktemp = None
            return
        else:
            # Mark point with marker symbol
            self.drawStueMarker(newPoint)
            if len(self.pointsToDraw) == 0:
                self.rubberband.reset(self.polygon)
                self.pointsToDraw.append(newPoint)
            else:
                self.pointsToDraw.append(newPoint)
                self.lineFinished()

    def doubleClicked(self, position):
        pass

    ###########################################################################
    ### Methods handling start and end point coordinates
    ###########################################################################

    def changedPointAField(self):
        x = strToNum(self.coordFields['Ax'].text())
        y = strToNum(self.coordFields['Ay'].text())
        # Only do something if coordinates have changed
        if not (x == self.pointA[0] and y == self.pointA[1]):
            self.changeCoordA([x, y])
            self.updateLineFromGui()

    def changedPointEField(self):
        x = strToNum(self.coordFields['Ex'].text())
        y = strToNum(self.coordFields['Ey'].text())
        # Only do something if coordinates have changed
        if not (x == self.pointE[0] and y == self.pointE[1]):
            self.changeCoordE([x, y])
            self.updateLineFromGui()

    def changeCoordA(self, newpoint):
        # Delete fixed intermediate support from previous cable line
        self.fixStue = {}
        # Check if point is inside elevation model
        state = self.checkPoint(newpoint)
        self.coordStateA = state
        # Update coordinate state icon
        self.changePointSym(state, 'A')
        if state != 'yellow':
            # Update coordinate field
            self.coordFields['Ax'].setText(formatNum(newpoint[0]))
            self.coordFields['Ay'].setText(formatNum(newpoint[1]))
            self.pointA = newpoint
            self.setAzimut()
        # Update profile and length fields
        self.checkProfileStatus()
        self.checkLenghtStatus()

    def changeCoordE(self, newpoint):
        # Delete fixed intermediate support from previous cable line
        self.fixStue = {}
        # Check if point is inside elevation model
        state = self.checkPoint(newpoint)
        self.coordStateE = state
        # Update coordinate state icon
        self.changePointSym(state, 'E')
        if state != 'yellow':
            # Update coordinate field
            self.coordFields['Ex'].setText(formatNum(newpoint[0]))
            self.coordFields['Ey'].setText(formatNum(newpoint[1]))
            self.pointE = newpoint
            self.setAzimut()
        # Update profile and length fields
        self.checkProfileStatus()
        self.checkLenghtStatus()

    def setAzimut(self):
        dx = (self.pointE[0] - self.pointA[0]) * 1.0
        dy = (self.pointE[1] - self.pointA[1]) * 1.0
        import math
        if dx == 0:
            dx = 0.0001
        azimut = math.atan(dy/dx)
        if dx > 0:
            azimut += 2 * math.pi
        else:
            azimut += math.pi
        self.azimut = azimut

    def checkLenghtStatus(self):
        if self.coordStateA != 'yellow' and self.coordStateE != 'yellow':
            self.updateLenghtField(self.pointA, self.pointE)
        else:
            self.laenge.setText('')

    def checkProfileStatus(self):
        if self.coordStateA == self.coordStateE == 'green':
            self.buttonShowProf.setEnabled(True)
        else:
            self.buttonShowProf.setEnabled(False)

    def updateLenghtField(self, pointA, pointE):
        [Ax, Ay] = pointA
        [Ex, Ey] = pointE
        l = ((Ex - Ax)**2 + (Ey - Ay)**2)**0.5
        self.laenge.setText(formatNum(l))

    def updateLineFromGui(self):
        self.rubberband.reset(self.polygon)
        if self.coordStateA != 'yellow' and self.coordStateE != 'yellow':
            points = [QgsPoint(self.pointA[0], self.pointA[1]),
                      QgsPoint(self.pointE[0], self.pointE[1])]
            self.rubberband.setToGeometry(QgsGeometry.fromPolyline(points), None)
            self.drawnLine = self.createDigiFeature(points)
            self.clearMap()
            self.drawStueMarker(points[0])
            self.drawStueMarker(points[1])
            self.createProfile()
        else:
            self.clearMap()

    def checkPoint(self, point):
        state = 'yellow'
        if self.dhm != {}:
            extent = self.dhm['extent']
            [extLx, extHy, extHx, extLy] = extent
            try:
                [x, y] = point
                if extLx <= float(x) <= extHx and extLy <= float(y) <= extHy:
                    state = 'green'
                else:
                    state = 'red'
            except ValueError:
                state = 'yellow'
        return state

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

    def removeCoords(self):
        for field in self.coordFields.values():
            field.setText('')

    def transform2MapCoords(self, dist):
        import math
        x = self.pointA[0] + dist * math.cos(self.azimut)
        y = self.pointA[1] + dist * math.sin(self.azimut)
        return [x, y]


    ###########################################################################
    ### Methods for adding additional layer
    ###########################################################################

    def onClickOsmButton(self):
        """ Load OpenStreetMap Layer to canvas.
        """
        self.osmLyrOn = False
        # Check if there is already an OSM layer
        legend = self.iface.legendInterface()
        availLayers = legend.layers()
        for lyr in availLayers:
            if lyr.name() == 'OSM_Karte':
                self.osmLayer = lyr
                self.osmLyrOn = True
                break

        if self.osmLyrOn:
            # Remove OSM layer
            QgsMapLayerRegistry.instance().removeMapLayer(self.osmLayer.id())
            self.osmLyrOn = False
        else:
            # Add OSM layer
            xmlPath = os.path.join(self.homePath, 'config', 'OSM_Karte.xml')
            baseName = QFileInfo(xmlPath).baseName()
            self.osmLayer = QgsRasterLayer(xmlPath, baseName)
            QgsMapLayerRegistry.instance().addMapLayer(self.osmLayer)
            self.osmLyrOn = True

    def onClickContourButton(self):
        contourLyr = self.dhm['contour']
        if contourLyr:
            QgsMapLayerRegistry.instance().removeMapLayer(contourLyr.id())
        else:
            algOutput = processing.runalg("gdalogr:contour", self.dhm['layer'],
                                       100.0, "Hoehe", None, None)
            contourPath = algOutput['OUTPUT_VECTOR']
            contourName = u"Hoehenlinien_" + self.dhm['name']
            contour = QgsVectorLayer(contourPath, contourName, "ogr")
            QgsMapLayerRegistry.instance().addMapLayer(contour)
            self.dhm['contour'] = contour
        # More useful stuff
        # layer.crs().authid() == u'EPSG:21781'
        # layer.featureCount()

    ###########################################################################
    ### Methods for loading and saving projects
    ###########################################################################

    def createProfile(self):
        createProf = CreateProfile(self.iface, self.drawnLine, self.dhm['layer'])
        profile = createProf.create()
        self.profileWin = ProfileWindow(self, self.iface, profile[0])

    def onShowProfile(self):
        if not self.profileWin:
            self.createProfile()
        self.profileWin.show()

    def onLoadProjects(self):
        title = 'Projekt laden'
        fFilter = 'Txt Dateien (*.txt)'
        filename = QtGui.QFileDialog.getOpenFileName(self, title,
                                        self.outputOpt['outputPath'], fFilter)
        if filename:
            self.loadProj(filename)
        else:
            return False

    def loadProj(self, path):
        # Read project data from file
        projHeader, projData  = self.openProjFromTxt(path)
        # Set project data
        self.setProjName(projHeader['Projektname'])
        self.searchForRaster(projHeader['Hoehenmodell'])
        # Update coordinates
        pointA = projHeader['Anfangspunkt'].split('/')
        pointE = projHeader['Endpunkt'].split('/')
        self.changeCoordA([strToNum(pointA[0]), strToNum(pointA[1])])
        self.changeCoordE([strToNum(pointE[0]), strToNum(pointE[1])])
        self.updateLineFromGui()
        # Extract and update data of fixed intermediate support
        fixStueString = projHeader['Fixe Stuetzen'].split('/')[:-1]
        for stue in fixStueString:
            [key, values] = stue.split(':')
            [posX, posY, posH] = [string.strip() for string in values.split(',')]
            self.fixStue[int(key)] = [posX, posY, posH]
        self.fieldProjName.setText(self.projName)
        # Fill in parameter values
        self.fillInValues(projData, 'Wert')
        self.createProfile()

    def onSaveProjects(self):
        title = 'Projekt speichern'
        fFilter = 'TXT (*.txt)'
        dialog = QtGui.QFileDialog(self, title, self.outputOpt['outputPath'])
        dialog.setAcceptMode(QtGui.QFileDialog.AcceptSave)
        dialog.setNameFilter(fFilter)
        dialog.setDefaultSuffix('txt')
        if self.projName != '':
            defaultFilename = u'{}.txt'.format(self.projName)
            dialog.selectFile(defaultFilename)
        if dialog.exec_():
            filename = unicode(dialog.selectedFiles()[0])
            fileExtention = u'.txt'
            if filename[-4:] != fileExtention:
                filename += fileExtention
            self.saveProjToTxt(filename)
        else:
            return False

    def saveProjToTxt(self, path):
        # Extract field data
        noError, toolData, projInfo = self.getGuiContent()
        if not noError:
            # If there where invalid values
            return False
        if not self.paramOrder:
            # Get the order of the parameter values for the output
            self.getParamOrder()
        # Extract project data (project name, elevation model...)
        _, fileheader = self.getProjectInfo()
        if os.path.exists(path):
            os.remove(path)
        with io.open(path, encoding='utf-8', mode='w+') as f:
            # Write header
            f.writelines(fileheader)
            # Write parameter values
            for name, sortNr in self.paramOrder:
                try:
                    d = toolData[name][0]
                except KeyError:
                    continue
                p = self.param[name]
                name = name.decode('utf-8')
                line = u'{0: <17}{1: <12}{2: <45}{3: <9}{4}'.format(name, d,
                                                 p['label'], p['unit'], nl)
                f.writelines(line)

    def openProjFromTxt(self, path):
        """Opens a saved project and saves it to a dictionary.
        """
        fileData = {}
        projInfo = {}
        if os.path.exists(path):
            with io.open(path, encoding='utf-8') as f:
                lines = f.read().splitlines()
                for hLine in lines[:5]:
                    # Dictionary keys cant be in unicode
                    name = hLine[:17].rstrip().encode('ascii')
                    projInfo[name] = hLine[17:]
                for line in lines[10:]:
                    if line == u'': break
                    line = re.split(r'\s{2,}', line)
                    if line[1] == u'-':
                        line[1] = u''
                    key = line[0].encode('ascii')
                    fileData[key] = {'Wert': line[1]}
            return projInfo, fileData
        else:
            return False, False

    def onInfo(self):
        QtGui.QMessageBox.information(self, "SEILAPLAN Info", infoTxt,
                                      QtGui.QMessageBox.Ok)

    def getParamOrder(self):
        """Get order of parameters to layout them correctly for the output
        report.
        """
        orderList = []
        for name, d in self.param.items():
            orderList.append([name, int(d['sort'])])
        self.paramOrder = sorted(orderList, key=itemgetter(1))

    def onShowInfoImg(self):
        sender = self.sender().objectName()
        infoType = sender[4:]
        infoTitle = infImg[infoType.encode('ascii')]
        imgPath = os.path.join(self.homePath, 'img', infoType + '.png')
        self.imgBox.setWindowTitle(infoTitle)
        # Load image
        myPixmap = QtGui.QPixmap(imgPath)
        self.imgBox.label.setPixmap(myPixmap)
        self.imgBox.setLayout(self.imgBox.container)
        self.imgBox.show()

    def onShowOutputOpt(self):
        self.optionWin.show()

    ###########################################################################
    ### Methods for extracting and checking GUI field values
    ###########################################################################

    def getGuiContent(self):
        try:
            projInfo, projHeader = self.getProjectInfo()
        except:
            return False, False, False
        projInfo['header'] = projHeader
        fieldData = self.getFieldValues()

        toolData = {}
        errTxt = []
        finalErrorState = True
        for name, d in self.param.items():
            if d['ftype'] ==  'no_field':
                val = d['std_val']
            else:
                val = fieldData[name]
            # Check value type
            cval, errState  = castToNumber(val, d['dtype'])
            if errState:
                errTxt.append(u"-->Der Wert '{}' im Feld '{}' ist ungültig. "
                              u"Bitte geben Sie eine korrekte "
                              u"Zahl ein.".format(val, unicode(d['label'])))
                finalErrorState = False
                continue
            # Check value range
            if d['ftype'] not in ['drop_field', 'no_field']:
                result, [rMin, rMax] = self.checkValues(cval, d['dtype'],
                                                        d['min'],d['max'])
                # Additional check for special fields
                ankerError = False
                if name == 'd_Anker_A':
                    if int(fieldData['HM_Anfang']) == 0:
                        ankerError = True
                if name == 'd_Anker_E':
                    if int(fieldData['HM_Ende_max']) == 0:
                        ankerError = True
                if ankerError:
                    errTxt.append(u"--> Der Wert '{}' im Feld '{}' ist "
                                  u"ungültig. Anker können nur definiert "
                                  u"werden, wenn die entsprechende Stütze "
                                  u"höher als 0 Meter ist.".format(cval,
                                                        unicode(d['label'])))
                    finalErrorState = False
                if result is False:
                    errTxt.append(u"--> Der Wert '{}' im Feld '{}' ist "
                                  u"ungültig. Bitte wählen Sie einen Wert "
                                  u"zwischen {} und {} {}.".format(cval,
                                   unicode(d['label']), rMin, rMax, d['unit']))
                    finalErrorState = False
                    continue
            # If there was no error value is saved to dictionary
            toolData[name] = [cval, d['label'], d['unit'], d['sort']]

        # Show dialog window with error messages
        if finalErrorState is False:
            errorMsg = u"Es wurden folgende Fehler gefunden:" + nl
            errorMsg += nl.join(errTxt)
            QtGui.QMessageBox.information(self, 'Fehler', errorMsg,
                                          QtGui.QMessageBox.Ok)
            return finalErrorState, {}, {}

        return finalErrorState, toolData, projInfo

    def getFieldValues(self):
        """Read out values from GUI fields.
        """
        fieldData = {}

        for name, field in self.settingFields.items():
            d = self.param[name]
            if d['ftype'] == 'drop_field':
                val = field.currentText()
            else:
                val = field.text()
            if val == '':
                val = '-'
            fieldData[name] = unicode(val)
        return fieldData

    def checkValues(self, val, dtype, rangeMin, rangeMax):
        """Checks field data for correct range.
        """
        rangeSet = []
        for rangeItem in [rangeMin, rangeMax]:
            try:
                # If range is a variable name
                if any(c.isalpha() for c in rangeItem):
                    # Read out value of variable name
                    rangeSet.append(float(self.settingFields[rangeItem].text()))
                else:
                    if dtype == 'float':
                        rangeSet.append(float(rangeItem))
                    else:   # dtype = int
                        rangeSet.append(int(rangeItem))
            except ValueError:
                return False, [None, None]
        # Check range
        if rangeSet[0] <= val <= rangeSet[1]:
            return True, rangeSet
        else:
            return False, rangeSet

    def getProjectInfo(self):
        Ax = strToNum(self.coordAx.text())
        Ay = strToNum(self.coordAy.text())
        Ex = strToNum(self.coordEx.text())
        Ey = strToNum(self.coordEy.text())
        noStue = []
        if self.profileWin:
            noStue = self.profileWin.sc.getNoStue()
        projInfo = {'Projektname': self.projName,
                    'Hoehenmodell': self.dhm,
                    'Anfangspunkt': [Ax, Ay],
                    'Endpunkt': [Ex, Ey],
                    'Laenge': self.laenge.text(),
                    'fixeStuetzen': self.fixStue,
                    'keineStuetzen': noStue}
        # Layout project data
        projHeader = ''
        coord = []
        for i in [Ax, Ay, Ex, Ey]:
            val = formatNum(i)
            coord.append(val)

        info = [[u'Projektname', projInfo['Projektname']],
                [u'Hoehenmodell', '{}'. format(self.dhm['path'])],
                [u'Anfangspunkt', '{0: >7} / {1: >7}'.format(*tuple(coord[:2]))],
                [u'Endpunkt', '{0: >7} / {1: >7}'.format(*tuple(coord[2:]))]]
                # TODO: save cable line sections that shouldn't contain
                # TODO:     intermediate support
        fixStueString = u''
        for key, values in self.fixStue.iteritems():
                fixStueString += '{0:0>2}: {1: >7}, {2: >7}, ' \
                                 '{3: >4}  /  '.format(key, *tuple(values))
        info.append([u'Fixe Stuetzen', fixStueString])

        for title, txt in info:
            line = u'{0: <17}{1}'.format(title, unicode(txt))
            projHeader += line + nl
        paramHeader = u'{5}{5}{0}{5}{1: <17}{2: <12}{3: <45}{4: <9}' \
                      u'{5:-<84}{5}'.format(u'Parameter:', u'Name', u'Wert',
                                            u'Label', u'Einheit', nl)
        projHeader += paramHeader
        return projInfo, projHeader

    def layoutToolParams(self, fieldData):
        """ """
        if not self.paramOrder:
            self.getParamOrder()
        txt = []
        for name, sortNr in self.paramOrder:
            try:
                value = str(fieldData[name][0])
            except KeyError:
                continue
            p = self.param[name]
            # Shorten whole-numbered floats
            if value[-2:] == '.0':
                value = value[:-2]
            # Combine values and units
            if p['unit']:
                value += " {}".format(p['unit'])
            line = [p['label'], value]
            txt.append(line)
        return txt

    def getStueInfo(self, toolData):
        toolData['HM_fix_d'] = []
        toolData['HM_fix_h'] = []
        toolData['noStue'] = []
        if self.fixStue:
            for [pointX, _, pointH] in self.fixStue.itervalues():
                toolData['HM_fix_d'].append(int(pointX))
                toolData['HM_fix_h'].append(int(pointH))
        if self.profileWin:
            toolData['noStue'] = self.profileWin.sc.getNoStue()
        return toolData


    ###########################################################################
    ### Methods for OK and Cancel Button
    ###########################################################################

    def apply(self):
        # Extract values from GUI fields
        noError, toolData, projInfo = self.getGuiContent()
        if noError:
            self.threadingControl.setState(True)
        else:
            # If there was an error extracting the values return to GUI
            return False

        # Project data gets layout for report generation
        projInfo['Params'] = self.layoutToolParams(toolData)
        projInfo['outputOpt'] = self.outputOpt
        # Project data is saved to reload it later
        projInfo['projFile'] = os.path.join(projInfo['outputOpt']['outputPath'],
                                            self.projName + '_Projekt.txt')
        self.saveProjToTxt(projInfo['projFile'])
        # Save fixed intermediate supports
        toolData = self.getStueInfo(toolData)
        # All user data is handed over to class that handles calculation
        self.threadingControl.setValue(toolData, projInfo)
        self.close()

    def cleanUp(self):
        self.removeCoords()
        # Clean markers and lines from map canvas
        self.clearMap()
        self.rubberband.reset(self.polygon)
        self.drawnLine = None
        self.cleanDigi()
        # Close additional dialogs
        self.imgBox.close()
        if self.profileWin:
            self.profileWin.close()
        self.updateCommonPathFile()
        self.optionWin.close()

    def Reject(self):
        self.close()

    def closeEvent(self, QCloseEvent):
        self.cleanUp()

