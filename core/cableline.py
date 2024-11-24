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
from math import inf


def calcBandH(zi, di, H_Anfangsmast, H_Endmast, z_null, z_ende, d_null, d_ende):
    # Definition der Seilfelder
    hilfh = [z_null, zi[0] * 0.1 + H_Anfangsmast,
             zi[-1] * 0.1 + H_Endmast, z_ende]
    hilfb = [d_null, di[0], di[-1], d_ende]
    h = [a - b for a, b in zip(hilfh[1:4], hilfh[0:3])]
    b = [a - b for a, b in zip(hilfb[1:4], hilfb[0:3])]

    # Nullfelder löschen
    indices = [i for i in range(len(b) -1, -1, -1) if b[i] == 0]
    for index in indices:
        del b[index]
        del h[index]
    # Cast lists to arrays
    b = np.array(b, dtype=float)
    h = np.array(h, dtype=float)

    feld = 1
    if indices:     # Überprüfen ob Liste mit Werten gefüllt ist
        if indices[-1] == 0 or b.size == 1:
            feld = 0
    return b, h, feld


def checkCable(zi, si, sc, befGSK, SeilSys, R_R):
    """ Prüft ob an allen Punkten die minimale Bodenfreiheit gegeben ist
    R_R = Rückerrichtung  1 = rauf, -1 = runter
    Seilsys     0 = Zweiseil-System, 1 = Mehrseil-System
    R_R = 0 --> egal ob rauf oder runder weil kein Gravitationsseilkran
    """
    sc_dm = np.array(sc*10, dtype=int)
    sc_dm[sc_dm == 0] = -10
    bodenabst = np.sum((si-zi) > sc_dm, axis=0) == sc_dm.size

    if SeilSys == 1:        # Mehrseil-System
        Cable_Possible = bodenabst
    else:                   # Zweiseil-System
        if R_R == -1:       # runter
            Cable_Possible = bodenabst and (si[1] > si[0] or befGSK[0]==0)
        else:               # für Gravitationslift (rauf rücken)
            Cable_Possible = bodenabst and (si[-2] > si[-1] or befGSK[-1]==0)
    return Cable_Possible


class vectorSum:
    """ Ersetzt Pythons numpy.sum, da es bei kurzen Arrays performanter ist,
    wenn Vektorelemente einzeln (vektor[i]) summiert werden.
    """
    def __init__(self, sizeB):
        self.sizeB = sizeB
        self.functionToCall = 'calcSum{}'.format(sizeB)
        
    def calcSum1(self, vector):
        return vector
    
    def calcSum2(self, vector):
        return vector[0] + vector[1]
    
    def calcSum3(self, vector):
        return vector[0] + vector[1] + vector[2]


