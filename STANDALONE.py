# -*- coding: utf-8 -*-

""" standalone Skript um Tool (Algorithmus, Ausgabe..) unabhängig von QGIS zu
testen.
"""

import os
import pickle
from tool.outputReport import getTimestamp, plotData, generateReportText, \
                                generateReport, createOutputFolder
from tool.outputGeo import generateGeodata, generateCoordTable
from tool.mainSeilaplan import main as mainSeilaplan

class Dummy:
    def __init__(self):
        self.running = True


def main(storeDump):

    # Ganze Berechnungen laufen lassen
    ##################################

    # homePath = os.path.dirname(__file__)
    # storefile = os.path.join(homePath, 'backups+testFiles', '{}.pckl'.format(storeDump))
    # f = open(storefile)
    # [inputData, projInfo] = pickle.load(f)
    # f.close()
    # progress = Dummy()
    #
    # inputData['HM_fix_d'] = inputData['HM_fix_d'][0]
    # inputData['HM_fix_h'] = inputData['HM_fix_h'][0]
    # projInfo['fixeStuetzen'] = []
    #
    # result = mainCalc(progress, inputData, projInfo)
    # if not result:
    #     sys.exit()
    # [t_start, disp_data, seilDaten, gp, HM, konkav, mast_ind, IS,
    #      kraft, optSTA, StuetzenPos, length_reached, optiLen] = result

    # # Nur Outputgenerierung laufen lassen
    # #####################################
    # homePath = os.path.dirname(__file__)
    # storefile = os.path.join(homePath, 'backups+testFiles', '{}.pckl'.format(storeDump))
    # f = open(storefile)
    # output = pickle.load(f)
    # f.close()
    #
    # [[result, resultStatus], [IS, projInfo]] = output
    # [t_start, disp_data, seilDaten, gp, HM,
    #  konkav, IS, kraft, optSTA, optiLen] = result

    # generateGeodata(projInfo, HM, seilDaten)
    #
    #
    # # Generiere Plot für Report
    # plotImage, plotSize, labelTxt = plotData(disp_data, gp["di"], seilDaten,
    #                                          konkav, HM['HM_z'], mast_ind, IS['HM_fix_d'])
    # # Berechnungsdauer und Zeitstempel auslesen
    # duration, timestamp1, timestamp2 = getTimestamp(t_start)
    # # Generiere Report Text
    # reportText = generateReportText(IS, projInfo, HM, mast_ind, kraft,
    #                                 optSTA, duration, timestamp2, labelTxt)
    # # Generiere Excel Daten mit Koordinaten
    # # generateOuputCoords(seilDaten, gp["zi"], mast_ind, timestamp1, HM)
    # # Generiere Report.pdf
    # reportPDF = generateReport(plotImage, plotSize, reportText,
    #                            projInfo['Projektname'], timestamp1)



    # # NEUE VERSION
    # #########################################
    #
    # outputFolder = projInfo['outputOpt']['outputPath']
    # outputName = projInfo['Projektname']
    # outputLoc = createOutputFolder(outputFolder, outputName)
    # # Generiere Plot für Report
    # plotImage, plotSize, labelTxt = plotData(disp_data, gp["di"], seilDaten,
    #                                              konkav, HM,
    #                                              IS, projInfo, resultStatus)
    # duration, timestamp1, timestamp2 = getTimestamp(t_start)
    #
    # # Bericht erzeugen
    # if projInfo['outputOpt']['report']:
    #     reportSavePath = os.path.join(outputLoc,
    #                                   outputName + '_Bericht.pdf')
    #     reportText = generateReportText(IS, projInfo, HM,
    #                                     kraft, optSTA, duration,
    #                                     timestamp2, labelTxt)
    #     # Generiere Report.pdf
    #     generateReport(plotImage[0], plotSize, reportText, reportSavePath,
    #                    outputName)
    #
    # # Plot als PDF erzeugen
    # if projInfo['outputOpt']['plot']:
    #     # TODO: Überprüfen ob dieses Paket in QGIS vorhanden ist
    #     import shutil
    #     outputPath = os.path.join(outputLoc, outputName + '_Plot.pdf')
    #     shutil.copyfile(plotImage[1], outputPath)
    #     os.remove(plotImage[1])
    #
    # # Shapedaten erzeugen
    # if projInfo['outputOpt']['geodata']:
    #     generateGeodata(projInfo, HM, seilDaten, labelTxt[0],
    #                     outputLoc)
    #
    # # Koordinatentabellen erzeugen
    # if projInfo['outputOpt']['coords']:
    #     csvPathStue = os.path.join(outputLoc,
    #                                outputName + '_KoordStuetzen.csv')
    #     csvPathSeil = os.path.join(outputLoc,
    #                                outputName + '_KoordSeil.csv')
    #     generateCoordTable(seilDaten, gp["zi"], HM,
    #                        [csvPathSeil, csvPathStue], labelTxt[0])

    # Version 3
    homePath = os.path.dirname(__file__)
    storefile = os.path.join(homePath, 'backups+testFiles', '{}.pckl'.format(storeDump))
    f = open(storefile)
    dump = pickle.load(f)
    f.close()


    [userInput] = dump


    [inputData, projInfo] = userInput

    # import pydevd
    # pydevd.settrace('localhost', port=53100,
    #              stdoutToServer=True, stderrToServer=True)

    # Berechnungen starten
    [result, resultStatus] = mainSeilaplan(Dummy, inputData, projInfo)
    # Resultate entpacken
    [t_start, disp_data, seilDaten, gp, HM,
     konkav, IS, kraft, optSTA, optiLen] = result


    # OUTPUT GENERIEREN
    ###################
    outputFolder = projInfo['outputOpt']['outputPath']
    outputName = projInfo['Projektname']
    outputLoc = createOutputFolder(outputFolder, outputName)
    # Gespeichertes Projekt in Output Ordner verschieben
    if os.path.exists(projInfo['projFile']):
        newpath = os.path.join(outputLoc,
                    os.path.basename(projInfo['projFile']))
        os.rename(projInfo['projFile'], newpath)
        projInfo['projFile'] = newpath
    # Generiere Plot für Report
    plotSavePath = os.path.join(outputLoc, "{}_Diagramm.pdf".format(outputName))
    plotImage, labelTxt = plotData(disp_data, gp["di"], seilDaten, konkav,
                                   HM, inputData, projInfo,
                                   resultStatus, plotSavePath)
    # Berechnungsdauer und Zeitstempel auslesen
    duration, timestamp1, timestamp2 = getTimestamp(t_start)

    # Bericht erzeugen
    if projInfo['outputOpt']['report']:
        reportSavePath = os.path.join(outputLoc,
                                      "{}_Bericht.pdf".format(outputName))
        reportText = generateReportText(IS, projInfo, HM,
                                        kraft, optSTA, duration,
                                        timestamp2, labelTxt)
        # Generiere Report.pdf
        generateReport(reportText, reportSavePath, outputName)

    # Plot als PDF erzeugen
    if not projInfo['outputOpt']['plot']:
        # Wurde bereits erzeugt. Falls nicht nötig, wird es hier gelöscht
        if os.path.exists(plotImage):
            os.remove(plotImage)

    # Geodaten erzeugen
    if projInfo['outputOpt']['geodata']:
        generateGeodata(projInfo, HM, seilDaten, labelTxt[0],
                        outputLoc)

    # Koordinatentabellen erzeugen
    if projInfo['outputOpt']['coords']:
        table1SavePath = os.path.join(outputLoc,
                                      outputName + '_KoordStuetzen.csv')
        table2SavePath = os.path.join(outputLoc,
                                      outputName + '_KoordSeil.csv')
        # TODO: Keine Ahnung ob richtige Parameter (die ersten zwei)
        generateCoordTable(seilDaten, gp["zi"], HM,
                           [table1SavePath, table2SavePath], labelTxt[0])


if __name__ == "__main__":
    # store = sys.argv[1]
    store = "testYSP"
    main(store)
    # path = "/home/pi/Dropbox/Seiloptimierung/SeilbahnPlugin/backups+testFiles/"
    # command = "python {0}gprof2dot.py -f pstats {0}{1}.prof | dot -Tpng -o {0}{1}.png".format(path, name)
    # os.system("cd /home/pi/Dropbox/Seiloptimierung/SeilbahnPlugin/backups+testFiles/")
    # os.system(command)
