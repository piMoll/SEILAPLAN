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
from .heightSource import AbstractSurveyReader


class CsvXyzReader(AbstractSurveyReader):
    
    def __init__(self, path):
        AbstractSurveyReader.__init__(self, path)
        
        self.sep = None
        self.idxX = None
        self.idxY = None
        self.idxZ = None
        
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
                idxX = [idx for idx, h in enumerate(row) if
                        self.formatHeader(h) == 'X']
                idxY = [idx for idx, h in enumerate(row) if
                        self.formatHeader(h) == 'Y']
                idxZ = [idx for idx, h in enumerate(row) if
                        self.formatHeader(h) == 'Z']
                break
        
        # Check if data is in x, y, z format
        if len(idxX) == 1 and len(idxY) == 1 and len(idxZ) == 1:
            self.sep = sep
            self.idxX = idxX[0]
            self.idxY = idxY[0]
            self.idxZ = idxZ[0]
            self.valid = True
    
    def readOutData(self):
        try:
            x, y, z = np.genfromtxt(self.path, delimiter=self.sep, dtype='float64',
                                    usecols=(self.idxX, self.idxY, self.idxZ),
                                    unpack=True, skip_header=1)
        except TypeError as e:
            return False
        # Check for missing values and remove whole row
        x = x[~(np.isnan(x) + np.isnan(y) + np.isnan(z))]
        y = y[~(np.isnan(x) + np.isnan(y) + np.isnan(z))]
        z = z[~(np.isnan(x) + np.isnan(y) + np.isnan(z))]

        # Are there enough points?
        if len(x) < 2:
            return False

        self.surveyPoints = {
            'x': x,
            'y': y,
            'z': z
        }
        self.nr = np.arange(len(x)) + 1
        return True
