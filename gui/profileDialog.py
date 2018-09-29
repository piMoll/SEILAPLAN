# -*- coding: utf-8 -*-
"""
/***************************************************************************
 SeilaplanPlugin
                                 A QGIS plugin
 Seilkran-Layoutplaner
                              -------------------
        begin                : 2013
        copyright            : (C) 2015 by ETH Zürich
        email                : pi1402@gmail.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/

 Code is based on these two examples:
 https://github.com/eliben/code-for-blog/blob/master/2009/qt_mpl_bars.py
 http://www.technicaljar.com/?p=688
"""

import numpy as np
from qgis.PyQt.QtCore import QSize, Qt
from qgis.PyQt.QtWidgets import QDialog, QWidget, QLabel, QDialogButtonBox, \
    QHBoxLayout, QSizePolicy, QPushButton, QVBoxLayout, QGridLayout, QFrame, \
    QSpacerItem, QLineEdit, QApplication
from qgis.PyQt.QtGui import QColor

from qgis.core import QgsGeometry, QgsPoint
from qgis.gui import QgsRubberBand

from .profilePlot import QtMplCanvas
from .guiHelperFunctions import QgsMovingCross
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT \
    as NavigationToolbar

css = "QLineEdit {background-color: white;}"
cssErr = "QLineEdit {background-color: red;}"


