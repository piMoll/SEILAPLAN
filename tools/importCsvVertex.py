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
import csv
import numpy as np
from qgis.core import QgsCoordinateReferenceSystem
from .outputGeo import GPS_CRS, latLonToUtmCode, reprojectToCrs
from .heightSource import AbstractSurveyReader


class CsvVertexReader(AbstractSurveyReader):
    
    def __init__(self, path):
        AbstractSurveyReader.__init__(self, path)
        
        self.sep = None
        self.notes = []
        self.idxMark = None
        self.idxTYPE = None
        self.idxLon = None
        self.idxLat = None
        self.idxSEQ = None
        self.idxAlti = None
        self.idxHD = None
        self.idxH = None
        self.idxAz = None
        
        self.checkStructure()

    def checkStructure(self):
    
        with open(self.path, newline='') as file:
            reader = csv.reader(file)
            sep = ','
            for row in reader:
                if len(row) == 1:
                    row = row[0].split(';')
                    sep = ';'
                if len(row) == 1:
                    row = row[0].split(',')
                    sep = ','
            
                # Analyse header line
                idxMark = [idx for idx, h in enumerate(row) if
                           self.formatHeader(h) == 'MARK']
                idxTYPE = [idx for idx, h in enumerate(row) if
                           self.formatHeader(h) == 'TYPE']
                idxLon = [idx for idx, h in enumerate(row) if
                          self.formatHeader(h) == 'LON']
                idxLat = [idx for idx, h in enumerate(row) if
                          self.formatHeader(h) == 'LAT']
                idxSEQ = [idx for idx, h in enumerate(row) if
                          self.formatHeader(h) == 'SEQ']
                idxAlti = [idx for idx, h in enumerate(row) if
                           self.formatHeader(h) == 'ALTITUDE']
                idxHD = [idx for idx, h in enumerate(row) if
                         self.formatHeader(h) == 'HD']
                idxH = [idx for idx, h in enumerate(row) if
                         self.formatHeader(h) == 'H']
                idxAz = [idx for idx, h in enumerate(row) if
                         self.formatHeader(h) == 'AZ']
                break
    
        # Check if data is in vertex format
        if len(idxTYPE) == 1 and len(idxTYPE) == 1 and len(idxSEQ) == 1 \
                and len(idxAlti) == 1 and len(idxHD) == 1 and len(idxH) == 1 \
                and len(idxAz) == 1 and len(idxLat) == 1 and len(idxLon) == 1:
    
            self.sep = sep
            self.idxMark = idxMark[0]
            self.idxTYPE = idxTYPE[0]
            self.idxLon = idxLon[0]
            self.idxLat = idxLat[0]
            self.idxSEQ = idxSEQ[0]
            self.idxAlti = idxAlti[0]
            self.idxHD = idxHD[0]
            self.idxH = idxH[0]
            self.idxAz = idxAz[0]
            
            self.valid = True

    def readOutData(self):
        try:
            # Readout mark (marks the rows with measurements) and measuring
            #  type separately because the data is of type string
            (mark, dataType) = np.genfromtxt(self.path, delimiter=self.sep,
                                             dtype=str, usecols=(self.idxMark,
                                             self.idxTYPE), unpack=True)
            # Analyse when data rows start
            skipHead = np.where(mark == '$')[0][0]
            # Read out numerical values
            (seq, alti,
                hd, h, az,
                lon, lat) = np.genfromtxt(self.path, delimiter=self.sep,
                                         usecols=(self.idxSEQ, self.idxAlti,
                                                  self.idxHD, self.idxH, self.idxAz,
                                                  self.idxLon, self.idxLat),
                                         skip_header=skipHead, unpack=True)
        except ValueError:
            return False
    
        # See if dimensions of extracted numerical data and mark fit
        if not (mark[skipHead:].size == seq.size == alti.size ==
                hd.size == h.size == az.size == lon.size == lat.size):
            return False
    
        # Create a mask to mark missing / wrong values and skip them when
        #  processing
        mask_use = np.array([True] * seq.size)
    
        # Check if there are multiple measurement series by searching for
        #  seq = 1 or the lowest value. Only take the longest sequence of
        #  measurements
        sequence_len = []
        sequence_starts = np.where(seq == np.min(seq))[0]
        last_start = 0
        for sequence_start in sequence_starts:
            if sequence_start != 0:
                sequence_len.append(sequence_start - last_start)
            last_start = sequence_start
        sequence_len.append(seq.size - last_start)
        # Find sequence start and end index
        start_of_longest_sequence = sequence_starts[np.argmax(sequence_len)]
        end_of_longest_sequence = sequence_starts[np.argmax(sequence_len) + 1] \
            if sequence_len == seq.size else -1
    
        # Update mask by setting every other measurement series to False
        mask_use[:start_of_longest_sequence] = False
        if end_of_longest_sequence != -1:
            mask_use[end_of_longest_sequence:] = False

        # Check if there are rows of type '3P': These are measurements of
        #  possible tree poles
        treePosition = seq[np.where(dataType[skipHead:] == '3P')[0]]
        treeAltitude = alti[np.where(dataType[skipHead:] == '3P')[0]]
        
        # Check for entries of other type than 'TRAIL' and filter them out
        mask_use *= dataType[skipHead:] == 'TRAIL'
        
        # Apply mask to measurement values
        seq = seq[mask_use]
        alti = alti[mask_use]
        hd = hd[mask_use]
        az = az[mask_use]
        lon = lon[mask_use]
        lat = lat[mask_use]
        # Check if some gps measurements are missing
        mask_gps = ~(np.isnan(lon) + np.isnan(lat))
    
        # Quality checks
    
        # If relative measurements are missing, we cannot create a line
        if np.sum(np.isnan(az)) > 0 \
                or np.sum(np.isnan(hd)) > 0:
            self.errorMsg = self.tr('Die Messdaten sind unvollstaendig, '
                                    'die CSV-Datei kann nicht geladen werden.')
            return False
    
        # CAN'T DO THIS CHECK ANYMORE BECAUSE THERE CAN BE 3P POINTS
        # # Check if the sequence numbers are in order and that there are no gaps
        # if np.sum(np.cumsum(np.array([1] * seq.size)) == seq) != seq.size:
        #     # Only add a warning, create the profile ether way
        #     self.errorMsg = self.tr('Die CSV-Datei enthaelt Messluecken, '
        #                             'das erstellte Profil koennte fehlerhaft sein.')
    
        # If there are multiple measurement series (sequence restarts at one),
        # there is most certainly an issue with the CSV data
        if np.sum(seq == 1) > 1:
            # Only add a warning
            self.warnMsg = self.tr('Die CSV-Datei enthaelt mehr als eine '
                                    'Messreihe. Es wurde nur die laengste Messreihe geladen.')
    
        # Check if at least one pair of absolute coordinates are present to
        #  transform relative measurements into destination coordinate system
        if lon[mask_gps].size == 0 or lat[mask_gps].size == 0:
            self.errorMsg = self.tr('Die CSV-Datei enthaelt keine '
                                    'GPS-Koordinaten, das Profil kann nicht erstellt werden.')
            return False
    
        # Calculate X/Y coordinate relative to the first point (0, 0)
        #  by adding the distance (horizontalDist * sin(azimuth))
        relCoords = np.array(
            [np.cumsum(hd * np.sin(np.radians(az))),
             np.cumsum(hd * np.cos(np.radians(az)))
             ])
    
        # Guess UTM epsg code by analysing lat, lon values
        try:
            utmEpsg = latLonToUtmCode(lat[mask_gps][0], lon[mask_gps][0])
        except Exception:
            self.errorMsg = self.tr(
                'Die CSV-Datei enthaelt ungueltige GPS-Koordinaten.')
            return False
    
        # Transform GPS coordinates to projected UTM coordinates
        utmx, utmy = reprojectToCrs(lon[mask_gps], lat[mask_gps], GPS_CRS,
                                    utmEpsg)
        utmCoords = np.array([utmx, utmy])
    
        # Calculate mean distance to UTM coords but only on rows where
        #  GPS coords are present
        deltaX = utmCoords[0] - relCoords[0][mask_gps]
        deltaY = utmCoords[1] - relCoords[1][mask_gps]
        meanDist = np.mean(np.sqrt(np.square(deltaX) + np.square(deltaY)))
        # Calculate mean azimut to UTM coords
        meanAz = np.mean(np.arctan(deltaX / deltaY))
    
        # Move relative coordinates to UTM system
        relCoordsNew = np.array([
            relCoords[0] + meanDist * np.sin(meanAz),
            relCoords[1] + meanDist * np.cos(meanAz)
        ])
        # Translate back to WGS84
        gpsx, gpsy = reprojectToCrs(relCoordsNew[0], relCoordsNew[1], utmEpsg,
                                    GPS_CRS)
        self.surveyPoints = {
            'x': gpsx,
            'y': gpsy,
            'z': alti
        }
        self.spatialRef = QgsCoordinateReferenceSystem(GPS_CRS)
        self.nr = seq.astype(int)
        
        if len(treePosition) > 0:
            self.notes = [''] * len(seq)
            for treeCount, treeNr in enumerate(treePosition):
                # Sequence of tree ground point comes one before
                terrainNr = int(treeNr) - 1
                # Check if measurement of tree ground point exists in array
                if not (terrainNr in self.nr):
                    continue
                arrayIdx = np.where(self.nr == terrainNr)[0]
                if len(arrayIdx) > 0:
                    treeHeight = treeAltitude[treeCount] - alti[arrayIdx[0]]
                    self.notes[arrayIdx[0]] = f'3P, h = {treeHeight:0.1f}m'
        
        # QS: Calculate difference between GPS coords (in UTM) and relative
        #  measurements that were moved to UTM system
        # self.warnMsg = f'Max diff utmx {np.round(np.max(relCoordsNew[0] - utmx), 2)},' \
        #                f' utmy {np.round(np.max(relCoordsNew[1] - utmy), 2)} m'
        
        return True
