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

from qgis.PyQt.QtCore import QSize, Qt
from qgis.PyQt.QtWidgets import QDialog, QWidget, QLabel, QDialogButtonBox, \
    QHBoxLayout, QComboBox, QSizePolicy, QPushButton, QCheckBox, \
    QVBoxLayout, QFileDialog, QLineEdit, QMessageBox
from qgis.PyQt.QtGui import QIcon, QPixmap


class DialogSaveParamset(QDialog):
    def __init__(self, interface, toolWindow):
        """Small window to define the name of the saved parmeter set."""
        QDialog.__init__(self, interface.mainWindow())
        self.iface = interface
        self.tool = toolWindow
        self.paramData = None
        self.availableParams = None
        self.savePath = None
        self.setname = None
        self.setWindowTitle("Name Parameterset")
        main_widget = QWidget(self)
        
        # Build gui
        hbox = QHBoxLayout()
        setnameLabel = QLabel("Dateiname des Parametersets")
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
        container.addWidget(buttonBox)
        container.setAlignment(Qt.AlignLeft)
        self.setLayout(container)
    
    def setData(self, availableParams, savePath):
        self.availableParams = availableParams
        self.savePath = savePath
    
    def getNewSetname(self):
        return
    
    def checkName(self, setname):
        if setname in self.availableParams:
            return False
        
        savePath = os.path.join(self.savePath, f'{setname}.txt')
        try:
            open(savePath, 'w')
            return True
        except IOError:
            return False
    
    def Apply(self):
        setname = self.setnameField.text()
        valid = self.checkName(setname)
        if not valid:
            QMessageBox.information(self, 'Fehler', "Bitte geben Sie einen "
                                    "gültigen Dateinamen für das Parameterset an",
                                    QMessageBox.Ok)
            return
        self.setname = setname
        self.close()
    
    def Reject(self):
        self.setnameField.setText('')
        self.close()


class DialogOutputOptions(QDialog):
    def __init__(self, interface, toolWindow, confHandler):
        """
        :type confHandler: configHandler.ConfigHandler
        """
        QDialog.__init__(self, interface.mainWindow())
        self.iface = interface
        self.tool = toolWindow
        self.confHandler = confHandler
        
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
        iconPath = os.path.join(os.path.dirname(__file__),
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
        self.checkBoxReport.setChecked(self.confHandler.outputOptions['report'])
        self.checkBoxPlot.setChecked(self.confHandler.outputOptions['plot'])
        self.checkBoxGeodata.setChecked(self.confHandler.outputOptions['geodata'])
        self.checkBoxCoords.setChecked(self.confHandler.outputOptions['coords'])
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
        QFileDialog.getExistingDirectory(self, title,
                                         self.confHandler.outputOptions['outputPath'])
        self.fillInDropDown(self.confHandler.commonPaths)
    
    def Apply(self):
        # Save checkbox status
        options = {
            'outputPath': self.pathField.currentText(),
            'report': int(self.checkBoxReport.isChecked()),
            'plot': int(self.checkBoxPlot.isChecked()),
            'geodata': int(self.checkBoxGeodata.isChecked()),
            'coords': int(self.checkBoxCoords.isChecked())
        }
        # Update output settings
        self.confHandler.setOutputOptions(options)
        # Update output location with currently selected path
        self.confHandler.addPath(self.pathField.currentText())
        self.close()
    
    def Reject(self):
        self.close()



