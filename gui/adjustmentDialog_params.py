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
    """
    Organizes all functionality in the second tab "cable parameters" of the
    tab widgets.
    """
    
    def __init__(self, dialog):
        self.dialog = dialog
        self.params = {}
        self.fields = {
            'Q': self.dialog.fieldQ,
            'qT': self.dialog.fieldqT,
            'A': self.dialog.fieldA,
            'E': self.dialog.fieldE,
            'qz1': self.dialog.fieldqz1,
            'qz2': self.dialog.fieldqz2,
            # 'Vorsp': self.dialog.fieldVorsp,
        }
        self.connectFields()

    def fillInParams(self, cableparams):
        self.params = {
            'Q': cableparams['Q'][0],
            'qT': cableparams['qT'][0],
            'A': cableparams['A'][0],
            'E': cableparams['E'][0],
            'qz1': cableparams['qz1'][0],
            'qz2': cableparams['qz2'][0],
            # 'Vorsp': cableparams['Vorsp'][0],
        }
        for key, field in self.fields.items():
            field.blockSignals(True)
            field.setText(str(self.params[key]))
            field.blockSignals(False)
        
    def connectFields(self):
        self.dialog.fieldQ.textChanged.connect(
            lambda newVal: self.paramHasChanged(newVal, 'Q'))
        self.dialog.fieldqT.textChanged.connect(
            lambda newVal: self.paramHasChanged(newVal, 'qT'))
        self.dialog.fieldA.textChanged.connect(
            lambda newVal: self.paramHasChanged(newVal, 'A'))
        self.dialog.fieldE.textChanged.connect(
            lambda newVal: self.paramHasChanged(newVal, 'E'))
        self.dialog.fieldqz1.textChanged.connect(
            lambda newVal: self.paramHasChanged(newVal, 'qz1'))
        self.dialog.fieldqz2.textChanged.connect(
            lambda newVal: self.paramHasChanged(newVal, 'qz2'))

    def paramHasChanged(self, newVal, fieldName=''):
        valid = self.validate(newVal)
        if valid:
            self.params[fieldName] = newVal
            self.dialog.updateCableParam(fieldName, newVal)

    def validate(self, newVal):
        # TODO: Validate funktion vom Hauptfenster verwenden
        
        # if False:
        #     QMessageBox.information(self.dialog, 'Ungültiger Wert', error)
        #     # Restore old value
        #     self.fields[fieldName].setText(self.params[fieldname])
        return True, ''
        

