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
    sys.path.append(r'C:\Program Files\QGIS 3.4\apps\qgis-ltr\python')
    # sys.path.append(r'C:\Program Files (x86)\QGIS 3.4\apps\qgis-ltr\python')
    # Other possible paths:
    #   r'C:\Program Files\QGIS 3.4\apps\qgis-ltr\python'
    #   r'C:\Program Files\QGIS 3.10\apps\qgis\python'
# #############################################################################

import os
# Add shipped libraries to python path (reportlab)
try:
    import reportlab
except ModuleNotFoundError:
    libPath = os.path.join(os.path.dirname(__file__), 'lib')
    if libPath not in sys.path:
        sys.path.insert(-1, libPath)

import traceback
from qgis.core import QgsTask, QgsApplication
from qgis.PyQt.QtCore import pyqtSignal, QTranslator, QCoreApplication
from SEILAPLAN.tools.configHandler import ConfigHandler
from SEILAPLAN.core.mainSeilaplan import main as mainSeilaplan
from SEILAPLAN.core.cablelineFinal import preciseCable, updateWithCableCoordinates
from SEILAPLAN.gui.adjustmentPlot import AdjustmentPlot, calculatePlotDimensions
from SEILAPLAN.tools.outputReport import (generateReportText, generateReport,
                                createOutputFolder, generateShortReport)
from SEILAPLAN.tools.outputGeo import (organizeDataForExport, generateCoordTable, writeGeodata)
from SEILAPLAN.tools.birdViewMapExtractor import extractMapBackground
from SEILAPLAN.tools.globals import ResultQuality


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
        self.confHandler: ConfigHandler = confHandler
        self.projInfo = confHandler.project
        self.result = None
        self.status = []
    
    def isCanceled(self):
        return
    
    def emit(*args):
        return
    
    def cancel(self):
        super().cancel()
    
    def getStatusAsStr(self):
        return max(self.status)


def optimizeCableLine(conf: ConfigHandler):
    """ This function performs the optimization of the pole locations and
    calculates the finale cable line.
    """
    # Ready configuration data from project file
    print('Set up configuration and input values...')
    success = conf.prepareForCalculation(runOptimization=True)
    if not success:
        print('ERROR: Error while preparing config data for optimization.')
        exit()
    # Initialize dummy task manager
    task = ProcessingTask(conf)
    res = None
    try:
        print('Start optimization...')
        # Start optimization
        res = mainSeilaplan(task, conf.project)
    except Exception as e:
        # Catch errors and print them to console
        print(traceback.format_exc())
        exit()
        
    if not res:
        print('ERROR: Error during optimization algorithm:')
        print(task.exception)
        exit()
    
    return task.getStatusAsStr(), res['cableline'], res['optSTA'], \
           res['force'], config.project.poles


def calculateFinalCableLine(conf: ConfigHandler):
    """ This function only calculates the finale cable line. Pole locations
    are read from a project file.
    """
    print('Set up configuration and input values...')
    success = conf.prepareForCalculation(runOptimization=False)
    if not success:
        print('ERROR: Error while preparing config data for optimization.')
        exit()
    print('Load pole setup from file...')
    optiResults, _ = conf.prepareResultWithoutOptimization()
    parameters = conf.params.getSimpleParameterDict()

    print('Calculate precise cable line..')
    cable, force, cable_possible = preciseCable(parameters, conf.project.poles,
                                                optiResults['optSTA'])
    
    resultQuality = ResultQuality.SuccessfulRerun
    if not cable_possible:
        resultQuality = ResultQuality.CableLiftsOff
    
    return resultQuality, cable, optiResults['optSTA'], force, conf.project.poles






