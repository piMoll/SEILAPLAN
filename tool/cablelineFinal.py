# -*- coding: utf-8 -*-
"""
#------------------------------------------------------------------------------
# Name:        Seiloptimierungstool
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
from math import pi, cos, sin, inf


def xfrange(start, stop, step):
    while start < stop:
        yield start
        start += step


def preciseCable(IS, poles, STA):
    """Berechnet die exakte Seilmechanik für ein vorgegebenes Seilsystem:
    Seilstatik (gemäss dem Paper von Zweifel 1960)
    Fall: Stützen unbeweglich, Seile auf Zwischenstützen gleitend
         Inputdaten:
    Felddimensionen:
    b: Breite der Seilfelder [m] Bsp.: [98.2700, 184.8300]
    h: Höhe der Seilfelder   [m] Bsp.: [56.211, 55.22]
    HM: Höhe der Stützen     [m] Bsp.: [12, 12, 12]
    IS: Eigenschaften des Seilsystems
    AnkerIncluded: Ist der Anker bereits in den Seilfeldern inbegriffen?
    (True: ja, False: nein)
         Output:
    Der Output erfolgt als array in EigSeillinie
    Bem.: Die Ausgabe der x Koordinaten hat als Ursprung den Anfangspunkt
    (Auf! der ersten Stütze)
    .l:               y-Koordinaten des Laengenprofils
    .x_leer:          x-Koordinaten des Leerseils
    .x_last_zweifel   x-Koordinaten des Lastseils nach Zweifel (Zw)
    .x_last_pestal    x-Koordinaten des Lastseils nach Pestal (Pe)
    .Kraft_Mast       Einwirkende Kraft auf den Masten
    .STfm_Last        Seilzugkraft in Feldmitte unter Last (Zw)
    .y_LeerSeil       Durchhang in Feldmitte des Leerseils
    .d_ST_out         Erhöhung der Seilzugkraft bei Belastung
    .Hm   Horizontalkomponente der Seilzugkraft in Feldmitte unter Last (Zw)
    .Hs   Horizontalkomp. d. Seilzugkraft an den Stützen (Leerseilverhältn.)
    .ym   Durchhang in Feldmitte unter Last (Zw)"""

    Q = IS["Q"]        # [kN]
    qT = IS["qT"]      # [kN/m]
    F = IS["A"]        # [mm^2]
    E = IS["E"]        # [kN/mm^2]
    #beta = IS["beta"]     # [1/°C] Ausdehnungskoeffizient von Stahl
    Federkonstante = inf        # Federkonstante der Verankerung
    qz1 = IS["qz1"]     # [kN/m] Zugseilgewicht links
    qz2 = IS["qz2"]     # [kN/m] Zugseilgewicht rechts

    # Field dimension
    b, h = poles.getCableFieldDimension()
    # Round the field dimensions do dm because this is going to be the
    # the resolution of the cable calculation
    b = np.round(b, 1)
    h = np.round(h, 1)

    anzFelder = b.size
    anzStue = anzFelder+1
    bquad = b**2
    seil_possible = True

    if np.where(b == 0)[0].size == 0:
        korrektur = 0
    else:
        korrektur = h[0]

    z = np.zeros(anzStue)
    l = np.zeros(anzStue)
    z[0] = korrektur
    z[1:] = np.cumsum(h)
    zfm = z[:-1] + h*0.5
    b_cum = np.cumsum(b)
    l[1:] = b_cum

    # Berechnung der Sehne
    c = (bquad+h**2)**0.5
    c_sum = np.sum(c)
    # Mit Berücksichtigung des Zugseilgewichtes
    q_strich = qT + (qz1 + qz2)/2

    # Leerseil
    # --------
    zfmqT = zfm * qT
    STfm = STA + zfmqT  # Seilzugkraft in Feldmitte
    HT = (STfm * b) / c # Horizontalkomponente der Seilzugkraft
    # Überlänge der Lastlänge gegenüber dem Sehnenzug (Leerfeld)
    delta_s = ((bquad**2 * qT**2) / (24 * c * HT**2)) * \
              (1 + (3*bquad + 8 * h**2) / (240 * c**2) *
               (b * qT / HT)**2)

    delta_s_sum = np.sum(delta_s)
    UeberLaenge_Leerseil = delta_s_sum
    Laenge_Leerseil = c_sum + delta_s_sum
    Laenge_Leerseil_bei_0_kN = Laenge_Leerseil + Laenge_Leerseil * STA/ (F*E)

    # Vollseil
    # --------
    # Iteration zur Berechnung des d_ST, welches unter dem Gewicht von Q
    # entsteht. Berechnung könnte noch beschleunigt werden, falls nicht alle
    # Felder sondern nur das betreffende berechnet werden!
    CableImpossible = False
    d_ST_out = np.zeros(anzFelder)     # Änderung der Seilzugkraft unter Last
    gen = 6         # Genauigkeit der Iteration: 6 sollte ausreichen
    basis = 2       # Hilfsgrösse für die Iteration
    for n in range(anzFelder):
        expon = -5	        # -5 ist Standard
        d_ST = 0.	        # Änderung der Zugkraft
        d_Laenge = 1	    # Startgrösse
        change_dir = False	# Hilfsgrösse für die Iteration
        za = 0	            # Hilfsgrösse für die Iteration
        d_ST_alt = 0	    # Startgrösse
        genauig = basis**-gen
        # Diese Prüfung führt in wenigen Einzelfällen zu anderen Resultaten
        # als das Matlab-Programm weil die Berechnung von d_Laenge nach
        # einigen Iterationen zu Abweichungen im Submilimeter-Bereich führen
        while (abs(d_Laenge) > genauig) and CableImpossible is False:
            STfm_neu = STfm + d_ST
            ym = c / (4 * STfm_neu) * (Q + c * qT/2)    # 8a
            # Funktion mit Berücksichtigung des Zugseilgewichtes:
            #ym = c / (4 * STfm_neu) * (Q + c * q_strich/2) #(8)
            d_c = 2 * bquad / c**3 * ym**2   # 10a
            # 11a Leerseil
            delta_s_leer = (bquad * c * qT**2) / (24 * STfm_neu**2)
            delta_s_last = delta_s_leer * 0.25
            # delta s für die Belastung im betrachteten Abschnitt
            delta_s = np.copy(delta_s_leer)
            delta_s[n] = delta_s_last[n]
            UeberLaenge_Vollseil = d_c[n] + np.sum(delta_s)

            d_Laenge = UeberLaenge_Vollseil - UeberLaenge_Leerseil \
                            - d_ST/(F*E) * Laenge_Leerseil \
                            - d_ST/(F*E) * poles.anchor['len'] \
                            - d_ST/Federkonstante
            #print "Laenge ={}".format(d_Laenge)
            d_ST_out[n] = d_ST

            # Abfangen von falschen Berechnungen
            if (d_ST == 0) and (d_Laenge < 0):
                CableImpossible = True
            # Steuerung delta ST (Seilzugkraft)
            if d_Laenge > genauig:
                d_ST_alt = d_ST
                d_ST += basis**-expon
                za += 1
            else:
                expon += 1
                d_ST = d_ST_alt + basis**-expon
                change_dir = True
                za = 0
            if za == (basis - 1) and change_dir:
                expon += 1
                d_ST = d_ST_alt + basis**-expon
                za = 0

    # Eigenschaften des Seils
    # -----------------------
    # Seilzugkraft in Feldmitte unter Last [kN]
    STfm_Last = STfm + d_ST_out
    # Horizontalanteil der Seilzugkraft in Feldmitte unter Last [kN]
    Hm = b/c * STfm_Last
    # Durchbiegung in Feldmitte unter Last [m]
    ym = c/(4 * STfm_Last) * (Q + c * q_strich/2)        # 8
    # Horizontalkräfte an den Stützen (Leerseilverhältnisse) [kN]
    Hs = b/c * STfm


    # Genaue Seil-Koordinaten bestimmen
    # ---------------------------------
    # Achtung, komplett anders implementier als in matlab!

    # Um genauere Seildaten zu erhalten, muss Schrittgrösse von defaul=1 auf
    # Submeter reduziert werden. Siehe matlab: DP = 0.01 m
    Q_Null = 0
    step = 0.1
    multipl = 10
    # Round the decimeter values and then convert to int to use as index
    lenSeil = int(round(b_cum[-1] * multipl, 0)) + 1
    
    b1 = np.zeros(lenSeil)      # 1 cm Schritte zwischen den Stützen
    # Leere Koordinaten Arrays initialisieren
    y_leer = np.copy(b1)
    H = np.copy(b1)
    y_last_zweifel = np.copy(b1)
    z_coord_leer = np.copy(b1)
    z_coord_zweifel = np.copy(b1)
    l_coord = np.copy(b1)

    start = 0
    for n in range(anzFelder):
        bn = b[n]
        Hmn = Hm[n]
        s_small = int(round(bn * multipl, 0))
        end = start+s_small+1
        b1 = np.arange(0, bn+step, step)
        b2 = bn - b1
        l_coord[start:end] = l[n] + b1
        y_leer[start:end] = b1*b2/(bn * HT[n]) * (Q_Null + c[n]*qT/2)
        # Interpolationsbeziehung für die Berechnung der Lastwegkurve
        H[start:end] = Hmn * (1- (1-(Hs[n] / Hmn)**2) * (1-2*b1/ bn)**2)**0.5
        y_last_zweifel[start:end] = ym[n] * Hmn / H[start:end] * (1-(1-2*b1/bn)**2)
        # Y-Koordinate (Länge) der Lastwegkurve unter Zweifel
        h_sehne = b1 / bn * h[n]
        # Leerseil
        z_coord_leer[start:end] = h_sehne - y_leer[start:end] + z[n]
        # X-Koordinate der Lastkurve unter Zweifel
        z_coord_zweifel[start:end] = h_sehne - y_last_zweifel[start:end] + z[n]


        start = end-1

        # for b1 in xfrange(0, int(bn)+0.1, 0.1):
        # #for b1 in range(int(b[n])):
        #     di_ex.append(b1)
        #     b2 = bn-b1
        #     y_leer = b1*b2/(bn * HT[n]) * (Q_Null + c[n]*qT/2)
        #     # Interpolationsbeziehung für die Berechnung der Lastwegkurve
        #     H.append(Hmn * (1-(1-(Hs[n] / Hmn)**2) * (1-2*b1 / bn)**2)**0.5)
        #     y_last_zweifel = ym[n] * Hmn / H[-1] * (1-(1-2*b1/bn)**2)
        #     # Y-Koordinate (Länge) der Lastwegkurve unter Zweifel
        #     h_sehne = b1 / bn * h[n]
        #     # Leerseil
        #     z_coord_leer.append(h_sehne - y_leer + z[n])
        #     # X-Koordinate der Lastkurve unter Zweifel
        #     z_coord_zweifel.append(h_sehne - y_last_zweifel + z[n])
        #     l_coord.append(l[n]+b1)

    k = anzFelder - 1
    lastElement = h[k] + z[k]
    z_coord_leer[-1] = lastElement
    z_coord_zweifel[-1]= lastElement
    l_coord[-1] = l[k] + b[k]
    H[-1] = Hm[k] * (1-(1-(Hs[k] / Hm[k])**2) * (1-2*b[k] / b[k])**2)**0.5


    # Seilparameter berechnen
    # -----------------------

    kraft = {}
    # Suche der Indizes zur Berechnung der Seilwinkel
    idxStuetze = np.zeros(anzStue).astype('int')

    idxStuetze[1:] = b_cum * multipl
    idxNachher = idxStuetze[:-1] + 1
    idxVorher = idxStuetze[1:] - 1

    # Last nicht auf Stütze, sondern in unmittelbarer Nähe
    # Berechnung der Sattelkräfte

    # Berechnung der Lastseilwinkel wie bei Leerseil
    tg_phi_ob = (h / 2 + 2 * ym) / (b / 2)
    tg_phi_un = (h / 2 - 2 * ym) / (b / 2)

    # Winkel bei Last unmittelbar in der Nähe der Stütze
    phi = np.array([[np.nan]*anzStue]*2)
    phi_ob = np.array([np.nan]*anzStue)
    phi_un = np.array([np.nan]*anzStue)
    phi_ob[1:] = np.arctan(tg_phi_ob)
    phi_un[:-1] = np.arctan(tg_phi_un)
    phi[0] = phi_ob / pi*180
    phi[1] = phi_un / pi*180
    kraft['Anlegewinkel_Lastseil'] = phi

    # Seilzugkräfte
    Hn = H[idxNachher]
    Hv = H[idxVorher]
    dln = l_coord[idxNachher+1] - l_coord[idxNachher-1]
    dxn = z_coord_zweifel[idxNachher+1] - z_coord_zweifel[idxNachher-1]
    sn = np.array([np.nan]*anzStue)
    sn[:-1] = Hn/dln * (dln**2 + dxn**2)**0.5

    dlv = l_coord[idxVorher+1] - l_coord[idxVorher-1]
    dxv = z_coord_zweifel[idxVorher+1] - z_coord_zweifel[idxVorher-1]
    sv = np.array([np.nan]*anzStue)
    sv[1:] = Hv/dlv * (dlv**2 + dxv**2)**0.5
    # Werte richtig anordnen (links/rechts)
    seilzugkr = np.array([np.nan]*anzStue*2)
    seilzugkr[::2] = sv
    seilzugkr[1::2] = sn
    # Seilzugkraft unmittelbar bei Stütze
    kraft['Seilzugkraft_beiStuetze'] = seilzugkr

    # Untenstehend wird der Nachweis für die Sattelkraft und die Änderung
    # des Winkels berechnet: (gemäss Skript von Oplatka)
    # Muss noch verifiziert werden
    y_LeerSeil = b/ (4*HT) * (c*qT/2)       #Leerseildurchhang

    tg_phi_o = (h/2 + 2*y_LeerSeil) / (b/2)
    tg_phi_u = (h/2 - 2*y_LeerSeil) / (b/2)
    phi_o = np.array([np.nan]*anzStue)
    phi_u = np.array([np.nan]*anzStue)
    phi_o[1:] = np.arctan(tg_phi_o)
    phi_u[:-1] = np.arctan(tg_phi_u)

    dAnkerA = poles.anchor['field'][0]
    zAnkerA = poles.anchor['field'][1]
    dAnkerE = poles.anchor['field'][2]
    zAnkerE = poles.anchor['field'][3]

    # TODO An einem sinnvolleren Ort implementieren
    if poles.A_type == 'crane':
        dAnkerA = 0
    if poles.A_type == 'pole_anchor':
        dAnkerA = 0
    if poles.E_type == 'pole_anchor':
        dAnkerE = 0

    try:
        phi_oA = np.arctan(zAnkerA/dAnkerA)
    except ZeroDivisionError:
        phi_oA = np.nan
    try:
        phi_oE = np.arctan((-1*zAnkerE)/dAnkerE)
    except ZeroDivisionError:
        phi_oE = np.nan
    oldsettings = np.geterr()
    j = np.seterr(all='ignore')

    phi_o[0] = phi_oA
    phi_u[-1] = phi_oE
    phi_o = phi_o
    phi_u = phi_u
    phi_leer = np.array([[np.nan]*anzStue]*2)
    phi_leer[0] = phi_o / pi*180
    phi_leer[1] = phi_u / pi*180
    kraft['Anlegewinkel_Leerseil'] = phi_leer
    phi_leer_knick = (phi_o - phi_u) / pi*180
    kraft['Leerseilknickwinkel'] = phi_leer_knick

    # Berechnung Lastseilknickwinkel mit der Last rechts bzw. links direkt neben der Stütze
    # Hinzufügen des Leerseilwinkels vor dem Anfangspunkt resp. nach dem Endpunkt
    phi_ob[0] = phi_oA
    phi_un[-1] = phi_oE

    # Der grössere Knickwinkel wird als Lastseilknickwinkel ausgegeben
    phi_last_knick_ob = (phi_ob - phi_u) / pi * 180
    phi_last_knick_un = (phi_o - phi_un) / pi * 180
    phi_last_knick = np.fmax(phi_last_knick_un, phi_last_knick_ob)
    kraft['Lastseilknickwinkel'] = phi_last_knick

    zqT = z*qT
    ST = STA + zqT
    Vi = ST * (np.sin(phi_o) - np.sin(phi_u))      # Vi darf nicht negativ sein
    # Nachweis basierend auf Leerseilknickwinkel
    kraft['Nachweis'] = np.where(phi_leer_knick >= 2, ['Ja'], ['Nein'])
    if 'Nein' in kraft['Nachweis'][1:-1]:  # Test für die Zwischenstützen
        seil_possible = False

    Hi = ST * (np.cos(phi_o) - np.cos(phi_u))
    kraft['Sattelkraft_ausSeil'] = np.array([(Vi**2 + Hi**2)**0.5, Vi, Hi])

    # Tragseilkraft
    # Ueberlange Lastlänge gegenüber dem Sehnenzug (Leerfeld):
    Gew_Seil = (c + delta_s) * qT
    KraftTragseil = np.append(Gew_Seil, 0)/2 + np.append(0, Gew_Seil)/2

    # Zugseilkraft
    c_cum = np.append(0, np.cumsum(c))
    Gew_Seil_li = c_cum * IS['qz1']
    Gew_Seil_re = (c_cum[-1] - c_cum) * IS['qz2']
    KraftZugseil = (Gew_Seil_li + Gew_Seil_re) / 2

    sattelkrTotV = Vi + IS['Q'] + KraftZugseil + KraftTragseil
    kraft['Sattelkraft_Total'] = np.array([(sattelkrTotV**2 + Hi**2)**0.5,
                                           sattelkrTotV, Hi])

    kraft['UebrigeKraft_befStuetze'] = IS['Q'] + KraftZugseil + KraftTragseil

    # Sattelkraft für nicht befahrbare Stuetzen
    ###########################################
    # Kraft in unmittelbarer Nähe der Stützen
    # 1. Fall: Lastseil auf der linken Seite
    Vi_nbS_L = sv * (np.sin(phi_ob) - np.sin(phi_u))
    Hi_nbS_L = sv * (np.cos(phi_ob) - np.cos(phi_u))

    # Wird das benötigt?
    # kraft['Sattelkraft_beiStuetze_L'] = np.concatenate((
    #     (Vi_nbS_L**2 + Hi_nbS_L**2)**0.5, Vi_nbS_L, Hi_nbS_L))

    # 2. Fall: Lastseil auf der rechten Seite
    Vi_nbS_R = sn * (np.sin(phi_o) - np.sin(phi_un))
    Hi_nbS_R = sn * (np.cos(phi_o) - np.cos(phi_un))

    # Wird das benötigt?
    # kraft['Sattelkraft_beiStuetze_R'] = np.concatenate((
    #     (Vi_nbS_R**2 + Hi_nbS_R**2)**0.5, Vi_nbS_R, Hi_nbS_R))

    # Sattelkraft bei Stützen berechnen

    # sSt = np.array([[0]*anzSt*2]*3)
    # sSt[0][:anzSt] = (Vi_nbS_L**2 + Hi_nbS_L**2)**0.5
    # sSt[0][anzSt:] = (Vi_nbS_R**2 + Hi_nbS_R**2)**0.5
    # sSt[1][:anzSt] = Vi_nbS_L
    # sSt[1][anzSt:] = Vi_nbS_R
    # sSt[2][:anzSt] = Hi_nbS_L
    # sSt[2][anzSt:] = Hi_nbS_R


    sSt = np.array([np.array([(Vi_nbS_L**2 + Hi_nbS_L**2)**0.5,
                              (Vi_nbS_R**2 + Hi_nbS_R**2)**0.5]),
                    np.array([Vi_nbS_L, Vi_nbS_R]),
                    np.array([Hi_nbS_L, Hi_nbS_R])])
    # richtige Reihenfolge herstellen (immer links, rechts, links, ...)
    sattelkraft = []
    kompCount = 0
    while kompCount < 3:   # für resultierende, horizontale und vertikale Komponente
        werte = [0]*anzStue*2
        j = 0
        for i in range(anzStue):      # es wird die i-te Stütze angesprochen
            komp = sSt[kompCount]
            werte[j:j+2] = ([komp[0][i], komp[1][i]])    # 0 = links, 1 = rechts
            j += 2
        sattelkraft.append(werte)
        kompCount += 1
    kraft['Sattelkraft_beiStuetze'] = np.array(sattelkraft)

    # Max auftretende Seilzugkraft
    STfm_Last_max = np.max(STfm_Last)
    feld_max = np.argmax(STfm_Last)

    # Auftretende Maximalseilzugkraft...
    kraft['MaxSeilzugkraft_L'] = np.array([np.nan]*3)
    #   am höchsten Punkt
    kraft['MaxSeilzugkraft_L'][0] = STfm_Last_max + (np.max(z) - zfm[feld_max]) * qT
    #   an Anker A
    kraft['MaxSeilzugkraft_L'][1] = STfm_Last_max + (z[0] - zfm[feld_max]) * qT
    #   an Anker E
    kraft['MaxSeilzugkraft_L'][2] = STfm_Last_max + (z[-1] - zfm[feld_max]) * qT

    # Auftretende Maximalseilzugkraft...
    kraft['MaxSeilzugkraft'] = np.array([[np.nan]*anzFelder]*3)
    #   in Feldmitte
    kraft['MaxSeilzugkraft'][0] = STfm_Last
    #   horiz. Komponente
    kraft['MaxSeilzugkraft'][1] = Hm
    #   am höchsten Punkt (mit mit Last in Feldmitte)
    kraft['MaxSeilzugkraft'][2] = STfm_Last + (np.max(z) - zfm)*qT

    j = np.seterr(**oldsettings)

    kraft['Durchhang'] = [y_LeerSeil, ym]
    kraft['LaengeSeil'] = [Laenge_Leerseil, Laenge_Leerseil_bei_0_kN, c]

    kraft['Spannkraft'] = [ST[0], ST[-1]]
    kraft['Seilzugkraft'] = [ST, Hs]

    anchorField = poles.getAnchorCable()
    cableline = {
        'xaxis': l_coord + poles.firstPole['dtop'],    # X-data starts at first pole
        'empty': z_coord_leer + poles.firstPole['ztop'],   # Y-data is calculated relative
        'load': z_coord_zweifel + poles.firstPole['ztop'],
        'anchorA': anchorField['A'],
        'anchorE': anchorField['E'],
        'groundclear_di': [],
        'groundclear': [],
        'groundclear_under': [],
        'groundclear_rel': [],
    }

    return cableline, kraft, seil_possible


def preciseCableLight(zi, di, IS, STA, HM, LP):
    qT = IS["qT"]      # [kN/m]

    # Seilfeld berechnen, b = Breite, h = Höhe
    b = di[LP[1:]] - di[LP[:-1]]
    h = zi[LP[1:]] * 0.1 + HM[1:] - zi[LP[:-1]] * 0.1 - HM[:-1]

    anzFelder = b.size
    anzStue = anzFelder+1
    bquad = b**2

    if np.where(b == 0)[0].size == 0:
        korrektur = 0
    else:
        korrektur = h[0]

    z = np.zeros(anzStue)
    l = np.zeros(anzStue)
    z[0] = korrektur
    z[1:] = np.cumsum(h)
    zfm = z[:-1] + h*0.5
    b_cum = np.cumsum(b)
    l[1:] = b_cum

    # Berechnung der Sehne
    c = (bquad+h**2)**0.5

    # Leerseil
    # --------
    zfmqT = zfm * qT
    STfm = STA + zfmqT  # Seilzugkraft in Feldmitte
    HT = (STfm * b) / c # Horizontalkomponente der Seilzugkraft

    y_LeerSeil = b/ (4*HT) * (c*qT/2)       #Leerseildurchhang

    tg_phi_o = (h/2 + 2*y_LeerSeil) / (b/2)
    tg_phi_u = (h/2 - 2*y_LeerSeil) / (b/2)
    phi_o = np.array([np.nan]*anzStue)
    phi_u = np.array([np.nan]*anzStue)
    phi_o[1:] = np.arctan(tg_phi_o)
    phi_u[:-1] = np.arctan(tg_phi_u)

    dAnkerA = IS['Ank'][0][0]
    zAnkerA = IS['Ank'][0][1]
    dAnkerE = IS['Ank'][0][2]
    zAnkerE = IS['Ank'][0][3]
    try:
        phi_oA = np.arctan(zAnkerA/dAnkerA)
    except ZeroDivisionError:
        phi_oA = np.nan
    try:
        phi_oE = np.arctan((-1*zAnkerE)/dAnkerE)
    except ZeroDivisionError:
        phi_oE = np.nan
    # oldsettings = np.geterr()
    # j = np.seterr(all='ignore')

    phi_o[0] = phi_oA
    phi_u[-1] = phi_oE

    # TODO: Werte sind +- 2 Grad anders als in matlab
    leerseilknickwinkel = (phi_o - phi_u) / pi*180

    zqT = z*qT
    ST = STA + zqT
    Vi = ST * (np.sin(phi_o) - np.sin(phi_u))      # Vi darf nicht negativ sein
    seilHebtAb = np.prod(Vi[1:-1] >= 0.01) == 0

    return leerseilknickwinkel, seilHebtAb


def updateWithCableCoordinates(cableline, pointA, azimut):
    cableline['coordx'] = pointA[0] + cableline['xaxis'] * sin(azimut)
    cableline['coordy'] = pointA[1] + cableline['xaxis'] * cos(azimut)
