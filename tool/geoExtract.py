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
# TODO: Veraltete scipy bibliothek? Siehe warnung in QGIS
from scipy import interpolate
from osgeo import gdal

from peakdetect import peakdetect

# Spezieller Import, noetig für Operation 'scipy interpolate'
# frozen == Programm wird in EXE verwandelt
# if getattr(sys, 'frozen', None):
#     from scipy.sparse.csgraph import _validation

p = 21
nl = unicode(os.linesep)


def generateDhm(rasterdata, coords):
    """ Raster wird auf die nötige Grösse zugeschnitten und in numpy Array
    exportiert. Extent der Zuschnittmaske ist Anfangs- und Endpunkt + Buffer
    """
    path = rasterdata['path']
    cellsize = rasterdata['cellsize']
    [xMin, yMax, xMax, yMin] = rasterdata['extent']
    [Ax, Ay, Ex, Ey] = coords

    # Minimum und Maximum der benötigten Koordinaten
    # TODO: Gewährleisten, dass 2*p nicht aus raster rausragt!
    pointXmin = min(Ax, Ex) - 2*p
    pointXmax = max(Ax, Ex) + 2*p
    pointYmin = min(Ay, Ey) - 2*p
    pointYmax = max(Ay, Ey) + 2*p

    # Offset in Anz. Zellen von der oberen linken Ecke des suraster berechnen
    xOff = int((pointXmin - xMin)/cellsize)
    yOff = int((yMax - pointYmax)/cellsize)
    xLen = int((pointXmax-pointXmin)/cellsize)
    yLen = int((pointYmax-pointYmin)/cellsize)

    ds = gdal.Open(path)
    band = ds.GetRasterBand(1)
    # ACHTUNG: xoff und yoff von oberer linken Ecke!
    subraster = band.ReadAsArray(xoff=int(xOff), yoff=int(yOff),
                                 win_xsize=xLen, win_ysize=yLen)

    subraster *= 10
    del ds
    extent = [xMin + xOff*cellsize,         # xMin
              xMin + (xOff+xLen)*cellsize,  # xMax
              yMax - (yOff+yLen)*cellsize,  # yMin
              yMax - yOff*cellsize]         # yMax

    rasterdata['extent'] = extent
    rasterdata['subraster'] = subraster

    # ALS ERKLÄRUNG: Gdal Hirarchie
    # Driver
    #   Datasource
    #     Layer
    #         Feature
    #             Geometry
    #                 Point

    # Exportieren nach txt -> Zur Kontrolle des ausgeschnittenen Subraster
    # path2 = os.path.join(os.path.dirname(__file__), "test.txt")
    # rasterheader = "ncols {1}{0}nrows {2}{0}xllcorner {3}{0}yllcorner {4}{0}" \
    #                "cellsize {5}{0}NODATA_value {6}".format(nl,
    #                     subraster.shape[1], subraster.shape[0], extent[0],
    #                     extent[4], cellsize, -9999)
    # np.savetxt(path2, np.round(subraster, 3), header=rasterheader, comments='')
    return rasterdata

