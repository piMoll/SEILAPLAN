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
    
    def __init__(self, parent, paramHandler):
        """
        :type parent: gui.adjustmentDialog.AdjustmentDialog
        :type paramHandler: configHandler.ParamConfHandler
        """
        self.parent = parent
        self.paramHandler = paramHandler
        self.params = {}
        self.fields = {
            'Q': self.parent.fieldQ,
            'qT': self.parent.fieldqT,
            'A': self.parent.fieldA,
            'MBK': self.parent.fieldMBK,
            'qZ': self.parent.fieldqZ,
            'qR': self.parent.fieldqR,
            'Vorsp': self.parent.fieldVorsp,
            'Bodenabst_min': self.parent.fieldBabstMin
        }
        self.connectFields()

    def fillInParams(self):
        self.params = {
            'Q': self.paramHandler.getParameterAsStr('Q'),
            'qT': self.paramHandler.getParameterAsStr('qT'),
            'A': self.paramHandler.getParameterAsStr('A'),
            'MBK': self.paramHandler.getParameterAsStr('MBK'),
            'qZ': self.paramHandler.getParameterAsStr('qZ'),
            'qR': self.paramHandler.getParameterAsStr('qR'),
            'Bodenabst_min': self.paramHandler.getParameterAsStr('Bodenabst_min'),
            'Vorsp': str(self.parent.result['optSTA']),
        }
        for key, field in self.fields.items():
            field.blockSignals(True)
            field.setText(self.params[key])
            field.blockSignals(False)
        
    def connectFields(self):
        self.parent.fieldQ.editingFinished.connect(
            lambda: self.paramHasChanged('Q'))
        self.parent.fieldqT.editingFinished.connect(
            lambda: self.paramHasChanged('qT'))
        self.parent.fieldA.editingFinished.connect(
            lambda: self.paramHasChanged('A'))
        self.parent.fieldMBK.editingFinished.connect(
            lambda: self.paramHasChanged('MBK'))
        self.parent.fieldqZ.editingFinished.connect(
            lambda: self.paramHasChanged('qZ'))
        self.parent.fieldqR.editingFinished.connect(
            lambda: self.paramHasChanged('qR'))
        self.parent.fieldqR.editingFinished.connect(
            lambda: self.paramHasChanged('qR'))
        self.parent.fieldBabstMin.editingFinished.connect(
            lambda: self.paramHasChanged('Bodenabst_min'))

    def paramHasChanged(self, fieldName=''):
        newVal = self.fields[fieldName].text()
        if fieldName == 'Vorsp':
            newVal = self.parent.updateOptSTA(newVal)
        else:
            newVal = self.paramHandler.setParameter(fieldName, newVal)
        if newVal is not False:
            # Set correctly formatted Value
            self.fields[fieldName].blockSignals(True)
            self.fields[fieldName].setText(newVal)
            self.fields[fieldName].blockSignals(False)
            self.parent.updateCableParam()
