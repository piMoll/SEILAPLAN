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

import os
import sys
from qgis.PyQt.QtCore import QSettings, QTranslator, qVersion, QCoreApplication
from qgis.PyQt.QtWidgets import QAction
from qgis.PyQt.QtGui import QIcon
from qgis.core import QgsApplication
# Initialize Qt resources from file resources.py
from .gui import resources_rc
# Main dialog window
from .seilaplanPluginDialog import SeilaplanPluginDialog
# Further dialog windows and helpers
from .gui.progressDialog import ProgressDialog
from .configHandler import ConfigHandler
from .processingThread import ProcessingTask
from .gui.adjustmentDialog import AdjustmentDialog

# Add shipped libraries to python path
libPath = os.path.join(os.path.dirname(__file__), 'lib')
if libPath not in sys.path:
    sys.path.append(libPath)


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

        self.actions = []
        self.menu = self.tr('SEILAPLAN')
        self.dlg = None
        self.progressDialog = None
        self.adjustmentWindow = None
        self.result = None

        # Check if plugin was started the first time in current QGIS session
        # Must be set in initGui() to survive plugin reloads
        self.first_start = None

    # noinspection PyMethodMayBeStati
    def tr(self, message):
        """Get the translation for a string using Qt translation API.
        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('SEILAPLAN', message)

    def add_action(self, icon_path, text, callback, enabled_flag=True,
                   add_to_menu=True, add_to_toolbar=True, status_tip=None,
                   whats_this=None, parent=None):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)
        if whats_this is not None:
            action.setWhatsThis(whats_this)
        if add_to_toolbar:
            # Adds plugin icon to Plugins toolbar
            self.iface.addToolBarIcon(action)
        if add_to_menu:
            self.iface.addPluginToMenu(
                self.menu,
                action)
        self.actions.append(action)
        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""
        icon_path = ':/plugins/SeilaplanPlugin/gui/icons/icon_app.png'
        self.add_action(
            icon_path,
            text=self.tr('SEILAPLAN'),
            callback=self.run,
            parent=self.iface.mainWindow())

        # will be set False in run()
        self.first_start = True

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr('&SEILAPLAN'),
                action)
            self.iface.removeToolBarIcon(action)

    def run(self):
        """Run method that performs all the real work"""
        
        # # Uncomment when debugging
        # try:
        #     import pydevd_pycharm
        #     pydevd_pycharm.settrace('localhost', port=53100,
        #                             stdoutToServer=True, stderrToServer=True)
        # except ConnectionRefusedError:
        #     pass
        # except ImportError:
        #     pass
        
        # Configuration handler
        conf = ConfigHandler()

        # Initialize dialog window
        self.dlg = SeilaplanPluginDialog(self.iface, conf)
        self.dlg.setupContentForFirstRun()

        # Control variables for possible rerun of algorithm
        reRun = True
        firstRun = True

        while reRun:
            reRun = False
            result = False
            status = False
            
            if not firstRun:
                # Reset configuration from earlier optimization run
                conf.reset()
                # Setup start window
                self.dlg.setupContent()
            firstRun = False
            
            # Start event loop
            self.dlg.show()
            self.dlg.exec()

            # # Uncomment when trying to debug adjustment window
            # # Show adjustment window directly without running optimization algorithm
            # conf.loadFromFile("/home/pi/Seilaplan/project_to_pickl_20191022.txt")
            # pickleFile = '/home/pi/Projects/seilaplan/pickle_dumps/pickl_20191022.pckl'
            # conf.prepareForCalculation()
            # self.adjustmentWindow = AdjustmentDialog(self.iface, conf)
            # self.adjustmentWindow.loadData(pickleFile)
            # self.adjustmentWindow.unsavedChanges = False
            # self.adjustmentWindow.show()
            # self.adjustmentWindow.exec()

            # Begin with computation when user clicked on "Start calculations"
            # and parameters are valid
            if self.dlg.startAlgorithm:
    
                # Create separate thread for calculations so QGIS stays responsive
                workerThread = ProcessingTask(conf)
    
                # To see progress, a new dialog window shows a progress bar
                self.progressDialog = ProgressDialog(self.iface)
                self.progressDialog.setThread(workerThread)

                # Add task to task manager of QGIS and start the calculations
                QgsApplication.taskManager().addTask(workerThread)

                # Show progress bar and start event loop
                self.progressDialog.show()
                self.progressDialog.exec()
                
                # Check if user wants a rerun
                if self.progressDialog.doReRun:
                    reRun = True
                    
                # Save result if calculation was successful and user didn't
                # cancel
                if self.progressDialog.wasSuccessful:
                    result, status = workerThread.getResult()
                    
                del workerThread
                del self.progressDialog
            
            elif self.dlg.goToAdjustment:
                result, status = conf.loadCableDataFromFile()
            
            if result:
                # Show adjustment window to modify calculated cable line
                self.adjustmentWindow = AdjustmentDialog(self.iface, conf)
                self.adjustmentWindow.initData(result, status)
                self.adjustmentWindow.show()
                self.adjustmentWindow.exec()
                
                if self.adjustmentWindow.doReRun:
                    reRun = True
                del self.adjustmentWindow

        self.dlg.cleanUp()
        del self.dlg
        return
