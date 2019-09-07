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

from qgis.PyQt.QtWidgets import QMessageBox


class AdjustmentDialogThresholds(object):
    
    def __init__(self, dialog):
        self.dialog = dialog
        self.data = dialog.originalData
        self.fillInThresholds()
        self.fillInValues()
        self.checkThresholds()
    
    def fillInThresholds(self):
        pass
    
    def fillInValues(self):
        pass
    
    def checkThresholds(self):
        pass
