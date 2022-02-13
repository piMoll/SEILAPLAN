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
# import numpy as np
# from qgis.core import QgsCoordinateReferenceSystem
# from .outputGeo import GPS_CRS, latLonToUtmCode, reprojectToCrs
from .heightSource import AbstractSurveyReader


class ExcelProtocolReader(AbstractSurveyReader):
    
    def __init__(self, path):
        AbstractSurveyReader.__init__(self, path)
        self.checkFile()
    
    def checkFile(self):
        pass

    def readOutData(self):
        pass

