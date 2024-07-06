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
from SEILAPLAN.tools.configHandler_params import ParameterConfHandler


class AdjustmentDialogParams(object):
    """
    Organizes all functionality in the second tab "cable parameters" of the
    tab widgets.
    """
    
    def __init__(self, parent, paramHandler):
        """
        :type parent: gui.adjustmentDialog.AdjustmentDialog
        :type paramHandler: tools.configHandler_params.ParamConfHandler
        """
        self.parent = parent
        self.paramHandler: ParameterConfHandler = paramHandler
        self.params = {}
        self.fields = {
            'Q': self.parent.fieldQ,
            'qT': self.parent.fieldqT,
            'D': self.parent.fieldD,
            'MBK': self.parent.fieldMBK,
            'qZ': self.parent.fieldqZ,
            'qR': self.parent.fieldqR,
            'Vorsp': self.parent.fieldVorsp,
            'Bodenabst_min': self.parent.fieldBabstMin,
            'Anlagetyp': self.parent.fieldAnlagetyp,
        }
        self.connectFields()

    def fillInParams(self):
        self.params = {
            'Q': self.paramHandler.getParameterAsStr('Q'),
            'qT': self.paramHandler.getParameterAsStr('qT'),
            'D': self.paramHandler.getParameterAsStr('D'),
            'MBK': self.paramHandler.getParameterAsStr('MBK'),
            'qZ': self.paramHandler.getParameterAsStr('qZ'),
            'qR': self.paramHandler.getParameterAsStr('qR'),
            'Bodenabst_min': self.paramHandler.getParameterAsStr('Bodenabst_min'),
            'Anlagetyp': self.paramHandler.getParameterAsStr('Anlagetyp'),
            'Vorsp': str(self.paramHandler.optSTA),
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
        self.parent.fieldD.editingFinished.connect(
            lambda: self.paramHasChanged('D'))
        self.parent.fieldMBK.editingFinished.connect(
            lambda: self.paramHasChanged('MBK'))
        self.parent.fieldqZ.editingFinished.connect(
            lambda: self.paramHasChanged('qZ'))
        self.parent.fieldqR.editingFinished.connect(
            lambda: self.paramHasChanged('qR'))
        self.parent.fieldVorsp.editingFinished.connect(
            lambda: self.paramHasChanged('Vorsp'))
        self.parent.fieldBabstMin.editingFinished.connect(
            lambda: self.paramHasChanged('Bodenabst_min'))
        self.parent.fieldAnlagetyp.editingFinished.connect(
            lambda: self.paramHasChanged('Anlagetyp'))

    def paramHasChanged(self, fieldName=''):
        newVal = self.fields[fieldName].text()
        if fieldName != 'Anlagetyp':
            try:
                newVal = float(newVal)
            except ValueError:
                newVal = False
        
        if newVal is not False:
            if fieldName == 'Vorsp':
                newVal = self.parent.updateOptSTA(newVal)
            elif fieldName in ['D', 'MBK']:
                newVal = self.paramHandler.setParameter(fieldName, newVal)
                self.paramHandler.prepareForCalculation()
            elif fieldName in ['qZ', 'qR']:
                newVal = self.paramHandler.setParameter(fieldName, newVal)
                self.paramHandler.setPullRope(self.parent.profile.direction)
            else:
                newVal = self.paramHandler.setParameter(fieldName, newVal)
                
        if newVal is False:
            newVal = ''
        # Set correctly formatted Value
        self.fields[fieldName].blockSignals(True)
        self.fields[fieldName].setText(str(newVal))
        self.fields[fieldName].blockSignals(False)
        self.parent.updateCableParam()
