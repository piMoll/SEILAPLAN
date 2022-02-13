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
        self.checkFile()

    def checkFile(self):
    
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
                # Fields of Vertex csv
                idxTYPE = [idx for idx, h in enumerate(row) if
                           self.formatStr(h) == 'TYPE']
                idxLon = [idx for idx, h in enumerate(row) if
                          self.formatStr(h) == 'LON']
                idxLat = [idx for idx, h in enumerate(row) if
                          self.formatStr(h) == 'LAT']
                idxSEQ = [idx for idx, h in enumerate(row) if
                          self.formatStr(h) == 'SEQ']
                idxAlti = [idx for idx, h in enumerate(row) if
                           self.formatStr(h) == 'ALTITUDE']
                idxHD = [idx for idx, h in enumerate(row) if
                         self.formatStr(h) == 'HD']
                idxAz = [idx for idx, h in enumerate(row) if
                         self.formatStr(h) == 'AZ']
                break
    
        # Check if data is in vertex format
        if len(idxTYPE) == 1 and len(idxSEQ) == 1 and len(idxAlti) == 1 \
                and len(idxHD) == 1 and len(idxAz) == 1 \
                and len(idxLat) == 1 and len(idxLon) == 1:
            self.valid = True
            try:
                self.success = self.readOutData(idxTYPE[0], idxSEQ[0], idxAlti[0],
                            idxHD[0], idxAz[0], idxLon[0], idxLat[0], sep)
            except Exception:
                self.success = False

    def readOutData(self, idxTYPE, idxSEQ, idxAlti, idxHD, idxAz, idxLon,
                          idxLat, sep):
        try:
            # Readout measuring type separately (because the data is of
            # type string)
            dataType = np.genfromtxt(self.path, delimiter=sep, dtype=str,
                                     usecols=idxTYPE)
            # Analyse when data rows start
            skipHead = np.where(dataType == 'TRAIL')[0][0]
            # Read out numerical values
            seq, alti, hd, az, lon, lat = np.genfromtxt(self.path,
                                                        delimiter=sep,
                                                        usecols=(
                                                        idxSEQ, idxAlti, idxHD,
                                                        idxAz, idxLon, idxLat),
                                                        skip_header=skipHead,
                                                        unpack=True)
        except ValueError:
            return False
    
        # Make sure array dataType has the same size as the numerical data
        #  and check if the readout data has type TRAIL
        trail = dataType[skipHead:] == 'TRAIL'
    
        # See if dimensions of extracted data fit
        if not (trail.size == seq.size == alti.size == hd.size ==
                az.size == lon.size == lat.size):
            return False
    
        # Check for missing values and create array masks to skip them when
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
    
        # Check if the sequence numbers are in order and that there are no gaps
        if np.sum(np.cumsum(np.array([1] * seq.size)) == seq) != seq.size:
            # Only add a warning, create the profile ether way
            self.errorMsg = self.tr('Die CSV-Datei enthaelt Messluecken, '
                                    'das erstellte Profil koennte fehlerhaft sein.')
    
        # If there are multiple measurement series (sequence restarts at one),
        # there is most certainly an issue with the CSV data
        if np.sum(seq == 1) > 1:
            # Only add a warning
            self.errorMsg = self.tr('Die CSV-Datei enthaelt mehr als eine '
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
        self.nr = np.arange(len(gpsx)) + 1
        return True
