# -*- coding: utf-8 -*-

import os
import sys
import subprocess

from PyQt4.QtCore import *
from PyQt4.QtGui import *

# Import Tool Scripts
from tool.mainSeilaplan import main
from tool.outputReport import getTimestamp, plotData, generateReportText, \
    generateReport, createOutputFolder
from tool.outputGeo import generateGeodata, addToMap, generateCoordTable

"""
Nach http://gis.stackexchange.com/questions/45514/how-do-i-maintain-a-resposive-gui-using-qthread-with-pyqgis
implementiert
"""

textOK = (u"Die Berechnungen wurden erfolgreich abgeschlossen! Die Ergebnisse "
          u"sind in folgendem Ordner abgespeichert:")
textSeil = (u"Die Seillinie wurde berechnet, das Tragseil hebt jedoch "
            u"bei mindestens einer Stütze ab. "
            u"Die Resultate sind in folgendem Ordner abgespeichert:")
textHalf = (u"Die Seillinie konnte nicht komplett berechnet werden, es "
            u"sind nicht genügend Stützenstandorte bestimmbar. Die "
            u"unvollständigen Resultate sind in folgendem Ordner "
            u"abgespeichert:")
textBad = (u"Aufgrund der Geländeform oder den Eingabeparametern konnten keine "
           u"Stützenstandorte bestimmt werden. Es wurden keine Output-Daten "
           u"erzeugen.'")

