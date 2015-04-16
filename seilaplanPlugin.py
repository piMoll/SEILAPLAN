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


# TODO: clear when testing is over
# import sys
# path1 = "/home/pi/Software/PyCharm/pycharm-4.0.3/debug-eggs/pycharm-debug.egg"
# path2 = "/home/pi/Software/pycharm-4.0/debug-eggs/pycharm-debug.egg"
# if path1 not in sys.path:
#     sys.path.append(path1)
# if path2 not in sys.path:
#     sys.path.append(path2)

import os
from PyQt4.QtCore import QSettings, QTranslator, qVersion, QCoreApplication, \
    QObject, SIGNAL
from PyQt4.QtGui import QAction, QIcon
import qgis.utils
# Initialize Qt resources from file resources.py
import resources_rc
# GUI
from seilaplanPluginDialog import SeilaplanPluginDialog
# Algorithm
from processingThread import MultithreadingControl, WorkerThread


class SeilaplanPlugin:
    """QGIS Plugin Implementation."""
    def __init__(self, iface):
        # Save reference to the QGIS interface
        self.iface = iface
        # Initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # Initialize locale
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
        # Connect the action to the run method
        QObject.connect(self.action, SIGNAL("triggered()"), self.run)

        # Add toolbar button and menu item
        self.iface.addToolBarIcon(self.action)
        self.iface.addPluginToMenu(u"&SEILAPLAN", self.action)


    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        self.iface.removePluginMenu(u'&SEILAPLAN', self.action)
        self.iface.removeToolBarIcon(self.action)

    def run(self):
        """Run method that performs all the real work"""
        # import pydevd
        # pydevd.settrace('localhost', port=53100,
        #             stdoutToServer=True, stderrToServer=True)

        # Control variables for possible rerun of algorithm
        reRun = True
        reRunProj = None

        while reRun:
            # Initalize helper GUI that later will start algorithm
            self.threadControl = MultithreadingControl(self.iface)
            # Initalize dialog window
            self.dlg = SeilaplanPluginDialog(self.iface, self.threadControl)
            # Get available raster from table of content in QGIS
            self.dlg.updateRasterList()
            # Load initial values of dialog
            self.dlg.loadInitialVals()

            # If this is a rerun of the algorithm the previous user values are
            #   loaded into the GUI
            if reRunProj:
                self.dlg.loadProj(reRunProj)

            self.dlg.show()
            # Start event loop
            self.dlg.exec_()

            reRun = False
            reRunProj = None

            # Algorithm is executed in a separate class with two Threads. The
            #   first thread (MultithreadingControl, self.threadControl)
            #   controls the small dialog window with a progressbar, the
            #   second thread executes the algorithm.

            # If user clicked 'Ok'
            if self.threadControl.getState() is True:
                self.threadControl.workerThread = WorkerThread(
                                                qgis.utils.iface.mainWindow())
                # Get user input
                self.threadControl.workerThread.userInput = \
                                                self.threadControl.getValue()
                self.threadControl.workerThread.iface = self.iface
                self.threadControl.run()

                # Check if user wants a rerun after the algorithm has run and
                #   the progress dialog is closed
                if self.threadControl.reRun:
                    reRun = True
                    reRunProj = self.threadControl.savedProj
            del self.threadControl
            del self.dlg

        return

    def reject(self):
        self.dlg.Reject()

    def cleanUp(self):
        pass