def calcProfile(inputPoints, rasterdata, IS, Delta, coeff):
    """ Infotext.
    """
    dhm = rasterdata['subraster']
    # path2 = os.path.join(os.path.dirname(__file__), "test.txt")
    # rasterheader = "ncols {1}{0}nrows {2}{0}xllcorner {3}{0}yllcorner {4}{0}" \
    #                "cellsize {5}{0}NODATA_value {6}".format(nl,
    #                     dhm.shape[1], dhm.shape[0], rasterdata['extent'][0],
    #                     rasterdata['extent'][4], cellsize, -9999)
    # np.savetxt(path2, dhm, header=rasterheader, comments='')

    [xMin, xMax, yMin, yMax] = rasterdata['extent']
    cellsize = rasterdata['cellsize']
    [Xa, Ya, Xe, Ye] = inputPoints

    # Koordinatenarrays des DHMs
    coordX = np.arange(xMin, xMax, cellsize)
    # Negative Start- und Endkoordinaten damit Array aufsteigend ist
    # (Nötig für die Interpolation mit der Methode 'RectBivariateSpline')

    coordY = np.arange(yMax-cellsize, yMin-cellsize, -cellsize)
    # coordY = np.arange(yMax, yMin, cellsize)

    ganzdist = ((Xe-Xa)**2 + (Ye-Ya)**2)**0.5
    xDist = Xe - Xa
    yDist = Ye - Ya
    zwischendist = Delta
    anzTeilstuecke = ganzdist / zwischendist

    if xDist == 0:
        zwischendistY = yDist / anzTeilstuecke
        # yi = np.arange(Ya, Ye, zwischendistY)
        # yi = np.linspace(Ya, Ye-zwischendistY, anzTeilstuecke)
        yi = np.arange(Ya, Ye, zwischendistY)
        xi = np.array([Xa] * len(yi))
        # TODO: Hack
        zwischendistX = 0.000001
    else:
        zwischendistX = xDist / anzTeilstuecke
        # xi = np.linspace(Xa, Xe-zwischendistX, anzTeilstuecke)
        xi = np.arange(Xa, Xe, zwischendistX)

        if yDist == 0:
            yi = np.array([Ya] * len(xi))
            # TODO: Hack
            zwischendistY = 0.000001
        else:
            zwischendistY = yDist / anzTeilstuecke
            # höheninformationen beziehen sich auf die untere linke Ecke jedes
            # pixels, deshalb muss in der y-Richtung die cellsize abgezogen werden
            # yi = np.arange(Ya, Ye, zwischendistY)
            # yi = np.linspace(Ya, Ye-zwischendistY, anzTeilstuecke)
            yi = np.arange(Ya, Ye, zwischendistY)

    # TODO: Beeinflusst dieser Hack die Berechnung?????
    # xi[-1] = float(Xe)
    # yi[-1] = float(Ye)

    # Zusätzliche Daten für Anzeige
    ###############################
    # Längenprofil wird etwas verlängert um Anfangs- und Endpunkt sowie
    #   Ankerfelder übersichtlich darstellen zu können.

    # Anker-Informationen
    d_Anker_A = IS['d_Anker_A'][0]
    d_Anker_E = IS['d_Anker_E'][0]
    b = max([d_Anker_A, d_Anker_E, p])        # p= Standartwert = 21m

    xiA_disp = np.linspace(Xa-zwischendistX, Xa-b*zwischendistX, b)
    yiA_disp = np.linspace(Ya-zwischendistY, Ya-b*zwischendistY, b)
    xiE_disp = np.linspace(xi[-1]+zwischendistX, xi[-1]+b*zwischendistX, b)
    yiE_disp = np.linspace(yi[-1]+zwischendistY, yi[-1]+b*zwischendistY, b)

    # Linear Interpolation
    # kx, ky bezeichnen grad der interpolation, 1=linear
    spline = interpolate.RectBivariateSpline(-coordY, coordX, dhm, kx=1, ky=1)
    zi = spline.ev(-yi, xi)

    # import pydevd
    # pydevd.settrace('localhost', port=53100,
    #                      stdoutToServer=True, stderrToServer=True)

    # Distanz in der Horizontalen
    di = np.array(range(len(zi))) * 1.0

    # Da Y-Achse und DHM gespiegelt sind, müsse Koordianten vertauscht und
    # umgekehrt werden
    # ziA_disp = spline.ev(-1*yiE_disp, xiA_disp)
    # ziE_disp = spline.ev(-1*yiA_disp, xiE_disp)
    # zi_disp = np.concatenate((ziE_disp[::-1], zi, ziA_disp))
    ziA_disp = spline.ev(-1*yiA_disp, xiA_disp)
    ziE_disp = spline.ev(-1*yiE_disp, xiE_disp)
    zi_disp = np.concatenate((ziA_disp[::-1], zi, ziE_disp))

    # Vereinfachung des Längenprofils
    #################################
    # Nur jede x-te (coeff) Position in Array wird in Berechnung berwendet
    zi_short = zi[::coeff]
    di_short = di[::coeff]
    # Abspeichern der Indexpositionen im grossen Array (zi/di)
    di_ind = np.arange(len(di))[::coeff]

    # Normalisierung des gekürzten Längenprofils
    di_norm = di - di[0]        # eigentlich überflüssig
    zi_norm = zi - zi[0]        # matlab: gp.zi, python: gp['zi_n']
    di_short = di_short - di_short[0]
    zi_short = zi_short - zi_short[0]   # matlab: zi

    gp = { 'xi' : xi,
           'yi' : yi,
           'zi' : zi,
           'zi_s' : zi_short,
           'zi_n' : zi_norm,
           'di' : di,
           'di_s' : di_short,
           'di_n' : di_norm,
           'linspaces' : [coordX, coordY]}

    return gp, zi_disp, di_ind

