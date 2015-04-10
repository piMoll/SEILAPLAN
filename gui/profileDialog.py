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
from PyQt4 import QtCore
from PyQt4 import QtGui
from PyQt4.QtCore import QObject, SIGNAL
from qgis.core import QGis, QgsGeometry, QgsPoint
from qgis.gui import QgsRubberBand

from profilePlot import QtMplCanvas
from guiHelperFunctions import QgsMovingCross
from matplotlib.backends.backend_qt4agg import NavigationToolbar2QTAgg \
    as NavigationToolbar

css = "QLineEdit {background-color: white;}"
cssErr = "QLineEdit {background-color: red;}"


class ProfileWindow(QtGui.QDialog):
    def __init__(self, toolWindow, interface, profile):
        QtGui.QDialog.__init__(self, interface.mainWindow())
        self.setWindowTitle(u"Höhenprofil")
        self.main_widget = QtGui.QWidget(self)
        self.iface = interface
        self.canvas = self.iface.mapCanvas()
        self.profile = profile
        self.toolWin = toolWindow

        self.mapMarker = None
        self.pointsToDraw = []
        self.mapLines = []

        self.sc = QtMplCanvas(self.iface, self.profile, self)
        self.sc.setMinimumSize(QtCore.QSize(600, 400))
        self.sc.setMaximumSize(QtCore.QSize(600, 400))
        bar = MyNavigationToolbar(self.sc, self)

        self.gridM = QtGui.QGridLayout()
        self.grid = QtGui.QGridLayout()
        self.gridM.addLayout(self.grid, 0, 0, 1, 1)

        # Get fixed intermediate support data
        self.fixStueOld = self.toolWin.fixStue
        self.fixStueProp = []
        self.menu = False

        # GUI fields
        self.stueTitle = QtGui.QLabel(u"<b>Stützenstandorte anpassen</b>")
        self.hbox = QtGui.QHBoxLayout()
        self.addGUIfields()
        self.buttonBox = QtGui.QDialogButtonBox(self.main_widget)
        self.buttonBox.setStandardButtons(QtGui.QDialogButtonBox.Cancel|
                                          QtGui.QDialogButtonBox.Ok)
        # Build up GUI
        self.container = QtGui.QVBoxLayout(self.main_widget)
        self.container.addWidget(self.sc)
        self.container.addWidget(bar)
        self.container.addWidget(self.line1)
        self.container.addWidget(self.stueTitle)
        self.container.addLayout(self.hbox)
        self.container.addLayout(self.gridM)
        self.container.addWidget(self.buttonBox)

        # Connect signals
        QObject.connect(self.fixStueAdd, SIGNAL("clicked()"),
                        self.sc.acitvateFadenkreuz)
        QObject.connect(self.noStueAdd, SIGNAL("clicked()"),
                        self.sc.acitvateFadenkreuz2)
        QObject.connect(self.buttonBox, SIGNAL("rejected()"), self.Reject)
        QObject.connect(self.buttonBox, SIGNAL("accepted()"), self.Apply)
        self.setLayout(self.container)

        # If fixed intermediate supports where already defined, redraw them
        if len(self.fixStueOld) > 0:
            for key, values in self.fixStueOld.iteritems():
                order = key-1
                [pointX, pointY, pointH] = values
                drawnPoint = self.sc.CreatePoint(int(pointX), int(pointY))
                self.CreateFixStue(pointX, pointY, drawnPoint, pointH, order)

    def addGUIfields(self):
        self.line1 = QtGui.QFrame()
        self.line1.setFrameShape(QtGui.QFrame.HLine)
        self.line1.setFrameShadow(QtGui.QFrame.Sunken)
        self.line2 = QtGui.QFrame()
        self.line2.setFrameShape(QtGui.QFrame.HLine)
        self.line2.setFrameShadow(QtGui.QFrame.Sunken)

        # Create lables and buttons
        self.fixStueAdd = QtGui.QPushButton(u"Fixe Stütze definieren")
        self.noStueAdd = QtGui.QPushButton(u"Abschnitte ohne Stützen definieren")
        spacerItem1 = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding,
                                        QtGui.QSizePolicy.Minimum)
        self.hbox.addWidget(self.fixStueAdd)
        self.hbox.addItem(spacerItem1)
        self.hbox.addWidget(self.noStueAdd)
        self.hbox.setAlignment(self.noStueAdd, QtCore.Qt.AlignRight)

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
        spacerItem1 = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding,
                                        QtGui.QSizePolicy.Minimum)
        spacerItem2 = QtGui.QSpacerItem(20, 40, QtGui.QSizePolicy.Minimum,
                                        QtGui.QSizePolicy.Expanding)
        headerLabel1 = QtGui.QLabel()
        headerLabel1.setText(u"<html><head/><body><p>Position [m]"
                             u"<br/><span style=\" font-size:8pt;\""
                             u">Horizontaldist. ab Anfangsstütze</span>"
                             u"</p></body></html>")
        headerLabel1.setAlignment(QtCore.Qt.AlignCenter)
        headerLabel2 = QtGui.QLabel()
        headerLabel2.setText(u"<html><head/><body><p>Stützenhöhe [m]<br/>"
                             u"<span style=\" font-size:8pt;\""
                             u">Angabe optional</span></p></body></html>")
        headerLabel2.setAlignment(QtCore.Qt.AlignCenter)

        self.grid.addWidget(headerLabel1, 0, 1, 1, 1)
        self.grid.addWidget(headerLabel2, 0, 2, 1, 1)
        self.gridM.addItem(spacerItem1, 0, 1, 1, 1)
        self.gridM.addItem(spacerItem2, 1, 0, 1, 1)
        self.container.insertWidget(self.container.count() - 1, self.line2)
        self.menu = True

    def addRow2Grid(self, row):
        # label
        stueLabel = QtGui.QLabel(u"Fixe Stütze {}".format(row+1))
        stueLabel.setAlignment(QtCore.Qt.AlignRight)
        stueLabel.setMinimumSize(QtCore.QSize(120, 0))
        stueLabel.setAlignment(QtCore.Qt.AlignRight|
                               QtCore.Qt.AlignTrailing|
                               QtCore.Qt.AlignVCenter)

        # Field for horizontal position in profile
        guiPos = QtGui.QLineEdit()
        guiH = QtGui.QLineEdit()
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Preferred,
                                       QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        guiPos.setSizePolicy(sizePolicy)
        guiPos.setMaximumSize(QtCore.QSize(70, 16777215))
        guiPos.setLayoutDirection(QtCore.Qt.RightToLeft)
        guiPos.setAlignment(QtCore.Qt.AlignRight)
        guiPos.setObjectName(u'{:0>2}_guiPos'.format(row))

        # Field for support height
        guiH.setSizePolicy(sizePolicy)
        guiH.setMaximumSize(QtCore.QSize(70, 16777215))
        guiH.setLayoutDirection(QtCore.Qt.RightToLeft)
        guiH.setAlignment(QtCore.Qt.AlignRight)
        guiH.setObjectName(u'{:0>2}_guiH'.format(row))

        # Button to remove row and support
        guiRemove = QtGui.QPushButton(u"x")
        guiRemove.setMaximumSize(QtCore.QSize(20, 20))
        guiRemove.setObjectName(u'{:0>2}_guiRemove'.format(row))

        # Connect signals
        QObject.connect(guiPos,
            SIGNAL("editingFinished()"), self.fixStueChanged)
        QObject.connect(guiH,
            SIGNAL("editingFinished()"), self.fixStueChanged)
        QObject.connect(guiRemove,
            SIGNAL("clicked()"), self.removeStue)

        # Place fields in GUI
        hbox1 = QtGui.QHBoxLayout()
        hbox1.addWidget(guiPos)
        hbox1.setAlignment(QtCore.Qt.AlignCenter)
        hbox2 = QtGui.QHBoxLayout()
        hbox2.addWidget(guiH)
        hbox2.setAlignment(QtCore.Qt.AlignCenter)

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
        print order
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
        self.mapMarker.setColor(QtGui.QColor(249, 236, 0))

    def activateMapLine(self, horiDist):
        mapLine = QgsRubberBand(self.canvas, False)
        mapLine.setWidth(3)
        mapLine.setColor(QtGui.QColor(255, 250, 90))
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
        focused_widget = QtGui.QApplication.focusWidget()
        if isinstance(focused_widget, QtGui.QLineEdit):
            focused_widget.clearFocus()
        QtGui.QDialog.mousePressEvent(self, event)



class MyNavigationToolbar(NavigationToolbar):
    # Only display the buttons we need
    toolitems = [t for t in NavigationToolbar.toolitems if
                 t[0] in ('Home', 'Pan', 'Zoom')]

    def __init__(self, *args, **kwargs):
        super(MyNavigationToolbar, self).__init__(*args, **kwargs)
        self.layout().takeAt(3)  # 3 = Amount of tools we need


