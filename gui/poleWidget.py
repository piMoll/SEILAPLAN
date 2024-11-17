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
from typing import List
from qgis.PyQt.QtWidgets import QWidget
from qgis.PyQt.QtCore import QSize, Qt, pyqtSignal, QObject, QCoreApplication
from qgis.PyQt.QtWidgets import (QDoubleSpinBox, QSpinBox, QPushButton, QHBoxLayout,
                                 QLineEdit, QLabel, QCheckBox, QGridLayout)
from qgis.PyQt.QtGui import QIcon, QPixmap
from numpy import nan

from SEILAPLAN.tools.poles import Poles


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
    
    def __init__(self, widget, layout, poles, mode='standard'):
        """
        :type widget: qgis.PyQt.QtWidgets.QWidget
        :type layout: qgis.PyQt.QtWidgets.QGridLayout
        :type poles: Poles|Array
        """
        super().__init__()
        self.widget: QWidget = widget
        self.layout: QGridLayout = layout
        self.mode = mode
        if self.mode == 'standard':
            self.poles: Poles = poles
            self.poleArr = poles.poles
        else:
            self.poles = None
            self.poleArr = poles
        self.poleRows: List[PoleRow] = []
        self.editActive = False
        self.pole_dist_step = Poles.POLE_DIST_STEP
        self.pole_height_step = Poles.POLE_HEIGHT_STEP
        self.distRange = []
        self.poleCount = 0
    
    def setInitialGui(self, distRange):
        """
        :type distRange: list
        """
        self.distRange = distRange
        self.layout.setAlignment(Qt.AlignTop)
        self.addHeader()
        self.createPoleRows()
    
    def createPoleRows(self):
        self.poleRows = []
        for idx, pole in enumerate(self.poleArr):
            delBtn = False
            addBtn = False
            
            # Distance input field: ranges are defined by neighbouring poles
            [lowerRange, upperRange] = self.getDistanceRange(idx)
            # Delete button: anchor and first and last pole cannot be deleted
            if self.mode != 'standard' or self.poles.idxA < idx < self.poles.idxE:
                delBtn = True
            # Add button: Pole can only be added between first and last pole
            if self.mode == 'standard' and self.poles.idxA <= idx < self.poles.idxE:
                addBtn = True

            # Create layout
            self.poleRows.append(
                PoleRow(self, self.widget, self.layout, idx, pole['nr'],
                        pole['name'], pole['poleType'], pole['d'],
                        [lowerRange, upperRange], pole['h'], pole['angle'],
                        pole['bundstelle'], delBtn, addBtn))
            if not pole['active']:
                self.poleRows[-1].deactivate()
        
        self.widget.setLayout(self.layout)
    
    def addHeader(self):
        self.layout.addWidget(QLabel(''), 0, 0, 1, 1, Qt.AlignLeft)
        self.layout.addWidget(QLabel(self.tr('Nr.')), 0, 1, 1, 1, Qt.AlignLeft)
        self.layout.addWidget(QLabel(self.tr('Stuetzenbezeichnung')), 0, 2, 1, 1, Qt.AlignLeft)
        self.layout.addWidget(QLabel(self.tr('Horiz.distanz')), 0, 3, 1, 1, Qt.AlignLeft)
        self.layout.addWidget(QLabel(self.tr('Stuetzenhoehe')), 0, 4, 1, 1, Qt.AlignLeft)
        if self.mode == 'standard':
            self.layout.addWidget(QLabel(self.tr('Neigung')), 0, 5, 1, 1, Qt.AlignLeft)
            self.layout.addWidget(QLabel(self.tr('O Bundst.')), 0, 6, 1, 2, Qt.AlignLeft)
            # When window grows, the second column (Stuetzenbezeichnung) should grow as well
            self.layout.setColumnStretch(2, 1)
        else:
            # When in the profile dialog, the last column (Stuetzenhoehe) should grow
            self.layout.setColumnStretch(4, 1)
    
    def onRowChange(self, newVal=None, idx=None, property_name=None):
        if self.editActive:
            return
        if property_name == 'name' and len(newVal) > Poles.POLE_NAME_MAX_LENGTH:
            text = newVal[:Poles.POLE_NAME_MAX_LENGTH]
            self.poleRows[idx].fieldName.setText(text)
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
        if idx:
            # This will remove the selected row, so user sees a UI feedback
            # immediately.However, deleting a pole will trigger a recalculation,
            # which will rebuild the PoleWidget completely.
            self.poleRows[idx].remove()
            del self.poleRows[idx]
        # Emit signal
        self.sig_deletePole.emit(idx)
    
    def changeRow(self, idx, property_name, newVal, prevAnchorA=None, prevAnchorE=None):
        self.updateAnchorState(prevAnchorA, prevAnchorE)
        
        self.updateBundstelle()
        if property_name == 'd':
            self.updateNeighbourDistRange(idx, newVal, newVal)
        elif property_name == 'h':
            # When changing first or last pole to/from 0m height, the anchor gets
            #  deactivated/activated and the row numbers need to reflect this
            self.updatePoleRowNumbers()
        self.editActive = False
    
    def refresh(self):
        self.removeAll()
        self.createPoleRows()
        self.editActive = False
  
    def updatePoleRowNumbers(self):
        labels = None
        if self.poles:
            [_, _, _, _, _, labels,
             _, _, _, _] = self.poles.getAsArray(True, True)

        pole: PoleRow
        for i, pole in enumerate(self.poleRows):
            nr = i + 1
            if labels:
                nr = labels[i]
            pole.updateLabelNr(nr)
    
    def updateBundstelle(self):
        pole: PoleRow
        for i, pole in enumerate(self.poleRows):
            pole.updateBundstelle(self.poleArr[i]['bundstelle'])
    
    def updateNeighbourDistRange(self, idx, rightLimit, leftLimit):
        if idx > 0:
            # Left neighbour: update its upper range
            self.poleRows[idx-1].updateUpperDistRange(
                leftLimit - self.pole_dist_step)
        if idx < self.poleCount - 1:
            # Right neighbour: update its lower range
            self.poleRows[idx+1].updateLowerDistRange(
                rightLimit + self.pole_dist_step)

    def updateAnchorState(self, prevAnchorA, prevAnchorE):
        """Check new anchor state and activate / deactivate anchor row
        accordingly."""
        if not self.poles or prevAnchorA is None or prevAnchorE is None:
            return
        if prevAnchorA is not self.poles.hasAnchorA:
            idxA = 0
            if self.poles.hasAnchorA:
                # Anchor A was activated
                self.activateRow(idxA, float(self.poleArr[idxA]['d']))
            else:
                # Anchor A was deactivated
                self.deactivateRow(idxA, self.distRange[0], self.poleArr[idxA + 1]['d'])

        if prevAnchorE is not self.poles.hasAnchorE:
            idxE = len(self.poles.poles) - 1
            if self.poles.hasAnchorE:
                # Anchor E was activated
                self.activateRow(idxE, float(self.poleArr[idxE]['d']))
            else:
                # Anchor E was deactivated
                self.deactivateRow(idxE, float(self.poleArr[idxE - 1]['d']), self.distRange[1])
    
    def deactivateRow(self, idx, leftLimit, rightLimit):
        # Update distance range of neighbours
        self.updateNeighbourDistRange(idx, leftLimit, rightLimit)
        self.poleRows[idx].deactivate()
        self.updatePoleRowNumbers()
    
    def activateRow(self, idx, dist):
        self.poleRows[idx].activate()
        self.poleRows[idx].fieldDist.setValue(dist)
        self.updateNeighbourDistRange(idx, dist, dist)
        self.updatePoleRowNumbers()
    
    def getDistanceRange(self, idx):
        lowerRange = self.distRange[0]
        upperRange = self.distRange[1]
        if idx > 0:
            lowerRange = self.poleArr[idx - 1]['d']
        if idx < len(self.poleArr) - 1:
            upperRange = self.poleArr[idx + 1]['d']
        return [lowerRange, upperRange]

    def zoomIn(self, idx):
        self.sig_zoomIn.emit(idx)
    
    def zoomOut(self):
        self.sig_zoomOut.emit()
    
    def removeAll(self):
        for pole in self.poleRows:
            pole.remove()
        self.poleRows = []
    
    def tr(self, message, **kwargs):
        return QCoreApplication.translate(type(self).__name__, message)


