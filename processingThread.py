# -*- coding: utf-8 -*-
"""
/***************************************************************************
 SeilaplanPlugin
                                 A QGIS plugin
 Seilkran-Layoutplaner
                              -------------------
        begin                : 2013
        copyright            : (C) 2015 by ETH Zürich
        email                : pi1402@gmail.com
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
import sys
import subprocess

from qgis.PyQt.QtCore import Qt, QThread, pyqtSignal
from qgis.PyQt.QtWidgets import QDialog, QVBoxLayout, QProgressBar, QLabel, \
    QHBoxLayout, QDialogButtonBox, QSizePolicy, QPushButton, QSpacerItem, \
    QLayout

# Import Tool Scripts
from .tool.mainSeilaplan import main
from .tool.outputReport import getTimestamp, plotData, generateReportText, \
    generateReport, createOutputFolder
from .tool.outputGeo import generateGeodata, addToMap, generateCoordTable


textOK = ("Die Berechnungen wurden <b>erfolgreich</b> abgeschlossen! Die Ergebnisse "
          "sind in folgendem Ordner abgespeichert:")
textSeil = ("Die Seillinie wurde berechnet, das <b>Tragseil hebt jedoch "
            "bei mindestens einer Stütze ab</b>."
            "Die Resultate sind in folgendem Ordner abgespeichert:")
textHalf = ("Die Seillinie konnte <b>nicht komplett berechnet</b> werden, es "
            "sind nicht genügend Stützenstandorte bestimmbar. Die "
            "unvollständigen Resultate sind in folgendem Ordner "
            "abgespeichert:")
textBad = ("Aufgrund der Geländeform oder der Eingabeparameter konnten <b>keine "
           "Stützenstandorte bestimmt</b> werden. Es wurden keine Output-Daten "
           "erzeugt.")

class MultithreadingControl(QDialog):
    """ Calculation and progress dialog window is handled in separate thread
    so that QGIS is still responsive. User parameters are send to method
    setValue.
    """
    def __init__( self, iface):
        QDialog.__init__(self, iface.mainWindow())
        # import pydevd
        # pydevd.settrace('localhost', port=53100,
        #              stdoutToServer=True, stderrToServer=True)
        self.iface = iface
        self.input = None
        self.state = False
        self.projInfo = None
        self.outputLoc = None
        self.resultStatus = None
        self.reRun = False
        self.savedProj = None
        self.workerThread = None

        self.setWindowTitle("SEILAPLAN wird ausgeführt")
        self.resize(500, 100)
        self.container = QVBoxLayout()
        self.progressBar = QProgressBar(self)
        self.progressBar.setMinimumWidth(500)
        self.statusLabel = QLabel(self)
        self.hbox = QHBoxLayout()
        self.cancelButton = QDialogButtonBox()
        # TODO: QLabel mit clicked Methode funktioniert nur für Ubuntu
        # self.resultLabel = QLabel(self)
        self.resultLabel = ExtendedQLabel(self)
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
        self.hbox.addWidget(self.rerunButton)
        self.hbox.addItem(spacer)
        self.hbox.addWidget(self.cancelButton)
        self.hbox.setAlignment(self.cancelButton, Qt.AlignHCenter)

        self.container.addWidget(self.progressBar)
        self.container.addWidget(self.statusLabel)
        self.container.addWidget(self.resultLabel)
        self.container.addLayout(self.hbox)
        self.container.setSizeConstraint(QLayout.SetFixedSize)
        self.setLayout(self.container)

    def setValue(self, toolData, projInfo):
        self.projInfo = projInfo
        self.input = [toolData, projInfo]

    def getValue(self):
        return self.input

    def setState(self, st):
        self.state = st

    def getState(self):
        return self.state

    def run(self):
        self.runThread()
        # Show modal dialog window (QGIS is still responsive)
        self.show()
        # start event loop
        self.exec_()

    def runThread( self):
        # Connet signals of thread
        self.workerThread.sig_jobEnded.connect(self.jobEnded)
        self.workerThread.sig_value.connect(self.valueFromThread)
        self.workerThread.sig_range.connect(self.rangeFromThread)
        # self.workerThread.sig_max.connect(self.maxFromThread)
        self.workerThread.sig_text.connect(self.textFromThread)
        self.workerThread.sig_result.connect(self.resultFromThread)
        # self.workerThread.sig_abort.connect(self.onAbort)
        # self.workerThread.sig_error.connect(self.onError)
        self.rerunButton.clicked.connect(self.onRerun)

        # Start thread
        self.workerThread.run()

    def jobEnded(self, success):
        if success:
            self.statusLabel.setText("Berechnungen abgeschlossen.")
            self.progressBar.setValue(self.progressBar.maximum())
            self.setFinalMessage()

        else:           # If there was an abort by the user
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
        # TODO: resultLabel can not be connected
        self.resultLabel.clicked.connect(self.onResultClicked)
        self.resultLabel.blockSignals(True)
        linkToFolder = ('<html><head/><body><p></p><p><a href='
                        '"file:////{0}"><span style="text-decoration: '
                        'underline; color:#0000ff;">{0}</span></a></p>'
                        '</body></html>'.format(self.outputLoc))
        # Optimization successful
        if self.resultStatus == 1:
            self.resultLabel.setText(textOK+linkToFolder)
            self.resultLabel.blockSignals(False)
        # Cable takes off from support
        elif self.resultStatus == 2:
            self.resultLabel.setText(textSeil+linkToFolder)
            self.resultLabel.blockSignals(False)
        # Optimization partially successful
        elif self.resultStatus == 3:
            self.resultLabel.setText(textHalf+linkToFolder)
            self.resultLabel.blockSignals(False)
        # Optimization not successful
        elif self.resultStatus == 4:
            self.resultLabel.setText(textBad)
        self.setLayout(self.container)


    def onResultClicked(self):
        path = self.outputLoc
        # Open a folder window
        if sys.platform == 'darwin':        # MAC
            subprocess.call(["open", "-R", path])
        elif sys.platform == 'linux2':      # LINUX
            subprocess.Popen(["xdg-open", path])
        elif sys.platform == 'win32':       # WINDOWS
            from subprocess import CalledProcessError
            try:
                subprocess.check_call(['explorer', path])
            except CalledProcessError:
                pass

    def onAbort(self):
        self.statusLabel.setText("Laufender Prozess wird abgebrochen...")
        self.cancelThread()

    def cancelThread(self):
        """Manual abort by user.
        """
        self.workerThread.stop()        # Terminates process cleanly

    def onError(self, exception_string):
        self.statusLabel.setText("Ein unerwarteter Fehler ist aufgetreten.")
        self.progressBar.setValue(self.progressBar.minimum())
        self.finallyDo()

    def onRerun(self):
        self.reRun = True
        self.savedProj = self.workerThread.projInfo['projFile']
        self.onClose()

    def finallyDo(self):
        self.cancelButton.setStandardButtons(QDialogButtonBox.Close)
        self.cancelButton.clicked.connect(self.onClose)

    def cleanUp(self):
        # TODO probably not necessary
        self.input = None
        self.state = False
        self.projInfo = None
        self.outputLoc = None
        self.resultStatus = None
        self.resultLabel.setText(u'')
        self.progressBar.setValue(self.progressBar.minimum())
        self.cancelButton.setStandardButtons(QDialogButtonBox.Cancel)
        self.cancelButton.clicked.connect(self.onAbort)

    def onClose(self):
        # self.cleanUp()
        self.close()

class ExtendedQLabel(QLabel):
    """ Customized label class which sends a signal when label is clicked.
    """
    def __init(self, parent):
        QLabel.__init__(self, parent)

    def mouseReleaseEvent(self, ev):
        self.clicked.emit()


class WorkerThread(QThread):
    
    # Signals
    sig_jobEnded = pyqtSignal(bool)
    sig_value = pyqtSignal(float)
    sig_range = pyqtSignal(list)
    # sig_max = pyqtSignal()
    sig_text = pyqtSignal(str)
    sig_result = pyqtSignal(list)
    sig_abort = pyqtSignal()
    sig_error = pyqtSignal()
    
    
    def __init__(self, parentThread):
        QThread.__init__(self, parentThread)
        self.iface = None
        self.userInput = None
        self.outputLoc = None
        self.resultStatus = None
        self.success = True

    def run(self):
        self.running = True
        self.doWork()
        self.sig_jobEnded.emit(self.success)

    def stop(self):
        """Manual abort by user.
        """
        self.running = False

    def doWork(self):
        self.sig_text.emit("Berechnungen werden gestartet...")
        [self.inputData, self.projInfo] = self.userInput

        # import pickle
        # self.userInput[1]['Hoehenmodell'].pop('layer')
        # homePath = os.path.dirname(__file__)
        # storefile = os.path.join(homePath, 'backups+testFiles', 'testYSP.pckl')
        # f = open(storefile, 'wb')
        # pickle.dump([self.userInput], f)
        # f.close()

        # Start algorithm
        output = main(self, self.inputData, self.projInfo)
        if not output:      # If abort by user or error in code
            self.success = False
            return
        else:
            [self.result, self.resultStatus] = output
        # Output resultStatus
        #   1 = Optimization successful
        #   2 = Cable takes off from support
        #   3 = Optimization partially successful
        #   4 = Optimization not successful
        if self.resultStatus == 4:
            self.sig_result.emit([None, self.resultStatus])
            return
        # Unpack results
        [t_start, disp_data, seilDaten, gp, HM,
         IS, kraft, optSTA, optiLen] = self.result

        # import pickle
        # self.projInfo['Hoehenmodell'].pop('layer')
        # homePath = os.path.dirname(__file__)
        # storefile = os.path.join(homePath, 'backups+testFiles', 'ohneHoeheimPlot.pckl')
        # f = open(storefile, 'w')
        # pickle.dump([output, self.userInput], f)
        # f.close()

        self.sig_value.emit(optiLen*1.01)
        self.sig_text.emit("Outputdaten werden generiert...")

        # Generate output
        ###################
        outputFolder = self.projInfo['outputOpt']['outputPath']
        outputName = self.projInfo['Projektname']
        self.outputLoc = createOutputFolder(outputFolder, outputName)
        # Move saved project file to output folder
        if os.path.exists(self.projInfo['projFile']):
            newpath = os.path.join(self.outputLoc,
                        os.path.basename(self.projInfo['projFile']))
            os.rename(self.projInfo['projFile'], newpath)
            self.projInfo['projFile'] = newpath
        # Generate plot
        plotSavePath = os.path.join(self.outputLoc, "{}_Diagramm.pdf".format(outputName))
        plotImage, labelTxt = plotData(disp_data, gp["di"], seilDaten, HM,
                                       self.inputData, self.projInfo,
                                       self.resultStatus, plotSavePath)
        self.sig_value.emit(optiLen*1.015)
        # Calculate duration and generate time stamp
        duration, timestamp1, timestamp2 = getTimestamp(t_start)

        # Create report
        if self.projInfo['outputOpt']['report']:
            reportSavePath = os.path.join(self.outputLoc,
                                          "{}_Bericht.pdf".format(outputName))
            reportText = generateReportText(IS, self.projInfo, HM,
                                            kraft, optSTA, duration,
                                            timestamp2, labelTxt)
            generateReport(reportText, reportSavePath, outputName)

        # Create plot
        if not self.projInfo['outputOpt']['plot']:
            # was already created before and gets deleted if not used
            if os.path.exists(plotImage):
                os.remove(plotImage)

        # Generate geo data
        if self.projInfo['outputOpt']['geodata']:
            geodata = generateGeodata(self.projInfo, HM, seilDaten,
                                      labelTxt[0], self.outputLoc)
            addToMap(self.iface, geodata, outputName)

        # Generate coordinate tables
        if self.projInfo['outputOpt']['coords']:
            table1SavePath = os.path.join(self.outputLoc,
                                          outputName + '_KoordStuetzen.csv')
            table2SavePath = os.path.join(self.outputLoc,
                                          outputName + '_KoordSeil.csv')
            generateCoordTable(seilDaten, gp["zi"], HM,
                               [table1SavePath, table2SavePath], labelTxt[0])

        self.sig_result.emit([self.outputLoc, self.resultStatus])