class MultithreadingControl(QDialog):
    """ Spezielle Klasse um es dem Programm zu ermöglichen, Benutzerparameter
    von der Hauptroutine zu schicken und die Berechnungen durchzuführen ohne
    dass QGIS einfrirrt.
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
        self.reportFile = None
        self.outputLoc = None
        self.resultStatus = None
        self.reRun = False
        self.savedProj = None
        self.initGui()

    def setValue(self, toolData, projInfo):
        self.projInfo = projInfo
        self.input = [toolData, projInfo]

    def getValue(self):
        return self.input

    def setState(self, st):
        self.state = st

    def getState(self):
        return self.state

    def initGui(self):
        # TODO: Name ändern
        self.setWindowTitle(u"SEILAPLAN wird ausgeführt")
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
        self.rerunButton = QPushButton(u"Berechnungen wiederholen")
        self.rerunButton.setVisible(False)
        spacer = QSpacerItem(40, 20, QSizePolicy.Expanding,
                             QSizePolicy.Minimum)
        self.cancelButton.setStandardButtons(QDialogButtonBox.Cancel)
        self.cancelButton.clicked.connect(self.onAbort)
        self.hbox.addWidget(self.rerunButton)
        self.hbox.addItem(spacer)
        self.hbox.addWidget(self.cancelButton)
        self.hbox.setAlignment(self.cancelButton, Qt.AlignHCenter)


        # hbox = QHBoxLayout()
        # hbox.addWidget(self.cancelButton, Qt.AlignHCenter)
        # hbox.setAlignment(w, Qt.AlignVCenter)

        self.container.addWidget(self.progressBar)
        self.container.addWidget(self.statusLabel)
        self.container.addWidget(self.resultLabel)
        self.container.addLayout(self.hbox)
        self.container.setSizeConstraint(QLayout.SetFixedSize)
        self.setLayout(self.container)

    def run(self):
        self.runThread()
        # Zeige Dialog im modalen Modus (QGIS ist immer noch bedienbar)
        self.show()
        # Event loop starten
        self.exec_()

    def runThread( self):
        # Signale des Threads verbinden
        QObject.connect(self.workerThread,
            SIGNAL("jobEnded(PyQt_PyObject)"), self.jobEnded)
        QObject.connect(self.workerThread,
            SIGNAL("value(PyQt_PyObject)"), self.valueFromThread)
        QObject.connect(self.workerThread,
            SIGNAL("range(PyQt_PyObject)"), self.rangeFromThread)
        QObject.connect(self.workerThread,
            SIGNAL("max(PyQt_PyObject)"), self.maxFromThread)
        QObject.connect(self.workerThread,
            SIGNAL("text(PyQt_PyObject)"), self.textFromThread)
        QObject.connect(self.workerThread,
            SIGNAL("result(PyQt_PyObject)"), self.resultFromThread)
        QObject.connect(self.workerThread,
            SIGNAL("abort(PyQt_PyObject)"), self.onAbort)
        QObject.connect(self.workerThread,
            SIGNAL("error(PyQt_PyObject)"), self.onError)
        QObject.connect(self.rerunButton,
            SIGNAL("clicked()"), self.onRerun)
        # TODO: zweimal dasselbe Signal
        # QObject.connect(self.workerThread,
        #     SIGNAL("result(PyQt_PyObject)"), self.onResultClicked)

        # Thread starten
        self.workerThread.start()

    def jobEnded(self, success):
        if success:
            self.statusLabel.setText(u"Berechnungen abgeschlossen.")
            self.progressBar.setValue(self.progressBar.maximum())
            self.setFinalMessage()

        else:           # Falls ein Abbruch durch den Nutzer erfolgt ist
            # Berechnungen wurden abgebrochen oder Fehler ist aufgetreten
            self.statusLabel.setText(u"Berechnungen abgebrochen.")
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
        [self.outputLoc, self.projFile, self.resultStatus] = result

    def setFinalMessage(self):
        # clickable(self.resultLabel).connect(self.onResultClicked)
        # QObject.connect(self.resultLabel,
        #         SIGNAL("clicked"), self.onResultClicked)
        self.connect(self.resultLabel, SIGNAL('clicked()'), self.onResultClicked)
        self.resultLabel.blockSignals(True)
        linkToFolder = (u'<html><head/><body><p></p><p><a href='
                        u'"file:////{0}"><span style="text-decoration: '
                        u'underline; color:#0000ff;">{0}</span></a></p>'
                        u'</body></html>'.format(self.outputLoc))
        # Berechnungen erfolgreich
        if self.resultStatus == 1:
            self.resultLabel.setText(textOK+linkToFolder)
            self.resultLabel.blockSignals(False)
        # Seil hebt von Stütze ab
        elif self.resultStatus == 2:
            self.resultLabel.setText(textSeil+linkToFolder)
            self.resultLabel.blockSignals(False)
        # Berechnungen teilweise erfolgreich
        elif self.resultStatus == 3:
            self.resultLabel.setText(textHalf+linkToFolder)
            self.resultLabel.blockSignals(False)
        # Berechnungen nicht erfolgreich
        elif self.resultStatus == 4:
            self.resultLabel.setText(textBad)
        self.setLayout(self.container)
        # Bei Klick auf Label wird Ordner geöffnet

    def onResultClicked(self):
        path = self.outputLoc
        # Öffne Ordner-Fenster in...
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
        self.statusLabel.setText(u"Laufender Prozess wird abgebrochen...")
        self.cancelThread()

    def cancelThread(self):
        """Manueller Abbruch durch den Benutzers"""
        self.workerThread.stop()        # Beendet des Prozess sauber

    def onError(self, exception_string):
        # txt = u'Ein Fehler ist aufgetreten:\n{}'.format(exception_string)
        self.statusLabel.setText(u"Ein unerwarteter Fehler ist aufgetreten.")
        self.progressBar.setValue(self.progressBar.minimum())
        self.finallyDo()

    def onRerun(self):
        self.reRun = True
        self.savedProj = self.projFile
        self.onClose()

    def finallyDo(self):
        self.cancelButton.setStandardButtons(QDialogButtonBox.Close)
        self.cancelButton.clicked.connect(self.onClose)

    def cleanUp(self):
        # TODO Eventuell nicht nötig
        self.input = None
        self.state = False
        self.projInfo = None
        self.reportFile = u''
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
    """ Anpassung der Label-Klasse, damit bei Klick auf das Label ein Signal
    gesendet wird.
    """
    def __init(self, parent):
        QLabel.__init__(self, parent)

    def mouseReleaseEvent(self, ev):
        # TODO nochmals anschauen
        # super(ExtendedQLabel, self).mouseReleaseEvent(ev)
        self.emit(SIGNAL('clicked()'))



class WorkerThread(QThread):
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
        self.emit(SIGNAL("jobEnded(PyQt_PyObject)"), self.success)

    def stop(self):
        """Manueller Abbruch des Benutzers"""
        self.running = False

    def doWork(self):
        self.emit(SIGNAL("text(PyQt_PyObject)"), u"Berechnungen werden gestartet...")
        [self.inputData, self.projInfo] = self.userInput

        # import pickle
        # self.projInfo['Hoehenmodell'].pop('layer')
        # homePath = os.path.dirname(__file__)
        # storefile = os.path.join(homePath, 'backups+testFiles', 'testYSP.pckl')
        # f = open(storefile, 'w')
        # pickle.dump([self.userInput], f)
        # f.close()

        # import pydevd
        # pydevd.settrace('localhost', port=53100,
        #              stdoutToServer=True, stderrToServer=True)

        # Berechnungen starten
        output = main(self, self.inputData, self.projInfo)
        if not output:      # Falls Abbruch durch Benutzer oder Fehler im Code
            self.success = False
            return
        else:
            [self.result, self.resultStatus] = output
        # Ausgabe: resultStatus
        #   1 = Berechnungen erfolgreich abgeschlossen
        #   2 = Berechnungen erfolgreich, jedoch hebt Seil von Stützen ab
        #   3 = Berechnungen teilweise erfolgreich, Seil spannt nicht ganze Länge
        #   4 = Seilverlauf konnte überhaupt nicht berechnet werden
        if self.resultStatus == 4:
            self.emit(SIGNAL("result(PyQt_PyObject)"), [None, self.resultStatus])
            return
        # Resultate entpacken
        [t_start, disp_data, seilDaten, gp, HM,
         konkav, IS, kraft, optSTA, optiLen] = self.result

        # import pickle
        # self.projInfo['Hoehenmodell'].pop('layer')
        # homePath = os.path.dirname(__file__)
        # storefile = os.path.join(homePath, 'backups+testFiles', 'ohneHoeheimPlot.pckl')
        # f = open(storefile, 'w')
        # pickle.dump([output, self.userInput], f)
        # f.close()
        #
        # import pydevd
        # pydevd.settrace('localhost', port=53100,
        #              stdoutToServer=True, stderrToServer=True)

        self.emit(SIGNAL("value(PyQt_PyObject)"), optiLen*1.01)
        self.emit(SIGNAL("text(PyQt_PyObject)"), u"Outputdaten werden generiert...")

        # OUTPUT GENERIEREN
        ###################
        outputFolder = self.projInfo['outputOpt']['outputPath']
        outputName = self.projInfo['Projektname']
        self.outputLoc = createOutputFolder(outputFolder, outputName)
        # Gespeichertes Projekt in Output Ordner verschieben
        if os.path.exists(self.projInfo['projFile']):
            newpath = os.path.join(self.outputLoc,
                        os.path.basename(self.projInfo['projFile']))
            os.rename(self.projInfo['projFile'], newpath)
            self.projInfo['projFile'] = newpath
        # Generiere Plot für Report
        plotSavePath = os.path.join(self.outputLoc, "{}_Diagramm.pdf".format(outputName))
        plotImage, labelTxt = plotData(disp_data, gp["di"], seilDaten, konkav,
                                       HM, self.inputData, self.projInfo,
                                       self.resultStatus, plotSavePath)
        self.emit(SIGNAL("value(PyQt_PyObject)"), optiLen*1.015)
        # Berechnungsdauer und Zeitstempel auslesen
        duration, timestamp1, timestamp2 = getTimestamp(t_start)

        # Bericht erzeugen
        if self.projInfo['outputOpt']['report']:
            reportSavePath = os.path.join(self.outputLoc,
                                          "{}_Bericht.pdf".format(outputName))
            reportText = generateReportText(IS, self.projInfo, HM,
                                            kraft, optSTA, duration,
                                            timestamp2, labelTxt)
            # Generiere Report.pdf
            generateReport(reportText, reportSavePath, outputName)

        # Plot als PDF erzeugen
        if not self.projInfo['outputOpt']['plot']:
            # Wurde bereits erzeugt. Falls nicht nötig, wird es hier gelöscht
            if os.path.exists(plotImage):
                os.remove(plotImage)

        # Geodaten erzeugen
        if self.projInfo['outputOpt']['geodata']:
            geodata = generateGeodata(self.projInfo, HM, seilDaten,
                                      labelTxt[0], self.outputLoc)
            addToMap(self.iface, geodata, outputName)

        # Koordinatentabellen erzeugen
        if self.projInfo['outputOpt']['coords']:
            table1SavePath = os.path.join(self.outputLoc,
                                          outputName + '_KoordStuetzen.csv')
            table2SavePath = os.path.join(self.outputLoc,
                                          outputName + '_KoordSeil.csv')
            generateCoordTable(seilDaten, gp["zi"], HM,
                               [table1SavePath, table2SavePath], labelTxt[0])

        self.emit(SIGNAL("result(PyQt_PyObject)"), [self.outputLoc,
                                self.projInfo['projFile'], self.resultStatus])
