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
from qgis.PyQt.QtCore import QSize, Qt, pyqtSignal, QObject
from qgis.PyQt.QtWidgets import (QDoubleSpinBox, QSpinBox, QPushButton,
                                 QLineEdit, QHBoxLayout, QLabel)
from qgis.PyQt.QtGui import QIcon, QPixmap

from ..tool.poles import Poles


class CustomPoleWidget(QObject):
    """
    Display pole properties in a gui object, one row per pole.
    """

    # Signals
    sig_zoomOut = pyqtSignal()
    sig_zoomIn = pyqtSignal(int)
    sig_createPole = pyqtSignal(int)
    sig_updatePole = pyqtSignal(int, str, object)
    sig_deletePole = pyqtSignal(int)
    
    def __init__(self, widget, layout):
        """
        :type widget: qgis.PyQt.QtWidgets.QWidget
        :type layout: qgis.PyQt.QtWidgets.QLayout
        """
        super().__init__()
        self.widget = widget
        self.layout = layout
        self.poleRows = []
        self.editActive = False
        self.pole_dist_step = Poles.POLE_DIST_STEP
        self.pole_height_step = Poles.POLE_HEIGHT_STEP
        self.distRange = []
        PoleRow.poleCount = 0
    
    def setInitialGui(self, poleData, distRange):
        """
        :type poleData: list
        :type distRange: list
        """
        self.distRange = distRange
        initCount = len(poleData)
        self.layout.setAlignment(Qt.AlignTop)

        for idx in range(initCount):
            delBtn = False
            addBtn = False
            
            # Distance input field: ranges are defined by neighbouring poles
            lowerRange = self.distRange[0]
            upperRange = self.distRange[1]
            if idx > 0:
                lowerRange = poleData[idx - 1]['d'] + self.pole_dist_step
            if idx < initCount - 1:
                upperRange = poleData[idx + 1]['d'] - self.pole_dist_step
                
            # Delete button: anchor and first and last pole cannot be deleted
            if 1 < idx < initCount - 2:
                delBtn = True
            # Add button: Pole can only be added between first and last pole
            if 0 < idx < initCount - 2:
                addBtn = True

            # Create layout
            self.poleRows.append(
                PoleRow(self, self.widget, self.layout, idx,
                        poleData[idx]['name'],
                        poleData[idx]['poleType'],
                        poleData[idx]['d'],
                        [lowerRange, upperRange],
                        poleData[idx]['h'],
                        poleData[idx]['angle'], delBtn, addBtn))

    def onRowChange(self, newVal=False, idx=False, property_name=False):
        if self.editActive:
            return
        self.editActive = True
        # Emit signal
        self.sig_updatePole.emit(idx, property_name, newVal)
    
    def onRowAdd(self, idx=False):
        if self.editActive:
            return
        self.editActive = True
        # Emit signal
        self.sig_createPole.emit(idx)

    def onRowDel(self, idx=False):
        if self.editActive:
            return
        self.editActive = True
        # Emit signal
        self.sig_deletePole.emit(idx)
    
    def changeRow(self, idx, property_name, newVal):
        if property_name == 'd':
            self.updateNeighbourDistRange(idx, newVal)
        self.editActive = False

    def addRow(self, idx, name, dist, lowerRange, upperRange, height,
               angle, poleType='pole', delBtn=True, addBtn=True):
        lowerRange += self.pole_dist_step
        upperRange -= self.pole_dist_step
        # Add pole row layout
        newRow = PoleRow(self, self.widget, self.layout, idx, name, poleType,
                         dist, [lowerRange, upperRange], height, angle,
                         delBtn, addBtn)
        self.poleRows.insert(idx, newRow)
        # Update index and distance range of neighbours
        self.updatePoleRowIdx()
        self.updateNeighbourDistRange(idx, dist)
        self.editActive = False
    
    def deleteRow(self, idx, distLower, distUpper):
        # Update distance range of neighbours
        if idx > 0:
            self.poleRows[idx-1].updateUpperDistRange(distUpper - self.pole_dist_step)
        if idx < len(self.poleRows)-1:
            self.poleRows[idx+1].updateLowerDistRange(distLower + self.pole_dist_step)
        # Remove pole row layout
        self.poleRows[idx].remove()
        del self.poleRows[idx]
        # Update index of neighbours
        self.updatePoleRowIdx()
        self.editActive = False
        
    def updatePoleRowIdx(self):
        pole: PoleRow
        for i, pole in enumerate(self.poleRows):
            pole.updateIndex(i)
    
    def updateNeighbourDistRange(self, idx, dist):
        if idx > 0:
            # Left neighbour
            self.poleRows[idx-1].updateUpperDistRange(
                dist - self.pole_dist_step)
        if idx < PoleRow.poleCount - 1:
            # Right neighbour
            self.poleRows[idx+1].updateLowerDistRange(
                dist + self.pole_dist_step)

    def zoomIn(self, idx):
        self.sig_zoomIn.emit(idx)
    
    def zoomOut(self):
        self.sig_zoomOut.emit()
    
    def removeAll(self):
        for idx, pole in enumerate(self.poleRows):
            self.poleRows[idx].remove()
        self.poleRows = []


