# -*- coding: utf-8 -*-

import time
import os
import sys
import numpy as np

# Pfad zu zusätzliche Libraries ergänzen
packagesPath = os.path.join(os.path.dirname(
                            os.path.dirname(__file__)), 'packages')
sys.path.append(packagesPath)


from .geoExtract import generateDhm, calcProfile, stuePos, \
    calcAnker, updateAnker, markFixStue
from .mainOpti import optimization
from .cablelineFinal import preciseCable
from .outputReport import vectorData



def main(progress, IS, projInfo):
    """
    
    :type progress: processingThread.ProcessingTask
    :type IS: dict
    :type projInfo: configHandler.ProjectConfHandler
    """

    # STARTE BERECHNUNGEN
    # -------------------
    # resultStatus:
        #   1 = Berechnungen erfolgreich abgeschlossen
        #   2 = Berechnungen erfolgreich, jedoch hebt Seil von Stützen ab
        #   3 = Berechnungen teilweise erfolgreich, Seil spannt nicht ganze Länge
        #   4 = Seilverlauf konnte überhaupt nicht berechnet werden
    resultStatus = [1]
    t_start = time.time()
    # Abtastrate des Längenprofils
    # wird verwendet um Abstand Lastwegkurve - Terrain genau zu bestimmen
    DeltaH = 1      # DEFAULT 1m Genauigkeit, nicht änderbar!
    # Horiz. Auflösung mögl. Stützenstandorte
    coeff = int(IS['L_Delta']/DeltaH)  # int
    inputPoints = projInfo.points['A'] + projInfo.points['E']

    # Rasterdaten laden
    rasterdata = generateDhm(projInfo.dhm, inputPoints)
    if progress.isCanceled():
        return False
    # Höhenprofil erstellen
    gp_old, zi_disp, diIdx = calcProfile(inputPoints, rasterdata, IS, DeltaH, coeff)
    if progress.isCanceled():
        return False
    # Mögliche Stützenpositionen finden
    gp, StuetzenPos, peakLoc, diIdx, R_R = stuePos(IS, gp_old, projInfo)
    possStue = gp['di_s'][StuetzenPos==1]
    IS['R_R'] = [R_R]

    # IS['HM_fix'] =
    IS['Ank'] = calcAnker(IS, inputPoints, rasterdata, gp)

    #Optimierungsprozedur
    out = optimization(IS, gp, StuetzenPos, progress, projInfo.fixedPoles)
    if not out:
        if not progress.isCanceled():
            progress.exception = "Fehler in Optimierungsalgorithmus."
        return False
    progress.sig_text.emit("Berechnung der optimale Seillinie...")
    [HM, HMidx, optValue, optSTA, optiLen] = out
    stuetzIdx = np.int32(diIdx[HMidx])
    IS['Ank'] = updateAnker(IS['Ank'], HM, stuetzIdx)
    IS['A_SK'] = optSTA[0]

    # Überprüfen ob Seil die gesamte Länge überspannt
    if int(HMidx[-1])+1 != gp['zi_s'].size:
        gp['di_s'] = gp['di_s'][:HMidx[-1]+1]
        gp['zi_s'] = gp['zi_s'][:HMidx[-1]+1]
        # Nicht alle Stützen konnten berechnet werden
        resultStatus.append(3)
        if HMidx == [0]:
            # Berechnungen nicht erfolgreich, keine einzige Stütze konnte
            #   berechnet werden
            progress.exception = (
                "Aufgrund der Geländeform oder der Eingabeparameter konnten <b>keine "
                "Stützenstandorte bestimmt</b> werden. Es wurden keine Output-Daten "
                "erzeugt.")
            return False

    # Informationen für die Darstellung der fixen Stützen
    IS['HM_fix_marker'] = markFixStue(stuetzIdx, projInfo.fixedPoles)

    # Präzise Seilfelddaten
    # Seilfeld berechnen, b = Breite, h = Höhe
    b = gp['di_s'][HMidx[1:]] - gp['di_s'][HMidx[:-1]]
    h = gp['zi_s'][HMidx[1:]] * 0.1 + HM[1:] - gp['zi_s'][HMidx[:-1]] * 0.1 - HM[:-1]
    seil, kraft, seil_possible = preciseCable(b, h, IS, IS['Ank'])
    if not seil_possible:       # Falls Seil von Stütze abhebt
        resultStatus.append(2)

    progress.sig_value.emit(optiLen*1.005)

    # Transformiere berechnete Daten in richtiges Koordinatensystem)
    [disp_data, seilDaten, HM] = vectorData(gp['xi'], gp['yi'], gp['di_n'],
                                        zi_disp, seil, stuetzIdx, HM, possStue)

    # IS.pop('Ank', None)
    return max(resultStatus), [t_start, disp_data, seilDaten, gp, HM, IS, kraft,
            optSTA, optiLen]
    # except:
    #     sys.exit()

