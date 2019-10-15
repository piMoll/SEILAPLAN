# -*- coding: utf-8 -*-
"""
#------------------------------------------------------------------------------
# Name:        Seillinienlayout - Start der Optimierungsberechnungen
# Purpose:
#
# Author:      Patricia Moll
#
# Created:     14.05.2013
# Copyright:   (c) mollpa 2012
# Licence:     <your licence>
#------------------------------------------------------------------------------
"""

from .cableline import calcCable, calcBandH


def calcSTA(IS, zi, di, sc, befGSK, H_Anfangsmast, H_Endmast, z_null,
            z_ende, d_null, d_ende):
    """
    Berechnet den Bereich der Anfangsseilzugkraft STA, welcher für den
    betrachteten Abschnitt möglich ist!

    Mastabfolge: Talstation - Anfangsmast - Endmast - Bergstation

    INPUT:
    IS        Seilkonfiguration
    zi        Höhenkote bei i. [dm](ü.M.)(Def. zw. Anfangs- und Endmast)
    di        Hor.Distanz von i = 0 zu i [m](Def. zw. Anfangs- und Endmast)
    H_Anfangsmast Höhe des Anfangsmast [m]
    H_Endmast Höhe des Endmast [m]
    z_null    Höhenkote an der Talstation inkl. Mast [m]
    z_ende    Höhenkote an der Bergstation inkl. Mast [m]
    d_null    Hor.Distanz von i = 0 zu i = 0 [m] (=0)
    d_ende    Hor.Distanz von Talstation zu Bergstation
    Ank       Ankerfelder --> Funktioniert noch nicht so recht !
    R_R       Rückerichtung [-1: runter; +1: rauf; 0: kein Grav. SK]
    Detail    Gibt die Genauigkeit an, mit welcher die Anfangsseilzugkraft
    gesucht wird an. Bsp.: Detail = 1 => maximaler Fehler ist 1 kN
    sc        Soil Clearance, gibt den minimalen Bodenabstand an
    """
    # Input Variablen
    zul_SK = IS["zul_SK"]                    # [kN] zulaessige Seilkraft!
    min_Anfangszugkraft = IS["min_SK"]       # [kN]
    CableLineImpossible = False
    # ACHTUNG: Ist nicht immer 1. Main File beachten!!
    Detail = 1.0

    # Test der maximal zulässigen Seilkraft
    Speicher = []
    STA = zul_SK
    [b, h, feld] = calcBandH(zi, di, H_Anfangsmast, H_Endmast, z_null,
                             z_ende, d_null, d_ende)

    out = calcCable(IS, zi, di, sc, befGSK, z_null, STA, b, h, feld)
    Cable_Possible, Seilkraft = out[0], out[1]
    Speicher.append([STA, Cable_Possible, Seilkraft])
    # print Speicher[-1]
    if Cable_Possible is False:
        CableLineImpossible = True
    else:
        STA = min_Anfangszugkraft
        out = calcCable(IS, zi, di, sc, befGSK, z_null, STA, b, h, feld)
        Cable_Possible, Seilkraft = out[0], out[1]
        Speicher.append([STA, Cable_Possible, Seilkraft])
        # print Speicher[-1]
        if Seilkraft == 0:
            CableLineImpossible = True
        else:
            extremeVal = ("maxSTA", "minSTA")
            for val in extremeVal:
                Delta = (zul_SK - min_Anfangszugkraft) / 2
                STA = min_Anfangszugkraft + Delta
                i = 0
                while Delta > Detail and STA >= min_Anfangszugkraft:
                    # if not progress.running:
                    #     return False
                    i += 1
                    index = None
                    for element in enumerate(Speicher):
                        if element[1][0] == STA:
                            index = element[0]
                    if index is None:
                        out = calcCable(IS, zi, di, sc, befGSK, z_null, STA, b, h, feld)
                        Cable_Possible, Seilkraft = out[0], out[1]
                        Speicher.append([STA, Cable_Possible, Seilkraft])
                        # print Speicher[-1]
                    # Unterscheidung: Berechnung von max STA oder min STA
                    else:
                        if val == "maxSTA":
                            Seilkraft = Speicher[index][2]
                        if val == "minSTA":
                            Cable_Possible = Speicher[index][1]
                    if val == "maxSTA":
                        if Seilkraft:
                            Vorzeichen = 1
                        else:
                            Vorzeichen = -1
                    else:
                        if not Cable_Possible:
                            Vorzeichen = 1
                        else:
                            Vorzeichen = -1
                    STA += Delta * Vorzeichen
                    Delta /= 2
    Reihe = []
    # import numpy as np
    # print np.sort(np.array(Speicher), 0)
    for element in Speicher:
        if element[1] and element[2]:   # Wenn beide Werte True sind
            Reihe.append(element)
    #print np.sort(np.array(Speicher)[:,0])
    if Reihe:
        Min = min(Reihe)[0]
        Max = max(Reihe)[0]
    else:
        Min = []
        Max = []
        CableLineImpossible = True
    return CableLineImpossible, Min, Max
