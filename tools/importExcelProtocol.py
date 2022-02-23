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
from ..lib.pylightxl import pylightxl as xl
import numpy as np
# from qgis.core import QgsCoordinateReferenceSystem
# from .outputGeo import GPS_CRS, latLonToUtmCode, reprojectToCrs
from .heightSource import AbstractSurveyReader


class ExcelProtocolReader(AbstractSurveyReader):
    
    # Addresses of excel values
    CELL_VERSION = 'I3'
    CELL_PRVERF = 'C4'
    CELL_PRNR = 'C6'
    CELL_PRGMD = 'G6'
    CELL_PRWALD = 'G8'
    CELL_PRBEM = 'C10'
    CELL_ANLAGE = 'C8'
    CELL_X = 'C14'
    CELL_Y = 'F14'
    CELL_Z = 'I14'
    CELL_NR = 'C16'
    CELL_AZI = 'C18'
    COL_NR = 'A'
    COL_DIST = 'B'
    COL_SLOPE = 'D'
    COL_NOTES = 'E'
    ROW_START = 21
    
    TEMPLATE_VERSION = 'v3.4'
    
    def __init__(self, path):
        AbstractSurveyReader.__init__(self, path)
        self.checkStructure()
    
    def checkStructure(self):
        db = xl.readxl(
            fn='/home/pi/Downloads/protokoll_test2.xlsx')
        sheet = db.ws(ws=db.ws_names[0])
    
        # TODO: check if excel has right format
        
        self.valid = True

    def readOutData(self):
        db = xl.readxl(
            fn='/home/pi/Downloads/protokoll_test2.xlsx')
        sheet = db.ws(ws=db.ws_names[0])
    
        # Readout data and check validity
        
        templateVersion = sheet.address(address=self.CELL_VERSION)
        
        try:
            assert templateVersion == self.TEMPLATE_VERSION
        except AssertionError:
            self.errorMsg = self.tr('Veraltetes Template, Daten koennen nicht eingelesen werden.')
            return False
    
        prData = {
            'header': {
                'PrVerf': sheet.address(address=self.CELL_PRVERF),
                'PrNr': sheet.address(address=self.CELL_NR),
                'PrGmd': sheet.address(address=self.CELL_PRGMD),
                'PrWald': sheet.address(address=self.CELL_PRWALD),
                'PrBemerkung': sheet.address(address=self.CELL_PRBEM),
            },
            'anlagetyp': sheet.address(address=self.CELL_ANLAGE),
        }
    
        try:
            absolutePoint = {
                'x': float(sheet.address(address=self.CELL_X)),
                'y': float(sheet.address(address=self.CELL_Y)),
            }
        except ValueError:
            self.errorMsg = self.tr('Koordinatenwerte sind ungueltig')
            return False
        
        # TODO: Check that coordinates are not geographical

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
        
        # Check existence and valid of mandatory values
        try:
            assert 0 <= azimuth <= 400
        except AssertionError:
            self.errorMsg = self.tr('Azimut ist ungueltig')
            return False
    
        nr = [1]
        distList = [0]
        slopeList = [0]
        notes = {
            'onPoint': [],
            'between': []
        }
        nextPoint = 2
        rowIdx = self.ROW_START + 1
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
        
            nr.append(nextPoint)
            distList.append(dist)
            slopeList.append(slope)
            notes['between'].append(sheet.address(address=f'{self.COL_NOTES}{rowIdx}'))
            notes['onPoint'].append(sheet.address(address=f'{self.COL_NOTES}{rowIdx + 1}'))
        
            try:
                nextPoint = int(sheet.address(address=f'{self.COL_NR}{rowIdx + 1}'))
            except ValueError:
                nextPoint = None
            
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
        except ValueError:
            self.errorMsg = self.tr('Punkt-Nr. nicht in Protokoll vorhanden')
            return False
        
        # Calculate relative coordinates (beginning with 0,0)
        relCoords = np.array(
            [np.cumsum(hd * np.sin(azimuth)),
             np.cumsum(hd * np.cos(azimuth))
        ])
        relHeight = h
        
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
