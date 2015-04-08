# -*- coding: utf-8 -*-
"""
/***************************************************************************
 SeilaplanPluginDialog
                                 A QGIS plugin
 Seilkran-Layoutplaner
                             -------------------
        begin                : 2013
        copyright            : (C) 2015 by ETH Zürich
        email                : bontle@ethz.ch
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

# Import standard Python Bibliotheken
import os
import io
import re
import numpy
from operator import itemgetter
import unicodedata

# GUI und QGIS Bibiliotheken
from PyQt4 import QtCore, QtGui
from PyQt4.QtCore import QObject, SIGNAL, QFileInfo
from qgis.core import QGis, QgsRasterLayer, QgsVectorLayer, QgsGeometry, \
    QgsPoint, QgsFeature, QgsMapLayerRegistry
from qgis.gui import QgsRubberBand
import processing

# Import andere Skripts
from gui.guiHelperFunctions import Raster, valueToIdx, QgsStueMarker, \
    strToNum, DialogOutputOptions, generateName, DialogWithImage, formatNum, \
    readFromTxt, castToNumber
from gui.ui_seilaplanDialog import Ui_Dialog
from bo.ptmaptool import ProfiletoolMapTool
from bo.createProfile import CreateProfile
from gui.profileDialog import ProfileWindow

# Globale Methoden
##################

# UTF-8 Kodierung
try:
    utf8 = QtCore.QString.fromUtf8
except AttributeError:
    utf8 = lambda s: s

# OS-abhängiger Zeilenumbruch
nl = unicode(os.linesep)

# Pfad zu Icons für GUI
greenIcon = '<html><head/><body><p><img src=":/plugins/SeilaplanPlugin/' \
            'icons/icon_green.png"/></p></body></html>'
yellowIcon = '<html><head/><body><p><img src=":/plugins/SeilaplanPlugin/' \
             'icons/icon_yellow.png"/></p></body></html>'
redIcon = '<html><head/><body><p><img src=":/plugins/SeilaplanPlugin/' \
          'icons/icon_red.png"/></p></body></html>'
# Text neben Icons
greenTxt = ''
yellowTxt = 'zu definieren'
redTxt = 'ausserhalb Raster'

# Info-Abbildungen
infImg = {'Bodenabstand': u'Erklärungen zum Bodenabstand',
          'VerankerungA': u'Erklärungen zur Verankerung am Anfangspunkt',
          'VerankerungE': u'Erklärungen zur Verankerung am Anfangspunkt',
          'Stuetzen': u'Erklärungen zu den Zwischenstützen'}

# TODO: Disclaimer, Lizenz
infoTxt = (u"SEILAPLAN - Seilkran-Layoutplaner\n\n"
    u"SEILAPLAN berechnet auf Grund eines digitalen Höhenmodells zwischen "
    u"definierten Anfangs- und Endkoordinaten sowie technischer Parameter das "
    u"optimale Seillinienlayout, d.h. Position und Höhe der Stützen und "
    u"schreibt die wichtigsten Kennwerte dieser Seillinie heraus.\n\n"
    u"Realisierung:\nProfessur für forstliches Ingenieurwesen\n"
    u"ETH Zürich\n8092 Zürich\n\nBeteiligte Personen:\n"
    u"Leo Bont (Konzept, Mechanik)\nPatricia Moll "
    u"(Implementation in Python / QGIS)")



###############################################################################
# Klasse, die sämtliches Verhalten des Dialogfensters steuert
###############################################################################


class SeilaplanPluginDialog(QtGui.QDialog, Ui_Dialog):
    def __init__(self, interface, helper):
        QtGui.QDialog.__init__(self, interface.mainWindow())
        # import pydevd
        # pydevd.settrace('localhost', port=53100,
        #             stdoutToServer=True, stderrToServer=True)

        # QGIS Interface (GUI von QGIS)
        self.iface = interface
        # QGIS Karte
        self.canvas = self.iface.mapCanvas()
        self.action = QtGui.QAction(
            QtGui.QIcon(":/plugins/SeilaplanPlugin/icons/icon_app.png"),
            u"SEILAPLAN", self.iface.mainWindow())
        self.action.setWhatsThis("SEILAPLAN")
        # Separate Klasse, die nach Schliessen der GUI die Berechnungen in
        #   einem separaten Thread (=Berechnungsprozess) übernimmt
        self.threadingControl = helper
        # Klasse um mit der QGIS Karte zu interagieren: damit lässt sich
        #   in die Karte zeichnen
        self.tool = ProfiletoolMapTool(self.canvas, self.action)
        self.savedTool = self.canvas.mapTool()
        # GUI des Seillinientools wird initialisiert
        #   (import aus ui_seilbahnplugin.py)
        self.setupUi(self)
        # Wichtige Pfade abrufen/erzeugen
        self.userHomePath = os.path.join(os.path.expanduser('~'))
        self.homePath = os.path.dirname(__file__)
        self.paramPath = os.path.join(self.homePath, 'config', 'params.txt')
        #self.laValPath = os.path.join(self.homePath, 'config', 'lastSettings.txt')
        self.commonPathsFile = os.path.join(self.homePath, 'config', 'commonPaths.txt')
        self.commonPaths, outputOpt = self.createCommonPathList()
        # Output Optionen initialisieren
        self.outputOpt = {'outputPath': self.commonPaths[-1],   # zuletzt verwendeter Pfad
                          'report': outputOpt[0],
                          'plot': outputOpt[1],
                          'geodata': outputOpt[2],
                          'coords': outputOpt[3]}
        # Parameter der Seillinie initialisieren
        self.param = None
        self.paramOrder = None
        self.header = None
        self.paramSet = None

        # GUI Felder gruppieren
        self.settingFields = {}
        # Koordinaten-Felder erzeugen
        self.coordFields = {}
        self.pointA = [-100, -100]
        self.pointE = [-100, -100]
        self.azimut = 0
        self.coordStateA = 'yellow'
        self.coordStateE = 'yellow'
        self.groupFields()
        # Info Fenster mit Darstellungen initialisieren
        self.imgBox = DialogWithImage(self.iface)

        # Zusätzliche Layer für Übersicht
        self.osmLayer = None
        self.osmLyrOn = False
        self.osmLyrButton.setEnabled(False)
        self.contourLyrButton.setEnabled(False)
        self.contourLyr = None
        self.contourLyrOn = False

        # Signals und Slots verbinden
        self.connectFields()
        self.buttonShowProf.setEnabled(False)
        # Initialisiere Geometrieobjekte um Linie auf Karte zu zeichnen
        self.zeichnen.setEnabled(False)
        self.polygon = False
        self.rubberband = QgsRubberBand(self.canvas, self.polygon)
        self.rubberband.setWidth(3)
        self.rubberband.setColor(QtGui.QColor(231, 28, 35))
        self.markers = []
        self.pointsToDraw = []
        self.dblclktemp = None
        self.drawnLine = None
        self.line = False
        self.lineLyr = None
        self.vl = None
        self.lineID = None
        # Dialogfenster für Höhenprofil initialisieren
        self.profileWin = None
        # Dialogfenster für Output Optionen
        self.optionenWin = DialogOutputOptions(self.iface, self)
        self.optionenWin.fillInDropDown(self.commonPaths)
        # Variable für alle wichtigen Eigenschaften des ausgewählten DHMs
        self.dhm = {}
        # Vom Benutzer definierte fixe Stützen
        self.fixStue = {}

    def connectFields(self):
        """ Verbindet die GUI Felder mit Aktionen
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
        # QObject.connect(self.buttonInfo,
        #     SIGNAL(utf8("clicked()")), self.OnInfo)
        QObject.connect(self.buttonInfo,
            SIGNAL(utf8("clicked()")), self.onInfo)
        QObject.connect(self.buttonOptionen,
            SIGNAL(utf8("clicked()")), self.onShowOutputOpt)
        # Info Buttons
        QObject.connect(self.infoBodenabstand,
            SIGNAL(utf8("clicked()")), self.onShowInfoImg)
        QObject.connect(self.infoVerankerungA,
            SIGNAL(utf8("clicked()")), self.onShowInfoImg)
        QObject.connect(self.infoVerankerungE,
            SIGNAL(utf8("clicked()")), self.onShowInfoImg)
        QObject.connect(self.infoStuetzen,
            SIGNAL(utf8("clicked()")), self.onShowInfoImg)
        # OSM Karte und Höhenlinien zeichnen
        QObject.connect(self.osmLyrButton,
            SIGNAL(utf8("clicked()")), self.onClickOsmButton)
        QObject.connect(self.contourLyrButton,
            SIGNAL(utf8("clicked()")), self.onClickContourButton)

        QObject.connect(self.fieldProjName,
            SIGNAL(utf8("textChanged (const QString&)")), self.setProjName)
        QObject.connect(self.zeichnen,
            SIGNAL(utf8("clicked()")), self.drawLine)
        QObject.connect(self.buttonShowProf,
            SIGNAL(utf8("clicked()")), self.onShowProfile)
        QObject.connect(self.fieldParamSet,
            SIGNAL(utf8("currentIndexChanged(const QString&)")), self.setParamSet)
        # Wird nur ausgeführt, wenn Koordinaten manuell geändert werden
        QObject.connect(self.coordAx,
            SIGNAL(utf8("editingFinished()")), self.changedPointAField)
        QObject.connect(self.coordAy,
            SIGNAL(utf8("editingFinished()")), self.changedPointAField)
        QObject.connect(self.coordEx,
            SIGNAL(utf8("editingFinished()")), self.changedPointEField)
        QObject.connect(self.coordEy,
            SIGNAL(utf8("editingFinished()")), self.changedPointEField)


    def groupFields(self):
        """Fasst die GUI Felder in einem Dicitionary zusammen um schneller auf
        die Felder zuzugreifen"""
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
        """ Standardwerte (Name des Projektes und ParameterSets) werden in die
        Felder der GUI geladen"""
        # Laden der unterschiedlichen Standardeinstellungen und Parameter
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
        # Projektname generieren
        self.fieldProjName.setText(generateName())
        self.enableToolTips()

    def enableToolTips(self):
        for [name, field] in self.settingFields.items():
            field.setToolTip(self.param[name]['tooltip'])

    def setParamSet(self, setName):
        self.paramSet = 'set_' + setName
        # Daten in Felder füllen
        self.fillInValues(self.param, self.paramSet)

    def fillInValues(self, data, datafield):
        """ Nimmt ein Dictionary mit Parameterdaten und füllt die GUI
        Felder mit den Werten."""
        for name, field in self.settingFields.items():
            val = data[name][datafield]
            # if self.param[name]['ftype'] == 'dialog_field':
            #     # val = self.CheckUserPath(val)
            if self.param[name]['ftype'] == 'drop_field':
                field.setCurrentIndex(valueToIdx(val))
                continue
            # Ganzzahlige Fliesskommazahlen werden für Darstellung umgewandelt
            if val[-2:] == '.0':
                val = val[:-2]
            if val == '-':
                val = ''
            field.setText(val)

    def updateRasterList(self):
        rasterlist = self.getAvailableRaster()
        self.addRastersToGui(rasterlist)

    def getAvailableRaster(self):
        """Alle Raster aus dem Table of content (Legende) aussuchen und im
        Drop-Down Menü der GUI anzeigen."""
        legend = self.iface.legendInterface()
        availLayers = legend.layers()
        rColl = []

        for lyr in availLayers:
            if legend.isLayerVisible(lyr):
                lyrType = lyr.type()
                lyrName = unicodedata.normalize('NFKD',
                                 unicode(lyr.name())).encode('ascii', 'ignore')
                if lyrType == 1:        # = Raster
                    r = Raster(lyr.id(), lyrName, lyr)
                    rColl.append(r)
        return rColl

    def addRastersToGui(self, rasterList):
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
            self.zeichnen.setEnabled(True)

    def setRaster(self, rastername):
        rasterlist = self.getAvailableRaster()
        for rlyr in rasterlist:
            if rlyr.name == rastername:        # = Raster
                path = rlyr.grid.dataProvider().dataSourceUri()
                spatialRef = rlyr.grid.crs().authid()
                # if self.dhm.get('path', 0) != path:
                #     self.RemoveCoords()
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
                self.dhm['contour'] = None
        # Wenn ein Raster gewählt wurde, kann auch der OSM Button aktiviert
        #   werden
        self.osmLyrButton.setEnabled(True)
        self.contourLyrButton.setEnabled(True)

    def searchForRaster(self, path):
        """ Sucht als erstes durch Table of Content um entsprechendes Raster
        zu finden. Ist das Raster nicht da, wird im angegebenen Pfad danach
        gesucht und es zu QGIS hinzugefügt.
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
                # TODO Raster zu Karte hinzufügen, funktioniert noch nicht
                rlayer = QgsRasterLayer(path, baseName)
                QgsMapLayerRegistry.instance().addMapLayer(rlayer)
                self.updateRasterList()
                self.setCorrectRasterInField(baseName)
                self.setRaster(baseName)
                self.zeichnen.setEnabled(True)
            else:
                txt = "Raster mit dem Pfad {} ist nicht vorhanden".format(path)
                QtGui.QMessageBox.information(self, "Fehler beim Laden des Rasters", txt)

    def setCorrectRasterInField(self, rasterName):
        for idx in range(self.rasterField.count()):
            if rasterName == self.rasterField.itemText(idx):
                self.rasterField.setCurrentIndex(idx)
                self.zeichnen.setEnabled(True)
                break

    def createCommonPathList(self):
        """ Liest die Output einstellungen und die vom benutzer ausgewählten
        Pfade aus einer Datei aus. Falls dabei nicht vorhanden ist, wird später
        eine neue Txt-Datei mit Standardwerten erzeugt (updateCommonPathFile).
        """
        commonPaths = []
        homePathPresent = False
        # Falls keine Voreinstellungen vorhanden sind, werden folgende
        #   Output-Optionen gewählt:
        #   [Bericht=ja, Plot als pdf, Shape-Files=ja, Koordinaten-Tabellen,
        #       Projektdaten speichern=ja]
        outputOpt = [1, 1, 0, 0]
        # Falls noch keine Output Pfade definiert wurden, werden die Daten
        #   im Benutzerverzeichnis abgelegt
        userPath = os.path.join(self.userHomePath, 'Seilaplan')

        if os.path.exists(self.commonPathsFile):
            with io.open(self.commonPathsFile, encoding='utf-8') as f:
                lines = f.read().splitlines()
                # Erste Linie enthält Infos zu Output Optionen
                try:
                    outputOpt = lines[0].split()
                    outputOpt = [int(x) for x in outputOpt]
                except IndexError:      # bedeutet: die Datei ist leer
                    pass
                except ValueError:      # bedeutet: es sind keine Zahlen
                    pass
                # Pfade von unten nach oben durchgehen (aktuellster Eintrag zuerst)
                for path in lines[1:]:
                    try:
                        if path == '': continue
                        if os.path.exists(path):   # Falls Pfad noch gültig ist
                            if path == userPath:
                                homePathPresent = True
                            commonPaths.append(path)      # in Liste einsetzten
                    except:
                        continue

        if not homePathPresent:  # Falls aktueller Userpath nicht vorhanden ist
            if not os.path.exists(userPath):
                os.mkdir(userPath)
            commonPaths.append(userPath)
        # Maximal gespeicherte Einträge = 12
        if len(commonPaths) > 12:
            del commonPaths[0]
        return commonPaths, outputOpt

    def updateCommonPathList(self, newPath):
        dublicateIdx = None
        # Überprüfen ob Pfad bereits vorhanden ist
        for idx, path in enumerate(self.commonPaths):
            if newPath == path:
                dublicateIdx = idx
                break
        # Eintrag wird hinzugefügt
        if os.path.exists(newPath):
            self.commonPaths.append(newPath)
        # Falls ein alter Eintrag vorhanden ist, wird er gelöscht
        if dublicateIdx:
            del self.commonPaths[dublicateIdx]
        # Maximal gespeicherte Einträge = 12
        if len(self.commonPaths) > 12:
            # Erster (=ältester) Eintrag wird gelöscht
            del self.commonPaths[0]

    def updateCommonPathFile(self):
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

    # TODO Funktioniert leider nicht, im Gegensatz zum Profil-Fenster
    # def mousePressEvent(self, event):
    #     focused_widget = QtGui.QApplication.focusWidget()
    #     if isinstance(focused_widget, QtGui.QLineEdit):
    #         focused_widget.clearFocus()
    #     QtGui.QDialog.mousePressEvent(self, event)


    ###########################################################################
    ### Linie in Karte zeichnen
    ###########################################################################

    def drawLine(self):
        # if self.ui.IDC_rbDigi.isChecked() is False:
        #     self.ui.IDC_rbDigi.setChecked(True)
        self.dblclktemp = None
        self.clearMap()
        self.rubberband.reset(self.polygon)
        self.__cleanDigi()
        self.__activateDigiTool()
        self.canvas.setMapTool(self.tool)

    def clearMap(self):
        if self.profileWin:
            self.profileWin.deactivateMapMarker()
            self.profileWin.removeLines()
            del self.profileWin
            self.profileWin = None
        self.removeStueMarker()

    def __createDigiFeature(self, pnts):
        # import pydevd
        # pydevd.settrace('localhost', port=53100,
        #             stdoutToServer=True, stderrToServer=True)
        line = QgsGeometry.fromPolyline(pnts)
        qgFeat = QgsFeature()
        qgFeat.setGeometry(line)
        # self.CreateLayer(qgFeat)
        return qgFeat

    def __lineFinished(self):
        lastPoint = self.pointsToDraw[-1]
        if len(self.pointsToDraw) < 2:
            self.removeStueMarker()
            self.__cleanDigi()
            self.pointsToDraw = []
            self.dblclktemp = lastPoint
            self.drawnLine = None
            self.buttonShowProf.setEnabled(False)
        # self.markers = [QgsStueMarker(self.canvas), QgsStueMarker(self.canvas)]
        # for i in range(2):
        #     self.markers[i].setCenter(self.pointsToDraw[i])
        # self.canvas.refresh()
        self.drawnLine = self.__createDigiFeature(self.pointsToDraw)
        # TODO: Umwandlung in Layer
        # self.CheckDrawnCoords(self.pointsToDraw[0])
        self.changeCoordA(self.pointsToDraw[0])
        self.changeCoordE(self.pointsToDraw[1])
        self.createProfile()
        self.__cleanDigi()
        self.dblclktemp = lastPoint

    def __lineFromFields(self):
        self.dblclktemp = None
        self.rubberband.reset(self.polygon)
        lastPoint = self.pointsToDraw[-1]
        # self.CreateLayer(self.pointsToDraw)

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

    def __cleanDigi(self):
        self.pointsToDraw = []
        self.canvas.unsetMapTool(self.tool)     # Signal DEACTIVATE wird ausgesandt
        # self.canvas.setCursor(QCursor(Qt.OpenHandCursor))
        self.canvas.setMapTool(self.savedTool)

    def __activateDigiTool(self):
        QObject.connect(self.tool, SIGNAL("moved"), self.__moved)
        QObject.connect(self.tool, SIGNAL("rightClicked"), self.__rightClicked)
        QObject.connect(self.tool, SIGNAL("leftClicked"), self.__leftClicked)
        QObject.connect(self.tool, SIGNAL("doubleClicked"), self.__doubleClicked)
        QObject.connect(self.tool, SIGNAL("deactivate"), self.__deactivateDigiTool)

    def __deactivateDigiTool(self):
        QObject.disconnect(self.tool, SIGNAL("moved"), self.__moved)
        QObject.disconnect(self.tool, SIGNAL("leftClicked"), self.__leftClicked)
        QObject.disconnect(self.tool, SIGNAL("rightClicked"), self.__rightClicked)
        QObject.disconnect(self.tool, SIGNAL("doubleClicked"), self.__doubleClicked)

    def __moved(self, position):
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
                self.rubberband.setToGeometry(QgsGeometry.fromPolyline(pnts),None)

    def __rightClicked(self, position):
        # Rerouting (es ist egal mit welcher Taste man klickt)
        self.__leftClicked(position)

    def __leftClicked(self, position):
        mapPos = self.canvas.getCoordinateTransform().\
            toMapCoordinates(position["x"], position["y"])
        newPoint = QgsPoint(mapPos.x(), mapPos.y())
        #if self.selectionmethod == 0:
        if newPoint == self.dblclktemp:
            self.dblclktemp = None
            return
        else:
            # Punkt mit Marker markieren
            self.drawStueMarker(newPoint)
            if len(self.pointsToDraw) == 0:
                self.rubberband.reset(self.polygon)
                self.pointsToDraw.append(newPoint)
            else:
                self.pointsToDraw.append(newPoint)
                self.__lineFinished()

    def __doubleClicked(self, position):
        pass

    #not in use right now
    def __lineCancel(self):
        pass

    def refreshLine(self):
        pass

    ###########################################################################
    ### Aktionen rund um Start- und Endkoordinaten
    ###########################################################################

    def changedPointAField(self):
        # import pydevd
        # pydevd.settrace('localhost', port=53100,
        #             stdoutToServer=True, stderrToServer=True)
        x = strToNum(self.coordFields['Ax'].text())
        y = strToNum(self.coordFields['Ay'].text())
        # Nur etwas ändern falls sich Koordinate verändert hat
        if not (x == self.pointA[0] and y == self.pointA[1]):
            self.changeCoordA([x, y])
            self.updateLineFromGui()

    def changedPointEField(self):
        x = strToNum(self.coordFields['Ex'].text())
        y = strToNum(self.coordFields['Ey'].text())
        # Nur etwas ändern falls sich Koordinate verändert hat
        if not (x == self.pointE[0] and y == self.pointE[1]):
            self.changeCoordE([x, y])
            self.updateLineFromGui()

    def changeCoordA(self, newpoint):
        # import pydevd
        # pydevd.settrace('localhost', port=53100,
        #             stdoutToServer=True, stderrToServer=True)

        # Vorhandene fixe Stützen werden zurückgesetzt
        self.fixStue = {}
        # Überprüfen, ob Punkt korrekt und innerhalb DHM ist
        state = self.checkPoint(newpoint)
        self.coordStateA = state
        # Symbol neben Felder aktualisieren
        self.changePointSym(state, 'A')
        # GUI Felder aktualisieren
        if state != 'yellow':
            self.coordFields['Ax'].setText(formatNum(newpoint[0]))
            self.coordFields['Ay'].setText(formatNum(newpoint[1]))
            self.pointA = newpoint
            self.setAzimut()
        # Profil-Button und Länge der Seillinie anpassen
        self.checkProfileStatus()
        self.checkLenghtStatus()

    def changeCoordE(self, newpoint):
        # Vorhandene fixe Stützen werden zurückgesetzt
        self.fixStue = {}
        # Überprüfen, ob Punkt korrekt und innerhalb DHM ist
        state = self.checkPoint(newpoint)
        self.coordStateE = state
        # Symbol neben Felder aktualisieren
        self.changePointSym(state, 'E')
        # GUI Felder aktualisieren
        if state != 'yellow':
            self.coordFields['Ex'].setText(formatNum(newpoint[0]))
            self.coordFields['Ey'].setText(formatNum(newpoint[1]))
            self.pointE = newpoint
            self.setAzimut()
        # Profil-Button und Länge der Seillinie anpassen
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

    # def enableAdditionalLyr(self):
    #     if self.dhm:
    #         self.osmLyrButton.setEnabled(True)
    #         self.contourLyrButton.setEnabled(True)
    #     else:
    #         self.osmLyrButton.setEnabled(False)
    #         self.contourLyrButton.setEnabled(False)

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
            self.drawnLine = self.__createDigiFeature(points)
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
        # import pydevd
        # pydevd.settrace('localhost', port=53100,
        #             stdoutToServer=True, stderrToServer=True)
        # dx = (self.pointE[0] - self.pointA[0]) * 1.0
        # dy = (self.pointE[1] - self.pointA[1]) * 1.0
        # import math
        # if dx == 0:
        #     dx = 0.000001
        # azimut = math.atan(dy/dx)
        # if dx > 0:
        #     azimut += 2 * math.pi
        # else:
        #     azimut += math.pi
        import math
        x = self.pointA[0] + dist * math.cos(self.azimut)
        y = self.pointA[1] + dist * math.sin(self.azimut)
        return [x, y]


    ###########################################################################
    ### Layer hinzufügen
    ###########################################################################

    def onClickOsmButton(self):
        """
        Lade OpenStreetMap Karte für eine Bessere Orientierung.
        """

        self.osmLyrOn = False
        # Ist bereits eine OSM Karte vorhanden (zB von einer früheren Instanz)?
        legend = self.iface.legendInterface()
        availLayers = legend.layers()
        for lyr in availLayers:
            if lyr.name() == 'OSM_Karte':
                self.osmLayer = lyr
                self.osmLyrOn = True
                break

        if self.osmLyrOn:
            # OSM Layer entfernen
            QgsMapLayerRegistry.instance().removeMapLayer(self.osmLayer.id())
            self.osmLyrOn = False
        else:
            # OSM Layer hinzufügen
            xmlPath = os.path.join(self.homePath, 'config', 'OSM_Karte.xml')
            baseName = QFileInfo(xmlPath).baseName()
            self.osmLayer = QgsRasterLayer(xmlPath, baseName)
            QgsMapLayerRegistry.instance().addMapLayer(self.osmLayer)
            self.osmLyrOn = True

    def onClickContourButton(self):
        self.createContourLines()

    def createContourLines(self):
        #Generate Contourlines
        # import pydevd
        # pydevd.settrace('localhost', port=53100,
        #             stdoutToServer=True, stderrToServer=True)

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

        # mem_layer = QgsVectorLayer("LineString?crs=epsg:21781", "temp_layer",
        #                                    "memory")
        # contourLyr = QgsVectorLayer(contourPath, "Hoehenlinien", "ogr")
        # layer = QgsMapLayerRegistry.instance().mapLayersByName(
        #           "memory:Hoehenlinien")[0]
        # contourLyr = QgsVectorLayer(contourPath, "Hoehenlinien", "ogr")
        # http://gis.stackexchange.com/questions/76594/how-to-load-memory-output-from-qgis-processing
        # QgsMapLayerRegistry.instance().addMapLayer(contourLyr)
        # layer.crs().authid() == u'EPSG:21781'
        # layer.featureCount()



    ###########################################################################
    ### Aktionen von Buttons zum laden und speichern
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
        """ Wird ausgeführt, wenn im Menü der Eintrag "Projekt laden..."
        aktiviert wird. Öffnet ein Dialogfenster, in dem csv-Dateien mit zuvor
        gespeicherten Parametersätzen geladen werden kann. Die Daten werden
        anschliessend in die Felder geladen"""
        # pydevd.settrace('localhost', port=53100,
        #                 stdoutToServer=True, stderrToServer=True)
        title = 'Projekt laden'
        fFilter = 'Txt Dateien (*.txt)'
        filename = QtGui.QFileDialog.getOpenFileName(self, title,
                                        self.outputOpt['outputPath'], fFilter)
        if filename:
            self.loadProj(filename)
        else:
            return False

    def loadProj(self, path):
        # import pydevd
        # pydevd.settrace('localhost', port=53100,
        #             stdoutToServer=True, stderrToServer=True)

        # Projektdaten in GUI schreiben
        projHeader, projData  = self.openProjFromTxt(path)
        self.setProjName(projHeader['Projektname'])
        self.searchForRaster(projHeader['Hoehenmodell'])
        # Koordinaten aktualisieren
        pointA = projHeader['Anfangspunkt'].split('/')
        pointE = projHeader['Endpunkt'].split('/')
        self.changeCoordA([strToNum(pointA[0]), strToNum(pointA[1])])
        self.changeCoordE([strToNum(pointE[0]), strToNum(pointE[1])])
        self.updateLineFromGui()
        # Fixe Stützen auslesen
        fixStueString = projHeader['Fixe Stuetzen'].split('/')[:-1]
        for stue in fixStueString:
            [key, values] = stue.split(':')
            [posX, posY, posH] = [string.strip() for string in values.split(',')]
            self.fixStue[int(key)] = [posX, posY, posH]
        self.fieldProjName.setText(self.projName)
        # Parameter in Gui schreiben
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
        """ Die aktuellen, geprüften Benutzereinstellungen werden abgespeichert
        um sie zu einem späteren Zeitpunkt zu laden"""
        # Feldwerte und Reihenfolge für Ausgabe abfragen
        noError, toolData, projInfo = self.getGuiContent()
        if not noError:
            # Falls Fehler vorhanden sind, Aktion abbrechen
            return False
        if not self.paramOrder:
            self.getParamOrder()
        # Projektinfos auslesen
        _, fileheader = self.getProjectInfo()
        if os.path.exists(path):
            os.remove(path)
        with io.open(path, encoding='utf-8', mode='w+') as f:
            # Schreibe Kopfzeilen der Ausgabedatei
            f.writelines(fileheader)
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
        """Öffnet ein gespeichertes Projekt, liest den Inhalt sammt
        Header aus und speichert ihn in ein Dicitonary."""
        fileData = {}
        projInfo = {}
        if os.path.exists(path):
            with io.open(path, encoding='utf-8') as f:
                lines = f.read().splitlines()
                for hLine in lines[:5]:
                    # Header im ascii Format sein, nicht utf-8
                    name = hLine[:17].rstrip().encode('ascii')
                    projInfo[name] = hLine[17:]
                for line in lines[10:]:
                    if line == u'': break
                    line = re.split(r'\s{2,}', line)
                    if line[1] == u'-':
                        line[1] = u''
                    # Keys von Dicitionaries immmer im ascii Format, nicht utf-8
                    key = line[0].encode('ascii')
                    fileData[key] = {'Wert': line[1]}
            return projInfo, fileData
        else:
            return False, False

    def onInfo(self):
        QtGui.QMessageBox.information(self, "SEILAPLAN Info", infoTxt,
                                      QtGui.QMessageBox.Ok)

    def onQuestionmark(self, question):
        pass

    def getParamOrder(self):
        """Reihenfolge der Parameter in Ausgabe bestimmen."""
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
        # Bild laden
        myPixmap = QtGui.QPixmap(imgPath)
        self.imgBox.label.setPixmap(myPixmap)
        self.imgBox.setLayout(self.imgBox.container)
        self.imgBox.show()

    def onShowOutputOpt(self):
        self.optionenWin.show()

    ###########################################################################
    ### Auslesen und prüfen von Feld-Inhalten der GUI
    ###########################################################################

    def getGuiContent(self):
        # Projektinfos auslesen
        try:
            projInfo, projHeader = self.getProjectInfo()
        except:
            return False, False, False
        projInfo['header'] = projHeader
        # Feldwerte und Reihenfolge für Ausgabe abfragen
        fieldData = self.getFieldValues()

        toolData = {}
        errTxt = []
        finalErrorState = True
        for name, d in self.param.items():
            if d['ftype'] ==  'no_field':
                val = d['std_val']
            else:
                val = fieldData[name]
            cval, errState  = castToNumber(val, d['dtype'])
            # Fehlerbehandlung, falls bei der Umwandlung zu einer Zahl ein
            # Fehler passiert ist
            if errState:
                errTxt.append(u"-->Der Wert '{}' im Feld '{}' ist ungültig. "
                              u"Bitte geben Sie eine korrekte "
                              u"Zahl ein.".format(val, unicode(d['label'])))
                finalErrorState = False
                continue
            # Überprüfung des Wertebereiches
            if d['ftype'] not in ['drop_field', 'no_field']:
                result, [rMin, rMax] = self.checkValues(cval, d['dtype'],
                                                        d['min'],d['max'])
                # Zusätzliche Prüfung für Spezialfall Ankerfelder
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

                # Fehlerbehandlung, falls Wert nicht in Wertebereich ist
                if result is False:
                    errTxt.append(u"--> Der Wert '{}' im Feld '{}' ist "
                                  u"ungültig. Bitte wählen Sie einen Wert "
                                  u"zwischen {} und {} {}.".format(cval,
                                   unicode(d['label']), rMin, rMax, d['unit']))
                    finalErrorState = False
                    continue
            # Wenn kein Fehler erzeugt wurde, Daten in Dicitonary laden
            toolData[name] = [cval, d['label'], d['unit'], d['sort']]

        # Fehler in Dialogbox zeigen
        if finalErrorState is False:
            # Fehler-Dialog zeigen
            errorMsg = u"Es wurden folgende Fehler gefunden:" + nl
            errorMsg += nl.join(errTxt)
            QtGui.QMessageBox.information(self, 'Fehler', errorMsg,
                                          QtGui.QMessageBox.Ok)
            return finalErrorState, {}, {}

        return finalErrorState, toolData, projInfo

    def getFieldValues(self):
        """ Werte aus den GUI-Feldern werden ausgelesen """
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
        """ Überprüft ob Werte in vordefinierten Wertebereichen liegen.
        Anstatt einfacher Grenzwert kann auch eine andere Variable angegeben
        werden."""
        rangeSet = []
        for rangeItem in [rangeMin, rangeMax]:
            try:
                # Überprüfe, ob es sich bei der Grenze um ein Variablennamen
                # handelt
                if any(c.isalpha() for c in rangeItem):
                    # Variablenwert wird ausgelesen
                    rangeSet.append(float(self.settingFields[rangeItem].text()))
                else:
                    if dtype == 'float':
                        rangeSet.append(float(rangeItem))
                    else:   # dtype = int
                        rangeSet.append(int(rangeItem))
            except ValueError:
                return False, [None, None]
        # Prüfung des Wertebereichs
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
        # Infos layouten
        projHeader = ''
        coord = []
        for i in [Ax, Ay, Ex, Ey]:
            val = formatNum(i)
            coord.append(val)

        info = [[u'Projektname', projInfo['Projektname']],
                [u'Hoehenmodell', '{}'. format(self.dhm['path'])],
                [u'Anfangspunkt', '{0: >7} / {1: >7}'.format(*tuple(coord[:2]))],
                [u'Endpunkt', '{0: >7} / {1: >7}'.format(*tuple(coord[2:]))]]
                # TODO muss hier noch mehr gespeichert werden?
        fixStueString = u''
        for key, values in self.fixStue.iteritems():
                fixStueString += '{0:0>2}: {1: >7}, {2: >7}, {3: >4}  /  '.format(key, *tuple(values))
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
            name = name.decode('utf-8')
            # Ganzzahlige Fliesskommazahlen werden für Darstellung umgewandelt
            if value[-2:] == '.0':
                value = value[:-2]
            # Wert und Einheit zusammenfügen
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
    ### Aktionen von OK und CANCEL Button
    ###########################################################################

    def apply(self):

        # Werte aus Gui auslesen auslesen
        noError, toolData, projInfo = self.getGuiContent()
        if noError:
            self.threadingControl.setState(True)
        else:
            # Apply wird nicht ausgeführt, zurück zum Dialogfenster
            return False
        # import pydevd
        # pydevd.settrace('localhost', port=53100,
        #              stdoutToServer=True, stderrToServer=True)
        # Projekt wird abgespeichert um es später neu zu laden
        # Inputparameter werden gelayoutet um sie ins Reportfile einzufügen
        projInfo['Params'] = self.layoutToolParams(toolData)
        projInfo['outputOpt'] = self.outputOpt
        projInfo['projFile'] = os.path.join(projInfo['outputOpt']['outputPath'],
                                            self.projName + '_Projekt.txt')
        self.saveProjToTxt(projInfo['projFile'])
        # Fixe Stützen werden richtig abgespeichert und toolData hinzugefügt
        toolData = self.getStueInfo(toolData)
        # Benutzerdaten werden der Klasse MultithreadingControl übergeben
        self.threadingControl.setValue(toolData, projInfo)
        self.close()
        # TODO: Was macht man mit QGsVector Polyline? Für Output sparen?

    def cleanUp(self):
        self.removeCoords()
        # Marker der Stützen entfernen
        self.clearMap()
        # Linie auf canvas löschen
        self.rubberband.reset(self.polygon)
        self.drawnLine = None
        self.__cleanDigi()
        # Falls Profilfenster oder Infofenster offen sind, diese ebenfalls
        # schliessen
        self.imgBox.close()
        if self.profileWin:
            self.profileWin.close()
        self.updateCommonPathFile()
        self.optionenWin.close()
        # TODO Weitere Sachen aufräumen???

    def Reject(self):
        self.close()

    def closeEvent(self, QCloseEvent):
        self.cleanUp()

