#  -*- coding: utf-8 -*-
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

import os
import math
import time

p = 21
nl = unicode(os.linesep)


def vectorData(xi, yi, di, zi_disp, seil, stuetzIdx, HM, z_kon):
    """ Kombination und Trasformation der Resultate
    Packt wichtige Resultate zusammen, abspeichern in Arrays/Dictionarys"""
    # Horizontaldistanz von float nach int umwandeln
    di = np.int32(di)
    # Längenprofil (Horizontaldistanz) am Anfang und Ende um 20m erweitern -->
    # besser für Darstellung
    di_start = np.arange(di[0]-p, di[0], 1)
    di_end = np.arange(di[-1]+1, di[-1]+p+1, 1)
    x_data = np.hstack((di_start, di, di_end))
    # Höhenwerte runden und von dm in m umrechnen
    y_data = np.round(zi_disp, 2)/10
    # Datenpunkte des Seilverlaufs reduzieren
    # redIdx = np.where(np.remainder(np.round(seil[2], 2), 1)==0)[0]
    z_Leer = seil[0]
    z_Zweifel = seil[1]
    # Normierte Höhen der Resultate in Höhe über Meer umwandeln
    z_Leer = z_Leer + y_data[p] + HM[0]
    z_Zweifel = z_Zweifel + y_data[p] + HM[0]
    stuetzeH = y_data[stuetzIdx+p] + np.array(HM)
    zi_n = np.round(z_kon, 2)/10
    konkav = y_data[p] + zi_n

    # CH-Koordinaten der Seillinien
    Seillinien_data = {'x': xi,
                       'y': yi * -1,
                       'z_Leer': z_Leer,
                       'z_Zweifel': z_Zweifel,
                       'l_coord': seil[2],
                       'Laengsprofil_di': di}

    # Koordinaten der Stuetzen
    HM_data = {'HM_x': xi[stuetzIdx],
               'HM_y': yi[stuetzIdx],
               'HM_z': stuetzeH,
               'HM_h': np.array([int(i) for i in HM]),
               'HM_idx': stuetzIdx}

    return [x_data, y_data], Seillinien_data, HM_data, konkav


def getTimestamp(tStart):
    # Dauer der Berechnung bestimmen
    tEnd = time.time()
    tDuration = tEnd - tStart
    # Zeitwert formatieren
    tsFormated1 = time.strftime("%Y-%m-%d_%H'%M", time.localtime(tStart))
    tsFormated2 = time.strftime("%d.%m.%Y, %H:%M Uhr", time.localtime(tStart))
    mini = int(math.floor(tDuration/60))
    sek = int(tDuration-mini*60)
    if mini == 0:
        tdFormated = str(sek) + " s"
    else:
        tdFormated = str(mini) + " min " + str(sek) + " s"
    return tdFormated, tsFormated1, tsFormated2