def ismember(a, b):
    bind = {}
    for i, elt in enumerate(b):
        if elt not in bind:
            bind[elt] = i
    return [bind.get(itm, None) for itm in a]  # None can be replaced by any other "not in b" value

def stuePos(IS, gp):
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
    # TODO: Besser schreiben

    # import pydevd
    # pydevd.settrace('localhost', port=53100,
    #                  stdoutToServer=True, stderrToServer=True)

    # Analyse des Geländes um konkave Stellen zu finden
    ###################################################
    # Erhöhungen im Gelände werden auf zwei Arten gesucht und
    # für die definitiven Positionen der Sützen die Schnittmenge ermittelt
    di = gp['di'].astype(int)
    zi_n = gp['zi_n']
    profilLen = di.size
    # Suche ab 10m Horizontaldistanz ab Anfangs- und Endpunkt
    buf = 10
    lim_u = buf
    lim_o = di[-1] - buf + 1
    diff = np.zeros(profilLen)
    diff[lim_u:lim_o] = zi_n[lim_u:lim_o] - (zi_n[lim_u-buf:lim_o-buf]
                                             + zi_n[lim_u+buf:lim_o+buf]) / 2

    # Peaks mit Programm peakdetect ermitteln
    peakLoc_raw = peakdetect(diff, di, 1)[0]        # Ergibt nicht die exakt gleichen Resultate wie die Matlab Version
    peakIdx = np.array(peakLoc_raw, dtype=int)[:,:1].flatten()
    ld = np.where(np.array(diff)>10)[0]
    # Verschneiden
    peakLoc = np.intersect1d(peakIdx, ld)

    # Bereiche ohne Stützen (benutzerdefiniert) aufbereiten
    noStue = np.zeros(gp['di_s'].size, dtype=int)
    for profileRange in IS['noStue']:
        anf = min(profileRange)
        end = max(profileRange)
        noStue += (gp['di_s']>anf) * (gp['di_s']<end)
    # Stützenpositionen sind definiert durch Peaks, fixe Stützenpositionen
    #   und benutzerdefinierte Bereiche ohne Stützen
    possiblePos = np.hstack([gp['di_s'][noStue==0], peakLoc, IS['HM_fix_d']])
    possiblePos = np.sort(possiblePos).astype('int')

    locb = np.unique(ismember(possiblePos, di))
    # xi = gp['xi'][locb]      # Nur für Baum Support nötig
    # yi = gp['yi'][locb]      # Nur für Baum Support nötig
    gp['zi_s'] = gp['zi_n'][locb]
    gp['di_s'] = di[locb]

    # Bodenfreiheit
    ###############
    # Hier muss der minimale Bodenabstand nicht eingehalten werden
    bodenabst = IS['Bodenabst_min'][0]  # float
    clearA = IS['Bodenabst_A'][0]       # int
    clearE = IS['Bodenabst_E'][0]       # int

    groundClear = np.ones(profilLen) * bodenabst
    groundClear[di<clearA+1] = 0
    groundClear[di>(di[-1]-clearE)] = 0
    gp['sc'] = groundClear
    gp['sc_s'] = groundClear[locb]

    # Befahrbarkeit
    ###############
    befGSK_A = IS['Befahr_A'][0]        # int
    befGSK_E = IS['Befahr_E'][0]        # int

    befahrbar = np.ones(profilLen)
    befahrbar[di<befGSK_A+1] = 0
    befahrbar[di>(di[-1]-befGSK_E)] = 0
    gp['befGSK'] = befahrbar
    gp['befGSK_s'] = befahrbar[locb]

    # Letztes Element hinzufügen
    ############################
    di_ind = np.copy(locb)
    gp["last_element_add"] = False
    if gp['di'][-1] > gp['di_s'][-1]:
        # vorher di / zi
        gp['di_s'] = np.append(gp['di_s'], gp['di_n'][-1])
        gp['zi_s'] = np.append(gp['zi_s'], gp['zi_n'][-1])
        gp['sc_s'] = np.append(gp['sc_s'], gp['sc'][-1])
        gp['befGSK_s'] = np.append(gp['befGSK_s'], gp['befGSK'][-1])
        di_ind = np.append(locb, gp['di'][-1])
        gp['last_element_add'] = True

    # Inhalt von EvalKonkav.m
    # -----------------------
    # Konkave Gelaendeformen herausfiltern
    ######################################
    di_diff = np.append(gp['di_s'][1:] - gp['di_s'][:-1], np.nan)
    zi_diff = np.append(gp['zi_s'][1:] - gp['zi_s'][:-1], np.nan)
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
    idxFix = ismember(IS['HM_fix_d'], gp['di_s'])
    Maststandort[idxFix] = 1
    # Idee an zweiter und zweitletzter Stelle soll immer eine Stütze möglich
    # sein, wegen zum Teil tiefen Anfangs- und Endstützenhoehen (0m)
    Maststandort[[1,-2]] = 1

    # Rückerichtung bestimmen
    #########################
    if IS['GravSK'][0] == 'nein':
        R_R = 0
    else:
        try:
            index = [i for i in range(len(gp['di_s']) -1, -1, -1) if di[i] < 100][0]
        except IndexError:
            index = -1
        if gp['zi_s'][index] > gp['zi_s'][0]:
            R_R = -1    # runter
        else:
            R_R = 1     # rauf

    return gp, Maststandort, peakLoc, di_ind, R_R


