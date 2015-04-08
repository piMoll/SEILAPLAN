# -*- coding: utf-8 -*-
"""
/***************************************************************************
 SeilbahnPluginDialog
                                 A QGIS plugin
 Optimierung von Sielbahnlinien
                             -------------------
        begin                : 2014-07-01
        copyright            : (C) 2014 by P.M.
        email                : p@m.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 *****
 """

import os
import io

# GUI und QGIS Bibiliotheken
from PyQt4 import QtCore, QtGui
from PyQt4.QtCore import QObject, SIGNAL
from qgis.gui import QgsVertexMarker


class Raster:
    def __init__(self, ide, name, grid):
        self.id = ide
        self.name = name
        self.grid = grid
        self.selected = False


class DialogWithImage(QtGui.QDialog):
    def __init__(self, interface):
        QtGui.QDialog.__init__(self, interface.mainWindow())
        self.iface = interface
        self.main_widget = QtGui.QWidget(self)
        self.main_widget.setMinimumSize(QtCore.QSize(100, 100))
        self.label = QtGui.QLabel()
        self.buttonBox = QtGui.QDialogButtonBox(self.main_widget)
        self.buttonBox.setStandardButtons(QtGui.QDialogButtonBox.Ok)
        QObject.connect(self.buttonBox, SIGNAL("accepted()"), self.Apply)
        #Access the Layout of the MessageBox to add the Checkbox
        self.container = QtGui.QVBoxLayout(self.main_widget)
        self.container.addWidget(self.label)
        self.container.addWidget(self.buttonBox)
        self.container.setAlignment(QtCore.Qt.AlignCenter)
        self.container.setSizeConstraint(QtGui.QLayout.SetFixedSize)
        self.setLayout(self.container)

    def Apply(self):
        self.close()

class QgsStueMarker(QgsVertexMarker):
    def __init__(self, canvas):
        QgsVertexMarker.__init__(self, canvas)
        self.setColor(QtGui.QColor(1, 1, 213))
        self.setIconType(QgsVertexMarker.ICON_BOX)
        self.setIconSize(11)
        self.setPenWidth(3)


class QgsMovingCross(QgsVertexMarker):
    def __init__(self, canvas):
        QgsVertexMarker.__init__(self, canvas)
        self.setColor(QtGui.QColor(27, 25, 255))
        self.setIconType(QgsVertexMarker.ICON_CROSS)
        self.setIconSize(20)
        self.setPenWidth(3)


