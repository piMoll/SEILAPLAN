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
from qgis.PyQt.QtCore import QSize, Qt
from qgis.PyQt.QtWidgets import (QDoubleSpinBox, QSpinBox, QPushButton,
                                 QLineEdit, QHBoxLayout)
from qgis.PyQt.QtGui import QIcon, QPixmap


class AdjustmentDialogPoles(object):
    """
    Organizes all functionality in the first tab "poles" of the tab widgets.
    """
    
    def __init__(self, dialog, poleData):
        self.dialog = dialog
        self.poleRows = []

        # Create layout rows for pole input fields
        self.addPolesToGui(poleData)
    
    def addPolesToGui(self, poleData):
        initCount = len(poleData)
        self.dialog.poleVGrid.setAlignment(Qt.AlignTop)

        for idx in range(initCount):
            delBtn = False
            addBtn = False
            
            # Distance input field: ranges are defined by neighbouring poles
            if idx > 0:
                lowerRange = poleData[idx - 1]['dist'] \
                             + self.dialog.POLE_DIST_STEP
            else:
                lowerRange = self.dialog.HORIZONTAL_BUFFER * -1
            
            if idx < initCount - 1:
                upperRange = poleData[idx + 1]['dist'] \
                             - self.dialog.POLE_DIST_STEP
            else:
                upperRange = poleData[idx]['dist'] \
                             + self.dialog.HORIZONTAL_BUFFER
                
            # Pole type
            poleType = 'pole'
            if idx == 0 or idx == initCount - 1:
                poleType = 'anchor'
                
            # Delete button: anchor and first and last pole cannot be deleted
            if 1 < idx < initCount - 2:
                delBtn = True
            # Add Bbtton: Pole can only be added between first and last pole
            if 0 < idx < initCount - 2:
                addBtn = True

            # Create layout
            self.poleRows.append(
                PoleRow(self, self.dialog, idx, poleType,
                        poleData[idx]['dist'],
                        [lowerRange, upperRange],
                        poleData[idx]['height'],
                        poleData[idx]['angle'], delBtn, addBtn))

    def onRowChange(self, newVal=False, idx=False, fieldType=False):
        # Update data in dialog
        self.dialog.updatePole(idx, fieldType, newVal)
        
        # Adjust distance ranges of neighbours
        if fieldType == 'dist':
            if idx > 0:
                self.poleRows[idx - 1].updateUpperDistRange(
                    newVal - self.dialog.POLE_DIST_STEP)
            if idx < PoleRow.poleCount - 1:
                self.poleRows[idx + 1].updateLowerDistRange(
                    newVal + self.dialog.POLE_DIST_STEP)
    
    def onRowAdd(self, idx=False):
        # Update data in dialog
        newPoleIdx, dist, \
        lowerRange, upperRange, height, angle = self.dialog.addPole(idx)
        
        # Change index of right side neighbours
        for pole in self.poleRows[newPoleIdx:-1]:
            pole.index += 1
        
        # Add pole row layout
        newRow = PoleRow(self, self.dialog, newPoleIdx, 'pole', dist,
                          [lowerRange, upperRange], height, angle, True, True)
        self.poleRows.insert(newPoleIdx, newRow)
    
    def onRowDel(self, idx=False):
        # Update data in dialog
        self.dialog.deletePole(idx)

        # Remove pole row layout
        self.poleRows[idx].remove()
        del self.poleRows[idx]

        # Change index of right side neighbours
        for pole in self.poleRows[idx+1:-1]:
            pole.index -= 1





