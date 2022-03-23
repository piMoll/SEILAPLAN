# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'gui/surveyImportDialog.ui'
#
# Created by: PyQt5 UI code generator 5.14.1
#
# WARNING! All changes made in this file will be lost!


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_SurveyImportDialogUI(object):
    def setupUi(self, SurveyImportDialogUI):
        SurveyImportDialogUI.setObjectName("SurveyImportDialogUI")
        SurveyImportDialogUI.resize(551, 223)
        self.verticalLayout = QtWidgets.QVBoxLayout(SurveyImportDialogUI)
        self.verticalLayout.setObjectName("verticalLayout")
        self.verticalLayout_2 = QtWidgets.QVBoxLayout()
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.groupBox = QtWidgets.QGroupBox(SurveyImportDialogUI)
        self.groupBox.setObjectName("groupBox")
        self.horizontalLayout = QtWidgets.QHBoxLayout(self.groupBox)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.gridLayout_2 = QtWidgets.QGridLayout()
        self.gridLayout_2.setObjectName("gridLayout_2")
        self.radioExcelProtocol = QtWidgets.QRadioButton(self.groupBox)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.radioExcelProtocol.sizePolicy().hasHeightForWidth())
        self.radioExcelProtocol.setSizePolicy(sizePolicy)
        self.radioExcelProtocol.setObjectName("radioExcelProtocol")
        self.gridLayout_2.addWidget(self.radioExcelProtocol, 2, 0, 1, 1)
        self.buttonTemplateExcelProtocol = QtWidgets.QPushButton(self.groupBox)
        self.buttonTemplateExcelProtocol.setObjectName("buttonTemplateExcelProtocol")
        self.gridLayout_2.addWidget(self.buttonTemplateExcelProtocol, 2, 1, 1, 1)
        self.radioCsvXyz = QtWidgets.QRadioButton(self.groupBox)
        self.radioCsvXyz.setObjectName("radioCsvXyz")
        self.gridLayout_2.addWidget(self.radioCsvXyz, 0, 0, 1, 1)
        self.buttonTemplateCsvXyz = QtWidgets.QPushButton(self.groupBox)
        self.buttonTemplateCsvXyz.setObjectName("buttonTemplateCsvXyz")
        self.gridLayout_2.addWidget(self.buttonTemplateCsvXyz, 0, 1, 1, 1)
        self.radioCsvVertex = QtWidgets.QRadioButton(self.groupBox)
        self.radioCsvVertex.setObjectName("radioCsvVertex")
        self.gridLayout_2.addWidget(self.radioCsvVertex, 1, 0, 1, 2)
        self.horizontalLayout.addLayout(self.gridLayout_2)
        self.verticalLayout_2.addWidget(self.groupBox)
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.label_3 = QtWidgets.QLabel(SurveyImportDialogUI)
        self.label_3.setObjectName("label_3")
        self.horizontalLayout_2.addWidget(self.label_3)
        self.fieldSurveyFilePath = QtWidgets.QLineEdit(SurveyImportDialogUI)
        self.fieldSurveyFilePath.setReadOnly(True)
        self.fieldSurveyFilePath.setObjectName("fieldSurveyFilePath")
        self.horizontalLayout_2.addWidget(self.fieldSurveyFilePath)
        self.buttonOpenSurvey = QtWidgets.QPushButton(SurveyImportDialogUI)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.buttonOpenSurvey.sizePolicy().hasHeightForWidth())
        self.buttonOpenSurvey.setSizePolicy(sizePolicy)
        self.buttonOpenSurvey.setMaximumSize(QtCore.QSize(27, 27))
        self.buttonOpenSurvey.setText("")
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(":/plugins/SeilaplanPlugin/gui/icons/icon_open.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.buttonOpenSurvey.setIcon(icon)
        self.buttonOpenSurvey.setIconSize(QtCore.QSize(24, 24))
        self.buttonOpenSurvey.setObjectName("buttonOpenSurvey")
        self.horizontalLayout_2.addWidget(self.buttonOpenSurvey)
        self.verticalLayout_2.addLayout(self.horizontalLayout_2)
        spacerItem = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.verticalLayout_2.addItem(spacerItem)
        self.buttonBox = QtWidgets.QDialogButtonBox(SurveyImportDialogUI)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Cancel|QtWidgets.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName("buttonBox")
        self.verticalLayout_2.addWidget(self.buttonBox)
        self.verticalLayout.addLayout(self.verticalLayout_2)

        self.retranslateUi(SurveyImportDialogUI)
        self.buttonBox.accepted.connect(SurveyImportDialogUI.accept)
        self.buttonBox.rejected.connect(SurveyImportDialogUI.reject)
        QtCore.QMetaObject.connectSlotsByName(SurveyImportDialogUI)

    def retranslateUi(self, SurveyImportDialogUI):
        _translate = QtCore.QCoreApplication.translate
        SurveyImportDialogUI.setWindowTitle(_translate("SurveyImportDialogUI", "Import Gelaendeprofil"))
        self.groupBox.setTitle(_translate("SurveyImportDialogUI", "Profiltyp auswaehlen"))
        self.radioExcelProtocol.setText(_translate("SurveyImportDialogUI", "Feldaufnahme-Protokoll (*.xlsx)"))
        self.buttonTemplateExcelProtocol.setText(_translate("SurveyImportDialogUI", "Vorlage herunterladen"))
        self.radioCsvXyz.setText(_translate("SurveyImportDialogUI", "CSV-Datei mit X, Y, Z Werten (*.csv)"))
        self.buttonTemplateCsvXyz.setText(_translate("SurveyImportDialogUI", "Vorlage herunterladen"))
        self.radioCsvVertex.setText(_translate("SurveyImportDialogUI", "Exportdatei des Hagloef Vertex Messgeraetes (*.csv)"))
        self.label_3.setText(_translate("SurveyImportDialogUI", "Datei auswaehlen"))


from . import resources_rc