def plotData(disp_data, di, seilDaten, konkav, HM, IS, projInfo, resultStatus,
             locPlot):
    # import matplotlib
    # matplotlib.use('Cairo')
    from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure
    import matplotlib.patheffects as PathEffects
    from matplotlib.font_manager import FontProperties

    x_data = disp_data[0]
    y_data = disp_data[1]
    seillinieLeer = seilDaten['z_Leer']
    seillinieZweifel = seilDaten['z_Zweifel']
    seil_di = seilDaten['l_coord']
    di = np.int32(di)
    hoeheStue = HM['HM_h']
    zStue = HM['HM_z']
    idxStue = HM['HM_idx']

    # Erstelle Figure
    # Höhe der Figur angepasst an Höhendistanz der Seillinie (verzerrungsfrei)
    data_xlow = np.min(x_data)
    data_xhi = np.max(x_data)
    data_ylow = np.min(y_data)
    data_yhi = max([np.max(y_data), np.max(zStue)+18])
    data_xlen = x_data.size
    data_ylen = data_yhi - data_ylow
    # Anker
    [zAnkerseil, xAnkerseil] = IS['Ank'][3]
    # Markierungen für fixe Stützen
    [findFixStueX, findFixStueZ] = IS['HM_fix_marker']

    # Grösse des Plots definieren
    # cm2inch = 0.3937
    # lenA4 = 29.7 * cm2inch    #cm --> inch
    # border = 1.5 * cm2inch    #cm --> inch
    # fig_xlen = lenA4 *cm2inch * skalierung
    # fig_ylen = fig_xlen/(data_xlen*1.0) * data_ylen

    scaleFactor = 1.5       # Um Liniendicke und Schrift zu skalieren
    dpi = 100 / scaleFactor           # Ausgabequalität
    max_xlen = 10.10        # 11.69 inch = A4 Breite
    max_ylen = 7.07         # 8.27 inch = A4 Höhe
    fig_xlen = max_xlen * scaleFactor
    fig_ylen = max_ylen * scaleFactor

    fig = Figure(figsize=(fig_xlen, fig_ylen), dpi=dpi, facecolor='white')
    canvas = FigureCanvas(fig)
    axes = fig.add_subplot(111)

    #Daten plotten

    axes.plot(seil_di, seillinieLeer, color='#4D83B2', linewidth=1.8,
             label="Leerseil")
    axes.plot(seil_di, seillinieZweifel, color='#FF4D44', linewidth=1.8,
             label="Lastwegkurve nach Zweifel")
    # Gelände
    axes.fill_between(x_data, min(y_data), y_data, facecolor='#A4C9AC')

    axes.plot(x_data, y_data, color='#6F9679', linewidth=3)
    axes.plot(di, konkav, linewidth=2, color='#F3FF3E',
             label=u"Konkaves Gelände")
    # Ankerfelder
    if xAnkerseil[0] != xAnkerseil[1]:      # Falls Anker vom Benutzer definiert wurden
        axes.plot(xAnkerseil[:2], zAnkerseil[:2], color='#FF4D44', linewidth=1.8)
    if xAnkerseil[2] != xAnkerseil[3] and resultStatus != 3:
        # Falls Anker vom Benutzer definiert wurden
        axes.plot(xAnkerseil[2:], zAnkerseil[2:], color='#FF4D44', linewidth=1.8)
    # Stützen
    axes.vlines(idxStue, y_data[idxStue+p], zStue, colors='#484A4C',
               linewidth='3')

    # Beschriftungen setzten
    porjTitle = projInfo['Projektname']
    horiLabel = u"Horizontaldistanz [m] von der Anfangsstütze aus"
    vertiLabel = u"Höhe [m.ü.M]"
    titelLabel = u"SEILAPLAN Diagramm\n{}".format(porjTitle)
    axes.set_xlabel(horiLabel, fontsize=12)
    axes.set_ylabel(vertiLabel, verticalalignment='top', fontsize=12,
                    horizontalalignment='center', labelpad=20)
    axes.set_title(titelLabel, fontsize=13, multialignment='center', y=1.05)
    # Achsen anpassen
    axes.set_ylim([data_ylow, data_yhi])
    axes.set_xlim([data_xlow, data_xhi])
    axes.set_aspect('equal')
    stepx = stepy = 10
    if data_xhi >= 300:
        stepx = 20
    if data_xhi >= 500:
        stepy = 20      # sieht besser aus
    if data_xhi >= 700:
        stepx = 25
    if data_ylen >= 400:
        stepy = 20
    axes.set_yticks([i for i in range(int(data_ylow), int(data_yhi))
                     if i % stepy == 0])
    axes.set_xticks([i for i in range(int(data_xlow), int(data_xhi))
                     if i % stepx == 0])
    axes.grid()

    # Legende erzeugen
    fontP = FontProperties()
    fontP.set_size('medium')
    # Zusätzliche Beschreibung für fixe Stützen Beschriftung
    ncol = 3
    if np.sum(findFixStueX) > 0:
        ncol = 4
        axes.plot([data_xlow], [data_ylow], linewidth=0,
                  label=(u"Fixe Stützen: ° = fixe Position, "
                         u"°* = fixe Position und Höhe"))
    axes.legend(loc='lower center', prop=fontP, bbox_to_anchor=(0.5, 0),
                ncol=ncol)

    # Annotiations (Beschriftungen im Graph) und Text für Report vorbereiten
    # ----------------------------------------------------------------------
    # Stützenbeschriftungen
    stueLabel = [u"Anfangsstütze",  u"Endstütze"]
    # Feldbeschriftungen
    feldLabel = []
    # Zwischenstützen hinzufügen
    i = 0
    for i in range(1, len(idxStue)-1):
        marker = u''
        if findFixStueX[i] > 0:
            marker = u'°'
            if findFixStueZ[i] > 0:
                marker = u'°*'
        stueLabel.insert(i, u"{}. Stütze{}".format(i+1, marker))
        feldLabel.insert(i-1, u"{}. Feld".format(i))
    # Letztes Feld hinzufügen
    feldLabel.insert(i, u"{}. Feld".format(i+1))

    # Formatierung der Angaben für Stützenhöhen
    stueLabelH = []
    for i in range(len(hoeheStue)):
        if hoeheStue[i] == 0:        # Keine Höhenangabe falls Stütze == Anker
            stueLabelH.append(u"")
        else:
            # Formatierung je nach Zahlentyp mit oder ohne Nachkommastellen
            if hoeheStue[i]%1 == 0.0:
                stueLabelH.append(u"{:.0f} m".format(hoeheStue[i]))
            else:
                stueLabelH.append(u"{:.1f} m".format(hoeheStue[i]))

    for i in range(len(idxStue)):
        axes.annotate(stueLabel[i], xy=(idxStue[i], zStue[i]),
                     xycoords='data', xytext=(-25, 20),
                     textcoords='offset points', size=12,
                     path_effects=[PathEffects.withStroke(linewidth=3, foreground="w")])
        axes.annotate(stueLabelH[i], xy=(idxStue[i], zStue[i]-zStue[i]/2),
                     xycoords='data', xytext=(5, -5),
                     textcoords='offset points', size=12,
                     path_effects=[PathEffects.withStroke(linewidth=3, foreground="w")])

    # Abschnittsbeschriftungen
    for i in range(len(idxStue)-1):
        coordX = idxStue[i] + 0.5*(idxStue[i+1] - idxStue[i])
        coordY = zStue[i] + 0.5*(zStue[i+1] - zStue[i])
        axes.annotate(feldLabel[i], xy=(coordX, coordY),
                     xycoords='data', xytext=(-30, 25), style='italic',
                     textcoords='offset points', size=12,
                     path_effects=[PathEffects.withStroke(linewidth=3, foreground="w")])
    # Bezeichnung der fixen Stützen

    fig.tight_layout()

    # Plot als PNG exportieren
    # outPlotPNG = os.path.join(outputLoc, '{}_Plot.png'.format(outputName))
    outPlotPDF = os.path.join(locPlot)
    # canvas.print_png(outPlotPNG, dpi=dpi)
    canvas.print_pdf(outPlotPDF)
    del canvas

    return outPlotPDF, [stueLabel, feldLabel]


