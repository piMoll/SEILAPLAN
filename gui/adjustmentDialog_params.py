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
            # 'Vorsp': self.dialog.fieldVorsp,
        }
        self.connectFields()

    def fillInParams(self):
        self.params = {
            'Q': self.paramHandler.getParameter('Q'),
            'qT': self.paramHandler.getParameter('qT'),
            'A': self.paramHandler.getParameter('A'),
            'E': self.paramHandler.getParameter('E'),
            'qz1': self.paramHandler.getParameter('qz1'),
            'qz2': self.paramHandler.getParameter('qz2'),
            # 'Vorsp': cableparams['Vorsp'][0],
        }
        for key, field in self.fields.items():
            field.blockSignals(True)
            field.setText(self.params[key])
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
        newVal = self.paramHandler.setParameter(fieldName, newVal)
        if newVal:
            self.fields[fieldName].blockSignals(True)
            self.fields[fieldName].setText(newVal)
            self.fields[fieldName].blockSignals(False)
            self.dialog.updateCableParam()