def calcAnker(IS, inputPoints, rasterdata, gp):
    """
    """
    dhm = rasterdata['subraster']
    [Xa, Ya, Xe, Ye] = inputPoints
    # Letzte Koordinate in xi/yi entspricht nicht exakt den Endkoordinaten
    Xe_ = gp['xi'][-1]
    Ye_ = gp['yi'][-1]

    AnkA_dist = IS['d_Anker_A'][0]
    AnkE_dist = IS['d_Anker_E'][0]
    stueA_H = IS['HM_Anfang'][0]
    stueE_H = IS['HM_Ende_max'][0]

    # X- und Y-Koordinate der Geodaten im Projektionssystem berechnen
    dx = float(Xe - Xa)
    dy = float(Ye - Ya)
    if dx == 0:
        dx = 0.0001
    azimut = math.atan(dy/dx)
    if dx > 0:
        azimut += 2 * math.pi
    else:
        azimut += math.pi
    # X- und Y-Koordinaten der beiden Ankerpunkte am Boden
    AnkXa = Xa - AnkA_dist * math.cos(azimut)
    AnkYa = Ya - AnkA_dist * math.sin(azimut)
    AnkXe = Xe_ + AnkE_dist * math.cos(azimut)
    AnkYe = Ye_ + AnkE_dist * math.sin(azimut)

    # Linear Interpolation
    # Koordinatenarrays des DHMs
    coordX = gp['linspaces'][0]
    coordY = gp['linspaces'][1]
    # kx, ky bezeichnen grad der interpolation, 1=linear
    spline = interpolate.RectBivariateSpline(-coordY, coordX, dhm, kx=1, ky=1)
    xi = np.array([AnkXa, Xa, Xe_, AnkXe])
    yi = np.array([AnkYa, Ya, Ye_, AnkYe])
    # Z-Koordinate der Anker für Anfangs- und Endpunkte
    zAnker = spline.ev(-yi, xi)     # Höhenangaben am Boden

    AnkA_z = stueA_H + 0.1*(zAnker[1] - zAnker[0])
    AnkE_z = stueE_H + 0.1*(zAnker[2] - zAnker[3])

    if AnkA_dist == 0:
        AnkA_z = 0.0
    if AnkE_dist == 0:
        AnkE_z = 0.0

    Ank = [AnkA_dist, AnkA_z, AnkE_dist, AnkE_z]

    # Ausdehnungen der Anker Felder, alles in [m]
    #Ank = [d_Anker_A, z_Anker_A * 0.1, d_Anker_E, z_Anker_E * 0.1]
    Laenge_Ankerseil = (AnkA_dist**2 + AnkA_z**2)**0.5 + \
                       (AnkE_dist**2 + AnkE_z**2)**0.5

    # Eventuell nicht nötig
    #IS['z_Anker_A'][0] = z_Anker_A
    #IS['z_Anker_E'][0] = z_Anker_E
    return [Ank, Laenge_Ankerseil, zAnker]

