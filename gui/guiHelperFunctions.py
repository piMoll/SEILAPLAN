# -*- coding: utf-8 -*-
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
import io

from qgis.PyQt.QtCore import QSize, Qt, QFileInfo, QSettings
from qgis.PyQt.QtWidgets import QDialog, QWidget, QLabel, QDialogButtonBox, \
    QLayout, QHBoxLayout, QComboBox, QSizePolicy, QPushButton, QCheckBox, \
    QVBoxLayout, QFileDialog, QLineEdit
from qgis.PyQt.QtGui import QColor, QIcon, QPixmap
from qgis.gui import QgsVertexMarker
from qgis.core import QgsRasterLayer, QgsVectorLayer, QgsProject
from processing import run


class Raster(object):
    def __init__(self, ide, name, grid):
        self.id = ide
        self.name = name
        self.grid = grid
        self.selected = False


class DialogWithImage(QDialog):
    def __init__(self, interface):
        QDialog.__init__(self, interface.mainWindow())
        self.iface = interface
        self.main_widget = QWidget(self)
        self.main_widget.setMinimumSize(QSize(100, 100))
        self.label = QLabel()
        self.buttonBox = QDialogButtonBox(self.main_widget)
        self.buttonBox.setStandardButtons(QDialogButtonBox.Ok)
        self.buttonBox.accepted.connect(self.Apply)
        # Access the layout of the MessageBox to add the checkbox
        self.container = QVBoxLayout(self.main_widget)
        self.container.addWidget(self.label)
        self.container.addWidget(self.buttonBox)
        self.container.setAlignment(Qt.AlignCenter)
        self.container.setSizeConstraint(QLayout.SetFixedSize)
        self.setLayout(self.container)

    def Apply(self):
        self.close()


class QgsStueMarker(QgsVertexMarker):
    def __init__(self, canvas):
        QgsVertexMarker.__init__(self, canvas)
        self.setColor(QColor(1, 1, 213))
        self.setIconType(QgsVertexMarker.ICON_BOX)
        self.setIconSize(11)
        self.setPenWidth(3)


class QgsMovingCross(QgsVertexMarker):
    def __init__(self, canvas):
        QgsVertexMarker.__init__(self, canvas)
        self.setColor(QColor(27, 25, 255))
        self.setIconType(QgsVertexMarker.ICON_CROSS)
        self.setIconSize(20)
        self.setPenWidth(3)


class DialogOutputOptions(QDialog):
    def __init__(self, interface, toolWindow, options):
        QDialog.__init__(self, interface.mainWindow())
        self.iface = interface
        self.tool = toolWindow
        self.options = options
        self.setWindowTitle("Output Optionen")
        main_widget = QWidget(self)

        # Build up gui
        hbox = QHBoxLayout()
        saveLabel = QLabel("Speicherpfad")
        self.pathField = QComboBox()
        self.pathField.setMinimumWidth(400)
        self.pathField.setSizePolicy(
            QSizePolicy(QSizePolicy.Expanding,
                              QSizePolicy.Fixed))
        openButton = QPushButton()
        openButton.setMaximumSize(QSize(27, 27))
        icon = QIcon()
        iconPath = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                                'icons', 'icon_open.png')
        icon.addPixmap(QPixmap(iconPath), QIcon.Normal,
                       QIcon.Off)
        openButton.setIcon(icon)
        openButton.setIconSize(QSize(24, 24))
        openButton.clicked.connect(self.onOpenDialog)

        hbox.addWidget(saveLabel)
        hbox.addWidget(self.pathField)
        hbox.addWidget(openButton)
        # Create checkboxes
        questionLabel = \
            QLabel(u"Welche Produkte sollen erzeugt werden?")
        self.checkBoxReport = QCheckBox(u"Technischer Bericht")
        self.checkBoxPlot = QCheckBox(u"Diagramm")
        self.checkBoxGeodata = \
            QCheckBox(u"Shape-Daten der Stützen und Seillinie")
        self.checkBoxCoords = \
            QCheckBox(u"Koordinaten-Tabellen der Stützen und Seillinie")
        # Set tick correctly
        self.checkBoxReport.setChecked(self.options['report'])
        self.checkBoxPlot.setChecked(self.options['plot'])
        self.checkBoxGeodata.setChecked(self.options['geodata'])
        self.checkBoxCoords.setChecked(self.options['coords'])
        # Create Ok/Cancel Button and connect signal
        buttonBox = QDialogButtonBox(main_widget)
        buttonBox.setStandardButtons(QDialogButtonBox.Ok|
                                          QDialogButtonBox.Cancel)
        buttonBox.accepted.connect(self.Apply)
        buttonBox.rejected.connect(self.Reject)
        # Layout
        container = QVBoxLayout(main_widget)
        container.addLayout(hbox)
        container.addWidget(QLabel(""))
        container.addWidget(questionLabel)
        container.addWidget(self.checkBoxReport)
        container.addWidget(self.checkBoxPlot)
        container.addWidget(self.checkBoxGeodata)
        container.addWidget(self.checkBoxCoords)
        container.addWidget(buttonBox)
        container.setAlignment(Qt.AlignLeft)
        self.setLayout(container)

    def fillInDropDown(self, pathList):
        for i in reversed(range(self.pathField.count())):
            self.pathField.removeItem(i)
        for path in reversed(pathList):
            self.pathField.addItem(path)

    def onOpenDialog(self):
        title = u"Output Pfad auswählen"
        directory = QFileDialog.getExistingDirectory(self, title,
            self.options['outputPath'])
        
        self.tool.updateCommonPathList(directory)
        self.fillInDropDown(self.tool.commonPaths)

    def Apply(self):
        # Save checkbox status
        self.options['outputPath'] = self.pathField.currentText()
        self.options['report'] = int(self.checkBoxReport.isChecked())
        self.options['plot'] = int(self.checkBoxPlot.isChecked())
        self.options['geodata'] = int(self.checkBoxGeodata.isChecked())
        self.options['coords'] = int(self.checkBoxCoords.isChecked())

        # Update output location with currently selected path
        self.tool.updateCommonPathList(self.pathField.currentText())
        self.close()

    def Reject(self):
        self.close()