if __name__ == "__main__":
    # This section controls which functions are executed and what project
    #  file is loaded.
    
    # ################## ALL CONFIGURATIONS GO HERE ###########################
    
    # Location of QGIS installation: the easiest way to find it for your system
    # is to use the Scripting in the Python Console from within QGIS and look
    # at the output from running: QgsApplication.prefixPath()
    # on Ubuntu it's: "/usr"
    qgis_install_location = r'C:\OSGeo4W\apps\qgis'
    
    # Define the project file you want to load
    savedProjectFile = r'N:\forema\FPS\Projekte_der_Gruppe\Seillinienplanung\2c_AP1_Projekte\Martin_Ammann\Ammann_Buriwand\Versuche_Leo\seilaplan_2020_24_08\Projekteinstellungen.txt'

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
    
    # #########################################################################
    
    
    QgsApplication.setPrefixPath(qgis_install_location, True)
    # Create a reference to the QgsApplication. Setting the
    # second argument to False disables the GUI.
    qgs = QgsApplication([], False)
    # Load providers
    qgs.initQgis()
    # Load translations
    translator = QTranslator()
    translator.load(os.path.join(os.path.dirname(__file__), 'i18n', 'SeilaplanPlugin_de.qm'))
    QCoreApplication.installTranslator(translator)
    
    # Project settings are loaded
    print('Load configuration from project file...')
    config: ConfigHandler = ConfigHandler()
    configLoaded = config.loadSettings(savedProjectFile)
    if not configLoaded:
        print(f"ERROR: Project file does not exist or cannot be loaded.")
        qgs.exitQgis()
        exit()
    
    if perform == 'optimize':
        
        # Run optimization including final cable line calculation
        status, cableline, optSTA, forces, poles = optimizeCableLine(config)

    else:
        
        # Run calculation of cable line
        status, cableline, optSTA, forces, poles = calculateFinalCableLine(config)
    
    # Now that the cable line is calculated, analyze the ground clearance
    groundClear = config.project.profile.updateProfileAnalysis(cableline)
    cableline = {**cableline, **groundClear}
    
    print(f"Optimization status: {status}")

    # Output creation
    #################
    
    if createOutput and status != ResultQuality.LineNotComplete:
        # If you dont want that a certain output type is created, comment out
        #  the related code block below
        
        project = config.project
        profile = project.profile
        polesList = [pole for pole in poles.poles if pole['active']]
        
        projName = project.generateProjectName()
        outputLoc, projName_unique = createOutputFolder(outputLocation, projName)
        updateWithCableCoordinates(cableline, project.points['A'],
                                   project.azimut)
    
        # Save project file
        config.saveSettings(os.path.join(outputLoc, 'Projekteinstellungen.json'))
    
        resultDict = {
            'force': forces,
            'cableline': cableline,
            'optSTA_arr': [optSTA],
            'duration': ['-', '-', '-'],        # Dummy data for report
        }
        
        # Create short report PDF
        ####
        print('Create short report...')
        generateShortReport(config, resultDict, projName_unique, outputLoc)
        
        # Create detailed report PDF
        ####
        print('Create detailed report...')
        reportText = generateReportText(config, resultDict, projName_unique)
        generateReport(reportText, outputLoc)
    
        # Create plot PDF
        ###
        print('Create plot...')
        plotSavePath = os.path.join(outputLoc, 'Diagramm.pdf')
        width, height, ratio = calculatePlotDimensions(profile.di_disp, profile.zi_disp)
        printPlot = AdjustmentPlot(None, width, height, 150, withBirdView=True, profilePlotRatio=ratio)
        printPlot.initData(profile.di_disp, profile.zi_disp,
                           profile.peakLoc_x, profile.peakLoc_z,
                           profile.surveyPnts)
        printPlot.updatePlot(poles.getAsArray(), cableline, True)
        printPlot.layoutDiagrammForPrint(projName_unique, polesList, poles.direction)
        imgPath = None
        
        # Create Bird View
        ###
        xlim, ylim = printPlot.createBirdView(polesList, project.azimut)
        # Extract the map background
        imgPath = extractMapBackground(outputLoc, xlim, ylim,
                                       project.points['A'], project.azimut)
        printPlot.addBackgroundMap(imgPath)
        printPlot.exportPdf(plotSavePath)
        os.remove(imgPath)
    
        # Generate geo data
        ###
        print('Create geo data...')
        # Put geo data in separate sub folder
        savePath = os.path.join(outputLoc, 'geodata')
        os.makedirs(savePath)
        epsg = project.heightSource.spatialRef
        geodata = organizeDataForExport(polesList, cableline, profile)
        # Generate shape files
        writeGeodata(geodata, 'SHP', epsg, savePath)
    
        # Generate coordinate tables (CSV)
        ###
        print('Create csv files...')
        generateCoordTable(cableline, profile, polesList, savePath)

    print('STANDALONE finished')
    qgs.exitQgis()
