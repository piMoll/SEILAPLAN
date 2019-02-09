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

import sys
import subprocess

from qgis.PyQt.QtCore import Qt, pyqtSignal
from qgis.PyQt.QtWidgets import QDialog, QVBoxLayout, QProgressBar, QLabel, \
    QHBoxLayout, QDialogButtonBox, QSizePolicy, QPushButton, QSpacerItem, \
    QLayout


textOK = (
    "Die Berechnungen wurden <b>erfolgreich</b> abgeschlossen! Die Ergebnisse "
    "sind in folgendem Ordner abgespeichert:")
textSeil = ("Die Seillinie wurde berechnet, das <b>Tragseil hebt jedoch "
            "bei mindestens einer Stütze ab</b>."
            "Die Resultate sind in folgendem Ordner abgespeichert:")
textHalf = ("Die Seillinie konnte <b>nicht komplett berechnet</b> werden, es "
            "sind nicht genügend Stützenstandorte bestimmbar. Die "
            "unvollständigen Resultate sind in folgendem Ordner "
            "abgespeichert:")
textBad = (
    "Aufgrund der Geländeform oder der Eingabeparameter konnten <b>keine "
    "Stützenstandorte bestimmt</b> werden. Es wurden keine Output-Daten "
    "erzeugt.")

class ProgressDialog(QDialog):
    """ Progress dialog shows progress bar for algorithm.
    """
    
    def __init__(self, iface):
        QDialog.__init__(self, iface.mainWindow())
        
        self.workerThread = None
        self.state = False
        self.outputLoc = None
        self.resultStatus = None
        self.reRun = False
        self.savedProj = None
        
        # Build GUI Elements
        self.setWindowTitle("SEILAPLAN wird ausgeführt")
        self.resize(500, 100)
        self.container = QVBoxLayout()
        self.progressBar = QProgressBar(self)
        self.progressBar.setMinimumWidth(500)
        self.statusLabel = QLabel(self)
        self.hbox = QHBoxLayout()
        self.cancelButton = QDialogButtonBox()
        self.closeButton = QDialogButtonBox()
        self.resultLabel = ClickLabel(self)
        self.resultLabel.setMaximumWidth(500)
        self.resultLabel.setSizePolicy(
            QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding))
        self.resultLabel.setWordWrap(True)
        self.rerunButton = QPushButton("Berechnungen wiederholen")
        self.rerunButton.setVisible(False)
        spacer = QSpacerItem(40, 20, QSizePolicy.Expanding,
                             QSizePolicy.Minimum)
        self.cancelButton.setStandardButtons(QDialogButtonBox.Cancel)
        self.cancelButton.clicked.connect(self.onAbort)
        self.closeButton.setStandardButtons(QDialogButtonBox.Close)
        self.closeButton.clicked.connect(self.onClose)
        self.hbox.addWidget(self.rerunButton)
        self.hbox.addItem(spacer)
        self.hbox.addWidget(self.cancelButton)
        self.hbox.setAlignment(self.cancelButton, Qt.AlignHCenter)
        self.hbox.addWidget(self.closeButton)
        self.hbox.setAlignment(self.closeButton, Qt.AlignHCenter)
        self.closeButton.hide()
        
        self.container.addWidget(self.progressBar)
        self.container.addWidget(self.statusLabel)
        self.container.addWidget(self.resultLabel)
        self.container.addLayout(self.hbox)
        self.container.setSizeConstraint(QLayout.SetFixedSize)
        self.setLayout(self.container)
        
    def setThread(self, workerThread):
        self.workerThread = workerThread
        self.connectProgressSignals()
    
    def connectProgressSignals(self):
        # Connet signals of thread
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
        self.exec_()
    
    def jobEnded(self, success):
        self.setWindowTitle("SEILAPLAN")
        if success:
            self.statusLabel.setText("Berechnungen abgeschlossen.")
            self.progressBar.setValue(self.progressBar.maximum())
            self.setFinalMessage()
        
        else:  # If there was an abort by the user
            self.statusLabel.setText("Berechnungen abgebrochen.")
            self.progressBar.setValue(self.progressBar.minimum())
        self.finallyDo()
        self.rerunButton.setVisible(True)
    
    def valueFromThread(self, value):
        self.progressBar.setValue(value)
    
    def rangeFromThread(self, range_vals):
        self.progressBar.setRange(range_vals[0], range_vals[1])
    
    def maxFromThread(self, max):
        self.progressBar.setValue(self.progressBar.maximum())
    
    def textFromThread(self, value):
        self.statusLabel.setText(value)
    
    def resultFromThread(self, result):
        [self.outputLoc, self.resultStatus] = result
    
    def setFinalMessage(self):
        self.resultLabel.clicked.connect(self.onResultClicked)
        self.resultLabel.blockSignals(True)
        linkToFolder = ('<html><head/><body><p></p><p><a href='
                        '"file:////{0}"><span style="text-decoration: '
                        'underline; color:#0000ff;">{0}</span></a></p>'
                        '</body></html>'.format(self.outputLoc))
        # Optimization successful
        if self.resultStatus == 1:
            self.resultLabel.setText(textOK + linkToFolder)
            self.resultLabel.blockSignals(False)
        # Cable takes off of support
        elif self.resultStatus == 2:
            self.resultLabel.setText(textSeil + linkToFolder)
            self.resultLabel.blockSignals(False)
        # Optimization partially successful
        elif self.resultStatus == 3:
            self.resultLabel.setText(textHalf + linkToFolder)
            self.resultLabel.blockSignals(False)
        # Optimization not successful
        elif self.resultStatus == 4:
            self.resultLabel.setText(textBad)
        self.setLayout(self.container)
    
    def onResultClicked(self):
        # Open a folder window
        if sys.platform == 'darwin':  # MAC
            subprocess.call(["open", "-R", self.outputLoc])
        elif sys.platform.startswith('linux'):  # LINUX
            subprocess.Popen(["xdg-open", self.outputLoc])
        elif 'win32' in sys.platform:  # WINDOWS
            from subprocess import CalledProcessError
            try:
                subprocess.check_call(['explorer', self.outputLoc])
            except CalledProcessError:
                pass
    
    def onAbort(self):
        self.setWindowTitle("SEILAPLAN")
        self.statusLabel.setText("Laufender Prozess wird abgebrochen...")
        self.workerThread.cancel()  # Terminates process cleanly
    
    def onError(self, exception_string):
        self.setWindowTitle("SEILAPLAN: Berechnung fehlgeschlagen")
        self.statusLabel.setText("Ein Fehler ist aufgetreten:")
        self.resultLabel.setText(exception_string)
        self.progressBar.setValue(self.progressBar.minimum())
        self.finallyDo()
    
    def onRerun(self):
        self.reRun = True
        self.onClose()
    
    def finallyDo(self):
        self.cancelButton.hide()
        self.closeButton.show()
    
    def onClose(self):
        self.close()


class ClickLabel(QLabel):
    clicked = pyqtSignal()
    
    def mousePressEvent(self, event):
        self.clicked.emit()
        QLabel.mousePressEvent(self, event)