class DialogOutputOptions(QtGui.QDialog):
    def __init__(self, interface, toolWindow):
        QtGui.QDialog.__init__(self, interface.mainWindow())
        self.iface = interface
        self.tool = toolWindow
        self.setWindowTitle(u"Output Optionen")
        self.main_widget = QtGui.QWidget(self)

        self.hbox = QtGui.QHBoxLayout()
        self.saveLabel = QtGui.QLabel(u"Speicherpfad")
        self.pathField = QtGui.QComboBox()
        self.pathField.setMinimumWidth(400)
        self.pathField.setSizePolicy(
            QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding,
                              QtGui.QSizePolicy.Fixed))
        self.openButton = QtGui.QPushButton()
        self.openButton.setMaximumSize(QtCore.QSize(27, 27))
        icon = QtGui.QIcon()
        # TODO: Hardcoded Pfad anpassen wenn richtiger Name steht
        icon.addPixmap(QtGui.QPixmap(":/plugins/SeilaplanPlugin/icons/icon_open.png"),
                       QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.openButton.setIcon(icon)
        self.openButton.setIconSize(QtCore.QSize(24, 24))
        QObject.connect(self.openButton, SIGNAL("clicked()"), self.onOpenDialog)

        self.hbox.addWidget(self.saveLabel)
        self.hbox.addWidget(self.pathField)
        self.hbox.addWidget(self.openButton)
        # Checkboxen erzeugen
        self.questionLabel = QtGui.QLabel(u"Welche Produkte sollen erzeugt werden?")
        self.checkBoxReport = QtGui.QCheckBox(u"Technischer Bericht")
        self.checkBoxPlot = QtGui.QCheckBox(u"Diagramm")
        self.checkBoxGeodata = QtGui.QCheckBox(u"Shape-Daten der Stützen und Seillinie")
        self.checkBoxCoords = QtGui.QCheckBox(u"Koordinaten-Tabellen der Stützen und Seillinie")
        # Hacken richtig setzten
        self.checkBoxReport.setChecked(self.tool.outputOpt['report'])
        self.checkBoxPlot.setChecked(self.tool.outputOpt['plot'])
        self.checkBoxGeodata.setChecked(self.tool.outputOpt['geodata'])
        self.checkBoxCoords.setChecked(self.tool.outputOpt['coords'])
        # Ok/Cancel Button erzeugen und verbinden
        self.buttonBox = QtGui.QDialogButtonBox(self.main_widget)
        self.buttonBox.setStandardButtons(QtGui.QDialogButtonBox.Ok|QtGui.QDialogButtonBox.Cancel)
        QObject.connect(self.buttonBox, SIGNAL("accepted()"), self.Apply)
        QObject.connect(self.buttonBox, SIGNAL("rejected()"), self.Reject)

        # Layout
        self.container = QtGui.QVBoxLayout(self.main_widget)
        self.container.addLayout(self.hbox)
        self.container.addWidget(QtGui.QLabel(""))
        self.container.addWidget(self.questionLabel)
        self.container.addWidget(self.checkBoxReport)
        self.container.addWidget(self.checkBoxPlot)
        self.container.addWidget(self.checkBoxGeodata)
        self.container.addWidget(self.checkBoxCoords)
        self.container.addWidget(self.buttonBox)
        self.container.setAlignment(QtCore.Qt.AlignLeft)
        # self.container.setSizeConstraint(QtGui.QLayout.SetFixedSize)
        self.setLayout(self.container)

    def fillInDropDown(self, pathList):
        for i in reversed(range(self.pathField.count())):
            self.pathField.removeItem(i)
        for path in reversed(pathList):
            self.pathField.addItem(path)

    def onOpenDialog(self):
        title = u"Output Pfad auswählen"
        directory = QtGui.QFileDialog.getExistingDirectory(self, title,
                                            self.tool.outputOpt['outputPath'])
        self.tool.updateCommonPathList(directory)
        self.fillInDropDown(self.tool.commonPaths)

    def Apply(self):
        # Wert der Checkboxen in Variable outputOpt speichern
        self.tool.outputOpt['outputPath'] = self.pathField.currentText()
        self.tool.outputOpt['report'] = int(self.checkBoxReport.isChecked())
        self.tool.outputOpt['plot'] = int(self.checkBoxPlot.isChecked())
        self.tool.outputOpt['geodata'] = int(self.checkBoxGeodata.isChecked())
        self.tool.outputOpt['coords'] = int(self.checkBoxCoords.isChecked())

        # Liste der verwendeten Pfade wird aktualisiert und gewählter Pfad an
        #   erste Stelle gesetzt
        self.tool.updateCommonPathList(self.pathField.currentText())
        self.close()

    def Reject(self):
        self.close()

def readFromTxt(path):
    """ Generische Methode, die eine txt-Datei öffnet, den Inhalt sammt
    Header ausliest und in ein Dicitonary speichert. Das Dictionary
    besteht wiederum aus Dictionaries welche die verschiedenen Spalten
    als Key besitzen."""
    fileData = {}
    if os.path.exists(path):
        with io.open(path, encoding='utf-8') as f:
            lines = f.read().splitlines()
            # Header sollten im ascii Format sein, nicht utf-8
            header = lines[0].encode('ascii').split('\t')
            for line in lines[1:]:
                if line == '': break
                line = line.split('\t')
                row = {}
                for i in range(1, len(header)):
                    row[header[i]] = line[i]
                # Keys der Dicitionaries sollten im ascii Format sein
                key = line[0].encode('ascii')
                fileData[key] = row
        return fileData, header
    else:
        return False, False


def strToNum(coord):
    """ String in Nummer verwandeln.
    """
    try:
        num = int(coord.replace("'", ''))
    except ValueError:
        num = ''
    return num


def generateName():
    """ Projektname generieren.
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
    """ Koordinate ein 1000er-Strich und wenn nötig Millionen-Strich
    hinzufügen.
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
            cval = val.encode('utf-8')
            # result = True
        elif dtype == 'float':
            cval = float(val)
        else:
            cval = int(val)
    except ValueError:
        cval = None
        errState = True
    return cval, errState