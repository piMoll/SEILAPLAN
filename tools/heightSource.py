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
from qgis.PyQt.QtCore import QCoreApplication
from qgis.core import QgsCoordinateReferenceSystem


class AbstractHeightSource(object):
    
    def __init__(self):
        self.path = None
        self.spatialRef = None
        self.contourLayer = None
        self.extent = []
        self.errorMsg = ''
        self.buffer = (None, None)
        self.valid = False
    
    def getAsStr(self):
        return self.path or ''
    
    def prepareData(self, *args):
        raise NotImplementedError
    
    def getHeightAtPoints(self, coords):
        raise NotImplementedError
    
    def guessCrs(self):
        if self.extent and -180 <= self.extent[0] <= 180 \
                and -90 <= self.extent[1] <= 90:
            self.spatialRef = QgsCoordinateReferenceSystem('EPSG:4326')
        else:
            self.spatialRef = QgsCoordinateReferenceSystem()

    # noinspection PyMethodMayBeStatic
    def tr(self, message, **kwargs):
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
        return QCoreApplication.translate(type(self).__name__, message)

