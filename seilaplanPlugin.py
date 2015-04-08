# -*- coding: utf-8 -*-
"""
/***************************************************************************
 SeilaplanPlugin
                                 A QGIS plugin
 Seilkran-Layoutplaner
                              -------------------
        begin                : 2013
        copyright            : (C) 2015 by ETH Zürich
        email                : mollpa@ethz.ch and bontle@ethz.ch
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


# TODO: Löschen wenn Testing vorbei ist
import sys
path1 = "/home/pi/Software/PyCharm/pycharm-4.0.3/debug-eggs/pycharm-debug.egg"
path2 = "/home/pi/Software/pycharm-4.0/debug-eggs/pycharm-debug.egg"
if path1 not in sys.path:
    sys.path.append(path1)
if path2 not in sys.path:
    sys.path.append(path2)

import os
from PyQt4.QtCore import QSettings, QTranslator, qVersion, QCoreApplication, \
    QObject, SIGNAL
from PyQt4.QtGui import QAction, QIcon
import qgis.utils
# Initialize Qt resources from file resources.py
import resources_rc
# Importiert Klasse für GUI-Darstellung
from seilaplanPluginDialog import SeilaplanPluginDialog
# Importiert Klasse für Berechnungen
from processingThread import MultithreadingControl, WorkerThread


class SeilaplanPlugin:
    """QGIS Plugin Implementation."""
    def __init__(self, iface):
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value("locale/userLocale")[0:2]
        localePath = os.path.join(self.plugin_dir, 'i18n',
                                  'SeilaplanPlugin_{}.qm'.format(locale))

        if os.path.exists(localePath):
            self.translator = QTranslator()
            self.translator.load(localePath)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

    def initGui(self):
        # Create action that will start plugin configuration
        self.action = QAction(
            QIcon(":/plugins/SeilaplanPlugin/icons/icon_app.png"),
            u"SEILAPLAN", self.iface.mainWindow())
        # connect the action to the run method
        QObject.connect(self.action, SIGNAL("triggered()"), self.run)

        # Add toolbar button and menu item
        self.iface.addToolBarIcon(self.action)
        self.iface.addPluginToMenu(u"&SEILAPLAN", self.action)

        # TODO: Platzierung der MultiThreading Geschichte sehr wichtig wegen
        # TODO:     init Methode
        # # Initalize helper GUI that later will start optimization
        # # qgis.utils.iface
        # self.threadingControl = MultithreadingControl(self.iface)

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""

        self.iface.removePluginMenu(u'&SEILAPLAN', self.action)
        self.iface.removeToolBarIcon(self.action)

    def run(self):
        """Run method that performs all the real work"""
        # import pydevd
        # pydevd.settrace('localhost', port=53100,
        #             stdoutToServer=True, stderrToServer=True)

        # Kontrollwerte für eine Wiederholung der Berechnungen
        reRun = True
        reRunProj = None
        # import pydevd
        # pydevd.settrace('localhost', port=53100,
        #                 stdoutToServer=True, stderrToServer=True)

        while reRun:
            # Initalize helper GUI that later will start optimization
            self.threadingControl = MultithreadingControl(self.iface)
            # Initalize dialog window
            self.dlg = SeilaplanPluginDialog(self.iface, self.threadingControl)
            # Get available raster from table of content in QGIS
            self.dlg.updateRasterList()
            # Load initial values of dialog
            self.dlg.loadInitialVals()

            # Falls es sich um eine Wiederholung handelt, werden die Werte
            #   der letzten Durchführung geladen
            if reRunProj:
                self.dlg.loadProj(reRunProj)

            self.dlg.show()
            # Eventloop starten
            self.dlg.exec_()

            reRun = False
            reRunProj = None

            # Berechnungen werden in einer separaten Klasse mit zwei Threads
            #   ausgeführt. Der erste Thread (MultithreadingControl,
            #   self.threadingControl) kontrolliert das Dialogfenster mit
            #   Fortschrittsanzeige, der zweite Thread (WorkerThread) führt die
            #   Berechnungen aus.
            # Falls Ok geklickt wurde
            if self.threadingControl.getState() is True:
                # Daten holen
                [toolData, projInfo] = self.threadingControl.getValue()
                self.threadingControl.workerThread = WorkerThread(
                                                qgis.utils.iface.mainWindow())
                self.threadingControl.workerThread.userInput = [toolData, projInfo]
                self.threadingControl.workerThread.iface = self.iface
                self.threadingControl.run()

                # Wenn im Progress-Fenster Close geklickt wird, kommt man hier her
                # Steurung für die Wiederholung der Berechnungen
                if self.threadingControl.reRun:
                    reRun = True
                    reRunProj = self.threadingControl.savedProj


            del self.threadingControl
            del self.dlg

        return

    def reject(self):
        self.dlg.Reject()

    def cleanUp(self):
        pass
