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

import textwrap
from qgis.PyQt.QtCore import Qt, QCoreApplication
from qgis.PyQt.QtWidgets import (QDialog, QVBoxLayout, QProgressBar, QLabel,
    QHBoxLayout, QDialogButtonBox, QSizePolicy, QPushButton, QSpacerItem,
    QLayout)


class ProgressDialog(QDialog):
    """ Progress dialog shows progress bar for algorithm.
    """

    def __init__(self, parent, onCloseCallback):
        
        super(ProgressDialog, self).__init__(parent)

        self.workerThread = None
        # Is called when window is closed (necessary for parallel run)
        self.onCloseCallback = onCloseCallback
        # Control variable that gets returned in callback so parent knows how
        # to proceed when this dialog is closed
        self.continueToAdjustment = None
        
        self.messageTxt = {
            'msg_optimierung': self.tr('Berechnung der optimalen Stuetzenpositionen...'),
            'msg_seillinie': self.tr('Berechnung der optimale Seillinie...')
        }
        
        # Build GUI Elements
        self.setWindowTitle(self.tr("SEILAPLAN wird ausgefuehrt"))
        self.resize(500, 100)
        self.container = QVBoxLayout()
        self.progressBar = QProgressBar(self)
        self.progressBar.setMinimumWidth(500)
        self.statusLabel = QLabel(self)
        self.hbox = QHBoxLayout()
        self.cancelButton = QDialogButtonBox()
        self.closeButton = QDialogButtonBox()
        self.resultLabel = QLabel(self)
        self.resultLabel.setMaximumWidth(500)
        self.resultLabel.setSizePolicy(
            QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding))
        self.resultLabel.setWordWrap(True)
        spacer1 = QSpacerItem(20, 20, QSizePolicy.Policy.Fixed,
                              QSizePolicy.Policy.Fixed)
        self.rerunButton = QPushButton(self.tr("zurueck zum Startfenster"))
        self.rerunButton.setVisible(False)
        spacer2 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding,
                             QSizePolicy.Policy.Minimum)
        self.cancelButton.setStandardButtons(QDialogButtonBox.StandardButton.Cancel)
        self.cancelButton.button(QDialogButtonBox.StandardButton.Cancel).setText(self.tr("Abbrechen"))
        self.cancelButton.clicked.connect(self.onAbort)
        self.closeButton.setStandardButtons(QDialogButtonBox.StandardButton.Close)
        self.closeButton.button(QDialogButtonBox.StandardButton.Close).setText(self.tr("Schliessen"))
        self.closeButton.clicked.connect(self.close)
        self.hbox.addWidget(self.rerunButton)
        self.hbox.addItem(spacer2)
        self.hbox.addWidget(self.cancelButton)
        self.hbox.setAlignment(self.cancelButton, Qt.AlignmentFlag.AlignHCenter)
        self.hbox.addWidget(self.closeButton)
        self.hbox.setAlignment(self.closeButton, Qt.AlignmentFlag.AlignHCenter)
        self.closeButton.hide()
        
        self.container.addWidget(self.progressBar)
        self.container.addWidget(self.statusLabel)
        self.container.addWidget(self.resultLabel)
        self.container.addItem(spacer1)
        self.container.addLayout(self.hbox)
        self.container.setSizeConstraint(QLayout.SizeConstraint.SetFixedSize)
        self.setLayout(self.container)

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
        return QCoreApplication.translate(type(self).__name__, message)
        
    def setThread(self, workerThread):
        self.workerThread = workerThread
        self.connectThreadSignals()
    
    def connectThreadSignals(self):
        # Connect signals of thread
        self.workerThread.sig_jobEnded.connect(self.jobEnded)
        self.workerThread.sig_jobError.connect(self.onError)
        self.workerThread.sig_value.connect(self.valueFromThread)
        self.workerThread.sig_range.connect(self.rangeFromThread)
        self.workerThread.sig_text.connect(self.textFromThread)
        self.rerunButton.clicked.connect(self.onRerun)
    
    def jobEnded(self, success):
        self.setWindowTitle("SEILAPLAN")
        if success:
            self.progressBar.setValue(self.progressBar.maximum())
            self.continueToAdjustment = True
            # Close progress dialog so that adjustment window can be opened
            self.close()
        else:  # If there was an abort by the user
            self.statusLabel.setText(self.tr("Berechnungen abgebrochen."))
            self.progressBar.setValue(self.progressBar.minimum())
            self.finallyDo()
    
    def valueFromThread(self, value):
        self.progressBar.setValue(int(value))
    
    def rangeFromThread(self, range_vals):
        self.progressBar.setRange(int(round(range_vals[0])), int(round(range_vals[1])))
    
    def maxFromThread(self, max):
        self.progressBar.setValue(self.progressBar.maximum())
    
    def textFromThread(self, message):
        self.statusLabel.setText(self.messageTxt[message])
    
    def onAbort(self):
        self.setWindowTitle('SEILAPLAN')
        self.statusLabel.setText(self.tr(
            'Laufender Prozess wird abgebrochen...'))
        self.workerThread.cancel()  # Terminates process cleanly
    
    def onError(self, exception_string):
        self.setWindowTitle(self.tr('SEILAPLAN: Berechnung fehlgeschlagen'))
        self.statusLabel.setText(self.tr('Ein Fehler ist aufgetreten:'))
        self.resultLabel.setText(self.tr(exception_string))
        self.resultLabel.setHidden(False)
        self.progressBar.setValue(self.progressBar.minimum())
        self.setLayout(self.container)
        self.finallyDo()
    
    def onRerun(self):
        self.continueToAdjustment = False
        self.close()
    
    def finallyDo(self):
        self.rerunButton.setVisible(True)
        self.cancelButton.hide()
        self.closeButton.show()
    
    def cleanUp(self, endLoop=False):
        pass
    
    def closeEvent(self, QCloseEvent):
        self.onCloseCallback(self.continueToAdjustment)
