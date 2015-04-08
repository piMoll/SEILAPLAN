# -*- coding: utf-8 -*-
"""
#------------------------------------------------------------------------------
# Name:         SEILAPLAN
# Purpose:      SEIlkran LAyout PLANer
#
# Author:       Leo Bont und Patricia Moll
#               Professur für Forstliches Ingenieurwesen
#               ETH Zürich
#
# Created:      2013-1015
# Copyright:    (c) mollpa 2013
# Licence:      <your licence>
#------------------------------------------------------------------------------
"""

import numpy as np
import scipy.sparse as sps
from ..packages import networkx as nx
from yenKSP import YenKShortestPaths
from cablelineFinal import preciseCableLight


def findOptiSolution(zi, di, HeightE, Pos, HM, MinSTA, MaxSTA, aa, ee,
                     length, IS):

    natStuetze = IS['HM_nat'][0]
    kStuetz = HeightE > natStuetze
    KostStue = (HeightE + 100)**2 * (1 + (4*(kStuetz + 0)))
    # TODO: Was muss man hier schreiben wenn keine Baumspitzen berücksichtigt werden?
    # KostStue = (HeightE + 100)**2       # Ohne Berücksichtigung nat. Stützen
    indexMax = np.where(Pos==np.max(Pos))[0]
    emptyMatrix = np.zeros((length+1, length+1))      # Entspricht N+2

    min_SK = int(IS['min_SK'][0])
    zul_SK = int(IS['zul_SK'][0])
    mem = np.array([np.inf] * (zul_SK+1))
    memLength = np.zeros(zul_SK+1)
    min_path = ''
    min_dist = float('inf')
    Max_LengthInLP = 0

    # Gleichzeitige überprüfung des Leerseilknickwinkels
    LSKmax = 18        # Maximaler Leerseilknickwinkel
    searchKpaths = 20  # Es werden die 20 günstigsten Pfade untersucht
    mas = { 'STA': [],
            'LSK': [],
            'dist': [],
            'path': [],
            'hebtAb': []
            }
    testAbheben = False
    testKraefteKlein = False



    for sk in range(min_SK, zul_SK+1):
        # try:
            if sk == 100:
                print sk
            # if progress.abort is True:
            #     progress.killed.emit()
            G = emptyMatrix
            # OPTI sk ausserhalb for Schleife erstellen und > < ausserhalb abfragen
            ind = (MinSTA < sk) & (MaxSTA > sk)
            G[aa, ee] = KostStue * ind
            G[indexMax, length] = 1

            # Shortest Path
            Weight = sps.csc_matrix(G)
            dist, predecessors = sps.csgraph.dijkstra(Weight, directed=True,
                                    indices=0, return_predecessors=True)
            LengthInLP = np.where(dist < float('inf'))[0][-1]
            dist = dist[LengthInLP]

            # Extrahiere kürzesten Pfad
            i = LengthInLP
            path = []
            while i != 0:
                path.append(i)
                i = predecessors[i]
            path.append(0)
            path = path[::-1]

            if testAbheben:

                path = [0]
                dist = 0
                LengthInLP = 0
                GG = nx.Graph(G)
                yksp = YenKShortestPaths(GG, cap=None)
                shPath = yksp.findFirstShortestPath(0, length)

                if shPath:
                    path = shPath.nodeList
                    dist = shPath.cost
                    # Letzter Punkt, der im Längeprofil erreicht werden kann
                    LengthInLP = path[-1]

                    print [sk, '--', path, dist]

                    [LSK, seilHebtAb] = testShortestPath(path, length, HM, Pos, zi,
                                                         di, IS, sk)
                    # LSKval = np.sum((LSK[LSK > LSKmax] - LSKmax)**2)
                    # mas['STA'].append(sk)
                    # mas['LSK'].append(LSKval)
                    # mas['dist'].append(dist)
                    # mas['path'].append(path)
                    # mas['hebtAb'].append(seilHebtAb)

                    if (seilHebtAb or np.max(LSK) > LSKmax) and dist < min_dist:
                        # GG = nx.Graph(G)
                        # yksp = YenKShortestPaths(GG, cap=None)
                        # shPath = yksp.findFirstShortestPath(0, length)
                        # path = shPath.nodeList
                        # dist = shPath.cost

                        for k in range(searchKpaths):
                            nxtShPath = yksp.getNextShortestPath()
                            path = nxtShPath.nodeList
                            dist = nxtShPath.cost

                            print [sk, k, path, dist]

                            [LSK, seilHebtAb] = testShortestPath(path, length, HM,
                                                                 Pos, zi, di, IS, sk)
                            # LSKval = np.sum((LSK[LSK > LSKmax] - LSKmax)**2)
                            # mas['STA'].append(sk)
                            # mas['LSK'].append(LSKval)
                            # mas['dist'].append(dist)
                            # mas['path'].append(path)
                            # mas['hebtAb'].append(seilHebtAb)

                            # Falls Lösung gültig ist, ist Suche abgeschlossen
                            if seilHebtAb is False and np.max(LSK) < LSKmax:
                                break

            mem[sk] = dist
            memLength[sk] = LengthInLP
            if LengthInLP >= Max_LengthInLP:
                if LengthInLP > Max_LengthInLP:
                    min_dist = float('inf')
                    min_path = []
                    Max_LengthInLP = LengthInLP
                if dist < min_dist:
                    min_dist = dist
                    min_path = path
        # except TypeError, e:
        #     import traceback
        #     print traceback.format_exc()

    min_path = min_path
    Ind_Max_Length = [var for var in range(zul_SK+1)
                      if memLength[var] == max(memLength)]
    mem_neu = np.array([np.inf] * (zul_SK+1))
    mem_neu[Ind_Max_Length] = mem[Ind_Max_Length]

    # Indizes beachten!
    OptSTA = np.array([var for var in range(zul_SK+1)
                       if mem_neu[var] == min(mem_neu)])

    min_path = min_path[:-1]
    Value = min_dist
    Loesung_HM = [HM[i] for i in min_path]
    stueIdx = [Pos[i] for i in min_path]

    return Loesung_HM, stueIdx, Value, OptSTA


def testShortestPath(path, length, HM, Pos, zi, di, IS, sk):
    if path[0]+1 > length:
        # Pfad umkehren und ohne letztes Element
        pathTemp = path[:-1]
        HM_ = HM[pathTemp]
        Pos_ = Pos[pathTemp]
        [LSK, seilHebtAb] = preciseCableLight(zi, di, IS, sk, HM_, Pos_)

    else:
        LSK = np.array([np.nan])
        seilHebtAb = True
    return LSK, seilHebtAb



