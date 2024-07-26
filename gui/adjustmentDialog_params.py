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
            'SK': self.parent.fieldSK,
            'Bodenabst_min': self.parent.fieldBabstMin,
            'Anlagetyp': self.parent.fieldAnlagetyp,
            'SF_T': self.parent.fieldSFT,
        }
        self.fillParametersetList()
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
            # Fill in parameter SK or - if an optimization ran - optSTA
            'SK': str(self.paramHandler.getTensileForce()),
            'SF_T': self.paramHandler.getParameterAsStr('SF_T'),
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
        self.parent.fieldSK.editingFinished.connect(
            lambda: self.paramHasChanged('SK'))
        self.parent.fieldBabstMin.editingFinished.connect(
            lambda: self.paramHasChanged('Bodenabst_min'))
        self.parent.fieldAnlagetyp.editingFinished.connect(
            lambda: self.paramHasChanged('Anlagetyp'))
        self.parent.fieldSFT.editingFinished.connect(
            lambda: self.paramHasChanged('SF_T'))
        
        self.parent.fieldParamSet.currentIndexChanged.connect(self.onParameterSetChange)
    
    def onParameterSetChange(self):
        name = self.parent.fieldParamSet.currentText()
        if name:
            self.paramHandler.setParameterSet(name)
            # Inform parent of parameter changes
            self.parent.onUpdateCableParam()
            # Fill in values
            self.fillInParams()

    def paramHasChanged(self, fieldName=''):
        newVal = self.fields[fieldName].text()
        if fieldName != 'Anlagetyp':
            try:
                newVal = float(newVal)
            except ValueError:
                newVal = False
        
        if newVal is not False:
            if fieldName == 'SK':
                # Unset optSTA from the optimization and instead update SK from
                #  the parameterset
                self.paramHandler.setOptSTA(None)
            newVal = self.paramHandler.setParameter(fieldName, newVal)
                
        if newVal is False:
            newVal = ''
        # Set correctly formatted Value
        self.fields[fieldName].blockSignals(True)
        self.fields[fieldName].setText(str(newVal))
        self.fields[fieldName].blockSignals(False)
        self.parent.onUpdateCableParam()
    
    def fillParametersetList(self):
        self.parent.fieldParamSet.blockSignals(True)
        self.parent.fieldParamSet.clear()
        self.parent.fieldParamSet.addItems(self.paramHandler.getParametersetNames())
        if self.paramHandler.currentSetName:
            self.parent.fieldParamSet.setCurrentText(self.paramHandler.currentSetName)
        else:
            self.parent.fieldParamSet.setCurrentIndex(-1)
        self.parent.fieldParamSet.blockSignals(False)
