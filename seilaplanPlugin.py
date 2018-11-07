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
from qgis.PyQt.QtCore import QSettings, QTranslator, qVersion, QCoreApplication
from qgis.PyQt.QtWidgets import QAction
from qgis.PyQt.QtGui import QIcon
import qgis.utils
# Initialize Qt resources from file resources.py
from . import resources_rc
# GUI
from .seilaplanPluginDialog import SeilaplanPluginDialog
# Algorithm
from .gui.progressDialog import ProgressDialog


class SeilaplanPlugin(object):
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

        self.action = None
        self.progressDialog = None
        self.dlg = None
        
        try:
            import pydevd
            pydevd.settrace('localhost', port=53100,
                        stdoutToServer=True, stderrToServer=True)
        except ConnectionRefusedError:
            pass
        except ImportError:
            pass


    def initGui(self):
        # Create action that will start plugin configuration
        self.action = QAction(
            QIcon(":/plugins/SeilaplanPlugin/icons/icon_app.png"),
            "SEILAPLAN", self.iface.mainWindow())
        self.action.setWhatsThis("SEILAPLAN")
        # Connect the action to the run method
        self.action.triggered.connect(self.run)

        # Add toolbar button and menu item
        self.iface.addToolBarIcon(self.action)
        self.iface.addPluginToMenu("&SEILAPLAN", self.action)


    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        self.iface.removePluginMenu('&SEILAPLAN', self.action)
        self.iface.removeToolBarIcon(self.action)

    def run(self):
        """Run method that performs all the real work"""

        # Control variables for possible rerun of algorithm
        reRun = True
        reRunProj = None

        while reRun:
            # Initialize helper GUI that later will start algorithm
            self.progressDialog = ProgressDialog(self.iface)
            # Initialize dialog window
            self.dlg = SeilaplanPluginDialog(self.iface, self.progressDialog)
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

            # The algorithm is executed in a separate thread. To see pgrogress,
            #
            #   first thread (progressDialog, self.threadControl)
            #   controls the small dialog window with a progressbar, the
            #   second thread executes the algorithm.

            # If user clicked 'Ok'
            if self.progressDialog.getState() is True:

                self.progressDialog.runProcessing()

                # Check if user wants a rerun after the algorithm has run and
                #   the progress dialog is closed
                if self.progressDialog.reRun:
                    reRun = True
                    reRunProj = self.progressDialog.savedProj
            del self.progressDialog
            del self.dlg

        return

    def reject(self):
        self.dlg.Reject()

    def cleanUp(self):
        pass
