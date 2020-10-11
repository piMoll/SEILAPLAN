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

import numpy as np
from .terrainAnalysis import stuePos
from .mainOpti import optimization
from .cablelineFinal import preciseCable


def main(progress, project):
    """
    :type progress: processingThread.ProcessingTask
    :type project: configHandler.ProjectConfHandler
    """
    progress.status.append(1)
    if progress.isCanceled():
        return False
    
    params = project.params.getSimpleParameterDict()
    profile = project.profile
    poles = project.poles

    # Search suitable pole positions along profile
    # TODO: Refactor into profile Class
    gp, StuetzenPos, diIdx, R_R = stuePos(
        params, profile, project.noPoleSection, project.fixedPoles)
    
    # Extend params dictionary TODO: better solution?
    params['R_R'] = R_R
    params['Ank'] = poles.anchor

    out = optimization(params, profile, StuetzenPos, progress,
                       project.fixedPoles, [project.A_type, project.E_type])
    if not out:
        if not progress.isCanceled():
            progress.exception = "Fehler in Optimierungsalgorithmus."
        return False

    progress.sig_text.emit('msg_seillinie')
    [HM, HMidx, optValue, optSTA, optiLen] = out

    project.params.setOptSTA(optSTA[0])
    
    stuetzDist = np.int32(diIdx[HMidx])

    # Check result status
    if not HMidx or HMidx == [0]:
        # Not a single pole location was calculated, no cable line possible
        progress.exception = (
            "Aufgrund der Gelaendeform oder der Eingabeparameter konnten keine Stuetzenstandorte bestimmt werden.")
        return False
    # Corresponds last optimized pole with end point?
    if int(poles.lastPole['d']) != int(stuetzDist[-1]):
        # It was not possible to calculate poles along the entire profile
        progress.status.append(3)
    
    # Save optimized poles to Pole() object
    optiPoles = []
    for idx, d in enumerate(stuetzDist):
        name = ''
        # Check if this is a fixed pole
        for fPole in project.fixedPoles['poles']:
            if d == fPole['d']:
                name = fPole['name']
        optiPoles.append({
            'd': d,
            'h': HM[idx],
            'name': name
        })
    poles.updateAllPoles('optimization', optiPoles)

    # Calculate precise cable line data
    cableline, force, seil_possible = preciseCable(params, poles, optSTA[0])
    if not seil_possible:
        # Cable is lifting off the poles
        progress.status.append(2)

    progress.sig_value.emit(optiLen * 1.005)
    
    return {
        'cableline': cableline,
        'optSTA': optSTA[0],
        'optSTA_arr': optSTA,
        'force': force,
        'optLen': optiLen
    }
