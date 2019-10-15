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


class AdjustmentDialogParams(object):
    """
    Organizes all functionality in the second tab "cable parameters" of the
    tab widgets.
    """
    
    def __init__(self, dialog, paramHandler):
        """
        :type dialog: gui.adjustmentDialog.AdjustmentDialog
        :type paramHandler: configHandler.ParamConfHandler
        """
        self.dialog = dialog
        self.paramHandler = paramHandler
        self.params = {}
        self.fields = {
            'Q': self.dialog.fieldQ,
            'qT': self.dialog.fieldqT,
            'A': self.dialog.fieldA,
            'E': self.dialog.fieldE,
            'qz1': self.dialog.fieldqz1,
            'qz2': self.dialog.fieldqz2,
            'Vorsp': self.dialog.fieldVorsp,
        }
        self.connectFields()

    def fillInParams(self):
        self.params = {
            'Q': self.paramHandler.getParameterAsStr('Q'),
            'qT': self.paramHandler.getParameterAsStr('qT'),
            'A': self.paramHandler.getParameterAsStr('A'),
            'E': self.paramHandler.getParameterAsStr('E'),
            'qz1': self.paramHandler.getParameterAsStr('qz1'),
            'qz2': self.paramHandler.getParameterAsStr('qz2'),
            'Vorsp': str(self.dialog.result['optSTA']),
        }
        for key, field in self.fields.items():
            field.blockSignals(True)
            field.setText(self.params[key])
            field.blockSignals(False)
        
    def connectFields(self):
        self.dialog.fieldQ.editingFinished.connect(
            lambda: self.paramHasChanged('Q'))
        self.dialog.fieldqT.editingFinished.connect(
            lambda: self.paramHasChanged('qT'))
        self.dialog.fieldA.editingFinished.connect(
            lambda: self.paramHasChanged('A'))
        self.dialog.fieldE.editingFinished.connect(
            lambda: self.paramHasChanged('E'))
        self.dialog.fieldqz1.editingFinished.connect(
            lambda: self.paramHasChanged('qz1'))
        self.dialog.fieldqz2.editingFinished.connect(
            lambda: self.paramHasChanged('qz2'))
        self.dialog.fieldVorsp.editingFinished.connect(
            lambda: self.paramHasChanged('Vorsp'))

    def paramHasChanged(self, fieldName=''):
        newVal = self.fields[fieldName].text()
        if fieldName == 'Vorsp':
            newVal = self.dialog.updateOptSTA(newVal)
        else:
            newVal = self.paramHandler.setParameter(fieldName, newVal)
        if newVal is not False:
            # Set correctly formatted Value
            self.fields[fieldName].blockSignals(True)
            self.fields[fieldName].setText(newVal)
            self.fields[fieldName].blockSignals(False)
            self.dialog.updateCableParam()
