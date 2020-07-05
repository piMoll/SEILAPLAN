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

from qgis.PyQt.QtCore import QSize, Qt, QCoreApplication
from qgis.PyQt.QtWidgets import QDialog, QWidget, QLabel, QDialogButtonBox, \
    QHBoxLayout, QComboBox, QSizePolicy, QPushButton, QCheckBox, \
    QVBoxLayout, QFileDialog, QLineEdit, QMessageBox
from qgis.PyQt.QtGui import QIcon, QPixmap
from .guiHelperFunctions import validateFilename


class DialogSaveParamset(QDialog):
    def __init__(self, parent):
        """Small window to define the name of the saved parmeter set."""
        QDialog.__init__(self, parent)
        self.paramData = None
        self.availableSets = None
        self.savePath = None
        self.setname = None
        self.setWindowTitle(self.tr('Name Parameterset'))
        main_widget = QWidget(self)
        
        # Build gui
        hbox = QHBoxLayout()
        setnameLabel = QLabel(self.tr('Bezeichnung Parameterset'))
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
        buttonBox.button(QDialogButtonBox.Ok).setText(self.tr("OK"))
        buttonBox.button(QDialogButtonBox.Cancel).setText(self.tr("Abbrechen"))
        buttonBox.accepted.connect(self.apply)
        buttonBox.rejected.connect(self.onCancel)
        
        # Layout
        container = QVBoxLayout(main_widget)
        container.addLayout(hbox)
        container.addWidget(buttonBox)
        container.setAlignment(Qt.AlignLeft)
        self.setLayout(container)

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
    
    def setData(self, availableSets, savePath):
        self.availableSets = availableSets
        self.savePath = savePath
    
    def getNewSetname(self):
        return self.setname
    
    def checkName(self, setname):
        if setname in self.availableSets:
            return False
        fileName = validateFilename(setname)
        savePath = os.path.join(self.savePath, f'{fileName}.txt')
        if not os.access(savePath, os.W_OK):
            try:
                open(savePath, 'w').close()
                os.unlink(savePath)
            except IOError:
                return False
        return True
    
    def apply(self):
        setname = self.setnameField.text()
        valid = self.checkName(setname)
        if not valid:
            QMessageBox.information(self, self.tr('Fehler'),
                self.tr('Bitte geben Sie einen gueltigen Dateinamen fuer das '
                        'Parameterset an'), QMessageBox.Ok)
            return
        self.setname = setname
        self.close()
    
    def onCancel(self):
        self.setnameField.setText('')
        self.close()