# noinspection PyUnresolvedReferences
class PoleRow(object):
    """
    Creates all input fields necessary to change the properties of a pole in
    the cable layout. The layout is identified by the position (index) it has
    in the vertical layout.
    """
    ICON_ADD_ROW = ":/plugins/SeilaplanPlugin/gui/icons/icon_addrow.png"
    ICON_DEL_ROW = ":/plugins/SeilaplanPlugin/gui/icons/icon_bin.png"
    poleCount = 0
    
    def __init__(self, parent, widget, layout, idx, name, rowType, dist, distRange,
                 height=False, angle=False, delBtn=False, addBtn=False):
        self.parent = parent
        self.widget = widget
        self.layout = layout
        self.index = idx
        self.rowType = rowType
        PoleRow.poleCount += 1

        self.row = QHBoxLayout()
        self.row.setAlignment(Qt.AlignLeft)
        
        self.labelIndex = None
        self.fieldName = None
        self.fieldDist = None
        self.fieldHeight = None
        self.fieldAngle = None
        self.addBtn = None
        self.delBtn = None

        self.addRowToLayout()
        self.addBtnPlus(addBtn)
        self.addLabelIndex()
        self.addFieldName(name)
        self.addFieldDist(dist, distRange)
        if self.rowType in ['pole', 'fixed']:
            self.addFieldHeight(height)
            self.addFieldAngle(angle)
        self.addBtnDel(delBtn)

    def addRowToLayout(self):
        if self.index == PoleRow.poleCount:
            # Add layout at the end
            self.layout.addLayout(self.row)
        else:
            # Insert new row between existing ones
            self.layout.insertLayout(self.index + 1, self.row)
    
    def addLabelIndex(self):
        self.labelIndex = QLabel(self.widget)
        self.labelIndex.setFixedWidth(20)
        self.labelIndex.setAlignment(Qt.AlignVCenter | Qt.AlignRight)
        self.row.addWidget(self.labelIndex)
        if self.rowType == 'pole':
            self.labelIndex.setText(f"{self.index}:")
    
    def updateIndex(self, idx):
        self.index = idx
        if self.rowType == 'pole':
            self.labelIndex.setText(f"{self.index}:")
            
    def addFieldName(self, value):
        self.fieldName = QLineEditWithFocus(self.widget)
        self.fieldName.setFocusPolicy(Qt.ClickFocus)
        self.fieldName.setFixedWidth(180)
        self.fieldName.setText(value)
        self.row.addWidget(self.fieldName)

        # Connect events
        self.fieldName.inFocus.connect(
            lambda x: self.parent.zoomIn(self.index))
        self.fieldName.outFocus.connect(self.parent.zoomOut)
        self.fieldName.textChanged.connect(
            lambda newVal: self.parent.onRowChange(newVal, self.index, 'name'))
    
    def addFieldDist(self, value, distRange):
        self.fieldDist = QDoubleSpinBoxWithFocus(self.widget)
        self.fieldDist.setFocusPolicy(Qt.ClickFocus)
        self.fieldDist.setDecimals(0)
        self.fieldDist.setSingleStep(self.parent.pole_dist_step)
        self.fieldDist.setSuffix(" m")
        self.fieldDist.setFixedWidth(95)
        self.fieldDist.setRange(float(distRange[0]), float(distRange[1]))
        self.fieldDist.setValue(float(value))
        self.row.addWidget(self.fieldDist)

        # Connect events
        self.fieldDist.inFocus.connect(
            lambda x: self.parent.zoomIn(self.index))
        self.fieldDist.outFocus.connect(self.parent.zoomOut)
        self.fieldDist.valueChanged.connect(
            lambda newVal: self.parent.onRowChange(newVal, self.index, 'd'))
    
    def addFieldHeight(self, value):
        if value is False:
            return
        self.fieldHeight = QDoubleSpinBoxWithFocus(self.widget)
        self.fieldHeight.setFocusPolicy(Qt.ClickFocus)
        self.fieldHeight.setDecimals(1)
        if self.rowType == 'fixed':
            self.fieldHeight.setDecimals(0)
        self.fieldHeight.setSingleStep(self.parent.pole_height_step)
        self.fieldHeight.setSuffix(" m")
        self.fieldHeight.setFixedWidth(85)
        self.fieldHeight.setRange(0.0, 50.0)
        if value is not None:
            self.fieldHeight.setValue(float(value))
        self.row.addWidget(self.fieldHeight)

        # Connect events
        self.fieldHeight.inFocus.connect(
            lambda x: self.parent.zoomIn(self.index))
        self.fieldHeight.outFocus.connect(self.parent.zoomOut)
        self.fieldHeight.valueChanged.connect(
            lambda newVal: self.parent.onRowChange(newVal, self.index, 'h'))
    
    def addFieldAngle(self, value):
        if value is False:
            return
        self.fieldAngle = QSpinBoxWithFocus(self.widget)
        self.fieldAngle.setFocusPolicy(Qt.ClickFocus)
        self.fieldAngle.setSuffix(" °")
        self.fieldAngle.setFixedWidth(60)
        self.fieldAngle.setRange(-180, 180)
        if value is not None:
            self.fieldAngle.setValue(value)
        self.row.addWidget(self.fieldAngle)

        # Connect events
        self.fieldAngle.inFocus.connect(
            lambda x: self.parent.zoomIn(self.index))
        self.fieldAngle.outFocus.connect(self.parent.zoomOut)
        self.fieldAngle.valueChanged.connect(
            lambda newVal: self.parent.onRowChange(newVal, self.index, 'angle'))

    def addBtnPlus(self, createButton):
        if createButton is False:
            self.row.addSpacing(33)
            return
        self.addBtn = QPushButton(self.widget)
        self.addBtn.setMaximumSize(QSize(27, 27))
        icon = QIcon()
        icon.addPixmap(
            QPixmap(PoleRow.ICON_ADD_ROW), QIcon.Normal, QIcon.Off)
        self.addBtn.setIcon(icon)
        self.addBtn.setIconSize(QSize(16, 16))
        self.addBtn.setToolTip('Fügt eine neue Stütze nach dieser hinzu')
        self.addBtn.setAutoDefault(False)
        self.row.addWidget(self.addBtn)
        
        self.addBtn.clicked.connect(
            lambda x: self.parent.onRowAdd(self.index))
    
    def addBtnDel(self, createButton):
        if createButton is False:
            self.row.addSpacing(33)
            return
        self.delBtn = QPushButton(self.widget)
        self.delBtn.setMaximumSize(QSize(27, 27))
        icon = QIcon()
        icon.addPixmap(
            QPixmap(PoleRow.ICON_DEL_ROW), QIcon.Normal, QIcon.Off)
        self.delBtn.setIcon(icon)
        self.delBtn.setIconSize(QSize(16, 16))
        self.delBtn.setToolTip('Löscht die Stütze')
        self.delBtn.setAutoDefault(False)
        self.row.addWidget(self.delBtn)

        self.delBtn.clicked.connect(
            lambda x: self.parent.onRowDel(self.index))
 
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
            
        self.layout.removeItem(self.row)
        PoleRow.poleCount -= 1


