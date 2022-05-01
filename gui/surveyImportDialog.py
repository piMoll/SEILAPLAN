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
from qgis.PyQt.QtWidgets import QDialog, QFileDialog, QDialogButtonBox, QMessageBox
from .ui_surveyImportDialog import Ui_SurveyImportDialogUI
from ..tools.survey import SurveyData
from ..tools.fileFetcher import FileFetcher


class SurveyImportDialog(QDialog, Ui_SurveyImportDialogUI):
    """
    Dialog window that allows to import different types of table bases
    survey data.
    """
    
    def __init__(self, parent, confHandler):
        """
        :type confHandler: configHandler.ConfigHandler
        """
        QDialog.__init__(self, parent)
        self.confHandler = confHandler
        self.surveyType = ''
        self.filePath = ''
        self.doImport = False

        # Setup GUI (from ui_surveyImportDialog.py)
        self.setupUi(self)
        
        self.setButtonEnableState()
        self.connectGuiElements()
        
    def connectGuiElements(self):
        """Connect GUI elements with functions."""
        self.radioCsvXyz.clicked.connect(self.onSelectSurveyType)
        self.radioCsvVertex.clicked.connect(self.onSelectSurveyType)
        self.radioExcelProtocol.clicked.connect(self.onSelectSurveyType)
        
        self.buttonOpenSurvey.clicked.connect(self.onOpenFile)
        
        self.buttonTemplateCsvXyz.clicked.connect(
            lambda: self.onDownloadTemplate('csvXyz'))
        self.buttonTemplateExcelProtocol.clicked.connect(
            lambda: self.onDownloadTemplate('excelProtocol'))

        self.buttonBox.accepted.connect(self.onOk)
        self.buttonBox.rejected.connect(self.onCancel)
    
    def onSelectSurveyType(self):
        newSurveyType = None
        if self.radioCsvXyz.isChecked():
            newSurveyType = SurveyData.SOURCE_CSV_XYZ
        elif self.radioCsvVertex.isChecked():
            newSurveyType = SurveyData.SOURCE_CSV_VERTEX
        elif self.radioExcelProtocol.isChecked():
            newSurveyType = SurveyData.SOURCE_EXCEL_PROTOCOL
        
        # Reset file path if the file type is not valid anymore
        if ('CSV' in newSurveyType.upper()
                and 'CSV' not in self.surveyType.upper()) \
            or ('EXCEL' in newSurveyType.upper()
                and 'EXCEL' not in self.surveyType.upper()):
            self.filePath = ''
            self.fieldSurveyFilePath.setText(self.filePath)
        
        self.surveyType = newSurveyType
        self.setButtonEnableState()
    
    def onOpenFile(self):
        if self.surveyType in [SurveyData.SOURCE_CSV_XYZ, SurveyData.SOURCE_CSV_VERTEX]:
            fFilter = self.tr('csv Dateien (*.csv)')
        elif self.surveyType == SurveyData.SOURCE_EXCEL_PROTOCOL:
            fFilter = self.tr('Excel Dateien (*.xlsx)')
        else:
            # No survey type selected
            return
        
        title = self.tr('Gelaendeprofil laden')
        path = self.confHandler.getCurrentPath()
        filename, _ = QFileDialog.getOpenFileName(self, title, path, fFilter)
        
        if filename:
            self.filePath = filename
            self.fieldSurveyFilePath.setText(self.filePath)
        
        self.setButtonEnableState()
    
    def setButtonEnableState(self):
        if self.surveyType:
            self.buttonOpenSurvey.setEnabled(True)
            if self.filePath:
                self.buttonBox.button(QDialogButtonBox.Ok).setEnabled(True)
            else:
                self.buttonBox.button(QDialogButtonBox.Ok).setDisabled(True)
        else:
            self.buttonOpenSurvey.setDisabled(True)
            self.buttonBox.button(QDialogButtonBox.Ok).setDisabled(True)
    
    def onDownloadTemplate(self, templateName):
        title = self.tr('Vorlage speichern')
        path = self.confHandler.getCurrentPath()
        folder = QFileDialog.getExistingDirectory(self, title, path,
                                                  QFileDialog.ShowDirsOnly)
        if folder:
            templateUrl, filename = self.confHandler.getTemplateUrl(templateName)
            savepath = os.path.join(folder, filename)
            filefetcher = FileFetcher(templateUrl, savepath)

            if filefetcher.success:
                msg = self.tr('Vorlage erfolgreich heruntergeladen.')
            else:
                msg = self.tr('Download nicht erfolgreich. Link fuer manuellen Download: _templateUrl_')\
                    .replace('_templateUrl_', templateUrl)
            QMessageBox.information(self, self.tr('Download Vorlage'),
                                    msg, QMessageBox.Ok)
    
    def onOk(self):
        if self.surveyType and self.filePath:
            self.doImport = True
    
    def onCancel(self):
        self.doImport = False
    
    def closeEvent(self, QCloseEvent):
        # When user clicks 'x'
        self.doImport = False
    