def formatNum(numbr):
    strNum = str(round(numbr, 1))
    intPart, floatPart = strNum.split('.')
    splits = [intPart[::-1][x:x+3] for x in range(0, len(intPart), 3)][::-1]
    intRevers = [splits[x][::-1] for x in range(len(splits))]
    layoutNumbr = "'".join(intRevers) + "." + floatPart
    return layoutNumbr


def removeTxtElements(text, key):
    if type(text) is str:
        if key in text:
            return "-"
        else:
            return text
    elif type(text) is list:
        return [removeTxtElements(x, key) for x in text]
    elif type(text) is set:
        return {removeTxtElements(x, key) for x in text}
    else:
        return text


def generateReportText(IS, projInfo, HM, kraft, OptSTA, duration,
                       timestamp, labelTxt):
    import math
    # Absteckinformationen Horziontaldist, Schraegdist, Azimut
    HM_h = HM['HM_h']
    HM_x = HM['HM_x']
    HM_y = HM['HM_y']
    HM_z = HM['HM_z']

    # Report zusammenstellen
    # TODO: Länge des Seils oder Höhenunterschied auffschreiben?
    projname = projInfo['Projektname']
    hmodell = projInfo['Hoehenmodell']['path']
    laenge = projInfo['Laenge']
    Hdiff = int(abs(HM_z[-1]-HM_z[0]))

    # TODO: Fixe Stützen auf irgend eine Weise markieren. Sind hier gespeichert:
    fixeStue = projInfo['fixeStuetzen']

    # Berechnungen für Absteckung
    hDist = []
    sDist = []
    dY = HM_y[-1] - HM_y[0]
    dX = HM_x[-1] - HM_x[0]
    ri = math.atan(dX/dY) * 180/math.pi
    if dY < 0:
        az = ri + 180
    elif dX < 0:
        az = ri + 360
    else:
        az = ri
    for i in range(len(HM_z)-1):
        dX = HM_x[i+1] - HM_x[i]
        dY = HM_y[i+1] - HM_y[i]
        dZ = HM_z[i+1] - HM_z[i]
        hDist.append((dX**2 + dY**2)**0.5)
        sDist.append((hDist[i]**2 + dZ**2)**0.5)

    anzSt = len(HM_z)
    anzFe = anzSt - 1
    sHeader = labelTxt[0]
    fHeader = labelTxt[1]
    # for f in range(1, anzSt):
    #     fHeader.append("{}. Feld".format(f))
    #     if f < anzSt-1:
    #         sHeader.append("{}. Stütze".format(f+1))
    # sHeader.append("Endstütze")

    # Abschnitt Zeit und Höhenmodell
    str_time = [[], ["Zeitpunkt", "{}, Berechnungsdauer: {}".format(timestamp, duration)],
                ["Höhenmodell", hmodell], [],
                [u"Erklärungen und Diagramme zu den technischen Werten sind "
                 u"in der Dokumentation zu finden."],
                [(u"Markierung für fixe Stützen: ° = fixe Position, "
                    u"°* = fixe Position und Höhe")]]


    # Abschnitt Stützenpositionen
    str_posi = [["", "Höhe", "X-Koordinate", "Y-Koordinate", "Z-Koordinate", "(M.ü.M)"]]
    for s in range(anzSt):
        tex = u"{};{:.0f} m;{};{};{};".format(sHeader[s], HM_h[s],
            formatNum(HM_x[s]), formatNum(HM_y[s]), formatNum(HM_z[s])).split(';')
        str_posi.append(tex)

    sHeader = [label.strip(u"°*") for label in sHeader] # Markierungen entfernen

    # Abschnitt Absteckung im Feld
    str_abst = [["Azimut: {:.1f} gon".format(az)],
                ["", u"Horizontaldistanz", u"Schrägdistanz"]]
    for f in range(anzFe):
        tex = (u"von {} zu {},{: >3.0f} m,"
               u"{: >3.0f} m").format(sHeader[f], sHeader[f+1], hDist[f], sDist[f]).split(',')
        str_abst.append(tex)

    # Abschnitt Vorspannung der Seilzugkraft
    str_opti = [["optimaler Wertebeich",
                 "{} - {} kN".format(np.min(OptSTA), np.max(OptSTA))],
                ["gewählte Seilzugkraft bei der Anfangsstütze",
                 "{:.0f} kN".format(np.round(kraft['Spannkraft'][0]))]]

    # Abschnitt Seillänge
    str_laen = [[""]*2 + fHeader,
                ["Länge Leerseil bei Anfangszugkraft",
                 "{:.0f} m".format(kraft['LaengeSeil'][0])] + [""]*anzFe,
                ["Länge Leerseil bei 0 kN Seilzugkraft",
                 "{:.0f} m".format(kraft['LaengeSeil'][1])] + [""]*anzFe,
                ["Länge der Spannfelder"] + (",{:.0f} m"*anzFe).format(
                    *tuple(kraft['LaengeSeil'][2])).split(',', anzFe)]

    # Abschnitt Durchhang
    str_durc = [["Abk.", ""] + fHeader,
                ["yLE", "Leerseil"] + ("{:.2f} m,"*anzFe).format(
                    *tuple(kraft['Durchhang'][0])).rstrip(',').split(',', anzFe),
                ["yLA", "Lastseil"] + ("{:.2f} m,"*anzFe).format(
                    *tuple(kraft['Durchhang'][1])).rstrip(',').split(',', anzFe)]

    str_seil1 = [
        ["Abk.", "am Leerseil"] + [""]*(anzSt+1),
        ["T0,A","Seilzugkraft an der Anfangsstütze"] +
            ["{:.0f} kN".format(kraft['Spannkraft'][0])] + [""]*anzSt,
        ["T0,E","Seilzugkraft an der Endstütze"] +
            ["{:.0f} kN".format(kraft['Spannkraft'][1])] + [""]*anzSt,
        [""]*3 + sHeader,
        ["T0","Seilzugkraft des Leerseils an den Stützen", ""] +
            ("{:.0f} kN,"*anzSt).format(*tuple(
                np.round(kraft['Seilzugkraft'][0]))).rstrip(',').split(',', anzSt)]
    str_seil2 = [
        ["HS","Leerseilverhältnis: Horizontalkomponente"] + fHeader,
        ["", "     der Seilzugkraft an den Stützen"] +
            ("{:.0f} kN,"*anzFe).format(*tuple(
                kraft['Seilzugkraft'][1])).rstrip(',').split(',', anzFe)]
    str_seil3 = [
        ["", "am Lastseil"] + [""]*anzFe,
        ["", "Max. auftretende Seilzugkraft"],
        ["Tmax", "     am höchsten Punkt im Seilsystem",
         "{:.0f} kN".format(kraft['MaxSeilzugkraft_L'][0])],
        ["Tmax,A", "     am Anfangsanker",
         "{:.0f} kN".format(kraft['MaxSeilzugkraft_L'][1])],
        ["Tmax,E", "     am Endanker",
         "{:.0f} kN".format(kraft['MaxSeilzugkraft_L'][2])]]
    str_seil4 = [
        ["", "am Lastseil mit Last in Feldmitte"] + fHeader,
        ["Tm", "Max. auftretende Seilzugkraft gemessen in Feldmitte"] +
            ("{:.0f} kN,"*anzFe).format(*tuple(kraft['MaxSeilzugkraft'][0])
            ).rstrip(',').split(','),
        ["Hm", "     davon horizontale Komponente"] +
            ("{:.0f} kN,"*anzFe).format(*tuple(kraft['MaxSeilzugkraft'][1])
            ).rstrip(',').split(','),
        ["Tm,max", "     gemessen am höchsten Punkt im Seilsystem"] +
            ("{:.0f} kN,"*anzFe).format(*tuple(kraft['MaxSeilzugkraft'][2])
            ).rstrip(',').split(','),
        ]
    str_seil = [str_seil1, str_seil2, str_seil3, str_seil4]

    # Abschnitt Auftretende Kräfte an den Stützen
    str_stue1 = [
        ["", "an befahrbarer Stütze, Laufwagen auf Stütze"] + sHeader,
        ["F_Sa_BefRes", "Sattelkraft, resultierend"] +
            ("{:.0f} kN,"*anzSt).format(*tuple(
                kraft['Sattelkraft_Total'][0])).rstrip(',').split(','),
        ["F_Sa_BefV", "Sattelkraft, vertikale Komponente"] +
            ("{:.0f} kN,"*anzSt).format(*tuple(
                kraft['Sattelkraft_Total'][1])).rstrip(',').split(','),
        ["F_Sa_BefH", "Sattelkraft, horizontale Komponente"] +
            ("{:.0f} kN,"*anzSt).format(*tuple(
                kraft['Sattelkraft_Total'][2])).rstrip(',').split(','),
        ["FSR", "Sattelkraft (Anteil von Tragseil), resultierend"] +
            ("{:.0f} kN,"*anzSt).format(*tuple(
                kraft['Sattelkraft_ausSeil'][0])).rstrip(',').split(','),
        ["FSV", "Sattelkraft (Anteil von Tragseil), vertikale Komponente"] +
            ("{:.0f} kN,"*anzSt).format(*tuple(
                kraft['Sattelkraft_ausSeil'][1])).rstrip(',').split(','),
        ["FSH", "Sattelkraft (Anteil von Tragseil), horizontale Komponente"] +
            ("{:.0f} kN,"*anzSt).format(*tuple(
                kraft['Sattelkraft_ausSeil'][2])).rstrip(',').split(','),
        ["FU", "Einwirkung auf Stütze aus Last, Gewicht Zug- & Tragseil"] +
            ("{:.0f} kN,"*anzSt).format(*tuple(
                kraft['UebrigeKraft_befStuetze'])).rstrip(',').split(','),
        ]
    newHeader = [""]*(anzSt*2)
    a = 0
    for i in range(0, anzSt*2, 2):
        newHeader[i+1] = sHeader[a]
        a += 1
    str_stue2 = [
        ["", "an nicht befahrbarer Stütze,"] + newHeader,
        ["", "     Laufwagen unmittelbar links/rechts bei Stütze"] +
            ["links", "rechts"]*anzSt,
        ["TCS", "Seilzugkraft"] +
            ("{:.0f} kN,"*(anzSt*2)).format(*tuple(
                kraft['Seilzugkraft_beiStuetze'])).rstrip(',').split(','),
        ["F_Sa_NBefRes", "Sattelkraft, resultierend"] +
            ("{:.0f} kN,"*(anzSt*2)).format(*tuple(
                kraft['Sattelkraft_beiStuetze'][0])).rstrip(',').split(','),
        ["F_Sa_NBefV", "Sattelkraft, vertikale Komponente"] +
            ("{:.0f} kN,"*(anzSt*2)).format(*tuple(
                kraft['Sattelkraft_beiStuetze'][1])).rstrip(',').split(','),
        ["F_Sa_NBefH", "Sattelkraft, horizontale Komponente"] +
            ("{:.0f} kN,"*(anzSt*2)).format(*tuple(
                kraft['Sattelkraft_beiStuetze'][2])).rstrip(',').split(','),
    ]
    str_stue = [str_stue1, str_stue2]

    # Abschnitt Seilwinkel
    str_wink = [
        ["", "am Leerseil"] + sHeader,
        ["alpha LA", "eingehender Winkel"] +
            ("{:.0f}°,"*anzSt).format(*tuple(
                kraft['Anlegewinkel_Leerseil'][0])).rstrip(',').split(','),
        ["alpha LE", "ausgehender Winkel"] +
            ("{:.0f}°,"*anzSt).format(*tuple(
                kraft['Anlegewinkel_Leerseil'][1])).rstrip(',').split(','),
        [""],
        ["", "am Lastseil"] + sHeader,
        ["alpha LA", "eingehender Winkel", ""] +
            ("{:.0f}°,"*anzFe).format(*tuple(
                kraft['Anlegewinkel_Lastseil'][0][1:])).rstrip(',').split(','),
        ["alpha LE", "ausgehender Winkel"] +
            ("{:.0f}°,"*anzFe).format(*tuple(
                kraft['Anlegewinkel_Lastseil'][1][:-1])).rstrip(',').split(',')
        ]

    # Abschnitt Nachweis
    str_nach = [
        ["", ""] + sHeader,
        ["beta", "Leerseilknickwinkel"] +
            ("{:.0f}°,"*anzSt).format(*tuple(
                kraft['Leerseilknickwinkel'])).rstrip(',').split(','),
        ["", "Nachweis erfüllt"] +
            ("{},"*anzSt).format(*tuple(
                kraft['Nachweis'])).rstrip(',').split(',')
    ]

    # Abschnitt Annahmen
    str_anna = []
    annahmen = projInfo['Params']
    lenAnn= int(math.ceil(len(annahmen)/2))
    for i in range(lenAnn):
        part1 = annahmen[i]
        part2 = ['']
        part3 = annahmen[i+lenAnn]
        str_anna.append(part1+part2+part3)

    text = [str_time, str_posi, str_abst, str_opti, str_laen, str_durc,
            str_seil, str_stue, str_wink, str_nach, str_anna]
    str_report = removeTxtElements(text, "nan")

    return str_report


