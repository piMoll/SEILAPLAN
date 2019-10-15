# -*- coding: utf-8 -*-
"""
#------------------------------------------------------------------------------
# Name:        Seillinienlayout - Berechnung des Gelaendeprofils
# Purpose:
#
# Author:      Patricia Moll
#
# Created:     14.05.2013
# Copyright:   (c) mollpa 2012
# Licence:     <your licence>
#------------------------------------------------------------------------------
"""
import numpy as np
import os
import math
from osgeo import gdal

from .peakdetect import peakdetect

p = 21
nl = os.linesep


def ismember(a, b):
    bind = {}
    for i, elt in enumerate(b):
        if elt not in bind:
            bind[elt] = i
    return [bind.get(itm, None) for itm in a]  # None can be replaced by any other "not in b" value


def stuePos(IS, gp, noPoleSection, fixedPoles):
    """Evaluation der konkaven Standorte

    Output:
    Maststandort = 1 => Hier können Masten gesetzt werden!
                 = 0 => Hier können keine Masten gesetzt werden!
    z_kon      Bei den Konkaven Standorten wir die Z Koordinate angegeben
               Bei den nicht Kon. Stao wird keine Koord. angegeben (NaN)
    peakLoc     Position der Peaks

    Dokumentation der Variablen:
    zi_short (i)        Z-Koordinate bei i
    di_short (i)        Distanz von 0 zu i
    z2 (i)        Z Unterschied zwischen i und i+2
    d2 (i)        Distanz Unterschied zwischen i und i+2
    zi_diff (i)   Z Unterschied zwischen i und i+1
    di_diff (i)   Distanz Unterschied zwischen i und i+1
    z_dir (i)     Z Unterschied bei i+1 für eine Gerade von i zu i+2
    v (i)         Unterscheidungsvariable ob konkav oder konvex bei Pkt i
    """

    # Analyse des Geländes um konkave Stellen zu finden
    ###################################################
    # Erhöhungen im Gelände werden auf zwei Arten gesucht und
    # für die definitiven Positionen der Sützen die Schnittmenge ermittelt
    di = gp.di.astype(int)
    profilLen = di.size
    # Suche ab 10m Horizontaldistanz ab Anfangs- und Endpunkt
    buf = 10
    lim_u = buf
    lim_o = di[-1] - buf + 1
    diff = np.zeros(profilLen)
    diff[lim_u:lim_o] = gp.zi_n[lim_u:lim_o] - (gp.zi_n[lim_u-buf:lim_o-buf]
                                             + gp.zi_n[lim_u+buf:lim_o+buf]) / 2

    # Peaks mit Programm peakdetect ermitteln
    peakLoc_raw = peakdetect(diff, di, 1)[0]        # Ergibt nicht die exakt gleichen Resultate wie die Matlab Version
    peakIdx = np.array(peakLoc_raw, dtype=int)[:,:1].flatten()
    ld = np.where(np.array(diff)>10)[0]
    # Verschneiden
    peakLoc = np.intersect1d(peakIdx, ld)

    # Bereiche ohne Stützen (benutzerdefiniert) aufbereiten
    noStue = np.zeros(gp.di_s.size, dtype=int)
    for profileRange in noPoleSection:
        anf = min(profileRange)
        end = max(profileRange)
        noStue += (gp.di_s > anf) * (gp.di_s < end)
    # Stützenpositionen sind definiert durch Peaks, fixe Stützenpositionen
    #   und benutzerdefinierte Bereiche ohne Stützen
    possiblePos = np.hstack([gp.di_s[noStue == 0], peakLoc,
                             fixedPoles['HM_fix_d']])
    possiblePos = np.sort(possiblePos).astype('int')

    locb = np.unique(ismember(possiblePos, di))
    # xi = gp['xi'][locb]      # Nur für Baum Support nötig
    # yi = gp['yi'][locb]      # Nur für Baum Support nötig
    gp.zi_s = gp.zi_n[locb]
    gp.di_s = di[locb]

    # Bodenfreiheit
    ###############
    # Hier muss der minimale Bodenabstand nicht eingehalten werden
    bodenabst = IS['Bodenabst_min']  # float
    clearA = IS['Bodenabst_A']       # int
    clearE = IS['Bodenabst_E']       # int

    groundClear = np.ones(profilLen) * bodenabst
    groundClear[di < clearA+1] = 0
    groundClear[di > (di[-1]-clearE)] = 0
    gp.sc = groundClear
    gp.sc_s = groundClear[locb]

    # Befahrbarkeit
    ###############
    befGSK_A = IS['Befahr_A']        # int
    befGSK_E = IS['Befahr_E']        # int

    befahrbar = np.ones(profilLen)
    befahrbar[di < befGSK_A + 1] = 0
    befahrbar[di > (di[-1] - befGSK_E)] = 0
    gp.befGSK = befahrbar
    gp.befGSK_s = befahrbar[locb]

    # Letztes Element hinzufügen
    ############################
    di_ind = np.copy(locb)
    # gp["last_element_add"] = False
    if gp.di[-1] > gp.di_s[-1]:
        # vorher di / zi
        gp.di_s = np.append(gp.di_s, gp.di_n[-1])
        gp.zi_s = np.append(gp.zi_s, gp.zi_n[-1])
        gp.sc_s = np.append(gp.sc_s, gp.sc[-1])
        gp.befGSK_s = np.append(gp.befGSK_s, gp.befGSK[-1])
        di_ind = np.append(locb, gp.di[-1])
        # gp['last_element_add'] = True

    # Inhalt von EvalKonkav.m
    # -----------------------
    # Konkave Gelaendeformen herausfiltern
    ######################################
    di_diff = np.append(gp.di_s[1:] - gp.di_s[:-1], np.nan)
    zi_diff = np.append(gp.zi_s[1:] - gp.zi_s[:-1], np.nan)
    d2 = np.append(di_diff[1:] + di_diff[:-1], np.nan)
    z2 = np.append(zi_diff[1:] + zi_diff[:-1], np.nan)

    z_dir = z2 / d2 * di_diff
    v = zi_diff - z_dir
    v = np.insert(v[:-1], 0, np.nan)

    # Stützenstandorte bestimmen
    ############################
    Maststandort = np.ones(v.size)
    for element in enumerate(v):
        if element[1] <= 0:
            # Ungeeignete Standorte erhalten den Wert 0
            Maststandort[element[0]] = 0
    # Zusätzliche Maststandorte dort wo der Benutzer sie angegeben hat
    idxFix = ismember(fixedPoles['HM_fix_d'], gp.di_s)
    Maststandort[idxFix] = 1
    # Idee an zweiter und zweitletzter Stelle soll immer eine Stütze möglich
    # sein, wegen zum Teil tiefen Anfangs- und Endstützenhoehen (0m)
    Maststandort[[1,-2]] = 1

    # Rückerichtung bestimmen
    #########################
    if IS['GravSK'] == 'nein':
        R_R = 0
    else:
        try:
            index = [i for i in range(len(gp.di_s) - 1, -1, -1) if di[i] < 100][0]
        except IndexError:
            index = -1
        if gp.zi_s[index] > gp.zi_s[0]:
            R_R = -1    # runter
        else:
            R_R = 1     # rauf

    return gp, Maststandort, peakLoc, di_ind, R_R


def markFixStue(stuetzIdx, fixedPoles):
    # Fixe Stützen
    fixStueX = fixedPoles['HM_fix_d']
    fixStueZ = fixedPoles['HM_fix_h']

    if not fixStueX:
        return [np.zeros([len(stuetzIdx)])]*2       # Zwei leere Arrays

    findX = [stuetzIdx == idx for idx in fixStueX]
    findFixStueX = np.sum(findX, axis=0)
    findFixStueZ = np.copy(findFixStueX)
    findFixStueZ[np.where(findFixStueZ > 0)] = fixStueZ
    return [findFixStueX, findFixStueZ]
