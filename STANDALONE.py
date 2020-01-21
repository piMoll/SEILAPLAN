"""
STANDALONE.py

This script executes the seilaplan core algorithms without the help of QGIS.
No GUI is shown, so no parameters can be changed by hand in a window. All
settings are read out from a previously saved seilaplan project file.

To run the script, the following variables have to be set:
- Line ~21: Define path to python script files in your QGIS installation.
            The path should be similar to the one already written.
            
- Line ~120 - ~150: Define some paths for input and output and select what
                    algorithms should be run.

"""

import sys

# ################# PATH TO CURRENT QGIS PYTHON LOCATION ######################
if 'WIN' in sys.platform.upper():
    sys.path.append(r'C:\Program Files (x86)\QGIS 3.4\apps\qgis-ltr\python')
    # Other possible paths:
    #   r'C:\Program Files\QGIS 3.4\apps\qgis-ltr\python'
    #   r'C:\Program Files\QGIS 3.10\apps\qgis\python'
# #############################################################################

import os
import traceback
from qgis.core import QgsTask
from qgis.PyQt.QtCore import pyqtSignal
from .configHandler import ConfigHandler
from .tool.mainSeilaplan import main as mainSeilaplan
from .tool.cablelineFinal import preciseCable, updateWithCableCoordinates
from .gui.adjustmentPlot import AdjustmentPlot
from .tool.outputReport import generateReportText, generateReport, createOutputFolder
from .tool.outputGeo import generateGeodata, generateCoordTable


class ProcessingTask(QgsTask):
    """
    This is a Dummy Class to handle progress information events from the
    algorithm. Normally, this would be handled by the QGIS task manager.
    """
    # Signals
    sig_jobEnded = pyqtSignal(bool)
    sig_jobError = pyqtSignal(str)
    sig_value = pyqtSignal(float)
    sig_range = pyqtSignal(list)
    sig_text = pyqtSignal(str)
    sig_result = pyqtSignal(list)
    
    def __init__(self, confHandler, description="Dummy"):
        super().__init__(description, QgsTask.CanCancel)
        self.state = False
        self.exception = None
        self.confHandler = confHandler
        self.projInfo = confHandler.project
        self.result = None
        self.status = []
        self.statusNames = {
            1: 'optiSuccess',
            2: 'liftsOff',
            3: 'notComplete'
        }
    
    def isCanceled(self):
        return
    
    def emit(*args):
        return
    
    def cancel(self):
        super().cancel()
    
    def getStatusAsStr(self):
        return self.statusNames[max(self.status)]


def optimizeCableLine(conf):
    """ This function performs the optimization of the pole locations and
    calculates the finale cable line.
    """
    # Ready configuration data from project file
    conf.prepareForCalculation()
    # Initialize dummy task manager
    task = ProcessingTask(conf)
    res = None
    try:
        # Start optimization
        res = mainSeilaplan(task, conf.project)
    except Exception as e:
        # Catch errors and print them to console
        print(traceback.format_exc())
        exit()
    
    return task.getStatusAsStr(), res['cableline'], res['optSTA'], \
           res['force'], config.project.poles


def calculateFinalCableLine(conf):
    """ This function only calculates the finale cable line. Pole locations
    are read from a project file.
    """
    optiResults, _ = conf.loadCableDataFromFile()
    parameters = conf.params.getSimpleParameterDict()
    
    cable, force, cable_possible = preciseCable(parameters, conf.project.poles,
                                                optiResults['optSTA'])
    
    stat = 'successful'
    if not cable_possible:
        stat = 'liftsOff'
    
    return stat, cable, optiResults['optSTA'], force, conf.project.poles






if __name__ == "__main__":
    # This section controls which functions are executed and what project
    #  file is loaded.
    
    # ################## ALL CONFIGURATIONS GO HERE ###########################
    
    # Define the project file you want to load
    savedProjectFile = '/home/pi/Seilaplan/nullpunkt_test/NW_raster_350m_3pole_4manchor/Projekteinstellungen.txt'
    # TODO: savedProjectFile = r"C:\path\to\your\file.txt"

    # Define which functions the code should perform
    #  'optimize':  Run optimization algorithm to define pole positions and
    #               calculate final cable line.
    #  'cableline': Only calculate final cable line, no optimization. Position
    #               of poles will be extracted from project file. Only works
    #               if the optimization algorithm was run before the project
    #               file was saved.
    perform = 'optimize'
    
    # Do you want do generate output data? (PDFs, CSV, ...)
    createOutput = True     # or: False
    # Where do you want output to be saved?
    outputLocation = '/home/pi/Seilaplan'
    # TODO: outputLocation = r"C:\path\to\your\outputLocation"
    
    # #########################################################################

    # Project settings are loaded
    config = ConfigHandler()
    config.loadFromFile(savedProjectFile)
    
    if perform == 'optimize':
        
        # Run optimization including final cable line calculation
        status, cableline, optSTA, forces, poles = optimizeCableLine(config)

    else:
        
        # Run calculation of cable line
        status, cableline, optSTA, forces, poles = calculateFinalCableLine(config)
        
    # status:
    #   optiSuccess =   Optimization successful
    #   liftsOff =      Cable is lifting off one or more poles
    #   notComplete =   Optimization partially successful: It was not
    #                   possible to calculate poles along the entire profile
    print(f"Optimization status: {status}")

    # Output creation
    #################
    
    if createOutput:
        # If you dont want that a certain output type is created, comment out
        #  the related code block below
        
        outputFolder = config.getCurrentPath()
        project = config.project
        profile = project.profile
        projName = project.generateProjectName()
        outputLoc = createOutputFolder(os.path.join(outputFolder, projName))
        updateWithCableCoordinates(cableline, project.points['A'],
                                   project.azimut)
    
        # Save project file
        config.saveToFile(os.path.join(outputLoc, 'Projekteinstellungen.txt'))
    
        # Create report PDF
        ####
        resultDict = {
            'force': forces,
            'optSTA_arr': [optSTA],
            'duration': ['-', '-', '-'],        # Dummy data for report
        }
        reportText = generateReportText(config, resultDict, '')
        generateReport(reportText, outputLoc, projName)
    
        # Create plot PDF
        ###
        plotSavePath = os.path.join(outputLoc, 'Diagramm.pdf')
        printPlot = AdjustmentPlot()
        printPlot.initData(profile.di_disp, profile.zi_disp,
                           profile.peakLoc_x, profile.peakLoc_z,
                           profile.surveyPnts)
        printPlot.updatePlot(poles.getAsArray(), cableline, True)
        printPlot.printToPdf(plotSavePath, projName, poles.poles)
    
        # Generate geo data
        ###
        generateGeodata(project, poles.poles, cableline, outputLoc)
    
        # Generate coordinate tables (CSV)
        ###
        generateCoordTable(cableline, profile, poles.poles, outputLoc)

    print('STANDALONE finished')
