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

from qgis.core import QgsTask
from qgis.PyQt.QtCore import pyqtSignal

# Import Tool Scripts
from .tool.mainSeilaplan import main
from .tool.outputReport import getTimestamp


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
    
    def __init__(self, confHandler, description='SEILAPLAN'):
        """
        :type confHandler: configHandler.ConfigHandler
        """
        super().__init__(description, QgsTask.CanCancel)
        self.state = False
        self.exception = None
        self.confHandler = confHandler
        self.projInfo = confHandler.project
        self.resultStatus = None
        self.result = None
    
    def run(self):
        
        # try:
        #     import pydevd_pycharm
        #     pydevd_pycharm.settrace('localhost', port=53100,
        #                             stdoutToServer=True, stderrToServer=True)
        # except ConnectionRefusedError:
        #     pass
        # except ImportError:
        #     pass

        self.confHandler.prepareForCalculation()
        output = main(self, self.projInfo)
        
        if not output:  # If error in code
            return False
        else:
            [resultStatus, result] = output
        
        # Output resultStatus
        #   1 = Optimization successful
        #   2 = Cable takes off from support
        #   3 = Optimization partially successful
        
        # Unpack results
        [t_start, cableline, kraft, optSTA, optiLen] = result
        
        self.sig_value.emit(optiLen * 1.01)


        # Calculate duration and generate time stamp
        duration, timestamp1, timestamp2 = getTimestamp(t_start)
        self.resultStatus = resultStatus
        self.result = {
            'cableline': cableline,
            'optSTA': optSTA,
            'force': kraft,
            'optLen': optiLen,
            'duration': [duration, timestamp1, timestamp2]
        }

        # import pickle
        # import os
        # storeDump = 'project_to_pickl_20191009'
        # homePath = '/home/pi/Projects/seilaplan/pickle_dumps'
        # storefile = os.path.join(homePath, '{}.pckl'.format(storeDump))
        # f = open(storefile, 'wb')
        # poles = self.projInfo.poles.poles
        # pickle.dump({
        #     'cableline': cableline,
        #     'optSTA': optSTA,
        #     'force': kraft,
        #     'optLen': optiLen,
        #     'poles': poles,
        #     'duration': [duration, timestamp1, timestamp2]
        # }, f)
        # f.close()
        
        # self.sig_result.emit(resultStatus)
        
        return True
        
    def getResult(self):
        return self.result
    
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