class DialogSaveParamset(QDialog):
    def __init__(self, interface, toolWindow):
        """Small window to define the name of the saved parmeter set."""
        QDialog.__init__(self, interface.mainWindow())
        self.iface = interface
        self.tool = toolWindow
        self.paramData = None
        self.availableParams = None
        self.savePath = None
        self.field = None
        self.setWindowTitle("Name definieren")
        main_widget = QWidget(self)
        
        # Build gui
        hbox = QHBoxLayout()
        setnameLabel = QLabel("Setname definieren")
        self.setnameField = QLineEdit()
        self.setnameField.setMinimumWidth(400)
        self.setnameField.setSizePolicy(
            QSizePolicy(QSizePolicy.Expanding,
                        QSizePolicy.Fixed))
        
        hbox.addWidget(setnameLabel)
        hbox.addWidget(self.setnameField)
        
        # Create Ok/Cancel Button and connect signal
        buttonBox = QDialogButtonBox(main_widget)
        buttonBox.setStandardButtons(QDialogButtonBox.Ok |
                                     QDialogButtonBox.Cancel)
        buttonBox.accepted.connect(self.Apply)
        buttonBox.rejected.connect(self.Reject)
        
        # Layout
        container = QVBoxLayout(main_widget)
        container.addLayout(hbox)
        container.addWidget(QLabel(""))
        container.addWidget(buttonBox)
        container.setAlignment(Qt.AlignLeft)
        self.setLayout(container)
    
    def setData(self, newparams, availableParams, savePath, field):
        self.paramData = newparams
        self.availableParams = availableParams
        self.savePath = savePath
        self.field = field
    
    def saveParams(self, setname):
        self.savePath = os.path.join(self.savePath, f'{setname}.txt')
        self.paramData['label'] = setname
        
        with io.open(self.savePath, encoding='utf-8', mode='w+') as f:
            # Write header
            f.writelines('name\tvalue\n')
            # Write parameter values
            for key, val in self.paramData.items():
                f.writelines(f'{key}\t{val}\n')
        
        self.availableParams[setname] = self.paramData
        self.field.addItem(setname)
        self.field.setCurrentIndex(self.field.count()-1)

    def Apply(self):
        setname = self.setnameField.text()
        self.saveParams(setname)
        self.close()
    
    def Reject(self):
        self.close()


