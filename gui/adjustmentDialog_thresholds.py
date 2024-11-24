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
from qgis.PyQt.QtCore import (Qt, QObject, QAbstractTableModel, QModelIndex,
                              pyqtSignal, QSize)
from qgis.PyQt.QtGui import (QColor, QBrush, QStandardItemModel,
                             QIcon, QPixmap)
from qgis.PyQt.QtWidgets import QPushButton, QHBoxLayout, QWidget, QMessageBox, QTableView


class AdjustmentDialogThresholds(QObject):
    
    COLOR_ERROR = QColor(224, 103, 103)
    COLOR_ATTENTION = QColor(237, 148, 76)
    COLOR_NEUTRAL = QColor(255, 255, 255)
    COLOR = {
        1: COLOR_NEUTRAL,
        2: COLOR_ATTENTION,
        3: COLOR_ERROR
    }
    
    sig_clickedRow = pyqtSignal(int)
    
    def __init__(self, parent):
        """
        :type parent: gui.adjustmentDialog.AdjustmentDialog
        """
        super().__init__()
        self.parent = parent
        self.tbl: QTableView = self.parent.tableThresholds
        self.model = None
        self.selectedRow = None
        
        # Icons
        self.iconOk = QIcon()
        self.iconOk.addPixmap(
            QPixmap(":/plugins/SeilaplanPlugin/gui/icons/icon_green.png"),
            QIcon.Mode.Normal, QIcon.State.Off)
        self.iconErr = QIcon()
        self.iconErr.addPixmap(
            QPixmap(":/plugins/SeilaplanPlugin/gui/icons/icon_exclamation.png"),
            QIcon.Mode.Normal, QIcon.State.Off)

        self.tbl.clicked.connect(self.onClick)
    
    def initTableGrid(self, header, rowCount):
        self.model = QStandardItemModel(rowCount, len(header), self.tbl)
        self.tbl.setModel(self.model)
        self.model.setHorizontalHeaderLabels(header)
    
    def updateData(self, tblData, init=False):
        # Update value itself
        for row, rowData in enumerate(tblData):
            for col, cellData in enumerate(rowData):
                if col == 0:
                    if not init:
                        # Remove button
                        self.tbl.setIndexWidget(self.model.index(row, col), None)
                    # Create clickable info button in first column
                    btnWidget = self.createInfoBtn(cellData)
                    self.tbl.setIndexWidget(self.model.index(row, col), btnWidget)
                
                self.model.setData(self.model.index(row, col), cellData)
        
        if init:
            # Adjust column widths to data
            self.tbl.resizeColumnsToContents()
            self.tbl.resizeRowsToContents()
            for idx in range(2, self.model.columnCount()):
                currSize = self.tbl.sizeHintForColumn(idx)
                self.tbl.setColumnWidth(idx, max(currSize, 100))
            self.tbl.setColumnWidth(1, min(self.tbl.sizeHintForColumn(1), 200))
            self.tbl.setFocusPolicy(Qt.NoFocus)
    
    def colorBackground(self, row, col, color):
        # Update background color
        color = self.COLOR[color]
        self.model.setData(self.model.index(row, col),
                           QBrush(color), Qt.BackgroundRole)
    
    def updateTabIcon(self, warn):
        """ Updates icon of QTabWidget with an exclamation mark or check
        mark depending on presents of exceeded thresholds."""
        if warn:
            self.parent.tabWidget.setTabIcon(2, self.iconErr)
        else:
            self.parent.tabWidget.setTabIcon(2, self.iconOk)
    
    def onClick(self, item):
        # Row is already selected
        if self.selectedRow == item.row():
            # Deselect
            self.tbl.clearSelection()
            self.selectedRow = None
        else:
            self.selectedRow = item.row()
        # Emit select signal
        self.sig_clickedRow.emit(item.row())
    
    def select(self, row):
        if row is None:
            self.tbl.clearSelection()
        elif row >= 0:
            self.tbl.selectRow(row)
        self.selectedRow = row
    
    def createInfoBtn(self, cellData):
        button = QPushButton('?')
        button.setMaximumSize(QSize(22, 22))
        # Fill info text into message box
        button.clicked.connect(
            lambda: QMessageBox.information(self.parent, cellData['title'],
                                            cellData['message'],
                                            QMessageBox.StandardButton.Ok))
        cellWidget = QWidget()
        # Add layout to center button in cell
        layout = QHBoxLayout(cellWidget)
        layout.addWidget(button, 0, Qt.AlignCenter)
        layout.setAlignment(Qt.AlignCenter)
        cellWidget.setLayout(layout)
        return cellWidget


class ThresholdTblModel(QAbstractTableModel):
    
    def __init__(self, dataset, header, parent=None):
        QAbstractTableModel.__init__(self, parent)
        self.dataset = dataset
        self.header = header
    
    def rowCount(self, index=QModelIndex()):
        return len(self.dataset)
    
    def columnCount(self, index=QModelIndex()):
        return len(self.header)
    
    def headerData(self, col, orientation=Qt.Horizontal, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.header[col]
        return None
    
    def setData(self, index, value, role=Qt.EditRole):
        """ Adjust the data (set it to <value>) depending on the given
            index and role."""
        if role != Qt.EditRole and role != Qt.ItemDataRole.BackgroundRole:
            return False
        
        if index.isValid() and 0 <= index.row() < len(self.dataset) \
                and 0 <= index.column() < len(self.header):

            self.dataset[index.row()][index.column()] = value
            self.dataChanged.emit(index, index)
            return True
        return False