def updateAnker(Anker, HM, HMidx):
    """
     Da die Endstütze vom Benutzer variabel definiert werden kann
    (z.B. zwischen 0 und 10m), müssen die Ankerfelder der definitiven End-
    stützenhöhe angepasst werden.

    :param Anker: Eigenschaften der Ankerfelder aus IS['Ank']
    :param HM: Höhen der berechneten Stützen
    :param HMidx: Indizes, bzw. Hotizontaldistanzen der Stützen vom Nullpunkt
    :return: Updated properties of anchors
    """
    zAnker = Anker[2]
    [AnkA_dist, AnkA_z, AnkE_dist, _] = Anker[0]
    AnkE_z = HM[-1] + 0.1*(zAnker[2] - zAnker[3])

    if AnkA_dist == 0:
        AnkA_z = 0.0
    if HM[-1] == 0:
        AnkE_dist = 0.0
    if AnkE_dist == 0:
        AnkE_z = 0.0

    Ank = [AnkA_dist, AnkA_z, AnkE_dist, AnkE_z]
    Laenge_Ankerseil = (AnkA_dist**2 + AnkA_z**2)**0.5 + \
                       (AnkE_dist**2 + AnkE_z**2)**0.5

    # Daten für Darstellung im Plot
    stue = np.array([0, HM[0], HM[-1], 0])
    zAnkerseil = zAnker*0.1 + stue      # Höhenangaben des Ankerseils
    xAnkerseil = np.array([-AnkA_dist, 0, HMidx[-1], HMidx[-1] + AnkE_dist])
    Ankerseil = [zAnkerseil, xAnkerseil]

    return [Ank, Laenge_Ankerseil, zAnker, Ankerseil]

def markFixStue(stuetzIdx, IS):
    # Fixe Stützen
    fixStueX = IS['HM_fix_d']
    fixStueZ = IS['HM_fix_h']

    if not fixStueX:
        return [np.zeros([len(stuetzIdx)])]*2       # Zwei leere Arrays

    findX = [stuetzIdx == idx for idx in fixStueX]
    findFixStueX = np.sum(findX, axis=0)
    findFixStueZ = np.copy(findFixStueX)
    findFixStueZ[np.where(findFixStueZ > 0)] = fixStueZ
    return [findFixStueX, findFixStueZ]