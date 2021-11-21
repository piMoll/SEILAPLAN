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

import os
import math
import time
import textwrap

from qgis.PyQt.QtCore import QCoreApplication

from reportlab.lib.pagesizes import A4, portrait
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.graphics.shapes import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

p = 21
nl = os.linesep


def getTimestamp(tStart):
    """Calculate duration of algorithm run"""
    tEnd = time.time()
    tDuration = tEnd - tStart
    # Format time
    tsFormated1 = time.strftime("%Y-%m-%d_%H'%M", time.localtime(tStart))
    tsFormated2 = time.strftime("%d.%m.%Y, %H:%M Uhr", time.localtime(tStart))
    mini = int(math.floor(tDuration/60))
    sek = int(tDuration-mini*60)
    if mini == 0:
        tdFormated = str(sek) + " s"
    else:
        tdFormated = str(mini) + " min " + str(sek) + " s"
    return [tdFormated, tsFormated1, tsFormated2]


def formatNum(numbr):
    """Format big numbers with thousand separator"""
    return f"{numbr:,.1f}".replace(',', "'")


def removeTxtElements(text, key):
    """Prepare Text for report by removing 'nan' values"""
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


def generateReportText(confHandler, result, comment, projname):
    """ Arrange texts and values for report generation.
    
    :type confHandler: configHandler.ConfigHandler
    """
    poles = confHandler.project.poles
    polesWithAnchors = poles.poles
    polesWithoutAnchors = polesWithAnchors[poles.idxA:poles.idxE+1]
    hmpath = textwrap.wrap(confHandler.project.getHeightSourceAsStr(source=True, formatting='comma'), 120)
    # Shorten list to display max. 3 items
    del hmpath[3:]
    hmpath.append('...')
    hmodell = '\n'.join(hmpath)
    kraft = result['force']
    az_grad = math.degrees(poles.azimut)
    az_gon = az_grad * 1.11111

    poleCount = len(polesWithoutAnchors)
    fieldCount = poleCount - 1
    sHeader = [i['name'] for i in polesWithoutAnchors]
    fHeader = [f"{i+1}. " + tr('Feld') for i in range(fieldCount)]

    # First section with duration, dhm and several comments
    str_time = [
        [],
        [tr('Zeitpunkt'), "{}, {}: {}".format(result['duration'][2],
                                              tr('Berechnungsdauer'),
                                              result['duration'][0])],
        [tr('Hoehendaten'), hmodell], []]
    if comment:
        commentWraped = textwrap.fill(comment, 150).split('\n')
        # First line
        str_time.append([tr('Bemerkung'), commentWraped[0]])
        # Consecutive lines
        for line in commentWraped[1:]:
            str_time.append(['', line])
        str_time.append([])

    str_time.append(['', tr('Erklaerungen und Diagramme zu den technischen Werten '
                        'sind in der Dokumentation zu finden.')])
    
    # Section poles
    str_posi = [["", tr('Hoehe Sattel [m]'), tr('Neigung []'), tr('X-Koordinate'),
                 tr('Y-Koordinate'), tr('Z-Koordinate [m.ue.M.]')]]
    for pole in polesWithAnchors:
        if not pole['active']:
            continue
        angle = round(pole['angle'], 0) if pole['angle'] != 0 else '-'
        str_posi.append([
            f"{pole['name']}", f"{pole['h']:.1f}", f"{angle}",
            f"{formatNum(pole['coordx'])}",
            f"{formatNum(pole['coordy'])}",
            f"{formatNum(pole['z'])}"])

    # Section field survey
    str_abst = [["{}: {:.2f} {} / {:.2f} °".format(tr('Azimut'), az_gon, tr('gon'), az_grad)],
                ["", tr('Horizontaldistanz'), tr('Schraegdistanz')]]
    for i, pole in enumerate(polesWithAnchors[:-1]):
        nextPole = polesWithAnchors[i+1]
        dist_h = nextPole['d'] - pole['d']
        dist_z = nextPole['z'] - pole['z']
        dist_s = (dist_h**2 + dist_z**2)**0.5
        str_abst.append(["{} {} {} {}".format(tr('von'), pole['name'], tr('zu'), nextPole['name']),
                         f"{dist_h:.1f} m", f"{dist_s:.2f} m"])

    # Section cable pull strength
    str_opti = [[tr('gewaehlte Grundspannung bei der Anfangsstuetze'),
                 f"{confHandler.params.optSTA:.0f} kN"]]

    # Section cable length
    str_laen = [['']*2 + fHeader,
                [tr('Laenge Leerseil bei Anfangszugkraft'),
                 f"{kraft['LaengeSeil'][0]:.1f} m"] + ['']*fieldCount,
                [tr('Laenge Leerseil bei 0 kN Seilzugkraft'),
                 f"{kraft['LaengeSeil'][1]:.1f} m"] + ['']*fieldCount,
                [tr('Laenge der Spannfelder (Schraegdistanz)')] + (",{:.1f} m" * fieldCount).format(
                    *tuple(kraft['LaengeSeil'][2])).split(',', fieldCount)]

    # Section cable slack
    str_durc = [[tr('Abk.'), ''] + fHeader,
                ['yLE', tr('Leerseil')] + ("{:.1f} m," * fieldCount).format(
                    *tuple(kraft['Durchhang'][0])).rstrip(',').split(',', fieldCount),
                ['yLA', tr('Lastseil')] + ("{:.1f} m," * fieldCount).format(
                    *tuple(kraft['Durchhang'][1])).rstrip(',').split(',', fieldCount),
                ['', tr('Max. Abstand Leerseil - Boden'), f"{result['cableline']['maxDistToGround']:.1f} m"]
    ]

    str_seil1 = [
        [tr('Abk.'), tr('am Leerseil')] + [''] * (poleCount + 1),
        ['T0,A', tr('Seilzugkraft an der Anfangsstuetze')] +
        [f"{kraft['Spannkraft'][0]:.0f} kN"] + [''] * poleCount,
        ['T0,E', tr('Seilzugkraft an der Endstuetze')] +
        [f"{kraft['Spannkraft'][1]:.0f} kN"] + [''] * poleCount,
        [''] * 3 + sHeader,
        ['T0', tr('Seilzugkraft des Leerseils an den Stuetzen'), ''] +
        ('{:.0f} kN,' * poleCount).format(*tuple(
            np.round(kraft['Seilzugkraft'][0]))).rstrip(',').split(',', poleCount)]
    str_seil2 = [
        ['HS', tr('Leerseilverhaeltnis: Horizontalkomponente')] + fHeader,
        ['', '     ' + tr('der Seilzugkraft an den Stuetzen')] +
        ('{:.0f} kN,' * fieldCount).format(*tuple(
                kraft['Seilzugkraft'][1])).rstrip(',').split(',', fieldCount)]
    str_seil3 = [
        ['', tr('am Lastseil')] + ['']*fieldCount,
        ['', tr('Max. auftretende Seilzugkraft')],
        ['Tmax', '     ' + tr('am hoechsten Punkt im Seilsystem'),
         f"{kraft['MaxSeilzugkraft_L'][0]:.0f} kN"],
        ['Tmax,A', '     ' + tr('am Anfangsanker'),
         f"{kraft['MaxSeilzugkraft_L'][1]:.0f} kN"],
        ['Tmax,E', '     ' + tr('am Endanker'),
         f"{kraft['MaxSeilzugkraft_L'][2]:.0f} kN"]]
    str_seil4 = [
        ['', tr('am Lastseil mit Last in Feldmitte')] + fHeader,
        ['Tm', tr('Max. auftretende Seilzugkraft gemessen in Feldmitte')] +
        ("{:.0f} kN,"*fieldCount).format(*tuple(kraft['MaxSeilzugkraft'][0])
            ).rstrip(',').split(','),
        ['Hm', '     ' + tr('davon horizontale Komponente')] +
        ("{:.0f} kN,"*fieldCount).format(*tuple(kraft['MaxSeilzugkraft'][1])
            ).rstrip(',').split(','),
        ['Tm,max', '     ' + tr('gemessen am hoechsten Punkt im Seilsystem')] +
        ("{:.0f} kN,"*fieldCount).format(*tuple(kraft['MaxSeilzugkraft'][2])
            ).rstrip(',').split(','),
        ]
    str_seil = [str_seil1, str_seil2, str_seil3, str_seil4]

    # Section cable forces
    str_stue1 = [
        ['', tr('an befahrbarer Stuetze, Laufwagen auf Stuetze')] + sHeader,
        ['F_Sa_BefRes', tr('Sattelkraft, resultierend')] +
        ("{:.0f} kN,"*poleCount).format(*tuple(
                kraft['Sattelkraft_Total'][0])).rstrip(',').split(','),
        ['F_Sa_BefV', tr('Sattelkraft, vertikale Komponente')] +
        ("{:.0f} kN,"*poleCount).format(*tuple(
                kraft['Sattelkraft_Total'][1])).rstrip(',').split(','),
        ['F_Sa_BefH', tr('Sattelkraft, horizontale Komponente')] +
        ("{:.0f} kN,"*poleCount).format(*tuple(
                kraft['Sattelkraft_Total'][2])).rstrip(',').split(','),
        ['FSR', tr('Sattelkraft (Anteil von Tragseil), resultierend')] +
        ("{:.0f} kN,"*poleCount).format(*tuple(
                kraft['Sattelkraft_ausSeil'][0])).rstrip(',').split(','),
        ['FSV', tr('Sattelkraft (Anteil von Tragseil), vertikale Komponente')] +
        ("{:.0f} kN,"*poleCount).format(*tuple(
                kraft['Sattelkraft_ausSeil'][1])).rstrip(',').split(','),
        ['FSH', tr('Sattelkraft (Anteil von Tragseil), horizontale Komponente')] +
        ("{:.0f} kN,"*poleCount).format(*tuple(
                kraft['Sattelkraft_ausSeil'][2])).rstrip(',').split(','),
        ['FU', tr('Einwirkung auf Stuetze aus Last, Gewicht Zug- Tragseil')] +
        ("{:.0f} kN,"*poleCount).format(*tuple(
                kraft['UebrigeKraft_befStuetze'])).rstrip(',').split(','),
        ]
    newHeader = [""]*(poleCount*2)
    a = 0
    for i in range(0, poleCount*2, 2):
        newHeader[i+1] = sHeader[a]
        a += 1
    str_stue2 = [
        ['', tr('an nicht befahrbarer Stuetze,')] + newHeader,
        ['', '     ' + tr('Laufwagen unmittelbar links/rechts bei Stuetze')] +
        [tr('links'), tr('rechts')] * poleCount,
        ['TCS', tr('Seilzugkraft')] +
        ("{:.0f} kN,"*(poleCount*2)).format(*tuple(
                kraft['Seilzugkraft_beiStuetze'])).rstrip(',').split(','),
        ['F_Sa_NBefRes', tr('Sattelkraft, resultierend')] +
        ("{:.0f} kN,"*(poleCount*2)).format(*tuple(
                kraft['Sattelkraft_beiStuetze'][0])).rstrip(',').split(','),
        ['F_Sa_NBefV', tr('Sattelkraft, vertikale Komponente')] +
        ("{:.0f} kN,"*(poleCount*2)).format(*tuple(
                kraft['Sattelkraft_beiStuetze'][1])).rstrip(',').split(','),
        ['F_Sa_NBefH', tr('Sattelkraft, horizontale Komponente')] +
        ("{:.0f} kN,"*(poleCount*2)).format(*tuple(
                kraft['Sattelkraft_beiStuetze'][2])).rstrip(',').split(','),
    ]
    str_stue = [str_stue1, str_stue2]

    # Section cable angles
    str_wink = [
        ['', tr('am Leerseil')] + sHeader,
        ['alpha LA', tr('eingehender Winkel')] +
        ("{:.1f}°,"*poleCount).format(*tuple(
                kraft['Anlegewinkel_Leerseil'][0])).rstrip(',').split(','),
        ['alpha LE', tr('ausgehender Winkel')] +
        ("{:.1f}°,"*poleCount).format(*tuple(
                kraft['Anlegewinkel_Leerseil'][1])).rstrip(',').split(','),
        [''],
        ['', tr('am Lastseil')] + sHeader,
        ['alpha LA', tr('eingehender Winkel'), ''] +
        ("{:.1f}°,"*fieldCount).format(*tuple(
                kraft['Anlegewinkel_Lastseil'][0][1:])).rstrip(',').split(','),
        ['alpha LE', tr('ausgehender Winkel')] +
        ("{:.1f}°,"*fieldCount).format(*tuple(
                kraft['Anlegewinkel_Lastseil'][1][:-1])).rstrip(',').split(',')
        ]

    # Section verification
    tr('Ja'), tr('Nein')        # For automatic i18n string extraction
    nachweis = [tr(n) for n in kraft['Nachweis']]
    str_nach = [
        ['', ''] + sHeader,
        ['', tr('Lastseilknickwinkel')] +
        ("{:.1f}°," * poleCount).format(*tuple(
            kraft['Lastseilknickwinkel'])).rstrip(',').split(','),
        ['beta', tr('Leerseilknickwinkel')] +
        ("{:.1f}°,"*poleCount).format(*tuple(
                kraft['Leerseilknickwinkel'])).rstrip(',').split(','),
        ['', tr('Nachweis erfuellt')] +
        ('{},' * poleCount).format(*tuple(nachweis)).rstrip(',').split(','),
        ["", "  " + tr('(Leerseilknickwinkel 2)')]
    ]
    
    orderedParams = confHandler.params.paramOrder
    # Parameter set name
    setname = confHandler.params.currentSetName
    setname = setname if setname else '-'
    str_para = [[tr('Parameterset:'), setname, '', ''],
                ['']*4]     # empty row

    maxColLen = 10
    columns = [[['', '']]*maxColLen, [['', '']]*maxColLen, [['', '']]*maxColLen]
    for key in orderedParams:
        param = confHandler.params.params[key]
        paramStr = confHandler.params.getParameterAsStr(key) + ''
        if key == 'Seilsys':
            paramStr = tr(paramStr)
        sort = param['sort']
        col = int(sort/10) - 1
        row = int(sort % 10)
        columns[col][row] = ([tr(param['label']), f"{paramStr} {param['unit']}"])

    for i in range(maxColLen):
        str_para.append(columns[0][i] + [''] + columns[1][i] + [''] + columns[2][i])

    # Section headers
    headers = [
        [[tr('SEILAPLAN Projekt') + '        ' + projname]],
        [[tr('Stuetzenpositionen')]],
        [[tr('Daten fuer Absteckung im Feld (Bodenpunkt)')]],
        [[tr('Vorspannung der Seilzugkraft')]],
        [[tr('Seillaenge')]],
        [[tr('Durchhang')]],
        [[tr('Auftretende Kraefte am Seil')]],
        [[tr('Auftretende Kraefte an den Stuetzen')]],
        [[tr('Seilwinkel an den Stuetzen')]],
        [[tr('Nachweis, dass Tragseil nicht vom Sattel abhebt')]],
        [[tr('Annahmen')]],
    ]

    text = [headers, str_time, str_posi, str_abst, str_opti, str_laen, str_durc,
            str_seil, str_stue, str_wink, str_nach, str_para]
    str_report = removeTxtElements(text, "nan")

    return str_report


