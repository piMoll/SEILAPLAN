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
from qgis.PyQt.QtWidgets import QLabel, QComboBox, QGridLayout, QSizePolicy, QWidget
from qgis.PyQt.QtGui import QStandardItem, QStandardItemModel

from SEILAPLAN.tools.poles import Poles


birdViewKatConf = {
    '-': {
        'position': [],
        'abspann': [],
    },
    'mobiler_seilkran': {
        'position': ['mitte'],
        'abspann': ['anfang'],
    },
    'vorziehstuetze_1': {
        'position': ['links', 'rechts'],
        'abspann': ['anfang', 'ende'],
    },
    'vorziehstuetze_2': {
        'position': ['links', 'rechts'],
        'abspann': ['anfang', 'flach', 'ende'],
    },
    'vorgeneigte_stuetze': {
        'position': ['links', 'rechts'],
        'abspann': ['anfang', 'ende'],
    },
    'endmast': {
        'position': ['links', 'rechts'],
        'abspann': ['anfang', 'ende'],
    },
    # 'endmast_mit_zugseilleitrolle': {
    #     'position': ['links', 'rechts'],
    #     'abspann': ['anfang', 'ende'],
    # },
    # 'endmast_ohne_zugseilleitrolle': {
    #     'position': ['links', 'rechts'],
    #     'abspann': ['anfang', 'ende'],
    # },
    'normaler_ankerbaum': {
        'position': ['mitte'],
        'abspann': [],
    },
    'mehrbaumanker': {
        'position': ['mitte'],
        'abspann': ['anfang', 'ende'],
    },
    'totmannanker': {
        'position': ['mitte'],
        'abspann': [],
    },
    'verstaerkter_ankerbaum': {
        'position': ['mitte'],
        'abspann': ['anfang', 'ende'],
    },
}

birdViewPosKonf = ['links', 'mitte', 'rechts']
birdViewAbspannKonf = ['anfang', 'flach', 'ende']