class QLineEditWithFocus(QLineEdit):
    inFocus = pyqtSignal(bool)
    outFocus = pyqtSignal(bool)
    
    def focusInEvent(self, event):
        super(QLineEditWithFocus, self).focusInEvent(event)
        self.inFocus.emit(True)
    
    def focusOutEvent(self, event):
        super(QLineEditWithFocus, self).focusOutEvent(event)
        self.outFocus.emit(True)
        

class QDoubleSpinBoxWithFocus(QDoubleSpinBox):
    inFocus = pyqtSignal(bool)
    outFocus = pyqtSignal(bool)
    
    def focusInEvent(self, event):
        super(QDoubleSpinBoxWithFocus, self).focusInEvent(event)
        self.inFocus.emit(True)
        
    def focusOutEvent(self, event):
        super(QDoubleSpinBoxWithFocus, self).focusOutEvent(event)
        self.outFocus.emit(True)


class QSpinBoxWithFocus(QSpinBox):
    inFocus = pyqtSignal(bool)
    outFocus = pyqtSignal(bool)
    
    def focusInEvent(self, event):
        super(QSpinBoxWithFocus, self).focusInEvent(event)
        self.inFocus.emit(True)
    
    def focusOutEvent(self, event):
        super(QSpinBoxWithFocus, self).focusOutEvent(event)
        self.outFocus.emit(True)
