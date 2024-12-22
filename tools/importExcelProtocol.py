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
from SEILAPLAN.lib.pylightxl import pylightxl as xl
import numpy as np
from .heightSource import AbstractSurveyReader
from .outputGeo import reprojectToCrs, GPS_CRS


class ExcelProtocolReader(AbstractSurveyReader):
    
    # Addresses of excel values
    CELL_VERSION = 'G3'
    CELL_PRVERF = 'C4'
    CELL_PRNR = 'C6'
    CELL_PRGMD = 'G6'
    CELL_PRWALD = 'G8'
    CELL_PRBEM = 'C10'
    CELL_ANLAGE = 'C8'
    CELL_X = 'C14'
    CELL_Y = 'E14'
    CELL_Z = 'G14'
    CELL_NR = 'C16'
    CELL_AZI = 'C18'
    COL_NR = 'A'
    COL_DIST = 'B'
    COL_SLOPE = 'C'
    COL_NOTES = 'D'
    ROW_START = 21
    
    TEMPLATE_VERSION = 'v3.4'
    
    def __init__(self, path):
        AbstractSurveyReader.__init__(self, path)
        self.notes = {
            'onPoint': [],
            'between': []
        }
        self.checkStructure()
    
    def checkStructure(self):
        db = xl.readxl(fn=self.path)
        sheet = db.ws(ws=db.ws_names[0])
    
        # Check if the Excel file has a version in the right cell
        try:
            templateVersion = sheet.address(address=self.CELL_VERSION)
            self.valid = templateVersion and templateVersion.startswith('v')
        except ValueError:
            self.valid = False
            return

    def readOutData(self):
        db = xl.readxl(fn=self.path)
        sheet = db.ws(ws=db.ws_names[0])
    
        # Readout data and check validity
        templateVersion = sheet.address(address=self.CELL_VERSION)
        try:
            assert templateVersion == self.TEMPLATE_VERSION
        except AssertionError:
            self.errorMsg = self.tr('Veraltetes Template, Daten koennen nicht eingelesen werden')
            return False
    
        self.prHeaderData = {
            'Header': {
                'PrVerf': sheet.address(address=self.CELL_PRVERF),
                'PrNr': sheet.address(address=self.CELL_PRNR),
                'PrGmd': sheet.address(address=self.CELL_PRGMD),
                'PrWald': sheet.address(address=self.CELL_PRWALD),
                'PrBemerkung': sheet.address(address=self.CELL_PRBEM),
            },
            'Anlagetyp': sheet.address(address=self.CELL_ANLAGE),
        }
    
        try:
            absolutePoint = {
                'x': float(sheet.address(address=self.CELL_X)),
                'y': float(sheet.address(address=self.CELL_Y)),
            }
        except ValueError:
            self.errorMsg = self.tr('Koordinatenwerte sind ungueltig')
            return False

        # Check if coordinates are geographic and transform to projected
        if -90 <= abs(absolutePoint['x']) <= 90 and -180 <= absolutePoint['y'] <= 180:
            xnew, ynew = reprojectToCrs([absolutePoint['x']],
                                        [absolutePoint['y']], GPS_CRS)
            if xnew and ynew:
                absolutePoint['x'] = xnew
                absolutePoint['y'] = ynew
            else:
                self.errorMsg = self.tr('Koordinatenwerte sind ungueltig')
                return False

        try:
            absolutePoint['z'] = float(sheet.address(address=self.CELL_Z))
        except ValueError:
            # Z value is not mandatory
            absolutePoint['z'] = 0.0
        
        try:
            absolutePointNr = int(sheet.address(address=self.CELL_NR))
        except ValueError:
            self.errorMsg = self.tr('Punkt-Nummer ist ungueltig')
            return False

        try:
            azimuth = float(sheet.address(address=self.CELL_AZI))
        except ValueError:
            self.errorMsg = self.tr('Azimut ist ungueltig')
            return False
        
        try:
            assert 0 <= azimuth <= 400
        except AssertionError:
            self.errorMsg = self.tr('Azimut ist ungueltig')
            return False
        
        distList = [0]
        slopeList = [0]
        nr = [0]
        nextPoint = 1
        rowIdx = self.ROW_START
        self.notes['onPoint'].append('')
        
        # Check if there are measurements before first point
        dist = sheet.address(address=f'{self.COL_DIST}{self.ROW_START}')
        slope = sheet.address(address=f'{self.COL_SLOPE}{self.ROW_START}')
        if dist == '' and slope == '':
            # No measurements: start at point nr 1 instead of 0
            nr = [1]
            nextPoint = 2
            self.notes['onPoint'][0] = sheet.address(address=f'{self.COL_NOTES}{rowIdx + 1}')
            rowIdx = self.ROW_START + 2
        
        elif (dist == '' and slope != '') or (dist != '' and slope == ''):
            self.errorMsg = (self.tr(
                'Fehlende oder fehlerhafte Werte fuer Distanz oder Neigung auf Zeile _rowIdx_')).replace(
                '_rowIdx_', str(self.ROW_START))
            return False
        
        while nextPoint is not None:
            # Check if mandatory values are present
            dist = sheet.address(address=f'{self.COL_DIST}{rowIdx}')
            slope = sheet.address(address=f'{self.COL_SLOPE}{rowIdx}')
            try:
                dist = float(dist)
                slope = float(slope)
            except ValueError:
                if dist == '' and slope == '':
                    # End of protocol
                    break
                else:
                    # Invalid data in distance or slope cells
                    self.errorMsg = (self.tr('Fehlende oder fehlerhafte Werte fuer Distanz oder Neigung auf Zeile _rowIdx_')).replace('_rowIdx_', rowIdx)
                    return False
        
            try:
                nextPoint = int(sheet.address(address=f'{self.COL_NR}{rowIdx + 1}'))
            except ValueError:
                nextPoint = None
            
            nr.append(nextPoint)
            distList.append(dist)
            slopeList.append(slope)
            self.notes['between'].append(sheet.address(address=f'{self.COL_NOTES}{rowIdx}'))
            self.notes['onPoint'].append(sheet.address(address=f'{self.COL_NOTES}{rowIdx + 1}'))
            
            rowIdx += 2
        
        if len(distList) < 2:
            self.errorMsg = self.tr('Nicht genuegend Punkte in Protokoll vorhanden')
            return False
        
        # Calculate horizontal distance and height
        nr = np.array(nr)
        azimuth = np.radians(azimuth/400*360)
        slopeRad = np.arctan(np.array(slopeList)/100)
        sd = np.array(distList)
        hd = sd * np.cos(slopeRad)
        h = sd * np.sin(slopeRad)
        
        # See if point number of absolute point exists in protocol
        try:
            idxAbsPoint = np.where(np.array(nr) == absolutePointNr)[0][0]
        except IndexError:
            self.errorMsg = self.tr('Punkt-Nr. nicht in Protokoll vorhanden')
            return False
        
        # Calculate relative coordinates (beginning with 0,0)
        relCoords = np.array(
            [np.cumsum(hd * np.sin(azimuth)),
             np.cumsum(hd * np.cos(azimuth))
        ])
        relHeight = np.cumsum(h)
        
        # Calculate absolute coordinates
        deltaX = absolutePoint['x'] - relCoords[0][idxAbsPoint]
        deltaY = absolutePoint['y'] - relCoords[1][idxAbsPoint]
        deltaZ = absolutePoint['z'] - relHeight[idxAbsPoint]
        
        absCoords = np.array([
            relCoords[0] + deltaX,
            relCoords[1] + deltaY,
            relHeight + deltaZ
            ])

        self.surveyPoints = {
            'x': absCoords[0],
            'y': absCoords[1],
            'z': absCoords[2]
        }
        self.nr = np.array(nr)

        return True
