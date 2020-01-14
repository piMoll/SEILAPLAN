# -*- coding: utf-8 -*-

"""
STANDALONE.py

Dieses Skript ruft den Optimierungsalgorithmus ohne den Umweg über QIGS und
das Plugin auf.
Die Ausführung funktioniert nur, wenn in der Funktion 'main' gültige
Parameter definiert wurden.


Ausführen: im Pfad, in welchem sich der Ordner "SEILAPLAN" befindet,
folgenden Befehl ausführen:

python -m SEILAPLAN.STANDALONE

"""

import time
import traceback
from qgis.core import QgsTask
from qgis.PyQt.QtCore import pyqtSignal
from .configHandler import ConfigHandler
from .tool.mainSeilaplan import main as mainSeilaplan
from .tool.outputReport import getTimestamp


class ProcessingTask(QgsTask):
    """
    Dummy Class to handle progress information events from the algorithm,
    this would normally be handled by the qgis task manager.
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
    
    def isCanceled(self):
        return
    
    def emit(*args):
        return
    
    def cancel(self):
        super().cancel()


def main():
    """ Here we define parameters for the algorithm, let the algorithm rund
    and create output files."""

    t_start = time.time()
    conf = ConfigHandler()
    conf.loadFromFile('/home/pi/Seilaplan/nullpunkt_test/NW_raster_840m_6pole/Projekteinstellungen.txt')
    conf.prepareForCalculation()
    
    # Start calculations
    task = ProcessingTask(conf)
    try:
        result = mainSeilaplan(task, conf.project)
    except Exception as e:
        return traceback.format_exc()
        
    if not result:  # If error in code
        return False

    # Calculate duration of calculation and generate time stamp
    result['duration'] = getTimestamp(t_start)

    statusNames = {
        1: 'optiSuccess',
        2: 'liftsOff',
        3: 'notComplete'
    }
    status = statusNames[max(task.status)]
    
    return status, result, conf.project


if __name__ == "__main__":
    status, result, project = main()

    # status:
    #   optiSuccess =   Optimization successful
    #   liftsOff =      Cable is lifting off one or more poles
    #   notComplete =   Optimization partially successful: It was not possible
    #                   to calculate poles along the entire profile

    seillinie = result['cableline']
    optSTA = result['optSTA']
    optSTA_arr = result['optSTA_arr']
    kraft = result['force']
    optLen = result['optLen']
    duration = result['duration']
    
    # TODO: Bericht erstellen, csv exportieren
    

    print('done')