def readFromTxt(path):
    """Generic Method to read a txt file with header information and save it
    to a dictionary. The keys of the dictionary are the header items.
    """
    fileData = {}
    if os.path.exists(path):
        with io.open(path, encoding='utf-8') as f:
            lines = f.read().splitlines()
            header = lines[0].split('\t')
            for line in lines[1:]:
                if line == '': break
                line = line.split('\t')
                row = {}
                key = line[0]
                # if txtfile has structure key, value
                if len(header) == 2:
                    row = line[1]
                # if txtfile has structure key, value1, value2, value3 ...
                else:
                    for i in range(1, len(header)):
                        row[header[i]] = line[i]
                fileData[key] = row
        return fileData, header
    else:
        return False, False


def strToNum(coord):
    """ Convert string to number by removing the ' sign.
    """
    try:
        num = int(coord.replace("'", ''))
    except ValueError:
        num = ''
    return num


def generateName():
    """ Generate a unique project name.
    """
    import time
    now = time.time()
    timestamp = time.strftime("%d.%m_%H'%M", time.localtime(now))
    name = "seilaplan_{}".format(timestamp)
    return name


def valueToIdx(val):
    if val == 'ja':
        return 0
    else:
        return 1


def formatNum(number):
    """ Layout Coordinates with thousand markers.
    """
    roundNum = int(round(number))
    strNum = str(roundNum)
    if roundNum > 999:
        b, c = divmod(roundNum, 1000)
        if b > 999:
            a, b = divmod(b, 1000)
            strNum = "{:0d}'{:0>3n}'{:0>3n}".format(a, b, c)
        else:
            strNum = "{:0n}'{:0>3n}".format(b, c)
    return strNum


def castToNumber(val, dtype):
    errState = None
    try:
        if dtype == 'string':
            cval = val
            # result = True
        elif dtype == 'float':
            cval = float(val)
        else:
            cval = int(val)
    except ValueError:
        cval = None
        errState = True
    return cval, errState


def createContours(canvas, dhm):
    contourLyr = dhm['contour']
    contourName = "Hoehenlinien_" + dhm['name']
    
    # Get current CRS of qgis project
    s = QSettings()
    oldValidation = s.value("/Projections/defaultBehaviour")
    crs = canvas.mapSettings().destinationCrs()
    crsEPSG = crs.authid()
    # If project and raster CRS are equal and set correctly
    if crsEPSG == dhm['spatialRef'] and "USER" not in crsEPSG:
        s.setValue("/Projections/defaultBehaviour", "useProject")
    else:
        crs = dhm['layer'].crs()
    
    # If contours exist, remove them
    if contourLyr:
        QgsProject.instance().removeMapLayer(contourLyr.id())
        contourLyr = None
    
    # If no contours exist, create them
    else:
        outputPath = os.path.join(os.path.dirname(dhm['path']), contourName + '.shp')
        if os.path.exists(outputPath):
            contourLyr = QgsVectorLayer(outputPath, contourName, "ogr")
        else:
            processingParams = {
                'INPUT': dhm['layer'],
                'BAND': 1,
                'INTERVAL': 20,
                'FIELD_NAME': "Hoehe",
                'OUTPUT': outputPath
            }
            algOutput = run("gdal:contour", processingParams)
            contourLyr = QgsVectorLayer(algOutput['OUTPUT'], contourName, "ogr")
        # contourLyr the same CRS as qgis project
        contourLyr.setCrs(crs)
        QgsProject.instance().addMapLayer(contourLyr)
        s.setValue("/Projections/defaultBehaviour", oldValidation)
        
    # More useful stuff
    # uri = "linestring?crs=epsg:{}".format(crsNum)
    # contourName = "Hoehenlinien_" + self.dhm['name']
    # contour = QgsVectorLayer(uri, contourName,  "memory")
    
    return contourLyr


def loadOsmLayer(homePath):
    osmLyr = None
    
    for l in QgsProject.instance().layerTreeRoot().findLayers():
        if l.layer().name() == 'OSM_Karte':
            osmLyr = l.layer()
            QgsProject.instance().removeMapLayer(osmLyr.id())
            break
            
    if not osmLyr:
        # Add OSM layer
        xmlPath = os.path.join(homePath, 'config', 'OSM_Karte.xml')
        baseName = QFileInfo(xmlPath).baseName()
        osmLayer = QgsRasterLayer(xmlPath, baseName)
        QgsProject.instance().addMapLayer(osmLayer)
        