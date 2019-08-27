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

import os
import pickle
import time
from math import inf

from osgeo import gdal
from qgis.core import QgsTask
from qgis.PyQt.QtCore import pyqtSignal
from .tool.outputReport import getTimestamp, plotData, generateReportText, \
                                generateReport, createOutputFolder
from .tool.outputGeo import generateGeodata, generateCoordTable
from .tool.mainSeilaplan import main as mainSeilaplan






class Dummy(QgsTask):
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
    
    def __init__(self, description="Dummy"):
        super().__init__(description, QgsTask.CanCancel)
        self.running = True
        
    def isCanceled(self):
        return

    def emit(*args):
        return
    
    def cancel(self):
        super().cancel()






def main(storeDump):
    """ Here we define parameters for the algorithm, let the algorithm rund
    and create output files."""
    
    timestamp = time.strftime("%d.%m_%H'%M", time.localtime(time.time()))
    
    
    
    
    # Load parameter from pickle object - currently not used
    if storeDump:
        homePath = os.path.dirname(__file__)
        storefile = os.path.join(homePath, '{}.pckl'.format(storeDump))
        f = open(storefile, 'rb')
        dump = pickle.load(f)
        f.close()
        [inputData, projInfo] = dump
        outputName = "seilaplan_{}".format(timestamp)
        outputFolder = '/home/pi/Seilaplan'
    
    
    
    
    # Define input parameter
    else:
    
        ##############################
        # CHANGE INPUT PARAMETERS HERE
        ##############################
    
        # Output folder location
        outputName = "seilaplan_{}".format(timestamp)
        outputFolder = '/home/pi/Seilaplan'
        
        # DHM path
        dhm_path = '/home/pi/Dropbox/Seiloptimierung/geodata/dhm_foersterschule_mels.txt'
        dhm_spatialRef = 'EPSG:21781'       # or: 'EPSG:2056' for LV95
        
        
        # Start and end point
        # has to be inside DHM extent
        # has to be in same projection system (LV03, LV95, etc.) as DHM
        startpoint = [746425, 212938]
        endpoint = [745954, 212970]
        
    
        # Paramter set
        inputData = {
            'Q':             [25.0, 'Gewicht der Last inkl. Laufwagen', 'kN', '1'],
            'qT':            [0.0228, 'Gewicht Tragseil', 'kN/m', '2'],
            'A':             [380.0, 'Querschnittssfläche Tragseil', 'mm2', '3'],
            'E':             [100.0, 'Elastizitätsmodul Tragseil', 'kN/mm2', '4'],
            'zul_SK':        [179.0, 'Maximal zulässige Seilzugkraft', 'kN', '5'],
            'min_SK':        [50.0, 'Minimal zulässige Seilzugkraft', 'kN', '6'],
            'qz1':           [0.0058, 'Gewicht des Zugseils links', 'kN/m', '7'],
            'qz2':           [0.0, 'Gewicht des Zugseils rechts', 'kN/m', '8'],
            'Bodenabst_min': [7.0,  'Minimaler Abstand Tragseil - Boden', 'm', '9'],
            'Bodenabst_A':   [40, 'einzuhalten ab (vom Startpunkt)', 'm', '10'],
            'Bodenabst_E':   [40, 'einzuhalten bis (vor dem Endpunkt)',  'm', '11'],
            'GravSK':        ['ja', 'Gravitationsseilkran?', '', '12'],
            'Befahr_A':      [0, 'Befahrbarkeit ab (vom Startpunkt)', 'm',  '13'],
            'Befahr_E':      [0, 'Befahrbarkeit bis (vor dem Endpunkt)',  'm', '14'],
            'HM_Anfang':     [11, 'Höhe der Anfangsstütze', 'm', '15'],
            'd_Anker_A':     [10.0, 'Länge der Verankerung', 'm', '16'],
            'HM_Ende_min':   [0, 'Minimale Höhe der Endstütze', 'm',   '17'],
            'HM_Ende_max':   [10, 'Maximale Höhe der Endstütze', 'm',   '18'],
            'd_Anker_E':     [10.0, 'Länge der Verankerung', 'm', '19'],
            'Min_Dist_Mast': [10, 'Minimaler Abstand zwischen Stützen',  'm', '20'],
            'L_Delta':       [10, 'Horiz. Auflösung mögl. Stützenstandorte', 'm', '21'],
            'N_Zw_Mast_max': [10, 'Maximale Anzahl Zwischenstützen', '', '22'],
            'HM_min':        [8, 'Minimale Stützenhöhe', 'm', '23'],
            'HM_max':        [18, 'Maximal Stützenhöhe', 'm', '24'],
            'HM_Delta':      [2, 'Abstufungsinterval', 'm', '25'],
            'HM_nat':        [14, 'Künstliche Stützen ab Stützenhöhe', 'm',  '26'],
            'A_SK':          [12.0, 'Anfangsseilkraft', 'kN', '27'],
            'Min_Gradient':  [0.0, 'Min. nötiger Gradient', '', '28'],
            'Federkonstante':[inf, 'Federkonstante der Verankerung',  'kN/m', '29'],
            'L_min':         [30.0, 'Minimale Länge eines Seilfeldes', 'm', '30'],
            'HM_fix_d':      [[], 'Fixe Stützen: Position', ''],    # zB [12, 20, 40] = Horizontaldistanz ab Start
            'HM_fix_h':      [[], 'Fixe Stützen: Höhe', ''],        # zB [12, 20, 20]
            'noStue':        [[], 'Keine Stützen möglich', '']      # zB [5, 15] = Keine Stützen im Bereich von 5m bis 15m ab Start
        }
        
        
        #######################################################################
        ############# nothing to change after this point ######################
    
    
        # Analyse dhm
        ds = gdal.Open(dhm_path)
        cols = ds.RasterXSize
        rows = ds.RasterYSize
        upx, xres, xskew, upy, yskew, yres = ds.GetGeoTransform()
        ulx = upx + 0 * xres + 0 * xskew
        uly = upy + 0 * yskew + 0 * yres
        lrx = upx + cols * xres + rows * xskew
        lry = upy + cols * yskew + rows * yres
        dhm_extent = [ulx, uly, lrx, lry]
    
        projInfo = {
            'Anfangspunkt': startpoint,
            'Endpunkt': endpoint,
            'Projektname': outputName,
            'Hoehenmodell': {
                'path': dhm_path,
                'cellsize': xres,
                'spatialRef': dhm_spatialRef,
                'extent': dhm_extent
            },
            'Laenge': '?',
            'fixeStuetzen': [],
            'keineStuetzen': inputData['noStue'][0],
            'Parameterset': '?',
            'header': "Projektname      ?\nHoehenmodell     ?\nAnfangspunkt     ?\nEndpunkt         ?nParameterset     ?\nFixe Stuetzen    \n\n\nParameter:\nName             Wert        Label                                        Einheit  \n-----------------------------------------------------------------------------------\n",
            'Params': [[details[1], '{0} {2}'.format(*details)] for details in inputData.values()]
        }

        
        # Reformat input data, hacky
        inputData['HM_fix_d'] = inputData['HM_fix_d'][0]
        inputData['HM_fix_h'] = inputData['HM_fix_h'][0]
        inputData['noStue'] = inputData['noStue'][0]
        projInfo['Params'].append(['', ''])







    # Start calculations
    ###################
    output = mainSeilaplan(Dummy(), inputData, projInfo)

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






    # Generate output
    ###################
    
    outputLoc = createOutputFolder(outputFolder, outputName)
    
    
    # Generate plot
    plotSavePath = os.path.join(outputLoc, "{}_Diagramm.pdf".format(outputName))
    plotImage, labelTxt = plotData(disp_data, gp["di"], seilDaten, HM,
                                   inputData, projInfo,
                                   resultStatus, plotSavePath)
    
    # Calculate duration and generate time stamp
    duration, timestamp1, timestamp2 = getTimestamp(t_start)

    # Create report
    reportSavePath = os.path.join(outputLoc,
                                  "{}_Bericht.pdf".format(outputName))
    reportText = generateReportText(IS, projInfo, HM,
                                    kraft, optSTA, duration,
                                    timestamp2, labelTxt)
    # Generate Report pdf
    generateReport(reportText, reportSavePath, outputName)


    # Generate geo data
    # generateGeodata(projInfo, HM, seilDaten, labelTxt[0],
    #                 outputLoc)

    # Generate coordinate tables
    table1SavePath = os.path.join(outputLoc,
                                  outputName + '_KoordStuetzen.csv')
    table2SavePath = os.path.join(outputLoc,
                                  outputName + '_KoordSeil.csv')
    generateCoordTable(seilDaten, gp["zi"], HM,
                       [table1SavePath, table2SavePath], labelTxt[0])








if __name__ == "__main__":
    # Store is only used when working with pickle objects
    store = None    #"test"
    
    main(store)
