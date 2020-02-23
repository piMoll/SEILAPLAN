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

    def __init__(self, iface):
        QDialog.__init__(self, iface.mainWindow())
        self.workerThread = None
        self.state = False
        self.resultStatus = None
        self.doReRun = False
        self.wasCanceled = False
        self.wasSuccessful = False
        self.savedProj = None
        self.result = None
        
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
            QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding))
        self.resultLabel.setWordWrap(True)
        spacer1 = QSpacerItem(20, 20, QSizePolicy.Fixed,
                              QSizePolicy.Fixed)
        self.rerunButton = QPushButton(self.tr("zurueck zum Startfenster"))
        self.rerunButton.setVisible(False)
        spacer2 = QSpacerItem(40, 20, QSizePolicy.Expanding,
                             QSizePolicy.Minimum)
        self.cancelButton.setStandardButtons(QDialogButtonBox.Cancel)
        self.cancelButton.clicked.connect(self.onAbort)
        self.closeButton.setStandardButtons(QDialogButtonBox.Close)
        self.closeButton.clicked.connect(self.onClose)
        self.hbox.addWidget(self.rerunButton)
        self.hbox.addItem(spacer2)
        self.hbox.addWidget(self.cancelButton)
        self.hbox.setAlignment(self.cancelButton, Qt.AlignHCenter)
        self.hbox.addWidget(self.closeButton)
        self.hbox.setAlignment(self.closeButton, Qt.AlignHCenter)
        self.closeButton.hide()
        
        self.container.addWidget(self.progressBar)
        self.container.addWidget(self.statusLabel)
        self.container.addWidget(self.resultLabel)
        self.container.addItem(spacer1)
        self.container.addLayout(self.hbox)
        self.container.setSizeConstraint(QLayout.SetFixedSize)
        self.setLayout(self.container)

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
        self.workerThread.sig_result.connect(self.resultFromThread)
        self.rerunButton.clicked.connect(self.onRerun)
        
    def run(self):
        # Show modal dialog window (QGIS is still responsive)
        self.show()
        # start event loop
        self.exec()
    
    def jobEnded(self, success):
        self.setWindowTitle("SEILAPLAN")
        if success:
            self.progressBar.setValue(self.progressBar.maximum())
            self.wasSuccessful = True
            # Close progress dialog so that adjustment window can be opened
            self.close()
        else:  # If there was an abort by the user
            self.statusLabel.setText(self.tr("Berechnungen abgebrochen."))
            self.progressBar.setValue(self.progressBar.minimum())
            self.finallyDo()
    
    def valueFromThread(self, value):
        self.progressBar.setValue(value)
    
    def rangeFromThread(self, range_vals):
        self.progressBar.setRange(range_vals[0], range_vals[1])
    
    def maxFromThread(self, max):
        self.progressBar.setValue(self.progressBar.maximum())
    
    def textFromThread(self, value):
        self.statusLabel.setText(value)
    
    def resultFromThread(self, resultStatus):
        self.resultStatus = resultStatus
        # resultStatus:
        #   1 = Optimization successful
        #   2 = Cable takes off from support
        #   3 = Optimization partially successful
    
    def onAbort(self):
        self.setWindowTitle('SEILAPLAN')
        self.statusLabel.setText(self.tr(
            'Laufender Prozess wird abgebrochen...'))
        self.workerThread.cancel()  # Terminates process cleanly
        self.wasCanceled = True
    
    def onError(self, exception_string):
        self.setWindowTitle(self.tr('SEILAPLAN: Berechnung fehlgeschlagen'))
        self.statusLabel.setText(self.tr('Ein Fehler ist aufgetreten:'))
        self.resultLabel.setText(textwrap.fill(exception_string, 60)
                                 .replace('\n', '<br>'))
        self.resultLabel.setHidden(False)
        self.progressBar.setValue(self.progressBar.minimum())
        self.setLayout(self.container)
        self.finallyDo()
    
    def onRerun(self):
        self.doReRun = True
        self.onClose()
    
    def finallyDo(self):
        self.rerunButton.setVisible(True)
        self.cancelButton.hide()
        self.closeButton.show()
    
    def onClose(self):
        self.close()
