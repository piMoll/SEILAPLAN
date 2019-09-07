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


class AdjustmentDialogParams(object):
    
    def __init__(self, dialog):
        self.dialog = dialog
        self.params = {
            'Q': str(round(dialog.cableParams['Q'][0], 4)),
            'qT': str(round(dialog.cableParams['qT'][0], 4)),
        }
        self.fillInParams()
        self.connectFields()
    
    def fillInParams(self):
        self.dialog.fieldQ.setText(self.params['Q'])
        self.dialog.fieldqT.setText(self.params['qT'])
        # self.dialog.fieldA.setText(f"{self.params['A']}")
        # self.dialog.fieldE.setText(f"{self.params['E']}")
        # self.dialog.fieldqz1.setText(f"{self.params['qz1']}")
        # self.dialog.fieldqz2.setText(f"{self.params['qz2']}")
        # self.dialog.fieldVorsp.setText(f"{self.params['Vorsp']}")
        
    def connectFields(self):
        self.dialog.fieldQ.textChanged.connect(lambda newVal: self.paramHasChanged(newVal, 'Q'))
        self.dialog.fieldqT.textChanged.connect(lambda newVal: self.paramHasChanged(newVal, 'qT'))
        # self.dialog.fieldA.editingFinished.connect(self.paramHasChanged)
        # self.dialog.fieldE.editingFinished.connect(self.paramHasChanged)
        # self.dialog.fieldqz1.editingFinished.connect(self.paramHasChanged)
        # self.dialog.fieldqz2.editingFinished.connect(self.paramHasChanged)
        # self.dialog.fieldVorsp.editingFinished.connect(self.paramHasChanged)

    def paramHasChanged(self, newVal, fieldName=''):
        valid, error = self.validate(newVal)
        if valid:
            self.params[fieldName] = newVal
            self.dialog.enableRecalculation()
        else:
            QMessageBox.information(self.dialog, 'Ungültiger Wert', error)
            
    
    def validate(self, newVal):
        # TODO: Validate funktion vom Hauptfenster verwenden
        return True, ''
        