def generateShortReport(confHandler, result, comment, projname, outputLoc):

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='disclaimer', fontSize=6,
                              fontName='Helvetica', leading=9))
    styles.add(ParagraphStyle(name='continuousTxt', fontSize=9,
                              fontName='Helvetica'))
    
    poles = confHandler.project.poles
    polesArray = []
    for pole in poles.poles:
        if not pole['active']:
            continue
        polesArray.append(pole)
    hmPath = textwrap.wrap(confHandler.project.getHeightSourceAsStr(source=True, formatting='comma'), 85)
    hmodell = '\n'.join(hmPath)
    kraft = result['force']
    
    setname = confHandler.params.currentSetName
    setname = setname if setname else '-'
    
    az_grad = math.degrees(poles.azimut)
    az_gon = az_grad * 1.11111

    # General information
    ###
    s_gener = [
        [tr('Datum'), result['duration'][2]],
        [tr('Hoehendaten'), hmodell],
        [tr('Azimut'), "{:.2f} {} / {:.2f}°".format(az_gon, tr('gon'), az_grad)]
    ]
    
    # Input values
    ###
    param = {}
    param_list = ['D', 'MBK', 'Q', 'Bodenabst_min', 'Bodenabst_A',
                  'Bodenabst_E', 'SF_T']
    
    for key in param_list:
        p = confHandler.params.params[key]
        formatedVal = confHandler.params.getParameterAsStr(key) + ''
        param[key] = [tr(p['label']), f"{formatedVal} {p['unit']}"]

    s_input = [
        [tr('Parameterset') + ': ' + setname],
        param['D'] + param['MBK'],
        param['Q'],
        param['Bodenabst_min'] + param['Bodenabst_A'],
        ['', ''] + param['Bodenabst_E'],
        [tr('Grundspannung Tragseil (Anfangssp.)'), f"{confHandler.params.optSTA:.0f}kN"]
            + [tr('Grundspannung (Endpunkt)'), f"{kraft['Spannkraft'][1]:.0f} kN"],
        param['SF_T']]
    
    # Pole dimensions
    ###
    s_dimen = [[tr('Nr.'), tr('Bezeichnung'), tr('Sattelhoehe'),
                tr('Neigung'), tr('Min. BHD'), tr('Bundstelle')]]
    add_footnote = False
    for pole in polesArray:
        if pole['angriff'] > 45:
            pole['BHD'] = '*'
            add_footnote = True
        angle = np.nan if pole['angle'] == 0 else pole['angle']
        s_dimen.append([pole['nr'], pole['name'], f"{pole['h']:.1f} m",
                        f"{angle:.0f} °", f"{pole['BHD']} cm",
                        f"{pole['bundstelle']} cm"])
    s_dimen = removeTxtElements(s_dimen, "nan")
    s_dimen2 = None
    if add_footnote:
        s_dimen2 = [[tr('Angabe BDH bei zu steilem Winkel nicht moeglich')]]

    # Forces on poles
    ###
    s_force1 = [[tr('Maximal berechnete Seilzugkraft'),
                 f"{kraft['MaxSeilzugkraft_L'][0]:.0f} kN"], []]
    
    s_force2 = [[tr('Nr.'), tr('Bezeichnung'), tr('Max. Kraefte'), '',
                tr('Leerseil-knickwinkel'), tr('Lastseil-knickwinkel'),
                tr('Angriffs-winkel')]]
    i = 0
    for pole in polesArray:
        leerseil = np.nan
        lastseil = np.nan
        if pole['poleType'] != 'anchor':
            leerseil = kraft['Leerseilknickwinkel'][i]
            lastseil = kraft['Lastseilknickwinkel'][i]
            i += 1
        s_force2.append([pole['nr'], pole['name'],
                         f"{pole['maxForce'][0]:.0f} kN",
                         f"({tr(pole['maxForce'][1])})",
                         f"{leerseil:.1f} °", f"{lastseil:.1f} °",
                         f"{pole['angriff']:.1f} °"])
    s_force2 = removeTxtElements(s_force2, "nan")
    
    # Fields
    ###
    s_field1 = [[tr('Berechnete Seillaenge'), f"{kraft['LaengeSeil'][1]:.1f} m"],
                [tr('Max. Abstand Leerseil - Boden'),
                 f"{result['cableline']['maxDistToGround']:.1f} m"],
                []]
    s_field2 = [
        [tr('Feld'),
         tr('Horizontal-distanz'),
         tr('Schraeg-distanz'),
         tr('Hoehen-differenz'),
         tr('Durchhang Leerseil'),
         tr('Durchhang Lastseil')]]
    j = 0
    total_h = 0
    total_z = 0
    total_s = 0
    for i, pole in enumerate(polesArray[:-1]):
        nextPole = polesArray[i+1]
        poleName = pole['name'] + (f" ({pole['nr']})" if pole['nr'] else '')
        nextPoleName = nextPole['name'] + \
                       (f" ({nextPole['nr']})" if nextPole['nr'] else '')
        dist_h = nextPole['d'] - pole['d']
        dist_z = nextPole['z'] - pole['z']
        dist_s = (dist_h**2 + dist_z**2)**0.5
        total_h += dist_h
        total_z += dist_z
        total_s += dist_s
        h_diff = nextPole['z'] - pole['z']
        slack_e = np.nan
        slack_f = np.nan
        if pole['poleType'] != 'anchor' and nextPole['poleType'] != 'anchor':
            slack_e = kraft['Durchhang'][0][j]
            slack_f = kraft['Durchhang'][1][j]
            j += 1
        
        fieldIdent = "{} -> {}".format(poleName, nextPoleName)
        s_field2.append([
            (fieldIdent[:42] + '...') if len(fieldIdent) > 42 else fieldIdent,
            f"{dist_h:.0f} m", f"{dist_s:.1f} m", f"{h_diff:.1f} m",
            f"{slack_e:.1f} m", f"{slack_f:.1f} m"])
    s_field2.append([tr('Total'), f"{total_h:.1f} m", f"{total_s:.1f} m",
                     f"{total_z:.1f} m"])
    s_field2 = removeTxtElements(s_field2, "nan")
    
    # Comment
    ###
    s_comme = [[Paragraph(comment, style=styles['continuousTxt'])]]

    # Disclaimer
    ###
    s_discl = [[], [Paragraph(tr('Haftungsausschluss'), style=styles['disclaimer'])]]
    
    # Create reportlab element
    ###
    
    savePath = os.path.join(outputLoc, tr('Kurzbericht') + '.pdf')
    if os.path.exists(savePath):
        os.remove(savePath)

    width, height = portrait(A4)
    margin = 1.5 * cm
    widthT, heightT = [width - 2 * margin, height - 2 * margin]
    fontSize = 9
    smallfontSize = 7
    he_row = 0.42 * cm

    # Table styles
    font = 'Helvetica'
    fontBold = 'Helvetica-Bold'
    
    style_t = TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('FONT', (0, 0), (-1, -1), fontBold, 13),
        ('BACKGROUND', (0, 0), (-1, -1), colors.lightgrey),
        ('LINEBELOW', (0, 0), (-1, -1), 1, colors.black),
        ])
    style_h = TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('BACKGROUND', (0, 0), (-1, -1), colors.lightgrey),
        ('FONT', (0, 0), (-1, -1), fontBold, fontSize),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ])
    style_gener = [
        ('FONT', (0, 0), (-1, -1), font, fontSize),
        ('VALIGN', (0, 1), (-1, -1), 'MIDDLE'),
    ]
    style_gener_right = [
        ('FONT', (0, 0), (-1, -1), font, fontSize),
        ('VALIGN', (0, 1), (-1, -1), 'MIDDLE'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
    ]
    style_input = [
        ('FONT', (0, 0), (-1, -1), font, fontSize),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('ALIGN', (3, 0), (3, -1), 'RIGHT'),
    ]
    style_th = [
        ('FONT', (0, 0), (-1, 0), fontBold, fontSize),
        ('TOPPADDING', (0, 0), (-1, 0), 15),
        ('FONT', (0, 1), (-1, -1), font, fontSize),
        ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.whitesmoke, colors.transparent]),
        ('VALIGN', (0, 1), (-1, -1), 'MIDDLE'),
    ]
    # Align second column left, rest is right aligned
    style_2cl = style_th + [('ALIGN', (1, 0), (1, -1), 'LEFT')]
    # Align first column left, rest is right aligned
    style_fields = style_th + [('ALIGN', (0, 0), (0, -1), 'LEFT')] \
                   + [('FONT', (0, -1), (-1, -1), fontBold, fontSize)]
    # Disclaimer style (small font)
    style_small = [('FONT', (0, 0), (-1, -1), font, smallfontSize),
                   ]

    # Headers
    h_titel = Table([[f"{tr('SEILAPLAN Projekt')}: {projname}"]],
                    colWidths=widthT, style=style_t)
    h_input = Table([[tr('Eingabewerte')]],
                    colWidths=widthT, style=style_h)
    h_dimen = Table([[tr('Stuetzen- und Ankerdimensionen')]],
                    colWidths=widthT, style=style_h)
    h_force = Table([[tr('Kraefte und Winkel')]],
                    colWidths=widthT, style=style_h)
    h_field = Table([[tr('Anker- und Spannfelder')]],
                    colWidths=widthT, style=style_h)
    h_comme = Table([[tr('Bemerkung')]],
                    colWidths=widthT, style=style_h)
    
    # Build paragraphs
    data = []

    # General information
    t_gener = Table(s_gener, rowHeights=[he_row, len(hmPath)*he_row, he_row], style=style_gener)
    data.append([Table([[h_titel], [t_gener]])])

    # Input values
    t_input = Table(s_input, rowHeights=he_row, style=style_input)
    data.append([Table([[h_input], [t_input]])])

    # Pole dimensions
    t_dimen1 = Table(s_dimen, rowHeights=he_row, style=style_2cl)
    if s_dimen2:
        t_dimen2 = Table(s_dimen2, rowHeights=he_row, style=style_small)
        data.append([Table([[h_dimen], [t_dimen1], [t_dimen2]])])
    else:
        data.append([Table([[h_dimen], [t_dimen1]])])

    # Forces on poles
    t_force1 = Table(s_force1, rowHeights=he_row, style=style_gener)
    t_force2 = Table(s_force2, rowHeights=he_row, style=style_2cl)
    data.append([Table([[h_force], [t_force1], [t_force2]])])
    
    # Fields
    t_field1 = Table(s_field1, rowHeights=he_row, style=style_gener_right)
    t_field2 = Table(s_field2, rowHeights=he_row, style=style_fields)
    data.append([Table([[h_field], [t_field1], [t_field2]])])
    
    # Comment
    if comment:
        t_comme = Table(s_comme, style=style_gener)
        data.append([Table([[h_comme], [t_comme]])])

    # Disclaimer
    t_discl = Table(s_discl, style=style_small)
    data.append(([Table([[t_discl]])]))

    # Create document
    elements = []
    elements.append(Table(data))
    doc_short = SimpleDocTemplate(savePath, encoding='utf8', topMargin=margin,
                             bottomMargin=margin, leftMargin=margin,
                             rightMargin=margin, pageBreakQuick=1,
                             pagesize=portrait(A4))
    doc_short.build(elements)
    del elements
    

