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

import time
import traceback
from qgis.core import QgsTask
from qgis.PyQt.QtCore import pyqtSignal

# Import Tool Scripts
from SEILAPLAN.core.mainSeilaplan import main
from .outputReport import getTimestamp


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
    sig_result = pyqtSignal(str)
    
    def __init__(self, confHandler, description='SEILAPLAN'):
        """
        :type confHandler: configHandler.ConfigHandler
        """
        super().__init__(description, QgsTask.CanCancel)
        self.state = False
        self.exception = None
        self.confHandler = confHandler
        self.projInfo = confHandler.project
        self.result = None
        self.status = []
    
    def run(self):
        
        # # Uncomment when trying to debug the optimization algorithm
        # try:
        #     import pydevd_pycharm
        #     pydevd_pycharm.settrace('localhost', port=53100,
        #                             stdoutToServer=True, stderrToServer=True)
        # except ConnectionRefusedError:
        #     pass
        # except ImportError:
        #     pass

        t_start = time.time()
        try:
            # Create profile, initialize poles
            self.confHandler.prepareForCalculation()
            # Calculate pole positions
            result = main(self, self.projInfo)
        except Exception as e:
            self.exception = traceback.format_exc()
            return False

        # Check if there was an error
        if not result:
            return False
        self.sig_value.emit(result['optLen'] * 1.01)

        # Calculate duration and generate time stamp
        result['duration'] = getTimestamp(t_start)

        self.result = result

        statusNames = {
            1: 'optiSuccess',
            2: 'liftsOff',
            3: 'notComplete'
        }
        self.status = statusNames[max(self.status)]
        self.sig_result.emit(self.status)

        # import pickle
        # import os
        # storeDump = 'pickl_20191018'
        # homePath = '/home/pi/Projects/seilaplan/pickle_dumps'
        # storefile = os.path.join(homePath, '{}.pckl'.format(storeDump))
        # f = open(storefile, 'wb')
        # result['poles'] = self.projInfo.poles.poles
        # pickle.dump(result, f)
        # f.close()
        
        return True
        
    def getResult(self):
        return self.result, self.status
    
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