def calcCable(IS, zi, di, sc, befGSK, z_null, STA, b, h, feld):
    """ Berechnung der Seillinie basierend auf der Methode von Zweifel

    Berechnung der Seillinie basierend dem Paper von Zweifel 1960, jedoch mit
    der Vereinfachung, dass hier die Stützenabfolge Talstation -
    Anfangsstütze Seilfeld - Endstütze Seilfeld - Bergstation angenommen
    wird. Diese Funktion kann daher in Verbindung mit einem
    Netzwerkalgorithmus aufgerufen werden. Die Abweichungen vom original
    Verfahren von Zweifel sind äusserts gering und immer auf der sicheren
    Seite.
    Fall: Stützen unbeweglich, Seile auf Zwischenstützen gleitend, Tragseile
    beidseitig verankert
    Bem.: Die Nomenklatur richtet sich nach der Bezeichnung in Zweifel 1960
    Bem.: Beim Ankerfeld ist die Seillänge des Ankers mit berücksichtigt,
    jedoch ohne den Durchhang: dieser kann vernachlässigt werden. (Elastische
    Längenänderung des Seiles). Ebenfalls als vernachlässigbar angenommen
    wird das Nachrutschen des Seiles aus dem Ankerfeld hinaus.

    INPUT:
    zi        Höhenkote bei i. [dm](ü.M.)(Def. zw. Anfangs- und Endmast)
    di        Hor.Distanz von i = 0 zu i [m](Def. zw. Anfangs- und Endmast)
    H_Anfangsmast Höhe des Anfangsmast [m]
    H_Endmast Höhe des Endmast [m]
    z_null    Höhenkote an der Talstation inkl. Mast [m]
    z_ende    Höhenkote an der Bergstation inkl. Mast [m]
    d_null    Hor.Distanz von i = 0 zu i = 0 [m] (=0)
    d_ende    Hor.Distanz von Talstation zu Bergstation
    Ank       Ankerfelder --> Funktioniert noch nicht so recht !
    Ank_Felder = [d_Anker_A,z_Anker_A*0.1,d_Anker_E,z_Anker_E*0.1];
    STA       Anfangsseilzugkraft

    OUTPUT:
    Cable_Possible    Gibt an, ob Seillinie möglich ist. [0=false, 1=true],
                      Bem.: Nachweis der zulässigen Seilkraft ist hier nicht
                      inbegriffen, die Ausgabe dessen erfolgt mit einem
                      separatem Argument, vgl. unten.
    si        Höhenkote der Seillinie [dm] (Def. zw. Anfangs- und Endmast)
    ym_z              Durchhang in Feldmitte
    ZulSK_erfuellt    Nachweis, ob die zulässige Seilzugkraft nicht
                      überschritten wurde: 1: erfüllt (nicht überschritten),
                      0: nicht erfüllt
    RR_eval: tatsächliche Rückerichtung, unterscheidet sich von R_R dadurch
    das auch bei Grund-Seilung Einstellung ohne Gravitationsseilkran (R_R=0)
    evaluiert wird, ob theoretisch mit Gravitationsseilkran gerückt werden
    könnte und dann das entsprechende Resultat ausgegeben wird [-1 oder 1]
    """
    # Input values
    Q = IS["Q"]        # [kN]
    qT = IS["qT"]      # [kN/m]
    F = IS["A"]        # [mm^2]
    E = IS["E"]        # [kN/mm^2]
    # beta = IS["beta"]     # [1/°C] Ausdehnungskoeffizient von Stahl
    Federkonstante = inf        # Federkonstante der Verankerung
    qz1 = IS["qz1"]     # [kN/m] Zugseilgewicht links
    qz2 = IS["qz2"]     # [kN/m] Zugseilgewicht rechts
    # min_Bodenabstand = IS["Bodenabst_min"]*10     # [dm] (10*[m])
    zul_SK = float(IS["zul_SK"])  # [kN] zulaessige Seilkraft!
    ZulSK_erfuellt = True
    # Ankerseillaenge
    Laenge_Ankerseil = IS['Ank']['len']
    Cable_Possible = True

    sizeB = b.size
    bquad = b**2
    bquad_feld = bquad[feld]
    b_feld = b[feld]

    # Spezielle Klasse und Methode zur schnelleren Summenbildung initialisieren
    vSumInstance = vectorSum(sizeB)
    calcSum = vSumInstance.functionToCall

    # Berechnung der Sehne
    c = (bquad + h**2)**0.5
    c_sum = np.sum(c, axis=0)
    c_feld = c[feld]

    # Pruefung
    if STA > zul_SK:
        Cable_Possible = False
        ym_z = 0
        ZulSK_erfuellt = False
    else:
        # Höhenangaben der Stützen bzw. der Feldmitte
        z = np.zeros(sizeB+1)
        z[1:] = np.cumsum(h)
        zfm = z[:-1] + h*0.5
        # Mit Berücksichtigung des Zugseilgewichtes
        q_strich = qT + (qz1 + qz2)/2

        # Leerseil
        # --------
        zqT = z * qT
        zfmqT = zfm * qT
        # Stützbelastung
        ST = STA + zqT      # Seilzugkraft an den Stützen
        STfm = STA + zfmqT  # Seilzugkraft in Feldmitte
        STfm_feld = STfm[feld]
        HT = (STfm * b) / c # Horizontalkomponente der Seilzugkraft
        # Überlänge der Lastlänge gegenüber dem Sehnenzug (Leerfeld)
        delta_s = ((bquad**2 * qT**2) / (24 * c * HT**2)) * \
                  (1 + (3*bquad + 8 * h**2) / (240 * c**2) *
                   (b * qT / HT)**2)
        UeberLaenge_Leerseil = np.sum(delta_s, axis=0)
        # UeberLaenge_Leerseil = getattr(vSumInstance, calcSum)(delta_s)
        Laenge_Leerseil = c_sum + UeberLaenge_Leerseil

        # Vollseil
        # --------
        # Iteration zur Berechnung des d_ST, welches unter dem Gewicht von Q
        # entsteht. Berechnung könnte noch beschleunigt werden, falls nicht alle
        # Felder sondern nur das betreffende berechnet werden!
        CableImpossible = False
        d_ST_out = 0.0    # Änderung der Seilzugkraft unter Last
        gen = 6.0         # Genauigkeit der Iteration: 6 sollte ausreichen
        basis = 2.0       # Hilfsgrösse für die Iteration
        genauig = basis**-gen
        expon = -5.0        # -5 ist Standard
        d_ST = 0.0          # Änderung der Zugkraft
        d_Laenge = 1.0      # Startgrösse
        change_dir = False  # Hilfsgrösse für die Iteration
        za = 0.0            # Hilfsgrösse für die Iteration
        d_ST_alt = 0.0      # Startgrösse
        # Diese Prüfung führt in wenigen Einzelfällen zu anderen Resultaten
        # als das Matlab-Programm weil die Berechnung von d_Laenge nach
        # einigen Iterationen zu Abweichungen im Submilimeter-Bereich führen
        while (abs(d_Laenge) > genauig) and CableImpossible is False:
            STfm_neu = STfm + d_ST
            ym = c_feld / (4 * STfm_neu[feld]) * (Q + c_feld * qT/2)    # 8a
            # Funktion mit Berücksichtigung des Zugseilgewichtes:
            # ym = c / (4 * STfm_neu) * (Q + c * q_strich/2) #(8)
            d_c = 2 * bquad_feld / c_feld**3 * ym**2   # 10a
            # 11a Leerseil
            delta_s = (bquad * c * qT**2) / (24 * STfm_neu**2)
            # delta s für die Belastung im betrachteten Abschnitt
            delta_s[feld] *= 0.25
            delta_s_sum = np.sum(delta_s, axis=0)
            # delta_s_sum = vectorSum(delta_s, sizeB)
            # delta_s_sum = getattr(vSumInstance, calcSum)(delta_s)

            UeberLaenge_Vollseil = d_c + delta_s_sum

            d_Laenge = UeberLaenge_Vollseil - UeberLaenge_Leerseil \
                       - d_ST/(F*E) * Laenge_Leerseil \
                       - d_ST/(F*E) * Laenge_Ankerseil \
                       - d_ST/Federkonstante
            d_ST_out = d_ST

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
        # Maximalwert im Seilsystem aufgrund der Belastung im
        # betrachteten Feld
        ST_max_betr_Feld = max([np.max(ST), np.max(STfm)]) + d_ST_out
        if CableImpossible:
            Cable_Possible = False
            ym_z = 0
        elif zul_SK < ST_max_betr_Feld:
            ZulSK_erfuellt = False
            ym_z = 0
        else:
            # Eigenschaften des Seils
            # -----------------------
            # Seilzugkraft in Feldmitte unter Last [kN]
            STfm_Last = STfm_feld + d_ST_out

            # Durchbiegung in Feldmitte unter Last [m]
            ym = c_feld / (4 * STfm_Last) * (Q + c_feld * q_strich/2)        # 8
            # Horizontalkräfte an den Stützen (Leerseilverhältnisse) [kN]
            Hs = b_feld / c_feld * STfm_feld
            bi = di - di[0]

            # Interpolationsbeziehung für die Berechnung der Lastwegkurve
            # Berechnung nach Zweifel
            # Hier kann es vorkommen, dass von negativen Zahlen die Wurzel
            # gezogen wird
            if Hs < 0:
                print("Fehler, Hs < 0 ", Hs)
            H = Hs * (1-(1-(Hs / Hs)**2) * (1-2*bi / b_feld)**2)**0.5
            y_last_zweifel = ym * Hs / H * (1-(1-2*bi/b_feld)**2)
            h_sehne = bi / b_feld * h[feld]
            # X-Koordinate der Lastkurve unter Zweifel
            x_coord_last_zweifel = h_sehne - y_last_zweifel + z[feld]

            ym_z = ym       # Ausgabegrösse: dient zur Kontrolle
            si = 10 * (x_coord_last_zweifel + z_null)
            Cable_Possible = checkCable(zi, si, sc, befGSK, IS['Seilsys'],
                                        IS['R_R'])
            # add_values = [ym, HT, Hs, Hm, STfm_Last]

    return Cable_Possible, ZulSK_erfuellt, ym_z # ,  si , add_values