def generateReport(reportText, outputLoc):
    """Generate PDF report with reprotlab"""
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
    from reportlab.graphics.shapes import colors

    savePath = os.path.join(outputLoc, tr('Bericht') + '.pdf')
    if os.path.exists(savePath):
        os.remove(savePath)

    width, height = landscape(A4)
    margin = 1.5 * cm
    doc1 = SimpleDocTemplate(savePath, encoding='utf8', topMargin=margin,
                             bottomMargin=margin, leftMargin=margin,
                             rightMargin=margin, pageBreakQuick=1,
                             pagesize=landscape(A4))
    elements = []

    [headers, str_time, str_posi, str_abst, str_opti, str_laen,
     str_durc, [str_seil1, str_seil2, str_seil3, str_seil4],
     [str_stue1, str_stue2], str_wink, str_nach, str_para] = reportText

    [h_tite, h_posi, h_abst, h_opti, h_leng,
     h_durc, h_seil, h_stue, h_wink, h_nach, h_anna] = headers

    widthT, heightT = [width-2*margin, height-2*margin]
    wi_doc = [widthT]
    wi_clo = [2.7 * cm]
    wi_abk = [1.7*cm]
    he_row = [0.40 * cm]
    he_rowT = [0.45 * cm]
    poleCount = len(str_stue1[1])-2
    fieldCount = poleCount - 1
    lPadd = 6
    fontSize = 8
    smallfontSize = 6

    # Table styles
    font = 'Helvetica'
    fontBold = 'Helvetica-Bold'
    fontHeader = 'Helvetica-Oblique'

    title_style = TableStyle([('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                              ('BACKGROUND', (0, 0), (-1, -1), colors.lightgrey),
                              ('FONT', (0, 0), (-1, -1), font, 8),
                              ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                              ])
    stdStyleA = [('LEFTPADDING', (0, 0), (0, -1), lPadd),  # Align everything left
                ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),  # after first column aling right
                ('FONT', (0, 0), (-1, -1), font, fontSize)]
    stdStyleB = [('LEFTPADDING', (0, 0), (0, -1), lPadd),
                 ('FONT', (1, 0), (-1, -1), font, fontSize),
                 ('ALIGN', (2, 0), (-1, -1), 'RIGHT')]

    t_tite1 = Table(h_tite, wi_doc, [0.8*cm])
    rowheights = len(str_time) * he_row
    rowheights[2] = (str_time[2][1].count('\n') + 1) * he_row[0]
    t_tite2 = Table(str_time, [None, None], rowHeights=rowheights)
    t_tite1.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('FONT', (0, 0), (-1, -1), fontBold, 13),
        ('BACKGROUND', (0, 0), (-1, -1), colors.lightgrey),
        ('LINEBELOW', (0,0), (-1,-1), 1, colors.black),
        ]))
    t_tite2.setStyle(TableStyle([('FONT', (0, 0), (-1, -1), font, fontSize),
                                 ('VALIGN', (0, 1), (0, -1), 'MIDDLE'),
                                 ('LEFTPADDING', (0, 0), (0, -1), lPadd)]))

    t_posi1 = Table(h_posi, wi_doc, he_rowT)
    t_posi2 = Table(str_posi, [None] + 5*wi_clo, len(str_posi) * he_row)
    t_posi1.setStyle(title_style)
    t_posi2.setStyle(TableStyle(stdStyleA + [
        ('FONT', (0, 0), (-1, 0), fontHeader, smallfontSize)]))

    t_abst1 = Table(h_abst, wi_doc, he_rowT)
    t_abst2 = Table(str_abst, [None] + 2*wi_clo, len(str_abst) * he_row)
    t_abst1.setStyle(title_style)
    t_abst2.setStyle(TableStyle(stdStyleA + [
        ('FONT', (0, 1), (-1, 1), fontHeader, smallfontSize)]))

    t_opti1 = Table(h_opti, wi_doc, he_rowT)
    t_opti2 = Table(str_opti, [None] + wi_clo, len(str_opti) * he_row)
    t_opti1.setStyle(title_style)
    t_opti2.setStyle(TableStyle(stdStyleA))

    t_laen1 = Table(h_leng, wi_doc, he_rowT)
    t_laen2 = Table(str_laen, [None] + [2*cm] + [1.5*cm]*fieldCount, 4*he_row)
    t_laen1.setStyle(title_style)
    t_laen2.setStyle(TableStyle(stdStyleA + [
        ('FONT', (2, 0), (-1, 0), fontHeader, smallfontSize)]))  # field headers

    t_durc1 = Table(h_durc, wi_doc, he_rowT)
    t_durc2 = Table(str_durc, wi_abk + [None] + [1.7*cm]*fieldCount, 4*he_row)
    t_durc1.setStyle(title_style)
    t_durc2.setStyle(TableStyle(stdStyleB + [
        ('FONT', (2, 0), (-1, 0), fontHeader, smallfontSize),  # field headers
        ('FONT', (0, 0), (0, -1), font, smallfontSize)]))  # abbreviation in first column

    t_seil0 = Table(h_seil, wi_doc, he_rowT)
    t_seil1 = Table(str_seil1, wi_abk + [None] + [1*cm] + [None]*fieldCount, len(str_seil1)*he_row)
    t_seil2 = Table(str_seil2, wi_abk + [None] + [None]*poleCount, len(str_seil2)*he_row)
    t_seil3 = Table(str_seil3, wi_abk + [None] + [1*cm], len(str_seil3)*he_row)
    t_seil4 = Table(str_seil4, wi_abk + [None] + [None]*fieldCount, len(str_seil4)*he_row)
    t_seil0.setStyle(title_style)
    t_seil1.setStyle(TableStyle(stdStyleB + [
        ('FONT', (0, 0), (-1, 0), fontHeader, fontSize),  # first row = subsection
        ('FONT', (3, 3), (-1, 3), fontHeader, smallfontSize),  # pole header
        ('FONT', (0, 0), (0, -1), font, smallfontSize),  # abbreviation in first column
        ('BOTTOMPADDING', (0, -1), (-1, -1), 0)]))
    t_seil2.setStyle(TableStyle(stdStyleB + [
        ('FONT', (2, 0), (-1, 0), fontHeader, smallfontSize),  # pole header
        ('FONT', (0, 0), (0, -1), font, smallfontSize),  # abbreviation in first column
        ('TOPPADDING', (0, 0), (-1, 0), 0)]))
    t_seil3.setStyle(TableStyle(stdStyleB + [
        ('FONT', (0, 0), (-1, 0), fontHeader, fontSize),  # first row = subsection
        ('FONT', (0, 0), (0, -1), font, smallfontSize)]))  # abbreviation in first column
    t_seil4.setStyle(TableStyle(stdStyleB + [
        ('FONT', (0, 0), (1, 0), fontHeader, fontSize),  # first row = subsection
        ('FONT', (2, 0), (-1, 0), fontHeader, smallfontSize),  # field header
        ('FONT', (0, 0), (0, -1), font, smallfontSize)]))  # abbreviation in first column

    t_stue1 = Table(h_stue, wi_doc, he_rowT)
    t_stue2 = Table(str_stue1, wi_abk + [6.8*cm] + [2.4*cm]*poleCount, len(str_stue1)*he_row)
    t_stue3 = Table(str_stue2, wi_abk + [6.8*cm] + [1.2*cm]*poleCount, len(str_stue2)*he_row)
    t_stue1.setStyle(title_style)
    t_stue2.setStyle(TableStyle(stdStyleB + [
        ('FONT', (2, 0), (-1, 0), fontHeader, smallfontSize),  # field header
        ('FONT', (1, 0), (1, 0), fontHeader, fontSize),  # subsection
        ('FONT', (0, 0), (0, -1), font, smallfontSize)]))  # abbreviation in first column
    stdStyleStue = stdStyleB + [
        ('FONT', (2, 0), (-1, 1), fontHeader, smallfontSize),   # field header
        ('FONT', (1, 0), (1, 1), fontHeader, fontSize),  # subsection
        ('FONT', (0, 0), (0, -1), font, smallfontSize),  # abbreviation in first column
        ('ALIGN', (2, 1), (2, -1), 'CENTER'),
        ('ALIGN', (-2, 1), (-2, -1), 'CENTER')]
    for i in range(2, poleCount*2+2, 2):
        stdStyleStue += [
                         ('RIGHTPADDING', (i, 1), (i, -1), 1)]
    t_stue3.setStyle(TableStyle(stdStyleStue))

    t_wink1 = Table(h_wink, wi_doc, he_rowT)
    t_wink2 = Table(str_wink, wi_abk + [4*cm] + [None]*fieldCount, 7*he_row)
    t_wink1.setStyle(title_style)
    t_wink2.setStyle(TableStyle(stdStyleB + [
        ('FONT', (1, 0), (1, 0), fontHeader, fontSize),  # heading empty cable
        ('FONT', (1, 4), (1, 4), fontHeader, fontSize),  # heading load cable
        ('FONT', (2, 0), (-1, 0), fontHeader, smallfontSize),  # field header
        ('FONT', (2, 4), (-1, 4), fontHeader, smallfontSize),  # field header
        ('FONT', (0, 0), (0, -1), font, smallfontSize)]))  # abbreviation in first column

    t_nach1 = Table(h_nach, wi_doc, he_rowT)
    t_nach2 = Table(str_nach, wi_abk + [6.8*cm] + [None]*fieldCount, len(str_nach) * he_row)
    t_nach1.setStyle(title_style)
    t_nach2.setStyle(TableStyle(stdStyleB + [
        ('FONT', (2, 0), (-1, 0), fontHeader, smallfontSize),  # field header
        ('FONT', (0, 0), (0, -1), font, smallfontSize),  # abbreviation in first column
        ('FONT', (0, len(str_nach)-1), (-1, len(str_nach)-1), font, 7)]))  # Comment

    t_anna1 = Table(h_anna, wi_doc, he_rowT)
    t_anna2 = Table(str_para, [5*cm, 3*cm, 0.5*cm, 5*cm, 3*cm, 0.5*cm, 6.5*cm, 3*cm], len(str_para) * [0.35*cm])
    t_anna1.setStyle(title_style)
    t_anna2.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('LEFTPADDING', (0, 0), (0, -1), lPadd),
        ('ALIGN', (3, 0), (3, -1), 'LEFT'),
        ('ALIGN', (6, 0), (6, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('ALIGN', (4, 0), (4, -1), 'RIGHT'),
        ('ALIGN', (7, 0), (7, -1), 'RIGHT'),
        ('FONT', (0, 0), (-1, -1), font, fontSize)]))

    data = [ [Table([[t_tite1], [t_tite2]])], [Table([[t_posi1], [t_posi2]])],
             [Table([[t_abst1], [t_abst2]])],
             [Table([[t_opti1], [t_opti2]])], [Table([[t_laen1], [t_laen2]])],
             [Table([[t_durc1], [t_durc2]])], [Table([[t_seil0], [t_seil1],
             [t_seil2], [t_seil3], [t_seil4]])],
             [Table([[t_stue1], [t_stue2], [t_stue3]])],
             [Table([[t_wink1], [t_wink2]])],
             [Table([[t_nach1], [t_nach2]])], [Table([[t_anna1], [t_anna2]])]]

    elements.append(Table(data))
    doc1.build(elements)
    del elements


def createOutputFolder(location):
    i = 1
    while os.path.exists(location):
        if i == 1:
            location = "{}_{}".format(location, i)
        location = "{}_{}".format(location[:-2], i)
        i += 1
    os.makedirs(location)
    return location


# noinspection PyMethodMayBeStatic
def tr(message, **kwargs):
    """Get the translation for a string using Qt translation API.
    We implement this ourselves since we do not inherit QObject.

    :param message: String for translation.
    :type message: str, QString

    :returns: Translated version of message.
    :rtype: QString

    Parameters
    ----------
    **kwargs
    """
    # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
    return QCoreApplication.translate('@default', message)
