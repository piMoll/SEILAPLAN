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

from .terrainAnalysis import ismember
from .optiSTA import calcSTA
try:
    import scipy.sparse as sps
except ModuleNotFoundError:
    # Import error is handled in seilaplanPlugin.py run() function
    pass


def optimization(IS, profile, StuetzenPos, progress, fixedPoles, pole_type):
    """Berechnung der optimalen Anordnung der Stützen im Laengenprofil

    Diese Funktion berechnet aufgrund der zulässigen maximalen Seilzugkraft
    eine optimale Anordnung der Stützen im Laengenprofil. Falls das ganze
    Längenprofil nicht mit Seil überspannt werden kann, wird die maximale
    Länge ermittelt und für diese die optimale Seilzugkraft ermittelt.
    Die Funktion rechnet mit der 3 Span Methode nach Zweifel!

    Input:
    di: Distanz im Laengenprofil [m]
    zi: Höhenkoten im Laengenprofil [dm] --> Vorsicht !!!!
    IS: Informationen über die Seilkonfigurationen
    R_R: Rückerichtung [-1: runter; +1: rauf; 0: kein Grav. SK]
    stuetzi: Max Höhe einer nat. Stuetze bei i --> noch nicht implementiert!

    Output:
    Loesung_Pos: Position der Masten im Laengenprofil [m] inkl. Landing und
    Endmast
    Loesung_HM: Höhe der Masten [m] inkl. Landing und Endmast
    IndStuetzen: Indices der gesetzten Stützen
    Value: Zielfunktionswert der Lösung
    OptSTA: Optimale Werte der Anfangszugkraft STA
    """
    
    # TODO: Matrix  Grossbuchstaben, Array = Kleinbuchstaben

    # Vektoren in neuen Variabeln abspeichern
    di = profile.di_s
    zi = profile.zi_s
    zi_n = profile.zi_n
    di_n = profile.di_n
    sc = profile.sc
    befGSK = profile.befGSK
    min_HM = IS["HM_min"]                # int
    max_HM = IS["HM_max"]                # int
    Abstufung_HM = IS["HM_Delta"]        # int
    Min_Dist_Mast = int(IS["Min_Dist_Mast"])  # int
    dfix = np.array(fixedPoles['HM_fix_d'])
    hfix = np.array(fixedPoles['HM_fix_h'])
    sfix = dfix.size
    # treeSupp = gp.tree

    # Initialisierung der Matrizen mit Knoten für Optimierungsproblem
    # -------------------------------------------------------------------------

    posAnz = int(np.sum(StuetzenPos))
    posIdx = np.where(StuetzenPos == 1)[0][1:-1]
    posIdxEnd = StuetzenPos.size-1      # Annahme: Letzte Position in StuetzenPos ist immer 1 ==> Endstütze RICHTIG???
    hStufung = range(min_HM, max_HM+1, Abstufung_HM)

    # Anfangsstütze
    # Die Höhe der Anfangsstütze ist entweder durch die Höhe des Seilmastkrans
    #  fixiert oder hat eine variable Höhe von 0 Meter (=Verankerung) bis HM_max
    if pole_type in ['pole', 'pole_anchor']:
        # Anfangsstütze mit variabler Höhe
        hStufungAnf = range(0, max_HM+1, Abstufung_HM)
        stufenAnzAnf = len(hStufungAnf)
    else:
        # Fixe Höhe des Seilkranmasts
        hStufungAnf = IS["HM_Kran"]
        stufenAnzAnf = 1

    # Die Endstütze hat eine Höhe zwischen 0 und max_HM Meter
    hStufungEnd = range(0, max_HM + 1, Abstufung_HM)
    stufenAnzEnd = len(hStufungEnd)
    
    arraySize = stufenAnzAnf + (posAnz - 2) * len(hStufung) + stufenAnzEnd

    # Pos = Längenposition für den Knoten i
    Pos = np.empty(arraySize).astype(int)
    Pos[0:stufenAnzAnf] = 0
    Pos[stufenAnzAnf:-stufenAnzEnd] = np.ravel(np.array([posIdx]*len(hStufung)), order = 'F')
    Pos[-stufenAnzEnd:] = [posIdxEnd] * stufenAnzEnd

    # HM = Höhe der Stütze des Knoten i
    HM = np.empty(arraySize)
    HM[0:stufenAnzAnf] = hStufungAnf
    HM[stufenAnzAnf:-stufenAnzEnd] = np.tile(hStufung, posAnz-2)
    HM[-stufenAnzEnd:] = hStufungEnd

    # Position der Stützen in hochaufgelöstem Horizontaldistanz-Vektor gp[di]
    locb = np.array(ismember(di, profile.di))
    Pos_gp = locb[Pos]

    # Aufbau der Optimierungs-Matrix
    # -------------------------------------------------------------------------
    PosG = np.meshgrid(Pos, Pos)
    diPos = di[Pos]
    diG = np.meshgrid(diPos, diPos)
    #
    test1G = PosG[0] != PosG[1]
    test2G = (diG[1] - diG[0] - Min_Dist_Mast) > 0.001
    test3G = PosG[0] == Pos[0]
    test4G = PosG[1] == Pos[-1]
    testRes = (test1G * test2G) + ((test3G + test4G) * test1G)
    testRes = np.swapaxes(testRes, 0, 1)
    # Indices der möglichen Knoten generieren
    [aa, ee] = np.where(testRes == True)        # aa_n.size = 4638, max(aa_n) = 96
    optiLen = aa.size     # Anzahl Optimierungsdurchläufe
    a = Pos[aa]                                   # a.size = 4638, max(a) = 28
    e = Pos[ee]
    HeightA = HM[aa]
    HeightE = HM[ee]

    # Falls fixe Stützen vorhanden sind, kann Optimierungs-Problem gekürzt werden
    if sfix > 0:
        pa = di[a].astype(int) # di[Pos[a]]
        pe = di[e].astype(int)
        # n-dimensionales Array (n=sfix), in jeder Dim ein anderer Wert aus dfix/hfix
        DFix = np.add(np.zeros((sfix, optiLen)), np.reshape(dfix, (sfix, 1))).astype(int)
        HFix = np.add(np.zeros((sfix, optiLen)), np.reshape(hfix, (sfix, 1))).astype(int)
        # Abspeichern wo Höhe nicht definiert wurde (== False)
        HFix_notEmpty = HFix != -1
        # Tests um festzustellen ob Knoten nötig ist
        Erg = (pa < DFix) * (pe > DFix)
        ERG = np.sum(Erg, axis=0, dtype=bool)
        Ca = pa == DFix
        Ce = pe == DFix
        Cha = HFix_notEmpty * (HeightA.astype(int) != HFix)
        Che = HFix_notEmpty * (HeightE.astype(int) != HFix)
        Cc = (Cha * Ca) + (Che * Ce)
        CC = np.sum(Cc, axis=0, dtype=bool)

        AA = ERG + CC       # alles was True ist, muss gelöscht werden
        # Knoten aktualisieren
        newIdx = np.where(AA == False)[0]        # neue, verkürze Indices
        aa = aa[newIdx]
        ee = ee[newIdx]
        optiLen = aa.size     # Anzahl Optimierungsdurchläufe aktualisieren
        HeightA = HM[aa]
        HeightE = HM[ee]
    Pos_gp_A = Pos_gp[aa]
    Pos_gp_E = Pos_gp[ee]

    # Bestimmen der min. und max. Zeilvorzugspannung für jede Knotenverbindung
    # -------------------------------------------------------------------------
    MinSTA = np.zeros(optiLen)
    MaxSTA = np.zeros(optiLen)
    # Startwerte
    z_null = zi[0] * 0.1 + HM[0]
    z_ende = zi[-1] * 0.1 + HM[-1]
    d_null = di[0]
    d_ende = di[-1]

    # Progressbar einrichten
    progress.sig_range.emit([0, optiLen*1.02])
    progress.sig_text.emit("Berechnung der optimalen Stützenpositionen...")

    for i in range(optiLen):
        if progress.isCanceled():
            # Überprüfen ob vom Benutzer ein Abbruch durchgeführt wurde
            return False
        progress.sig_value.emit(i)
        zi_part = zi_n[Pos_gp_A[i]:Pos_gp_E[i]+1]
        di_part = di_n[Pos_gp_A[i]:Pos_gp_E[i]+1]
        sc_part = sc[Pos_gp_A[i]:Pos_gp_E[i]+1]
        befGSK_part = befGSK[Pos_gp_A[i]:Pos_gp_E[i]+1]

        # Zweifel-Methode
        [CableLineImpossible,
        Min, Max] = calcSTA(IS, zi_part, di_part, sc_part,
                            befGSK_part, HeightA[i], HeightE[i],
                            z_null, z_ende, d_null, d_ende)
        if not CableLineImpossible:
            MinSTA[i] = Min
            MaxSTA[i] = Max

    # Shortest Path bestimmen
    # -------------------------------------------------------------------------

    # [Loesung_HM, stueIdx,
    #     Value, OptSTA] = findOptiSolution(zi, di, HeightE, Pos, HM, MinSTA,
    #                                    MaxSTA, aa, ee, arraySize, IS)
    natStuetze = IS['HM_nat']
    kStuetz = HeightE > natStuetze
    KostStue = (HeightE + 100)**2 * (1 + (4*(kStuetz + 0)))
    indexMax = np.where(Pos == np.max(Pos))[0]
    emptyMatrix = np.zeros((arraySize+1, arraySize+1))      # Entspricht N+2

    min_SK = IS['min_SK']
    zul_SK = IS['zul_SK']
    mem = np.array([np.inf] * (zul_SK+1))
    memLength = np.zeros(zul_SK+1)
    min_path = ''
    min_dist = float('inf')
    Max_LengthInLP = 0

    for sk in range(min_SK, zul_SK+1):
        G = emptyMatrix
        ind = (MinSTA < sk) & (MaxSTA > sk)
        G[aa, ee] = KostStue * ind
        G[indexMax, arraySize] = 1

        G_n = G.copy()
        size_of_matrix_G = arraySize + 1
        G_n = np.zeros((size_of_matrix_G + 1, size_of_matrix_G + 1))
        G_n[:-1, :-1] = G
        ind_start = np.where(Pos == 0)[0]
        
        # Matrix erweitern
        G_n[ind_start, size_of_matrix_G] = 1
        G_n[size_of_matrix_G, ind_start] = 1
        # Shortest Path
        Weight = sps.csc_matrix(G_n)
        dist, predecessors = sps.csgraph.dijkstra(Weight, directed=True,
                                indices=size_of_matrix_G, return_predecessors=True)
        dist = dist[:- 1]
        
        LengthInLP = np.where(dist < float('inf'))[0][-1]
        dist = dist[LengthInLP]-1

        # Route of shortest path
        i = LengthInLP
        path = []

        while i > stufenAnzAnf:
            path.append(i)
            i = predecessors[i]
        path.append(0)

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

    min_path = min_path[::-1]
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

    return Loesung_HM, stueIdx, Value, OptSTA, optiLen