class PoleRow(object):
    """
    Creates all input fields necessary to change the properties of a pole in
    the cable layout. The layout is identified by the position (index) it has
    in the vertical layout.
    """
    ICON_ADD_ROW = ":/plugins/SeilaplanPlugin/gui/icons/icon_addrow.png"
    ICON_DEL_ROW = ":/plugins/SeilaplanPlugin/gui/icons/icon_bin.png"
    
    POLE_LABEL_WIDTH = 220
    SPINNER_WIDTH = 85
    
    def __init__(self, parent, widget, layout, idx, nr, name, rowType, dist, distRange,
                 height=False, angle=False, bundstelle=False, delBtn=False, addBtn=False):
        self.parent = parent
        self.widget = widget
        self.layout: QGridLayout = layout
        self.index = idx
        self.rowType = rowType
        self.parent.poleCount += 1
        
        self.labelNr = None
        self.statusSwitcher = None
        self.fieldName = None
        self.fieldDist = None
        self.fieldHeight = None
        self.fieldAngle = None
        self.fieldBundstelle = None
        self.addBtn = None
        self.delBtn = None

        self.addBtnPlus(addBtn)
        if self.rowType == 'anchor':
            self.addSwitcher()
        else:
            self.addLabelNr(nr)
        self.addFieldName(name)
        self.addFieldDist(dist, distRange)
        if self.rowType not in ['anchor']:
            self.addFieldHeight(height)
            self.addFieldAngle(angle)
        self.addFieldBundstelle(bundstelle)
        self.addBtnDel(delBtn)

    def addSwitcher(self):
        self.statusSwitcher = QCheckBox(self.widget)
        self.statusSwitcher.setText('')
        self.statusSwitcher.setChecked(True)
        self.layout.addWidget(self.statusSwitcher, self.index + 1, 1, 1, 1, Qt.AlignLeft)
        
        # Connect events
        self.statusSwitcher.stateChanged.connect(
            lambda newVal: self.parent.onRowChange(newVal == 2, self.index, 'active'))
    
    def addLabelNr(self, nr):
        self.labelNr = QLabel(self.widget)
        self.updateLabelNr(nr)
        self.layout.addWidget(self.labelNr, self.index + 1, 1, 1, 1, Qt.AlignLeft)
    
    def updateLabelNr(self, label):
        if self.labelNr:
            if label:
                self.labelNr.setText(f"{label}:")
            else:
                self.labelNr.setText("")
            
    def addFieldName(self, value):
        self.fieldName = QLineEditWithFocus(self.widget)
        self.fieldName.setFocusPolicy(Qt.ClickFocus)
        self.fieldName.setMinimumWidth(self.POLE_LABEL_WIDTH)
        self.fieldName.setText(value)
        # Add layout so the widget grows when the grid column grows
        hLayout = QHBoxLayout()
        hLayout.addWidget(self.fieldName)
        self.layout.addLayout(hLayout, self.index + 1, 2, 1, 1, Qt.AlignLeft)
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
        self.fieldDist.setMinimumWidth(self.SPINNER_WIDTH)
        self.fieldDist.setRange(float(distRange[0]), float(distRange[1]))
        self.fieldDist.setValue(float(value))
        # Add layout so the widget grows when the grid column grows
        hLayout = QHBoxLayout()
        hLayout.addWidget(self.fieldDist)
        self.layout.addLayout(hLayout, self.index + 1, 3, 1, 1, Qt.AlignLeft)

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
        self.fieldHeight.setSingleStep(self.parent.pole_height_step)
        # Pole rows with type fixed are only used in profile window, so before
        #  optimization. That's why they only have 1 meter resolution.
        if self.rowType == 'fixed':
            self.fieldHeight.setDecimals(0)
            self.fieldHeight.setSingleStep(1)
        self.fieldHeight.setSuffix(" m")
        self.fieldHeight.setMinimumWidth(self.SPINNER_WIDTH)
        self.fieldHeight.setRange(0.0, 50.0)
        if value is not None:
            self.fieldHeight.setValue(float(value))
        # Add layout so the widget grows when the grid column grows
        layout = QHBoxLayout()
        layout.addWidget(self.fieldHeight)
        self.layout.addLayout(layout, self.index + 1, 4, 1, 1, Qt.AlignLeft)

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
        self.fieldAngle.setMinimumWidth(self.SPINNER_WIDTH - 20)
        self.fieldAngle.setRange(-180, 180)
        if value is not None:
            self.fieldAngle.setValue(int(value))
        # Add layout so the widget grows when the grid column grows
        layout = QHBoxLayout()
        layout.addWidget(self.fieldAngle)
        self.layout.addLayout(layout, self.index + 1, 5, 1, 1, Qt.AlignLeft)

        # Connect events
        self.fieldAngle.inFocus.connect(
            lambda x: self.parent.zoomIn(self.index))
        self.fieldAngle.outFocus.connect(self.parent.zoomOut)
        self.fieldAngle.valueChanged.connect(
            lambda newVal: self.parent.onRowChange(newVal, self.index, 'angle'))
        
    def addFieldBundstelle(self, value):
        if value is False:
            return
        self.fieldBundstelle = QLabel(self.widget)
        self.updateBundstelle(value)
        self.layout.addWidget(self.fieldBundstelle, self.index + 1, 6, 1, 1, Qt.AlignLeft)
        
    def updateBundstelle(self, value):
        if self.fieldBundstelle:
            if value is False or value is nan:
                value = '-'
            else:
                value = f"{value} cm"
            self.fieldBundstelle.setText(value)
    
    def addBtnPlus(self, createButton):
        if createButton is False:
            return
        self.addBtn = QPushButton(self.widget)
        self.addBtn.setMaximumSize(QSize(27, 27))
        icon = QIcon()
        icon.addPixmap(
            QPixmap(PoleRow.ICON_ADD_ROW), QIcon.Normal, QIcon.Off)
        self.addBtn.setIcon(icon)
        self.addBtn.setIconSize(QSize(16, 16))
        self.addBtn.setToolTip(self.tr('Fuegt eine neue Stuetze nach dieser hinzu'))
        self.addBtn.setAutoDefault(False)
        self.layout.addWidget(self.addBtn, self.index + 1, 0, 1, 1, Qt.AlignLeft)
        
        self.addBtn.clicked.connect(
            lambda x: self.parent.onRowAdd(self.index))
    
    def addBtnDel(self, createButton):
        if createButton is False:
            return
        self.delBtn = QPushButton(self.widget)
        self.delBtn.setMaximumSize(QSize(27, 27))
        icon = QIcon()
        icon.addPixmap(
            QPixmap(PoleRow.ICON_DEL_ROW), QIcon.Normal, QIcon.Off)
        self.delBtn.setIcon(icon)
        self.delBtn.setIconSize(QSize(16, 16))
        self.delBtn.setToolTip(self.tr('Loescht die Stuetze'))
        self.delBtn.setAutoDefault(False)
        self.layout.addWidget(self.delBtn, self.index + 1, 7, 1, 1, Qt.AlignLeft)

        self.delBtn.clicked.connect(
            lambda x: self.parent.onRowDel(self.index))
 
    def updateLowerDistRange(self, minimum):
        self.fieldDist.setMinimum(minimum)
    
    def updateUpperDistRange(self, maximum):
        self.fieldDist.setMaximum(maximum)

    def activate(self):
        self.statusSwitcher.blockSignals(True)
        self.statusSwitcher.setChecked(True)
        self.statusSwitcher.blockSignals(False)
        self.fieldName.setEnabled(True)
        self.fieldDist.setEnabled(True)
        
    def deactivate(self):
        self.statusSwitcher.blockSignals(True)
        self.statusSwitcher.setChecked(False)
        self.statusSwitcher.blockSignals(False)
        self.fieldName.setEnabled(False)
        self.fieldDist.setEnabled(False)
    
    def remove(self):
        # Disconnect all widgets
        for widget in [self.statusSwitcher,
                       self.addBtn,
                       self.labelNr,
                       self.fieldName,
                       self.fieldDist,
                       self.fieldHeight,
                       self.fieldAngle,
                       self.fieldBundstelle,
                       self.delBtn,
                       ]:
            if widget:
                if not isinstance(widget, QLabel):
                    widget.disconnect()
            
                self.layout.removeWidget(widget)
                widget.deleteLater()
        
        # Remove layouts
        for column in reversed(range(self.layout.columnCount())):
            boxLayout = self.layout.itemAtPosition(self.index + 1, column)
            if boxLayout and isinstance(boxLayout, QHBoxLayout):
                self.layout.removeItem(boxLayout)

        self.parent.poleCount -= 1

    def tr(self, message, **kwargs):
        return QCoreApplication.translate('CustomPoleWidget', message)


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
