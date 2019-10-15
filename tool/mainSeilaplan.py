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
import numpy as np
from .geoExtract import stuePos
from .mainOpti import optimization
from .cablelineFinal import preciseCable


def main(progress, project):
    """
    :type progress: processingThread.ProcessingTask
    :type project: configHandler.ProjectConfHandler
    """
    resultStatus = [1]
    t_start = time.time()
    if progress.isCanceled():
        return False
    
    params = project.params.getSimpleParameterDict()
    profile = project.profile
    poles = project.poles

    # Search suitable pole positions along profile
    # TODO: Refactor into profile Class
    gp, StuetzenPos, peakLoc, diIdx, R_R = stuePos(
        params, profile, project.noPoleSection, project.fixedPoles)
    
    # Extend params dictionary TODO: better solution?
    params['R_R'] = R_R
    params['Ank'] = poles.anchor

    out = optimization(params, profile, StuetzenPos, progress,
                       project.fixedPoles)
    if not out:
        if not progress.isCanceled():
            progress.exception = "Fehler in Optimierungsalgorithmus."
        return False

    progress.sig_text.emit("Berechnung der optimale Seillinie...")
    [HM, HMidx, optValue, optSTA, optiLen] = out

    if HMidx == [0]:
        # Berechnungen nicht erfolgreich, keine einzige Stütze konnte
        #   berechnet werden
        progress.exception = (
            "Aufgrund der Geländeform oder der Eingabeparameter konnten <b>keine "
            "Stützenstandorte bestimmt</b> werden. Es wurden keine Output-Daten "
            "erzeugt.")
        return False
    
    # Save optimized pole locations
    stuetzIdx = np.int32(diIdx[HMidx])
    poles.addPolesFromOptimization(stuetzIdx, HM)

    lastPole_dist = int(poles.poles[-2]['d'])
    if lastPole_dist + 1 != np.size(profile.zi_s):
        # Nicht alle Stützen konnten berechnet werden
        resultStatus.append(3)

    # Calculate precise cable line data
    cableline, kraft, seil_possible = preciseCable(params, poles, optSTA[0])
    if not seil_possible:  # Falls Seil von Stütze abhebt
        resultStatus.append(2)

    progress.sig_value.emit(optiLen * 1.005)
    
    return max(resultStatus), [t_start, cableline, kraft, optSTA, optiLen]