class ProfileWindow(QDialog):
    def __init__(self, toolWindow, interface, profile):
        QDialog.__init__(self, interface.mainWindow())
        self.setWindowTitle("Höhenprofil")
        self.main_widget = QWidget(self)
        self.iface = interface
        self.canvas = self.iface.mapCanvas()
        self.profile = profile
        self.toolWin = toolWindow

        self.mapMarker = None
        self.pointsToDraw = []
        self.mapLines = []

        self.sc = QtMplCanvas(self.iface, self.profile, self)
        self.sc.setMinimumSize(QSize(600, 400))
        self.sc.setMaximumSize(QSize(600, 400))
        bar = MyNavigationToolbar(self.sc, self)

        self.gridM = QGridLayout()
        self.grid = QGridLayout()
        self.gridM.addLayout(self.grid, 0, 0, 1, 1)

        # Get fixed intermediate support data
        self.fixStueOld = self.toolWin.fixStue
        self.fixStueProp = []
        self.menu = False

        # GUI fields
        self.stueTitle = QLabel("<b>Stützenstandorte anpassen</b>")
        self.hbox = QHBoxLayout()
        self.addGUIfields()
        self.buttonBox = QDialogButtonBox(self.main_widget)
        self.buttonBox.setStandardButtons(QDialogButtonBox.Cancel|
                                          QDialogButtonBox.Ok)
        # Build up GUI
        self.container = QVBoxLayout(self.main_widget)
        self.container.addWidget(self.sc)
        self.container.addWidget(bar)
        self.container.addWidget(self.line1)
        self.container.addWidget(self.stueTitle)
        self.container.addLayout(self.hbox)
        self.container.addLayout(self.gridM)
        self.container.addWidget(self.buttonBox)

        # Connect signals
        self.fixStueAdd.clicked.connect(self.sc.acitvateFadenkreuz)
        self.noStueAdd.clicked.connect(self.sc.acitvateFadenkreuz2)
        self.buttonBox.rejected.connect(self.Reject)
        self.buttonBox.accepted.connect(self.Apply)
        self.setLayout(self.container)

        # If fixed intermediate supports where already defined, redraw them
        if len(self.fixStueOld) > 0:
            for key, values in self.fixStueOld.items():
                order = key-1
                [pointX, pointY, pointH] = values
                drawnPoint = self.sc.CreatePoint(int(pointX), int(pointY))
                self.CreateFixStue(pointX, pointY, drawnPoint, pointH, order)

    def addGUIfields(self):
        self.line1 = QFrame()
        self.line1.setFrameShape(QFrame.HLine)
        self.line1.setFrameShadow(QFrame.Sunken)
        self.line2 = QFrame()
        self.line2.setFrameShape(QFrame.HLine)
        self.line2.setFrameShadow(QFrame.Sunken)

        # Create lables and buttons
        self.fixStueAdd = QPushButton("Fixe Stütze definieren")
        self.noStueAdd = QPushButton("Abschnitte ohne Stützen definieren")
        spacerItem1 = QSpacerItem(40, 20, QSizePolicy.Expanding,
                                        QSizePolicy.Minimum)
        self.hbox.addWidget(self.fixStueAdd)
        self.hbox.addItem(spacerItem1)
        self.hbox.addWidget(self.noStueAdd)
        self.hbox.setAlignment(self.noStueAdd, Qt.AlignRight)

    def CreateFixStue(self, pointX, pointY, drawnPoint, pointH = u'', order=None):
        if not self.menu:       # If there is no fixed intermediate support yet
            self.initMenu()
        if not order:           # Position of field in list
            order = len(self.fixStueProp)

        guiPos, guiH, guiRemove = self.addRow2Grid(order)
        guiPos.setText(pointX)
        if pointH == u'-1':
            pointH = u''
        guiH.setText(pointH)

        # Draw marker on canvas
        [x, y] = self.toolWin.transform2MapCoords(float(pointX))
        self.toolWin.drawStueMarker(QgsPoint(x, y))
        # Save data of intermediate support
        self.addStueToDict(order, pointX, pointY, pointH, guiPos, guiH,
                           drawnPoint)

    def initMenu(self):
        spacerItem1 = QSpacerItem(40, 20, QSizePolicy.Expanding,
                                        QSizePolicy.Minimum)
        spacerItem2 = QSpacerItem(20, 40, QSizePolicy.Minimum,
                                        QSizePolicy.Expanding)
        headerLabel1 = QLabel()
        headerLabel1.setText("<html><head/><body><p>Position [m]"
                             "<br/><span style=\" font-size:8pt;\""
                             ">Horizontaldist. ab Anfangsstütze</span>"
                             "</p></body></html>")
        headerLabel1.setAlignment(Qt.AlignCenter)
        headerLabel2 = QLabel()
        headerLabel2.setText("<html><head/><body><p>Stützenhöhe [m]<br/>"
                             "<span style=\" font-size:8pt;\""
                             ">Angabe optional</span></p></body></html>")
        headerLabel2.setAlignment(Qt.AlignCenter)

        self.grid.addWidget(headerLabel1, 0, 1, 1, 1)
        self.grid.addWidget(headerLabel2, 0, 2, 1, 1)
        self.gridM.addItem(spacerItem1, 0, 1, 1, 1)
        self.gridM.addItem(spacerItem2, 1, 0, 1, 1)
        self.container.insertWidget(self.container.count() - 1, self.line2)
        self.menu = True

    def addRow2Grid(self, row):
        # label
        stueLabel = QLabel("Fixe Stütze {}".format(row+1))
        stueLabel.setAlignment(Qt.AlignRight)
        stueLabel.setMinimumSize(QSize(120, 0))
        stueLabel.setAlignment(Qt.AlignRight|
                               Qt.AlignTrailing|
                               Qt.AlignVCenter)

        # Field for horizontal position in profile
        guiPos = QLineEdit()
        guiH = QLineEdit()
        sizePolicy = QSizePolicy(QSizePolicy.Preferred,
                                       QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        guiPos.setSizePolicy(sizePolicy)
        guiPos.setMaximumSize(QSize(70, 16777215))
        guiPos.setLayoutDirection(Qt.RightToLeft)
        guiPos.setAlignment(Qt.AlignRight)
        guiPos.setObjectName(u'{:0>2}_guiPos'.format(row))

        # Field for support height
        guiH.setSizePolicy(sizePolicy)
        guiH.setMaximumSize(QSize(70, 16777215))
        guiH.setLayoutDirection(Qt.RightToLeft)
        guiH.setAlignment(Qt.AlignRight)
        guiH.setObjectName(u'{:0>2}_guiH'.format(row))

        # Button to remove row and support
        guiRemove = QPushButton("x")
        guiRemove.setMaximumSize(QSize(20, 20))
        guiRemove.setObjectName(u'{:0>2}_guiRemove'.format(row))

        # Connect signals
        guiPos.editingFinished.connect(self.fixStueChanged)
        guiH.editingFinished.connect(self.fixStueChanged)
        guiRemove.clicked.connect(self.removeStue)

        # Place fields in GUI
        hbox1 = QHBoxLayout()
        hbox1.addWidget(guiPos)
        hbox1.setAlignment(Qt.AlignCenter)
        hbox2 = QHBoxLayout()
        hbox2.addWidget(guiH)
        hbox2.setAlignment(Qt.AlignCenter)

        self.grid.addWidget(stueLabel, row+1, 0, 1, 1)
        self.grid.addLayout(hbox1, row+1, 1, 1, 1)
        self.grid.addLayout(hbox2, row+1, 2, 1, 1)
        self.grid.addWidget(guiRemove, row+1, 3, 1, 1)
        self.setLayout(self.container)
        return guiPos, guiH, guiRemove

    def addStueToDict(self, order, x, y, h, guiPos, guiH, drawnPnt):
        self.fixStueProp.append({'x': x,
                                 'y': y,
                                 'h': h,
                                 'guiPos': guiPos,
                                 'guiH': guiH,
                                 'drawnPnt': drawnPnt})

    def fixStueChanged(self):
        senderName = self.sender().objectName()
        order = int(senderName[:2])
        fieldType = senderName[3:]
        newval = self.sender().text()
        # If x coord has changed
        if fieldType == 'guiPos':
            self.sc.DeletePoint(self.fixStueProp[order]['drawnPnt'])
            # Test if new value is (1) empty, (2) zero or (3) has letters
            if newval == '' or int(newval) == 0 or newval.isalpha():
                newval = None
                self.sender().setStyleSheet(cssErr)
            else:
                # Calculate y coordinate
                indx = np.searchsorted(self.sc.x_data, [int(newval)])[0]
                yPos = self.sc.y_data[indx-1]
                drawnPoint = self.sc.CreatePoint(newval, yPos)
                self.fixStueProp[order]['drawnPnt'] = drawnPoint
                self.fixStueProp[order]['y'] = str(int(yPos))
                # Remove old point and draw new point on canvas
                self.toolWin.removeStueMarker(2+order)
                [x, y] = self.toolWin.transform2MapCoords(float(newval))
                self.toolWin.drawStueMarker(QgsPoint(x, y))
            self.fixStueProp[order]['x'] = str(int(float(newval)))
        # If height has changed
        if fieldType == 'guiH':
            self.fixStueProp[order]['h'] = newval

    def removeStue(self):
        senderName = self.sender().objectName()
        order = int(senderName[:2])
        print(order)
        # Remove point from plot and from canvas
        self.sc.DeletePoint(self.fixStueProp[order]['drawnPnt'])
        self.toolWin.removeStueMarker(2+order)
        # Delete intermediate support data
        del self.fixStueProp[order]
        rowCount = len(self.fixStueProp)
        # Adjust GUI
        # Remove row of deleted support and all subsequent rows
        for row in reversed(range(order+1, rowCount+2)):
            self.removeStueField(row)
        # Subsequent rows move up
        for row in range(order, rowCount):
            guiPos, guiH, guiRemove = self.addRow2Grid(row)
            guiPos.setText(self.fixStueProp[row]['x'])
            if self.fixStueProp[row]['h']:
                guiH.setText(self.fixStueProp[row]['h'])
            self.fixStueProp[row]['guiPos'] = guiPos
            self.fixStueProp[row]['guiH'] = guiH
            self.fixStueProp[row]['guiRemove'] = guiRemove
        self.setLayout(self.container)
        # If only remaining row was deleted also delete header
        if rowCount == 0:
            self.grid.takeAt(1).widget().deleteLater()
            self.grid.takeAt(0).widget().deleteLater()
            self.menu = False
        self.setLayout(self.container)

    def removeStueField(self, row):
        pos = row*4 + 1     # Header is in field 0 and 1
        for i in reversed(range(pos-3, pos+1)):
            # Remove widgets and layout items
            item = self.grid.takeAt(i)
            if item.widget() is not None:
                item.widget().deleteLater()
            elif item.layout() is not None:
                item.layout().takeAt(0).widget().deleteLater()
        self.setLayout(self.container)

    ##########################################################################

    def activateMapMarker(self, horiDist):
        [x, y] = self.toolWin.transform2MapCoords(horiDist)
        self.mapMarker = QgsMovingCross(self.canvas)
        initPoint = QgsPoint(x, y)
        self.mapMarker.setCenter(initPoint)

    def deactivateMapMarker(self):
        self.canvas.scene().removeItem(self.mapMarker)
        self.mapMarker = None

    def updateMapMarker(self, horiDist):
        if not self.mapMarker:
            self.activateMapMarker(horiDist)
        [xCoord, yCoord] = self.toolWin.transform2MapCoords(horiDist)
        newpnt = QgsPoint(xCoord, yCoord)
        self.mapMarker.setCenter(newpnt)
        self.canvas.refresh()

    def activateMapMarkerLine(self, horiDist):
        self.deactivateMapMarker()
        [x, y] = self.toolWin.transform2MapCoords(horiDist)
        self.mapMarker = QgsMovingCross(self.canvas)
        self.mapMarker.setColor(QColor(249, 236, 0))

    def activateMapLine(self, horiDist):
        mapLine = QgsRubberBand(self.canvas, False)
        mapLine.setWidth(3)
        mapLine.setColor(QColor(255, 250, 90))
        self.mapLines.append(mapLine)
        self.pointsToDraw = []
        # Create first point
        [xCoord, yCoord] = self.toolWin.transform2MapCoords(horiDist)
        initPoint = QgsPoint(xCoord, yCoord)
        self.pointsToDraw.append(initPoint)

    def lineMoved(self, horiDist):
        [xCoord, yCoord] = self.toolWin.transform2MapCoords(horiDist)
        newPnt = QgsPoint(xCoord, yCoord)
        points = self.pointsToDraw + [newPnt]
        self.mapLines[-1].setToGeometry(QgsGeometry.fromPolyline(points), None)

    def finishLine(self, horiDist):
        [xCoord, yCoord] = self.toolWin.transform2MapCoords(horiDist)
        endPoint = QgsPoint(xCoord, yCoord)
        self.pointsToDraw.append(endPoint)
        self.mapLines[-1].setToGeometry(QgsGeometry.fromPolyline(
            self.pointsToDraw), None)
        self.pointsToDraw = []

    def removeLines(self):
        for line in self.mapLines:
            line.reset(False)

    def clearUnfinishedLines(self):
        if len(self.pointsToDraw) == 1:
            self.sc.vLine.remove()
            self.mapLines[-1].reset(False)
            self.mapLines.pop(-1)
            self.pointsToDraw = []

    ###########################################################################

    def getValues(self):
        return [self.dist, self.height]

    def Apply(self):
        self.toolWin.fixStue = {}
        for i, fixStue in enumerate(self.fixStueProp):
            x = fixStue['x']
            y = fixStue['y']
            h = fixStue['h']
            if x == '' or x.isalpha():
                continue
            if h == '':
                h = u'-1'
            self.toolWin.fixStue[i+1] = [x, y, h]
        self.deactivateMapMarker()
        self.clearUnfinishedLines()
        self.close()

    def Reject(self):
        self.deactivateMapMarker()
        self.clearUnfinishedLines()
        self.fixStueProp = []
        self.menu = False
        self.close()

    def mousePressEvent(self, event):
        focused_widget = QApplication.focusWidget()
        if isinstance(focused_widget, QLineEdit):
            focused_widget.clearFocus()
        QDialog.mousePressEvent(self, event)



class MyNavigationToolbar(NavigationToolbar):
    # Only display the buttons we need
    toolitems = [t for t in NavigationToolbar.toolitems if
                 t[0] in ('Home', 'Pan', 'Zoom')]

    def __init__(self, *args, **kwargs):
        super(MyNavigationToolbar, self).__init__(*args, **kwargs)
        self.layout().takeAt(3)  # 3 = Amount of tools we need


