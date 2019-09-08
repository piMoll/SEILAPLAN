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
    
    def __init__(self, dialog, cableparams):
        self.dialog = dialog
        self.params = {
            'Q': str(round(cableparams['Q'][0], 4)),
            'qT': str(round(cableparams['qT'][0], 4)),
            'A': str(round(cableparams['A'][0], 4)),
            'E': str(round(cableparams['E'][0], 4)),
            'qz1': str(round(cableparams['qz1'][0], 4)),
            'qz2': str(round(cableparams['qz2'][0], 4)),
            # 'Vorsp': str(round(cableparams['Vorsp'][0], 4)),
        }
        self.fields = {
            'Q': self.dialog.fieldQ,
            'qT': self.dialog.fieldqT,
            'A': self.dialog.fieldA,
            'E': self.dialog.fieldE,
            'qz1': self.dialog.fieldqz1,
            'qz2': self.dialog.fieldqz2,
            # 'Vorsp': self.dialog.fieldVorsp,
        }
        self.fillInParams()
        self.connectFields()
    
    def fillInParams(self):
        for key, field in self.fields.items():
            field.setText(self.params[key])
        
    def connectFields(self):
        for key, field in self.fields.items():
            field.textChanged.connect(
                lambda newVal: self.paramHasChanged(newVal, key))

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
        

