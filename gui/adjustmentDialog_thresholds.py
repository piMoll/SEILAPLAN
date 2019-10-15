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

from qgis.PyQt.QtCore import Qt, QAbstractTableModel, QModelIndex
from qgis.PyQt.QtGui import QColor, QBrush, QStandardItem, QStandardItemModel


class AdjustmentDialogThresholds(object):
    
    def __init__(self, dialog, datasetSize):
        """
        :type dialog: gui.adjustmentDialog.AdjustmentDialog
        """
        self.dialog = dialog
        self.tbl = self.dialog.tableThresholds
        self.model = QStandardItemModel(datasetSize[0], datasetSize[1], self.tbl)
        self.tbl.setModel(self.model)
        self.tbl.resizeColumnsToContents()
        self.tbl.resizeRowsToContents()
    
    def populate(self, header, dataset):
        self.model.setHorizontalHeaderLabels(header)
        self.tbl.hideColumn(len(header)-1)
        
        for i, row in enumerate(dataset):
            for j, cell in enumerate(row):
                item = QStandardItem(cell)
                self.model.setItem(i, j, item)

        self.tbl.resizeColumnsToContents()
        self.tbl.setColumnWidth(0, 300)
        self.tbl.resizeRowsToContents()
    
    def updateData(self, dataset):
        self.tbl.clearSelection()
        for i, row in enumerate(dataset):
            for j, cell in enumerate(row):
                if j < 3:
                    continue
                if j == 3:
                    self.model.setData(self.model.index(i, j), cell)
                elif j == 4:
                    if cell is None:
                        continue
                    brush = QBrush(QColor(110, 194, 83))  # green
                    if len(cell) != 0:
                        brush = QBrush(QColor(224, 103, 103))  # red
                    self.model.setData(self.model.index(i, j-1), brush,
                                       Qt.BackgroundRole)


class ThresholdTblModel(QAbstractTableModel):
    
    def __init__(self, dataset, header, parent=None):
        QAbstractTableModel.__init__(self, parent)
        self.dataset = dataset
        self.header = header
    
    def rowCount(self, index=QModelIndex()):
        return len(self.dataset)
    
    def columnCount(self, index=QModelIndex()):
        return len(self.header)
    
    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        if role == Qt.DisplayRole:
            return self.dataset[index.row()][index.column()]
        if role == Qt.BackgroundColorRole:
            return QBrush(Qt.red)
        if role == Qt.TextAlignmentRole:
            return Qt.AlignVCenter
        else:
            return None
    
    def headerData(self, col, orientation=Qt.Horizontal, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.header[col]
        return None
    
    def setData(self, index, value, role=Qt.EditRole):
        """ Adjust the data (set it to <value>) depending on the given
            index and role."""
        if role != Qt.EditRole and role != Qt.BackgroundColorRole:
            return False
        
        if index.isValid() and 0 <= index.row() < len(self.dataset) \
                and 0 <= index.column() < len(self.header):

            self.dataset[index.row()][index.column()] = value
            self.dataChanged.emit(index, index)
            return True
        return False