class BirdViewWidget(QObject):
    
    sig_updatePole = pyqtSignal(int, str, object)
    
    def __init__(self, widget: QWidget, layout: QGridLayout, poles: Poles):
        """
        :type widget: qgis.PyQt.QtWidgets.QWidget
        :type layout: qgis.PyQt.QtWidgets.QLayout
        :type poles: Poles|Array
        """
        super().__init__()
        self.widget: QWidget = widget
        self.layout: QGridLayout = layout
        self.poles: Poles = poles.poles
        self.direction: str = poles.direction
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
        self.rowIndex = rowIdx      # Row number in grid layout: starts at 1
        self.poleIndex = poleIdx    # Pole number in Poles.poles array: can start at 0 or 1
        self.rowType = rowType
        # Default direction towards start point (abspannIdx = 0) if:
        #  - it's the first pole / anchor of the cable
        #  - we're going uphill, and it's not an anchor (= last pole of cable)
        #  Else: direction towards end point (abspannIdx = 2)
        self.defaultAbspannIdx = (0 if self.rowIndex == 1 or (self.parent.direction == 'uphill' and (self.rowType not in ['anchor', 'pole_anchor'])) else 2)
        
        self.labelNr = None
        self.fieldName = None
        self.fieldCat = None
        self.fieldPos = None
        self.fieldPosModel = None
        self.fieldAbspann = None
        self.fieldAbspannModel = None
        
        self.sizePolicy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.sizePolicy.setHorizontalStretch(0)
        self.sizePolicy.setVerticalStretch(0)
        
        # Possible drop down values
        self.katItems = [item for item in birdViewKatConf.keys()]
        self.posItems = [item for item in birdViewPosKonf]
        self.abspannItems = [item for item in birdViewAbspannKonf]
        
        # Build UI
        if self.rowType != 'anchor':
            self.addLabelNr(nr)
        self.addFieldName(name)
        self.addFieldCat(poleCat)
        self.addFieldPos()
        self.addFieldAbspann()
        
        # Fill in data
        self.onCatSelection(self.poleIndex, poleCat)
        if poleCat and poleCat != '-':
            self.setFieldPosValue(polePos)
            self.setFieldAbspannValue(abspann)
        
    def addLabelNr(self, nr):
        self.labelNr = QLabel(self.widget)
        self.labelNr.setAlignment(Qt.AlignVCenter | Qt.AlignRight)
        self.layout.addWidget(self.labelNr, self.rowIndex, 0)
        if nr:
            self.labelNr.setText(f"{nr}:")
        
    def addFieldName(self, value):
        self.fieldName = QLabel(self.widget)
        self.fieldName.setSizePolicy(self.sizePolicy)
        self.fieldName.setMaximumWidth(110)
        self.fieldName.setText(value)
        shortenTextToFitLabel(self.fieldName)
        self.layout.addWidget(self.fieldName, self.rowIndex, 1)
    
    def addFieldCat(self, value):
        self.fieldCat = QComboBox(self.widget)
        self.fieldCat.setSizePolicy(self.sizePolicy)
        self.fieldCat.setMaximumWidth(240)
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
            lambda newVal: self.onCatSelection(self.poleIndex, model.item(newVal).data()))
    
    def addFieldPos(self):
        self.fieldPos = QComboBox(self.widget)
        self.fieldPos.setSizePolicy(self.sizePolicy)
        self.fieldPosModel = QStandardItemModel()
        
        for idx, name in enumerate(self.posItems):
            item = QStandardItem(self.tr(name))
            item.setData(name)
            self.fieldPosModel.appendRow(item)
            
        self.fieldPos.setModel(self.fieldPosModel)
        self.layout.addWidget(self.fieldPos, self.rowIndex, 3)

        # Connect events
        self.fieldPos.currentIndexChanged.connect(
            lambda newVal: self.parent.onRowChange(self.poleIndex, 'position', self.fieldPosModel.item(newVal).data() if newVal > -1 else None))
    
    def addFieldAbspann(self):
        self.fieldAbspann = QComboBox(self.widget)
        self.fieldAbspann.setSizePolicy(self.sizePolicy)
        self.fieldAbspannModel = QStandardItemModel()
        
        for idx, name in enumerate(self.abspannItems):
            item = QStandardItem(self.tr(name))
            item.setData(name)
            self.fieldAbspannModel.appendRow(item)

        self.fieldAbspann.setModel(self.fieldAbspannModel)
        self.layout.addWidget(self.fieldAbspann, self.rowIndex, 4)
        
        self.fieldAbspann.setCurrentIndex(self.defaultAbspannIdx)
        
        # Connect events
        self.fieldAbspann.currentIndexChanged.connect(
            lambda newVal: self.parent.onRowChange(self.poleIndex, 'abspann', self.fieldAbspannModel.item(newVal).data() if newVal > -1 else None))
    
    def setFieldPosValue(self, dataValue):
        currentIndex = self.fieldPos.currentIndex()
        newIndex = None
        # If the dropdown is deactivated, unselect the current selection
        if not self.fieldPos.isEnabled():
            newIndex = -1
        else:
            # Set the dropdown to the new value IF that item is active
            for listIdx in range(self.fieldPosModel.rowCount()):
                item = self.fieldPosModel.item(listIdx)
                if item.data() == dataValue and item.isEnabled():
                    newIndex = listIdx
            if newIndex is None:
                # Set it to the first row that is enabled
                newIndex = 0 if self.fieldPosModel.item(0).isEnabled() else 1
        
        # Set the current index of the dropdown item
        if newIndex != currentIndex:
            self.fieldPos.setCurrentIndex(newIndex)
        
        # Manually trigger the event
        dataValue = None if newIndex == -1 else self.fieldPosModel.item(newIndex).data()
        self.parent.onRowChange(self.poleIndex, 'position', dataValue)

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
        
    def toggleFieldPos(self, newCategory):
        # Enable drop down elements
        allowedPos = birdViewKatConf[newCategory]['position']
        if len(allowedPos) == 0:
            # Deactivate
            self.fieldPos.setEnabled(False)
            self.setFieldPosValue(None)
            return
        
        if not self.fieldPos.isEnabled():
            self.fieldPos.setEnabled(True)
        
        # Activate or deactivate option for position drop down
        for listIdx in range(self.fieldPosModel.rowCount()):
            item = self.fieldPosModel.item(listIdx)
            if item.data() in allowedPos:
                item.setEnabled(True)
            else:
                item.setEnabled(False)
    
    def toggleFieldAbspann(self, newCategory):
        # If no options are available, deactivate
        allowedAbspann = birdViewKatConf[newCategory]['abspann']
        if len(allowedAbspann) == 0:
            # Deactivate
            self.fieldAbspann.setEnabled(False)
            self.setFieldAbspannValue(None)
            return
           
        if not self.fieldAbspann.isEnabled():
            self.fieldAbspann.setEnabled(True)
            
        # Activate or deactivate option for abspann drop down
        for listIdx in range(self.fieldAbspannModel.rowCount()):
            item = self.fieldAbspannModel.item(listIdx)
            if item.data() in allowedAbspann:
                item.setEnabled(True)
            else:
                item.setEnabled(False)
    
    def onCatDeselect(self, poleIdx):
        self.parent.onRowChange(poleIdx, 'category', None)
        # Deactivate the dropdown elements
        self.fieldPos.setEnabled(False)
        self.parent.onRowChange(poleIdx, 'position', None)
        self.fieldAbspann.setEnabled(False)
        self.parent.onRowChange(poleIdx, 'abspann', None)
        
        
    def onCatSelection(self, poleIdx, newCategory):
        if newCategory is None or newCategory == '-':
            self.onCatDeselect(poleIdx)
            return
        
        # Trigger a category changes
        self.parent.onRowChange(poleIdx, 'category', newCategory)
        
        # Update position field
        self.toggleFieldPos(newCategory)
        
        # Trigger a position change
        currentIdx = self.fieldPos.currentIndex()
        self.setFieldPosValue(None if currentIdx == -1 else self.fieldPosModel.item(currentIdx).data())
        
        # Update position field
        self.toggleFieldAbspann(newCategory)
        
        # Trigger a abspann change
        currentIdx = self.fieldAbspann.currentIndex()
        self.setFieldAbspannValue(None if currentIdx == -1 else self.fieldAbspannModel.item(currentIdx).data())
        
    def remove(self):
        # Disconnect all widgets
        self.fieldCat.disconnect()
        self.fieldPos.disconnect()
        self.fieldAbspann.disconnect()
        
        if self.labelNr:
            self.layout.removeWidget(self.labelNr)
        self.layout.removeWidget(self.fieldName)
        self.layout.removeWidget(self.fieldCat)
        self.layout.removeWidget(self.fieldPos)
        self.layout.removeWidget(self.fieldAbspann)
        
        if self.labelNr:
            self.labelNr.deleteLater()
        self.fieldName.deleteLater()
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
    
    
    
def shortenTextToFitLabel(labelField):
    # Compare length of displayed text with max length of label field
    #  If text is longer than the field, shorten it until it fits
    if labelField.fontMetrics().boundingRect(labelField.text()).width() > labelField.size().width():
        textFromLabel = labelField.text()
        # Add a tooltip if there is none yet
        if labelField.toolTip() == '':
            labelField.setToolTip(textFromLabel)
        # If this isn't the first time the text gets shortened, remove the ellipsis
        if textFromLabel[-1] == '…':
            textFromLabel = textFromLabel[:-1]
        # Shorten the text by 2 character
        labelField.setText(textFromLabel[:-2].strip() + '…')
        shortenTextToFitLabel(labelField)
    else:
        return labelField