class PoleRow(object):
    """
    Creates all input fields necessary to change the properties of a pole in
    the cable layout. The layout is identified by the position (index) it has
    in the vertical layout.
    """
    ICON_ADD_ROW = ":/plugins/SeilaplanPlugin/gui/icons/icon_addrow.png"
    ICON_DEL_ROW = ":/plugins/SeilaplanPlugin/gui/icons/icon_bin.png"
    poleCount = 0
    
    def __init__(self, tab, dialog, idx, rowType, dist, distRange,
                 height=False, angle=False, delBtn=False, addBtn=False):
        self.tab = tab
        self.dialog = dialog
        self.index = idx
        self.rowRype = rowType
        PoleRow.poleCount += 1
        
        self.row = QHBoxLayout()
        self.row.setAlignment(Qt.AlignLeft)
        
        self.fieldName = None
        self.fieldDist = None
        self.fieldHeight = None
        self.fieldAngle = None
        self.addBtn = None
        self.delBtn = None
        
        if self.rowRype == 'anchor':
            name = 'Verankerung'
        else:
            name = f'{self.index}. Stütze'

        self.addRowToLayout()
        self.addBtnPlus(addBtn)
        self.addFieldName(name)
        self.addFieldDist(dist, distRange)
        self.addFieldHeight(height)
        self.addFieldAngle(angle)
        self.addBtnDel(delBtn)

    def addRowToLayout(self):
        if self.index == PoleRow.poleCount:
            # Add layout at the end
            self.dialog.poleVGrid.addLayout(self.row)
        else:
            # Insert new row between existing ones
            self.dialog.poleVGrid.insertLayout(self.index + 1, self.row)
    
    def addFieldName(self, value):
        self.fieldName = QLineEdit(self.dialog.tabPoles)
        self.fieldName.setFixedWidth(180)
        self.fieldName.setText(value)
        self.row.addWidget(self.fieldName)
        
        self.fieldName.textChanged.connect(
            lambda newVal: self.tab.onRowChange(newVal, self.index, 'name'))
    
    def addFieldDist(self, value, distRange):
        self.fieldDist = QDoubleSpinBox(self.dialog.tabPoles)
        self.fieldDist.setDecimals(1)
        self.fieldDist.setSingleStep(self.dialog.POLE_DIST_STEP)
        self.fieldDist.setSuffix(" m")
        self.fieldDist.setFixedWidth(95)
        self.fieldDist.setRange(float(distRange[0]), float(distRange[1]))
        self.fieldDist.setValue(float(value))
        self.row.addWidget(self.fieldDist)
        
        # field.focusInEvent.connect(self.actionSelectPole)
        self.fieldDist.valueChanged.connect(
            lambda newVal: self.tab.onRowChange(newVal, self.index, 'dist'))
    
    def addFieldHeight(self, value):
        if value is False:
            return
        self.fieldHeight = QDoubleSpinBox(self.dialog.tabPoles)
        self.fieldHeight.setDecimals(1)
        self.fieldHeight.setSingleStep(self.dialog.POLE_HEIGHT_STEP)
        self.fieldHeight.setSuffix(" m")
        self.fieldHeight.setFixedWidth(85)
        self.fieldHeight.setRange(0.0, 50.0)
        self.fieldHeight.setValue(float(value))
        self.row.addWidget(self.fieldHeight)
        
        self.fieldHeight.valueChanged.connect(
            lambda newVal: self.tab.onRowChange(newVal, self.index, 'height'))
    
    def addFieldAngle(self, value):
        if value is False:
            return
        self.fieldAngle = QSpinBox(self.dialog.tabPoles)
        self.fieldAngle.setSuffix(" °")
        self.fieldAngle.setFixedWidth(60)
        self.fieldAngle.setRange(-180, 180)
        self.fieldAngle.setValue(value)
        self.row.addWidget(self.fieldAngle)

        self.fieldAngle.valueChanged.connect(
            lambda newVal: self.tab.onRowChange(newVal, self.index, 'angle'))

    def addBtnPlus(self, createButton):
        if createButton is False:
            self.row.addSpacing(33)
            return
        self.addBtn = QPushButton(self.dialog.tabPoles)
        self.addBtn.setMaximumSize(QSize(27, 27))
        icon = QIcon()
        icon.addPixmap(
            QPixmap(PoleRow.ICON_ADD_ROW), QIcon.Normal, QIcon.Off)
        self.addBtn.setIcon(icon)
        self.addBtn.setIconSize(QSize(16, 16))
        self.row.addWidget(self.addBtn)
        
        self.addBtn.clicked.connect(
            lambda x: self.tab.onRowAdd(self.index))
    
    def addBtnDel(self, createButton):
        if createButton is False:
            self.row.addSpacing(33)
            return
        self.delBtn = QPushButton(self.dialog.tabPoles)
        self.delBtn.setMaximumSize(QSize(27, 27))
        icon = QIcon()
        icon.addPixmap(
            QPixmap(PoleRow.ICON_DEL_ROW), QIcon.Normal, QIcon.Off)
        self.delBtn.setIcon(icon)
        self.delBtn.setIconSize(QSize(16, 16))
        self.row.addWidget(self.delBtn)

        self.delBtn.clicked.connect(
            lambda x: self.tab.onRowDel(self.index))
 
    def updateLowerDistRange(self, minimum):
        self.fieldDist.setMinimum(minimum)
    
    def updateUpperDistRange(self, maximum):
        self.fieldDist.setMaximum(maximum)
    
    def remove(self):
        for i in reversed(range(self.row.count())):
            item = self.row.takeAt(i)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
            else:
                # For spacers
                self.row.removeItem(item)
            
        self.dialog.poleVGrid.removeItem(self.row)
        PoleRow.poleCount -= 1