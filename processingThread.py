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
from qgis.core import QgsTask
from qgis.PyQt.QtCore import pyqtSignal

# Import Tool Scripts
from .tool.mainSeilaplan import main
from .tool.outputReport import getTimestamp, plotData, generateReportText, \
    generateReport, createOutputFolder
from .tool.outputGeo import generateGeodata, addToMap, generateCoordTable



class ProcessingTask(QgsTask):
    """This shows how to subclass QgsTask"""
    
    # Signals
    sig_jobEnded = pyqtSignal(bool)
    sig_value = pyqtSignal(float)
    sig_range = pyqtSignal(list)
    # sig_max = pyqtSignal()
    sig_text = pyqtSignal(str)
    sig_result = pyqtSignal(list)
    
    def __init__(self, progressbar, description='SEILAPLAN'):
        super().__init__(description, QgsTask.CanCancel)
        self.bar = progressbar
        self.total = 0
        self.iterations = 0
        self.exception = None
        self.inputData = None
        self.projInfo = None
        self.result = None
    
    def setProcessingInput(self, inputData, projInfo):
        self.inputData = inputData
        self.projInfo = projInfo
    
    def run(self):
        
        try:
            import pydevd
            pydevd.settrace('localhost', port=53100,
                        stdoutToServer=True, stderrToServer=True)
        except ConnectionRefusedError:
            pass
        except ImportError:
            pass


        output = main(self, self.inputData, self.projInfo)
        
        if not output:  # If abort by user or error in code
            return False
        else:
            [result, resultStatus] = output
        
        # Output resultStatus
        #   1 = Optimization successful
        #   2 = Cable takes off from support
        #   3 = Optimization partially successful
        #   4 = Optimization not successful
        if resultStatus == 4:
            self.sig_result.emit([None, resultStatus])
            return
        # Unpack results
        [t_start, disp_data, seilDaten, gp, HM,
         IS, kraft, optSTA, optiLen] = result
        
        # import pickle
        # projInfo['Hoehenmodell'].pop('layer')
        # homePath = os.path.dirname(__file__)
        # storefile = os.path.join(homePath, 'backups+testFiles', 'ohneHoeheimPlot.pckl')
        # f = open(storefile, 'w')
        # pickle.dump([output, self.userInput], f)
        # f.close()
        
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
        
        self.sig_result.emit([outputLoc, resultStatus])
        
        return True
    
    def finished(self, result):
        """This method is automatically called when self.run returns. result
        is the return value from self.run.

        This function is automatically called when the task has completed (
        successfully or otherwise). You just implement finished() to do whatever
        follow up stuff should happen after the task is complete. finished is
        always called from the main thread, so it's safe to do GUI
        operations and raise Python exceptions here.
        """
        
        if self.exception:
            # QgsMessageLog.logMessage(
            #     'Task "{name}" Exception: {exception}'.format(
            #         name=self.description(), exception=self.exception),
            #     'test', Qgis.Critical)
            raise self.exception
        
        self.bar.jobEnded(result)
    
    def cancel(self):
        super().cancel()

