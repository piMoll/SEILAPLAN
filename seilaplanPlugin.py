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
from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication
from qgis.PyQt.QtWidgets import QAction, QPushButton, QMessageBox
from qgis.PyQt.QtGui import QIcon
from qgis.core import Qgis
from . import PLUGIN_DIR

# Add shipped libraries to the python path if missing
try:
    import reportlab
except ModuleNotFoundError:
    libPath = os.path.join(PLUGIN_DIR, 'lib')
    if libPath not in sys.path:
        sys.path.insert(-1, libPath)

# Before continuing, we check if scipy and scipy.interpolate can be imported.
# If not, we will not import the plugin files.
ERROR = False
try:
    import scipy
except ModuleNotFoundError:
    # Depending on the os or distribution, scipy isn't available
    ERROR = 1
try:
    import scipy.interpolate
except ImportError:
    # On QGIS Version 3.10.9 and 3.14.15 there is a bug that prevents
    #  importing scipy.interpolate.
    ERROR = 1 if ERROR == 1 else 2
    
if not ERROR:
    # Import seilaplan plugin entry point
    from .seilaplanRun import SeilaplanRun
    from SEILAPLAN.gui.guiHelperFunctions import getAbsoluteIconPath
    from SEILAPLAN.utils.misc import removeOldSeilaplanPluginRepo


class SeilaplanPlugin:
    """QGIS Plugin Implementation."""
    
    def __init__(self, iface):
        # Save reference to the QGIS interface
        self.iface = iface
        
        # Initialize locale
        # Default locale is english
        useLocale = os.path.join(PLUGIN_DIR, 'i18n',
                                     'SeilaplanPlugin_en.qm')
        # Get locale from QGIS settings
        qgisLocale = QSettings().value("locale/userLocale")[0:2]
        localePath = os.path.join(PLUGIN_DIR, 'i18n',
                                  'SeilaplanPlugin_{}.qm'.format(qgisLocale))

        if qgisLocale in ['de', 'en', 'fr', 'it'] and os.path.exists(localePath):
            useLocale = localePath

        self.translator = QTranslator()
        self.translator.load(useLocale)
        QCoreApplication.installTranslator(self.translator)

        self.action = None
        self.pluginRuns = []
        self.preparationTasks()

    def tr(self, message):
        return QCoreApplication.translate(type(self).__name__, message)

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""
        icon = QIcon(getAbsoluteIconPath('icon_app.png'))
        self.action = QAction(icon, self.tr('SEILAPLAN'), self.iface.mainWindow())
        self.action.triggered.connect(self.run)
        self.action.setEnabled(True)
        self.action.setStatusTip(self.tr('SEILAPLAN'))
        self.action.setWhatsThis(self.tr('SEILAPLAN'))
        # Adds plugin icon to Plugins toolbar
        self.iface.addToolBarIcon(self.action)
        self.iface.addPluginToMenu(self.tr('SEILAPLAN'), self.action)

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        # Delete plugin run instances
        for run in self.pluginRuns:
            run.close()
            del run
            
        self.iface.removePluginMenu(self.tr('SEILAPLAN'), self.action)
        self.iface.removeToolBarIcon(self.action)
    
    def handleImportErrors(self):
        def showError():
            msgBox = QMessageBox(self.iface.mainWindow())
            msgBox.setIcon(QMessageBox.Icon.Information)
            msgBox.setWindowTitle(shortMessage)
            msgBox.setText(longMessage)
            msgBox.setStandardButtons(QMessageBox.StandardButton.Ok)
            msgBox.show()
            msgBox.exec()
        
        if ERROR == 1:
            barTitle = self.tr('SEILAPLAN Fehler')
            shortMessage = self.tr('Bibliothek scipy nicht vorhanden.')
            longMessage = self.tr('Seilaplan benoetigt die Python Bibliothek scipy um Berechnungen durchzufuehren.')
        else:   # ERROR == 2
            barTitle = self.tr('SEILAPLAN Fehler')
            shortMessage = self.tr('Fehlerhafte QGIS Version.')
            longMessage = self.tr('Aufgrund eines Fehlers in QGIS kann Seilaplan in der aktuell installierten Version nicht ausgefuehrt werden.')
    
        widget = self.iface.messageBar().createMessage(barTitle, shortMessage)
        button = QPushButton(widget)
        button.setText(self.tr("Weitere Informationen"))
        button.pressed.connect(showError)
        widget.layout().addWidget(button)
        self.iface.messageBar().pushWidget(widget, Qgis.Warning)
    
    @staticmethod
    def preparationTasks():
        """Contains cleanup tasks that run before the plugin is opened."""
        
        # All versions later than 3.7.0 are published on the official QGIS
        # plugin repository. The old GitHub-based repo is removed.
        removeOldSeilaplanPluginRepo()

    def run(self):
        # Check for import errors and show messages
        if ERROR:
            self.handleImportErrors()
            return
        
        # Create a SeilaplanRun instance and save reference. This allows to
        #  run the plugin multiple times in parallel
        seilaplanRun = SeilaplanRun(self.iface)
        self.pluginRuns.append(seilaplanRun)
        
        # Start the run by showing the project window
        seilaplanRun.showProjectWindow()