def generateReport(reportText, savePath, projname):
    from reportlab.lib.pagesizes import A4, inch, cm, landscape
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
    from reportlab.graphics.shapes import colors

    # from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, \
    #     PageBreak
    # from reportlab.graphics.shapes import Drawing, Image, colors

    breite, hoehe = landscape(A4)
    # plotBreite = plotSize[0] * inch
    # plotHoehe = plotSize[1] * inch
    margin = 1.5*cm
    if os.path.exists(savePath):
        os.remove(savePath)
    doc1 = SimpleDocTemplate(savePath, encoding='utf8', topMargin=margin,
                             bottomMargin=margin, leftMargin=margin,
                             rightMargin=margin, pageBreakQuick=1,
                             pagesize=landscape(A4))
    elements = []

    [str_time, str_posi, str_abst, str_opti, str_laen,
     str_durc, [str_seil1, str_seil2, str_seil3, str_seil4],
     [str_stue1, str_stue2], str_wink, str_nach, str_anna] = reportText

    breiteT, hoeheT = [breite-2*margin, hoehe-2*margin]
    breiteI = breite-1.5*cm

    Bdoc = [breiteT]
    Bspalte = [2.7 * cm]
    Babk = [1.7*cm]
    Hzeile = [0.40 * cm]
    HzeileT = [0.45 * cm]
    anzSt = len(str_posi)-1
    anzFe = anzSt - 1
    lPadd = 6
    fontSize = 8
    smallfontSize = 6

    # Plot auf erste Seite platzieren
    # img = Image(0, 0, plotBreite, plotHoehe, plot)
    # d = Drawing(plotBreite, plotHoehe)
    # d.add(img)
    # table_img = Table([[d]], breite-5*margin, hoehe-3*margin)
    # table_img.setStyle(TableStyle([('ALIGN', (0, 0), (-1, -1), 'CENTER'),
    #                                #('LEFTPADDING', (0, 0), (0, -1), -breiteI),
    #                                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    #                                #('BOTTOMPADDING', (0, 0), (0, -1), -hoeheI/2),
    #                                #('GRID', (0, 0), (-1,-1), 1, colors.black)
    #                                 ]))
    # Titeldefinition
    h_tite = [["Seilbahnprojekt        "+projname]]
    h_posi = [["Stützenpositionen"]]
    h_abst = [["Daten für Absteckung im Feld"]]
    h_opti = [["Vorspannung der Seilzugkraft"]]
    h_laen = [["Seillänge"]]
    h_durc = [["Durchhang"]]
    h_seil = [["Auftretende Kräfte am Seil"]]
    h_stue = [["Auftretende Kräfte an den Stützen"]]
    h_wink = [["Seilwinkel an den Stützen"]]
    h_nach = [["Nachweis, dass Tragseil nicht vom Sattel abhebt"]]
    h_anna = [["Annahmen"]]

    # Tablestyles
    font = 'Helvetica'
    fontBold = 'Helvetica-Bold'
    fontHeader = 'Helvetica-Oblique'

    title_style = TableStyle([('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                              ('BACKGROUND', (0, 0), (-1, -1), colors.lightgrey),
                              ('FONT', (0, 0), (-1, -1), font, 8),
                              ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                              #('GRID', (0, 0), (-1,-1), 1, colors.black)
                              ])
    stdStyleA = [('LEFTPADDING', (0, 0), (0, -1), lPadd),    # Alles einrücken
                ('ALIGN', (1, 0), (-1, -1), 'RIGHT'), # nach erster Spalte rechtsbündig
                # ('GRID', (0, 0), (-1,-1), 1, colors.black),
                ('FONT', (0, 0), (-1, -1), font, fontSize)]
    stdStyleB = [('LEFTPADDING', (0, 0), (0, -1), lPadd),    # Alles einrücken
                 ('FONT', (1, 0), (-1, -1), font, fontSize),
                 # ('GRID', (0, 0), (-1,-1), 1, colors.black),
                 ('ALIGN', (2, 0), (-1, -1), 'RIGHT')]   # nach zweiter Spalte rechtsbündig

    t_tite1 = Table(h_tite, Bdoc, [0.8*cm])
    t_tite2 = Table(str_time, [2.6*cm, 15.2*cm], len(str_time) * Hzeile)
    t_tite1.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('FONT', (0, 0), (-1, -1), fontBold, 13),
        ('BACKGROUND', (0, 0), (-1, -1), colors.lightgrey),
        ('LINEBELOW', (0,0), (-1,-1), 1, colors.black),
        #('GRID', (0, 0), (-1,-1), 1, colors.black)
        ]))
    t_tite2.setStyle(TableStyle([('FONT', (0, 0), (-1, -1), font, fontSize),
                                 ('LEFTPADDING', (0, 0), (0, -1), lPadd)]))

    t_posi1 = Table(h_posi, Bdoc, HzeileT)
    t_posi2 = Table(str_posi, [1.7*cm] + 5*[2.5*cm], len(str_posi) * Hzeile)
    t_posi1.setStyle(title_style)
    t_posi2.setStyle(TableStyle(stdStyleA + [
        ('ALIGN', (5, 0), (5, -0), 'LEFT'),
        ('FONT', (0, 0), (-2, 0), fontHeader, smallfontSize)]))

    t_abst1 = Table(h_abst, Bdoc, HzeileT)
    t_abst2 = Table(str_abst, [5*cm] + 2*Bspalte, len(str_abst) * Hzeile)
    t_abst1.setStyle(title_style)
    t_abst2.setStyle(TableStyle(stdStyleA + [
        ('FONT', (0, 1), (-1, 1), fontHeader, smallfontSize)]))

    t_opti1 = Table(h_opti, Bdoc, HzeileT)
    t_opti2 = Table(str_opti, [5*cm] + Bspalte, 2*Hzeile)
    t_opti1.setStyle(title_style)
    t_opti2.setStyle(TableStyle(stdStyleA))

    t_laen1 = Table(h_laen, Bdoc, HzeileT)
    t_laen2 = Table(str_laen, [5.8*cm] + [2*cm] + [1.5*cm]*anzFe, 4*Hzeile)
    t_laen1.setStyle(title_style)
    t_laen2.setStyle(TableStyle(stdStyleA + [
        ('FONT', (2, 0), (-1, 0), fontHeader, smallfontSize)]))  # Feld-Header

    t_durc1 = Table(h_durc, Bdoc, HzeileT)
    t_durc2 = Table(str_durc, Babk + [3*cm] + [1.7*cm]*anzFe, 3*Hzeile)
    t_durc1.setStyle(title_style)
    t_durc2.setStyle(TableStyle(stdStyleB + [
        ('FONT', (2, 0), (-1, 0), fontHeader, smallfontSize),   # Feld-Header
        ('FONT', (0, 0), (0, -1), font, smallfontSize)]))       # Abkürzungen in der 1. Spalte

    t_seil1 = Table(h_seil, Bdoc, HzeileT)
    t_seil2 = Table(str_seil1, Babk + [6*cm] + [1*cm] + [1.5*cm]*anzFe, len(str_seil1)*Hzeile)
    t_seil3 = Table(str_seil2, Babk + [7.7*cm] + [1.5*cm]*anzSt, len(str_seil2)*Hzeile)
    t_seil4 = Table(str_seil3, Babk + [6*cm] + [1*cm], len(str_seil3)*Hzeile)
    t_seil5 = Table(str_seil4, Babk + [7.7*cm] + [1.5*cm]*anzFe, len(str_seil4)*Hzeile)
    t_seil1.setStyle(title_style)
    t_seil2.setStyle(TableStyle(stdStyleB + [
        ('FONT', (0, 0), (-1, 0), fontHeader, fontSize),   # erste Zeile = Unterkapitel
        ('FONT', (3, 3), (-1, 3), fontHeader, smallfontSize),   # Stützen-Header
        ('FONT', (0, 0), (0, -1), font, smallfontSize),     # Abkürzungen in der 1. Spalte
        ('BOTTOMPADDING', (0, -1), (-1, -1), 0)]))
    t_seil3.setStyle(TableStyle(stdStyleB + [
        ('FONT', (2, 0), (-1, 0), fontHeader, smallfontSize),   # Stützen-Header
        ('FONT', (0, 0), (0, -1), font, smallfontSize),         # Abkürzungen in der 1. Spalte
        ('TOPPADDING', (0, 0), (-1, 0), 0)]))
    t_seil4.setStyle(TableStyle(stdStyleB + [
        ('FONT', (0, 0), (-1, 0), fontHeader, fontSize),   # erste Zeile = Unterkapitel
        ('FONT', (0, 0), (0, -1), font, smallfontSize)]))       # Abkürzungen in der 1. Spalte
    t_seil5.setStyle(TableStyle(stdStyleB + [
        ('FONT', (0, 0), (1, 0), fontHeader, fontSize),    # erste Zeile = Unterkapitel
        ('FONT', (2, 0), (-1, 0), fontHeader, smallfontSize),   # Feld-Header
        ('FONT', (0, 0), (0, -1), font, smallfontSize)]))       # Abkürzungen in der 1. Spalte

    t_stue1 = Table(h_stue, Bdoc, HzeileT)
    t_stue2 = Table(str_stue1, Babk + [6.8*cm] + [2.2*cm]*anzSt, len(str_stue1)*Hzeile)
    t_stue3 = Table(str_stue2, Babk + [6.8*cm] + [1.1*cm]*anzSt,len(str_stue2)*Hzeile)
    # t_stue4 = Table(str_stue3, Babk + [6.8*cm] + [1.1*cm]*(anzSt*2), len(str_stue3)*Hzeile)
    t_stue1.setStyle(title_style)
    t_stue2.setStyle(TableStyle(stdStyleB + [
        ('FONT', (2, 0), (-1, 0), fontHeader, smallfontSize),   # Feld-Header
        ('FONT', (1, 0), (1, 0), fontHeader, fontSize),    # Überschrift
        ('FONT', (0, 0), (0, -1), font, smallfontSize)]))    # Abkürzungen in der 1. Spalte
    stdStyleStue = stdStyleB + [
        ('FONT', (2, 0), (-1, 1), fontHeader, smallfontSize),   # Feld-Header
        ('FONT', (1, 0), (1, 1), fontHeader, fontSize),    # Überschrift
        # ('TOPPADDING', (0, -1), (-1, -1), 0),
        ('FONT', (0, 0), (0, -1), font, smallfontSize),    # Abkürzungen in der 1. Spalte
        # ('ALIGN', (2, 0), (-1, 0), 'CENTER'),
        ('ALIGN', (2, 1), (2, -1), 'CENTER'),
        ('ALIGN', (-2, 1), (-2, -1), 'CENTER')]
    for i in range(2, anzSt*2+2, 2):
        stdStyleStue += [
                         ('RIGHTPADDING', (i, 1), (i, -1), 1)]
    t_stue3.setStyle(TableStyle(stdStyleStue))

    t_wink1 = Table(h_wink, Bdoc, HzeileT)
    t_wink2 = Table(str_wink, Babk + [4*cm] + [1.7*cm]*anzFe, 7*Hzeile)
    t_wink1.setStyle(title_style)
    t_wink2.setStyle(TableStyle(stdStyleB + [
        ('FONT', (1, 0), (1, 0), fontHeader, fontSize),    # Leerseil Überschrift
        ('FONT', (1, 4), (1, 4), fontHeader, fontSize),    # Lastseil Überschrift
        ('FONT', (2, 0), (-1, 0), fontHeader, smallfontSize),   # Feld-Header
        ('FONT', (2, 4), (-1, 4), fontHeader, smallfontSize),   # Feld-Header
        ('FONT', (0, 0), (0, -1), font, smallfontSize)]))       # Abkürzungen in der 1. Spalte

    t_nach1 = Table(h_nach, Bdoc, HzeileT)
    t_nach2 = Table(str_nach, Babk + [4*cm] + [1.7*cm]*anzFe, 3*Hzeile)
    t_nach1.setStyle(title_style)
    t_nach2.setStyle(TableStyle(stdStyleB + [
        ('FONT', (2, 0), (-1, 0), fontHeader, smallfontSize),   # Feld-Header
        ('FONT', (0, 0), (0, -1), font, smallfontSize)]))       # Abkürzungen in der 1. Spalte

    t_anna1 = Table(h_anna, Bdoc, HzeileT)
    t_anna2 = Table(str_anna, [5*cm, 3*cm, 1*cm, 5*cm, 3*cm], len(str_anna) * [0.35*cm])
    t_anna1.setStyle(title_style)
    t_anna2.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('LEFTPADDING', (0, 0), (0, -1), lPadd),
        ('ALIGN', (3, 0), (3, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('ALIGN', (4, 0), (4, -1), 'RIGHT'),
        ('FONT', (0, 0), (-1, -1), font, fontSize)]))

    # notiz = [[u"Erklärungen und Diagramme zu den Seildaten sind in der Dokumentation zu finden."]]
    # t_notiz = Table(notiz, Bdoc, Hzeile)
    # t_notiz.setStyle(TableStyle(stdStyleB + [
    #     ('FONT', (0, 0), (-1, -1), font, fontSize)
    #                                         ]))

    data = [ [Table([[t_tite1], [t_tite2]])], [Table([[t_posi1], [t_posi2]])],
             [Table([[t_abst1], [t_abst2]])],
             [Table([[t_opti1], [t_opti2]])], [Table([[t_laen1], [t_laen2]])],
             [Table([[t_durc1], [t_durc2]])], [Table([[t_seil1], [t_seil2],
             [t_seil3], [t_seil4], [t_seil5]])],
             [Table([[t_stue1], [t_stue2], [t_stue3]])],
             [Table([[t_wink1], [t_wink2]])],
             [Table([[t_nach1], [t_nach2]])], [Table([[t_anna1], [t_anna2]])]]

    # elements.append(table_img)
    # elements.append(PageBreak())
    elements.append(Table(data))

    doc1.build(elements)
    del elements
    # os.remove(plot)


def createOutputFolder(folder, name):
    location = os.path.join(folder, name)
    i = 1
    while os.path.exists(location):
        if i == 1:
            location = "{}_{}".format(location, i)
        location = "{}_{}".format(location[:-2], i)
        i += 1
    os.makedirs(location)
    return location