class DialogOutputOptions(QDialog):
    def __init__(self, parent, confHandler):
        """
        :type confHandler: configHandler.ConfigHandler
        """
        QDialog.__init__(self, parent)
        self.confHandler = confHandler
        self.doSave = False
        
        self.setWindowTitle(self.tr('Output Optionen'))
        main_widget = QWidget(self)
        
        # Build up gui
        
        # Project title
        hbox1 = QHBoxLayout()
        projectNameLabel = QLabel(self.tr('Projektname'))
        projectNameLabel.setMinimumWidth(100)
        self.projectField = QLineEdit()
        self.projectField.setMinimumWidth(400)
        self.projectField.setSizePolicy(
            QSizePolicy(QSizePolicy.Expanding,
                        QSizePolicy.Fixed))
        hbox1.addWidget(projectNameLabel)
        hbox1.addWidget(self.projectField)
        
        # Save path
        hbox2 = QHBoxLayout()
        saveLabel = QLabel(self.tr('Speicherpfad'))
        saveLabel.setMinimumWidth(100)
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
        
        hbox2.addWidget(saveLabel)
        hbox2.addWidget(self.pathField)
        hbox2.addWidget(openButton)
        # Create checkboxes
        questionLabel = QLabel(self.tr('Welche Produkte sollen erzeugt werden?'))
        self.checkBoxShortReport = QCheckBox(self.tr('Kurzbericht'))
        self.checkBoxReport = QCheckBox(self.tr('Technischer Bericht'))
        self.checkBoxPlot = QCheckBox(self.tr('Diagramm'))
        self.checkBoxGeodata = QCheckBox(self.tr('Shape-Daten der Stuetzen und Seillinie'))
        self.checkBoxKML = QCheckBox(self.tr('KML-Daten der Stuetzen und Seillinie'))
        self.checkBoxCoords = QCheckBox(self.tr('Koordinaten-Tabellen der Stuetzen und Seillinie'))
        
        # Set tick correctly
        self.checkBoxShortReport.setChecked(self.confHandler.outputOptions['shortReport'])
        self.checkBoxReport.setChecked(self.confHandler.outputOptions['report'])
        self.checkBoxPlot.setChecked(self.confHandler.outputOptions['plot'])
        self.checkBoxGeodata.setChecked(self.confHandler.outputOptions['geodata'])
        self.checkBoxKML.setChecked(self.confHandler.outputOptions['kml'])
        self.checkBoxCoords.setChecked(self.confHandler.outputOptions['coords'])
        # Create Ok/Cancel Button and connect signal
        buttonBox = QDialogButtonBox(main_widget)
        buttonBox.setStandardButtons(QDialogButtonBox.Save |
                                     QDialogButtonBox.Cancel)
        buttonBox.button(QDialogButtonBox.Save).setText(self.tr("Speichern"))
        buttonBox.button(QDialogButtonBox.Cancel).setText(self.tr("Abbrechen"))
        buttonBox.button(QDialogButtonBox.Cancel).clicked.connect(self.onCancel)
        buttonBox.button(QDialogButtonBox.Save).clicked.connect(self.onSave)
        # Layout
        container = QVBoxLayout(main_widget)
        container.addLayout(hbox1)
        container.addLayout(hbox2)
        container.addWidget(QLabel(''))
        container.addWidget(questionLabel)
        container.addWidget(self.checkBoxShortReport)
        container.addWidget(self.checkBoxReport)
        container.addWidget(self.checkBoxPlot)
        container.addWidget(self.checkBoxGeodata)
        container.addWidget(self.checkBoxKML)
        container.addWidget(self.checkBoxCoords)
        container.addWidget(buttonBox)
        container.setAlignment(Qt.AlignLeft)
        self.setLayout(container)

        self.fillInData()

    # noinspection PyMethodMayBeStati
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

    def fillInData(self):
        # Project name
        self.projectField.setText(self.confHandler.project.getProjectName())
        
        # Dropdown Paths
        for i in reversed(range(self.pathField.count())):
            self.pathField.removeItem(i)
        for path in reversed(self.confHandler.commonPaths):
            self.pathField.addItem(path)
    
    def onOpenDialog(self):
        title = self.tr('Output Ordner auswaehlen')
        folder = QFileDialog.getExistingDirectory(self, title,
            self.confHandler.getCurrentPath(), QFileDialog.ShowDirsOnly)
        if folder:
            self.pathField.insertItem(0, folder)
            self.pathField.setCurrentIndex(0)
    
    def onSave(self):
        # Save checkbox status
        options = {
            'report': int(self.checkBoxReport.isChecked()),
            'plot': int(self.checkBoxPlot.isChecked()),
            'geodata': int(self.checkBoxGeodata.isChecked()),
            'coords': int(self.checkBoxCoords.isChecked()),
            'shortReport': int(self.checkBoxShortReport.isChecked()),
            'kml': int(self.checkBoxKML.isChecked()),
        }
        # Update project name
        self.confHandler.project.setProjectName(self.projectField.text())
        # Update output settings
        self.confHandler.setOutputOptions(options)
        # Update output location with currently selected path
        self.confHandler.addPath(self.pathField.currentText())
        self.doSave = True
        self.close()
    
    def onCancel(self):
        self.doSave = False
        self.close()
