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

from qgis.core import QgsTask
from qgis.PyQt.QtCore import pyqtSignal
from .configHandler import ConfigHandler
from .tool.mainSeilaplan import main as mainSeilaplan


class ProcessingTask(QgsTask):
    """
    Dummy Class to handle the progress information events from the algorithm
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
        self.resultStatus = None
        self.result = None
    
    def isCanceled(self):
        return
    
    def emit(*args):
        return
    
    def cancel(self):
        super().cancel()


def main():
    """ Here we define parameters for the algorithm, let the algorithm rund
    and create output files."""
    
    conf = ConfigHandler()
    conf.loadFromFile('/home/pi/Seilaplan/test/test_wartau_NO-SW_450m_DeltaP.txt')
    conf.prepareForCalculation()
    
    # Start calculations
    output = mainSeilaplan(ProcessingTask(conf), conf.project)
    
    if not output:  # If error in code
        return False
    else:
        [resultStatus, result] = output
    
    # Output resultStatus
    #   1 = Optimization successful
    #   2 = Cable takes off from support
    #   3 = Optimization partially successful
    
    return resultStatus, result, conf.project


if __name__ == "__main__":
    resultStatus, [t_start, cableline, kraft, optSTA, optiLen], project = main()
    
    print('done')
