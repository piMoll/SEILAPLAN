from qgis.core import QgsApplication
# Main dialog window
from SEILAPLAN.gui.seilaplanPluginDialog import SeilaplanPluginDialog
# Further dialog windows and helpers
from SEILAPLAN.gui.progressDialog import ProgressDialog
from SEILAPLAN.tools.configHandler import ConfigHandler
from SEILAPLAN.tools.processingThread import ProcessingTask
from SEILAPLAN.gui.adjustmentDialog import AdjustmentDialog


class SeilaplanRun:
    """Handles the program flow, manages settings/configuration and keeps a
     hold on the plugin state and calculation results between different dialog
     windows. Allows to run the plugin multiple times in parallel."""
    
    def __init__(self, interface):
        self.iface = interface
        
        # Each run of the plugin has its own ConfigHandler instance
        self.confHandler: ConfigHandler = ConfigHandler()
        
        self.projectWindow = None
        self.workerThread = None
        self.progressDialog = None
        self.adjustmentWindow = None
        
        self.result = False
        self.status = False
    
    def showProjectWindow(self):
        if not self.projectWindow:
            self.projectWindow = SeilaplanPluginDialog(self.iface, self.confHandler)
            self.projectWindow.setupContentForFirstRun()
        else:
            self.projectWindow.setupContent()
        
        # Show dialog and start event loop
        self.projectWindow.show()
        self.projectWindow.exec()
        
        if self.projectWindow.runOptimization is True:
            # Continue with optimization algorithm
            self.startOptimization()
        elif self.projectWindow.runOptimization is False:
            # Continue by skipping over optimization and go straight to the
            #  adjustment window
            self.result, self.status = self.confHandler.prepareResultWithoutOptimization()
            self.showAdjustmentWindow()
        else:  # None: runOptimization not set --> user canceled dialog
            self.close()
    
    def startOptimization(self):
        # Create separate thread for calculations so QGIS stays responsive
        self.workerThread = ProcessingTask(self.confHandler.project)
        
        # To see progress, a new dialog window shows a progress bar
        self.progressDialog = ProgressDialog(self.iface.mainWindow())
        self.progressDialog.setThread(self.workerThread)
        
        # Add task to task manager of QGIS and start the calculations
        QgsApplication.taskManager().addTask(self.workerThread)
        
        # Show progress bar and start event loop
        self.progressDialog.show()
        self.progressDialog.exec()
        
        # Save result if calculation was successful
        if self.progressDialog.continueToAdjustment:
            self.result, self.status = self.workerThread.getResult()
        
        # Cleanup
        self.progressDialog.deleteLater()
        del self.workerThread
        
        if self.progressDialog.continueToAdjustment is True:
            self.showAdjustmentWindow()
        elif self.progressDialog.continueToAdjustment is False:
            # User chose to go back to project window
            self.showProjectWindow()
        else:  # None: continueToAdjustment not set --> user canceled dialog
            self.close()
    
    def showAdjustmentWindow(self):
        # Show adjustment window to modify calculated cable line
        self.adjustmentWindow = AdjustmentDialog(self.iface, self.confHandler)
        self.adjustmentWindow.initData(self.result, self.status)
        self.adjustmentWindow.show()
        self.adjustmentWindow.exec()
        
        if self.adjustmentWindow.returnToProjectWindow is True:
            # User wants to go bach to project window dialog; reset result and status
            self.result = False
            self.status = False
            self.adjustmentWindow.deleteLater()
            
            # Reset configuration
            self.confHandler.reset()
            self.showProjectWindow()
        else:   # User clicked cancel or close
            self.close()
    
    def close(self):
        # Save user settings
        self.confHandler.updateUserSettings()
        
        # Cleanup any markers in map and delete dialogs
        for dialog in [self.projectWindow, self.progressDialog, self.adjustmentWindow]:
            if dialog:
                try:
                    dialog.cleanUp()
                    dialog.deleteLater()
                except RuntimeError:
                    # Already deleted
                    pass
            
