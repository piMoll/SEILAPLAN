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
from qgis.core import QgsTask
from qgis.PyQt.QtCore import pyqtSignal

# Import Tool Scripts
from .tool.mainSeilaplan import main
from .tool.outputReport import getTimestamp, plotData, generateReportText, \
    generateReport, createOutputFolder
from .tool.outputGeo import generateGeodata, addToMap, generateCoordTable



class ProcessingTask(QgsTask):
    """ Seperate Thread to run calculations without blocking QGIS. This class
    runs the algorithm, sends progress information to the progress gui and
    generates the results (diagram, pdf, geodata...).
    """
    
    # Signals
    sig_jobEnded = pyqtSignal(bool)
    sig_jobError = pyqtSignal(str)
    sig_value = pyqtSignal(float)
    sig_range = pyqtSignal(list)
    sig_text = pyqtSignal(str)
    sig_result = pyqtSignal(list)
    
    def __init__(self, description='SEILAPLAN'):
        super().__init__(description, QgsTask.CanCancel)
        self.state = False
        self.exception = None
        self.inputData = None
        self.projInfo = None
        self.result = None
    
    def setState(self, state):
        self.state = state
    
    def setProcessingInput(self, inputData, projInfo):
        self.inputData = inputData
        self.projInfo = projInfo
    
    def run(self):
        
        # Remove comment to debug algorithm
        try:
            import pydevd_pycharm
            pydevd_pycharm.settrace('localhost', port=53100,
                        stdoutToServer=True, stderrToServer=True)
        except ConnectionRefusedError:
            pass
        except ImportError:
            pass


        output = main(self, self.inputData, self.projInfo)
        
        if not output:  # If error in code
            return False
        else:
            [result, resultStatus] = output
        
        # Output resultStatus
        #   1 = Optimization successful
        #   2 = Cable takes off from support
        #   3 = Optimization partially successful
        
        # Unpack results
        [t_start, disp_data, seilDaten, gp, HM,
         IS, kraft, optSTA, optiLen] = result
        
        self.sig_value.emit(optiLen * 1.01)
        self.sig_text.emit("Outputdaten werden generiert...")
        
        # Generate output
        ###################
        outputFolder = self.projInfo['outputOpt']['outputPath']
        outputName = self.projInfo['Projektname']
        outputLoc = createOutputFolder(outputFolder, outputName)
        # Move saved project file to output folder
        if os.path.exists(self.projInfo['projFile']):
            newpath = os.path.join(outputLoc,
                                   os.path.basename(self.projInfo['projFile']))
            os.rename(self.projInfo['projFile'], newpath)
            self.projInfo['projFile'] = newpath
        # Generate plot
        plotSavePath = os.path.join(outputLoc,
                                    "{}_Diagramm.pdf".format(outputName))
        plotImage, labelTxt = plotData(disp_data, gp["di"], seilDaten, HM,
                                       self.inputData, self.projInfo,
                                       resultStatus, plotSavePath)
        self.sig_value.emit(optiLen * 1.015)
        # Calculate duration and generate time stamp
        duration, timestamp1, timestamp2 = getTimestamp(t_start)
        
        # Create report
        if self.projInfo['outputOpt']['report']:
            reportSavePath = os.path.join(outputLoc,
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
                                      labelTxt[0], outputLoc)
            addToMap(geodata, outputName)
        
        # Generate coordinate tables
        if self.projInfo['outputOpt']['coords']:
            table1SavePath = os.path.join(outputLoc,
                                          outputName + '_KoordStuetzen.csv')
            table2SavePath = os.path.join(outputLoc,
                                          outputName + '_KoordSeil.csv')
            generateCoordTable(seilDaten, gp["zi"], HM,
                               [table1SavePath, table2SavePath], labelTxt[0])
        
        
        resultData = [
            disp_data,
            gp,
            HM,
            IS,
            seilDaten
        ]

        # import pickle
        # storeDump = 'plotData_ergebnisfenster_20190911'
        # homePath = '/home/pi/Projects/seilaplan/pickle_dumps'
        # storefile = os.path.join(homePath, '{}.pckl'.format(storeDump))
        # f = open(storefile, 'wb')
        # pickle.dump(allData, f)
        # f.close()
        
        self.sig_result.emit([outputLoc, resultStatus, resultData])
        
        return True
    
    def finished(self, result):
        """This method is automatically called when self.run returns. result
        is the return value from self.run.
        This function is automatically called when the task has completed (
        successfully or otherwise).
        """

        if self.exception:
            self.sig_jobError.emit(self.exception)
        
        else:
            # Show successful run or user abort on progress gui
            self.sig_jobEnded.emit(result)
    
    def cancel(self):
        super().cancel()

