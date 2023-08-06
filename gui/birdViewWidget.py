"""
/***************************************************************************
 SeilaplanPlugin
                                 A QGIS plugin
 Seilkran-Layoutplaner
                              -------------------
        begin                : 2013
        copyright            : (C) 2023 by Patricia Moll
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
from qgis.PyQt.QtCore import Qt, pyqtSignal, QObject, QCoreApplication
from qgis.PyQt.QtWidgets import (QLabel, QComboBox, QGridLayout)
from qgis.PyQt.QtGui import QStandardItem, QStandardItemModel

from ..tools.poles import Poles


birdViewKatConf = {
    '-': {
        'abspann': [],
    },
    'mobiler_seilkran': {
        'abspann': [],
    },
    'vorziehstuetze_1': {
        'abspann': ['anfang', 'ende'],
    },
    'vorziehstuetze_2': {
        'abspann': ['anfang', 'flach', 'ende'],
    },
    'vorgeneigte_stuetze': {
        'abspann': ['anfang', 'ende'],
    },
    'mehrbaumanker': {
        'abspann': ['anfang', 'ende'],
    },
    'endmast_mit_zugseilrolle': {
        'abspann': ['anfang', 'ende'],
    },
    'endmast_ohne_zugseilrolle': {
        'abspann': ['anfang', 'ende'],
    },
    'totmannanker': {
        'abspann': [],
    },
    'verstaerkter_ankerbaum': {
        'abspann': ['anfang', 'ende'],
    },
    'normaler_ankerbaum': {
        'abspann': [],
    },
}

birdViewPosKonf = ['links', 'mitte', 'rechts']
birdViewAbspannKonf = ['anfang', 'flach', 'ende']


class BirdViewWidget(QObject):
    
    sig_updatePole = pyqtSignal(int, str, object)
    
    def __init__(self, widget, layout, poles):
        """
        :type widget: qgis.PyQt.QtWidgets.QWidget
        :type layout: qgis.PyQt.QtWidgets.QLayout
        :type poles: Poles|Array
        """
        super().__init__()
        self.widget = widget
        self.layout: QGridLayout = layout
        self.poles = poles.poles
        self.direction = poles.direction
        self.layout.setAlignment(Qt.AlignTop)
        self.poleRows = []
        
    def updateGui(self):
        if self.poleRows:
            self.removeRows()
        rowIdx = 0
            
        for poleIdx, pole in enumerate(self.poles):
            if not pole['active']:
                continue
            rowIdx += 1
            # Create layout
            self.poleRows.append(
                BirdViewRow(self, self.widget, self.layout, rowIdx, poleIdx, pole['nr'],
                            pole['name'], pole['poleType'], pole['category'],
                            pole['position'], pole['abspann']))
    
    def removeRows(self):
        for poleRow in reversed(self.poleRows):
            poleRow.remove()
        self.poleRows = []
        
    def onRowChange(self, idx, property_name, newVal):
        self.sig_updatePole.emit(idx, property_name, newVal)



class BirdViewRow(object):
    
    def __init__(self, parent, widget, layout, rowIdx, poleIdx, nr, name, rowType, poleCat,
                 polePos, abspann):
        self.parent = parent
        self.widget = widget
        self.layout = layout
        self.rowIndex = rowIdx      # Row number in grid layout
        self.poleIndex = poleIdx    # Pole number in Poles.poles array
        self.rowType = rowType
        self.defaultAbspannIdx = 2 if self.parent.direction == 'downhill' else 0
        
        self.labelNr = None
        self.fieldName = None
        self.fieldCat = None
        self.fieldPos = None
        self.fieldPosModel = None
        self.fieldAbspann = None
        self.fieldAbspannModel = None
        
        # Translate
        self.katItems = [item for item in birdViewKatConf.keys()]
        self.posItems = [item for item in birdViewPosKonf]
        self.abspannItems = [item for item in birdViewAbspannKonf]
        
        # Build UI
        if self.rowType != 'anchor':
            self.addLabelNr(nr)
        self.addFieldName(name)
        self.addFieldCat(poleCat)
        self.addFieldPos(polePos)
        self.addFieldAbspann(abspann)
        if poleCat == '-' or poleCat is None:
            self.fieldPos.setEnabled(False)
            self.fieldAbspann.setEnabled(False)
        
    def addLabelNr(self, nr):
        self.labelNr = QLabel(self.widget)
        self.labelNr.setAlignment(Qt.AlignVCenter | Qt.AlignRight)
        self.layout.addWidget(self.labelNr, self.rowIndex, 0)
        if nr:
            self.labelNr.setText(f"{nr}:")
        
    def addFieldName(self, value):
        self.fieldName = QLabel(self.widget)
        # TODO: How to make this grow based on available size? And we need MouseOver
        self.fieldName.setFixedWidth(120)
        self.fieldName.setText(value)
        self.layout.addWidget(self.fieldName, self.rowIndex, 1)
    
    def addFieldCat(self, value):
        self.fieldCat = QComboBox(self.widget)
        model = QStandardItemModel()
        currentIdx = 0
        for idx, name in enumerate(self.katItems):
            item = QStandardItem(self.tr(name))
            item.setData(name)
            model.appendRow(item)
            if name == value:
                currentIdx = idx
        self.fieldCat.setModel(model)
        self.layout.addWidget(self.fieldCat, self.rowIndex, 2)
        # Set the current value
        self.fieldCat.setCurrentIndex(currentIdx)
        # Connect events
        self.fieldCat.currentIndexChanged.connect(
            lambda newVal: self.onKatSelection(self.poleIndex, model.item(newVal).data()))
    
    def addFieldPos(self, value):
        self.fieldPos = QComboBox(self.widget)
        self.fieldPosModel = QStandardItemModel()
        currentIdx = 1
        for idx, name in enumerate(self.posItems):
            item = QStandardItem(self.tr(name))
            item.setData(name)
            self.fieldPosModel.appendRow(item)
            if name == value:
                currentIdx = idx
        self.fieldPos.setModel(self.fieldPosModel)
        self.layout.addWidget(self.fieldPos, self.rowIndex, 3)
        # Set the current value
        self.fieldPos.setCurrentIndex(currentIdx)
        # Connect events
        self.fieldPos.currentIndexChanged.connect(
            lambda newVal: self.parent.onRowChange(self.poleIndex, 'position', self.fieldPosModel.item(newVal).data()))
    
    def addFieldAbspann(self, dataValue):
        self.fieldAbspann = QComboBox(self.widget)
        self.fieldAbspannModel = QStandardItemModel()
        
        for idx, name in enumerate(self.abspannItems):
            item = QStandardItem(self.tr(name))
            item.setData(name)
            self.fieldAbspannModel.appendRow(item)

        self.fieldAbspann.setModel(self.fieldAbspannModel)
        self.layout.addWidget(self.fieldAbspann, self.rowIndex, 4)
        # Set the current value
        self.setFieldAbspannValue(dataValue)
        # Connect events
        self.fieldAbspann.currentIndexChanged.connect(
            lambda newVal: self.parent.onRowChange(self.poleIndex, 'abspann', self.fieldAbspannModel.item(newVal).data() if newVal > -1 else None))
    
    def setFieldAbspannValue(self, dataValue):
        currentIndex = self.fieldAbspann.currentIndex()
        newIndex = None
        # If the dropdown is deactivated, unselect the current selection
        if not self.fieldAbspann.isEnabled():
            newIndex = -1
        else:
            # Set the dropdown to the new value IF that item is active
            for listIdx in range(self.fieldAbspannModel.rowCount()):
                item = self.fieldAbspannModel.item(listIdx)
                if item.data() == dataValue and item.isEnabled():
                    newIndex = listIdx
            if newIndex is None:
                newIndex = self.defaultAbspannIdx
        
        # Set the current index of the dropdown item
        if newIndex != currentIndex:
            self.fieldAbspann.setCurrentIndex(newIndex)
        
        # Manually trigger the event
        dataValue = None if newIndex == -1 else self.fieldAbspannModel.item(newIndex).data()
        self.parent.onRowChange(self.poleIndex, 'abspann', dataValue)
        
    def onKatSelection(self, poleIdx, newCategory):
        if newCategory == '-':
            self.parent.onRowChange(poleIdx, 'category', None)
            # Deactivate the dropdown elements
            self.fieldPos.setEnabled(False)
            self.parent.onRowChange(poleIdx, 'position', None)
            self.fieldAbspann.setEnabled(False)
            self.parent.onRowChange(poleIdx, 'abspann', None)
            return
        
        # Save pole changes
        self.parent.onRowChange(poleIdx, 'category', newCategory)
        
        # Enable drop down elements
        if not self.fieldPos.isEnabled():
            self.fieldPos.setEnabled(True)
            # Trigger the change event to update the pole element
            self.parent.onRowChange(poleIdx, 'position', self.fieldPosModel.item(self.fieldPos.currentIndex()).data())
        
        if not self.fieldAbspann.isEnabled():
            self.fieldAbspann.setEnabled(True)
        
        # If no options are available, deactivate
        allowedAbspann = birdViewKatConf[newCategory]['abspann']
        if len(allowedAbspann) == 0:
            # Deactivate
            self.fieldAbspann.setEnabled(False)
            self.setFieldAbspannValue(None)
            return
        
        # Activate or deactivate option for abspann drop down
        for listIdx in range(self.fieldAbspannModel.rowCount()):
            item = self.fieldAbspannModel.item(listIdx)
            if item.data() in allowedAbspann:
                item.setEnabled(True)
            else:
                item.setEnabled(False)
        
        currentIdx = self.fieldAbspann.currentIndex()
        self.setFieldAbspannValue(None if currentIdx == -1 else self.fieldAbspannModel.item(currentIdx).data())
        
    def remove(self):
        # Disconnect all widgets
        self.fieldCat.disconnect()
        self.fieldPos.disconnect()
        self.fieldAbspann.disconnect()
        
        self.layout.removeWidget(self.labelNr)
        self.layout.removeWidget(self.fieldName)
        self.layout.removeWidget(self.fieldCat)
        self.layout.removeWidget(self.fieldPos)
        self.layout.removeWidget(self.fieldAbspann)
        
        self.fieldCat.deleteLater()
        self.fieldPos.deleteLater()
        self.fieldAbspann.deleteLater()
        
    
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
