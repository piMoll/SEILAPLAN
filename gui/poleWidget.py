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
from qgis.PyQt.QtCore import QSize, Qt, pyqtSignal, QObject, QCoreApplication
from qgis.PyQt.QtWidgets import (QDoubleSpinBox, QSpinBox, QPushButton,
                                 QLineEdit, QHBoxLayout, QLabel, QCheckBox)
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
        self.poleCount = 0
    
    def setInitialGui(self, distRange, poles=None):
        """
        :type poles: tool.poles.Poles
        :type distRange: list
        """
        self.distRange = distRange
        self.layout.setAlignment(Qt.AlignTop)
        if not poles:
            return

        for idx, pole in enumerate(poles.poles):
            delBtn = False
            addBtn = False
            
            # Distance input field: ranges are defined by neighbouring poles
            lowerRange = self.distRange[0]
            upperRange = self.distRange[1]
            if idx > 0:
                lowerRange = poles.poles[idx - 1]['d'] + self.pole_dist_step
            if idx < len(poles.poles) - 1:
                upperRange = poles.poles[idx + 1]['d'] - self.pole_dist_step
                
            # Delete button: anchor and first and last pole cannot be deleted
            if poles.idxA < idx < poles.idxE:
                delBtn = True
            # Add button: Pole can only be added between first and last pole
            if poles.idxA <= idx < poles.idxE:
                addBtn = True

            # Create layout
            self.poleRows.append(
                PoleRow(self, self.widget, self.layout, idx, pole['nr'],
                        pole['name'], pole['poleType'], pole['d'],
                        [lowerRange, upperRange], pole['h'], pole['angle'],
                        delBtn, addBtn))
            if not pole['active']:
                self.poleRows[-1].deactivate()

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
        # Emit signal
        self.sig_deletePole.emit(idx)
    
    def changeRow(self, idx, property_name, newVal):
        if property_name == 'd':
            self.updateNeighbourDistRange(idx, newVal)
        self.editActive = False

    def addRow(self, idx, nr, name, dist, lowerRange, upperRange, height,
               angle, poleType='pole', delBtn=True, addBtn=True, poleLabels=None):
        lowerRange += self.pole_dist_step
        upperRange -= self.pole_dist_step
        # Add pole row layout
        newRow = PoleRow(self, self.widget, self.layout, idx, nr, name, poleType,
                         dist, [lowerRange, upperRange], height, angle,
                         delBtn, addBtn)
        self.poleRows.insert(idx, newRow)
        # Update index and distance range of neighbours
        self.updatePoleRowIdx(poleLabels)
        self.updateNeighbourDistRange(idx, dist)
        self.editActive = False
        
        # TODO: Rewrite like this
        # # new param
        # newIdx = 2
        # newPole = self.poles[idx]
        # dist = newPole['d']
        # lowerRange = dist + self.pole_dist_step
        # upperRange = dist - self.pole_dist_step
        # newRow = PoleRow(self, self.widget, self.layout, idx, newPole['nr'],
        #                  newPole['name'], newPole['poleType'], dist,
        #                  [lowerRange, upperRange], newPole['height'],
        #                  newPole['angle'], delBtn, addBtn)
        # self.poleRows.insert(idx, newRow)
        # # Update index and distance range of neighbours
        # self.updatePoleRowIdx(poleLabels)
        # self.editActive = False
    
    def deleteRow(self, idx, distLower, distUpper, poleLabels=None):
        # If distance range was not defined, take outer ranges
        if not distLower:
            distLower = self.distRange[0]
        if not distUpper:
            distUpper = self.distRange[1]
        # Update distance range of neighbours
        if idx > 0:
            self.poleRows[idx-1].updateUpperDistRange(distUpper - self.pole_dist_step)
        if idx < self.poleCount - 1:
            self.poleRows[idx+1].updateLowerDistRange(distLower + self.pole_dist_step)
        # Remove pole row layout
        self.poleRows[idx].remove()
        del self.poleRows[idx]
        # Update index of neighbours
        self.updatePoleRowIdx(poleLabels)
        self.editActive = False
        
    def updatePoleRowIdx(self, poleLabels):
        pole: PoleRow
        for i, pole in enumerate(self.poleRows):
            pole.updateIndex(i)
            nr = i
            if poleLabels is not None:
                nr = poleLabels[i]
            pole.updateLabelNr(nr)
    
    def updateNeighbourDistRange(self, idx, dist):
        if idx > 0:
            # Left neighbour
            self.poleRows[idx-1].updateUpperDistRange(
                dist - self.pole_dist_step)
        if idx < self.poleCount - 1:
            # Right neighbour
            self.poleRows[idx+1].updateLowerDistRange(
                dist + self.pole_dist_step)
    
    def deactivateRow(self, idx, distLower, distUpper):
        if not distLower:
            distLower = self.distRange[0]
        if not distUpper:
            distUpper = self.distRange[1]
        distUpper -= self.pole_dist_step
        distLower += self.pole_dist_step
        # Update distance range of neighbours
        if idx > 0:
            self.poleRows[idx-1].updateUpperDistRange(distUpper)
        if idx < self.poleCount - 1:
            self.poleRows[idx+1].updateLowerDistRange(distLower)
        self.poleRows[idx].deactivate()
        self.editActive = False
    
    def activateRow(self, idx, dist):
        self.poleRows[idx].activate()
        self.poleRows[idx].fieldDist.setValue(float(dist))

    def zoomIn(self, idx):
        self.sig_zoomIn.emit(idx)
    
    def zoomOut(self):
        self.sig_zoomOut.emit()
    
    def removeAll(self):
        for pole in self.poleRows:
            pole.remove()
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
    
    def __init__(self, parent, widget, layout, idx, nr, name, rowType, dist, distRange,
                 height=False, angle=False, delBtn=False, addBtn=False):
        self.parent = parent
        self.widget = widget
        self.layout = layout
        self.index = idx
        self.rowType = rowType
        self.parent.poleCount += 1

        self.row = QHBoxLayout()
        self.row.setAlignment(Qt.AlignLeft)
        
        self.labelNr = None
        self.statusSwitcher = None
        self.fieldName = None
        self.fieldDist = None
        self.fieldHeight = None
        self.fieldAngle = None
        self.addBtn = None
        self.delBtn = None

        self.addRowToLayout()
        self.addBtnPlus(addBtn)
        if self.rowType == 'anchor':
            self.addSwitcher()
        else:
            self.addLabelNr(nr)
        self.addFieldName(name)
        self.addFieldDist(dist, distRange)
        if self.rowType not in ['anchor', 'pole_anchor']:
            self.addFieldHeight(height)
            self.addFieldAngle(angle)
        self.addBtnDel(delBtn)

    def addRowToLayout(self):
        if self.index == self.parent.poleCount:
            # Add layout at the end
            self.layout.addLayout(self.row)
        else:
            # Insert new row between existing ones
            self.layout.insertLayout(self.index + 1, self.row)
    
    def addSwitcher(self):
        self.statusSwitcher = QCheckBox(self.widget)
        self.statusSwitcher.setText('')
        self.statusSwitcher.setFixedWidth(20)
        self.statusSwitcher.setChecked(True)
        self.row.addWidget(self.statusSwitcher)
        
        # Connect events
        self.statusSwitcher.stateChanged.connect(
            lambda newVal: self.parent.onRowChange(newVal==2, self.index, 'active'))
    
    def addLabelNr(self, nr):
        self.labelNr = QLabel(self.widget)
        self.labelNr.setFixedWidth(20)
        self.labelNr.setAlignment(Qt.AlignVCenter | Qt.AlignRight)
        self.row.addWidget(self.labelNr)
        if nr:
            self.labelNr.setText(f"{nr}:")
    
    def updateIndex(self, idx):
        self.index = idx
    
    def updateLabelNr(self, label):
        if self.rowType != 'anchor':
            self.labelNr.setText(f"{label}:")
            
    def addFieldName(self, value):
        self.fieldName = QLineEditWithFocus(self.widget)
        self.fieldName.setFocusPolicy(Qt.ClickFocus)
        self.fieldName.setFixedWidth(200)
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
        self.fieldHeight.setSingleStep(self.parent.pole_height_step)
        # Pole rows with type fixed are only used in profile window, so before
        #  optimization. That's why they only have 1 meter resolution.
        if self.rowType == 'fixed':
            self.fieldHeight.setDecimals(0)
            self.fieldHeight.setSingleStep(1)
        self.fieldHeight.setSuffix(" m")
        self.fieldHeight.setFixedWidth(95)
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
            self.fieldAngle.setValue(int(value))
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
        self.addBtn.setToolTip(self.tr('Fuegt eine neue Stuetze nach dieser hinzu'))
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
        self.delBtn.setToolTip(self.tr('Loescht die Stuetze'))
        self.delBtn.setAutoDefault(False)
        self.row.addWidget(self.delBtn)

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
        self.fieldName.disconnect()
        self.fieldDist.disconnect()
        if self.fieldHeight: self.fieldHeight.disconnect()
        if self.fieldAngle: self.fieldAngle.disconnect()
        if self.addBtn: self.addBtn.disconnect()
        if self.delBtn: self.delBtn.disconnect()
        
        for i in reversed(range(self.row.count())):
            item = self.row.takeAt(i)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
            else:
                # For spacers
                self.row.removeItem(item)
            
        self.layout.removeItem(self.row)
        self.parent.poleCount -= 1

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
