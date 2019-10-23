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

 Code is based on these two examples:
 https://github.com/eliben/code-for-blog/blob/master/2009/qt_mpl_bars.py
 http://www.technicaljar.com/?p=688
"""

import numpy as np
from qgis.PyQt.QtCore import QSize, Qt
from qgis.PyQt.QtWidgets import QDialog, QWidget, QLabel, QDialogButtonBox, \
    QHBoxLayout, QPushButton, QVBoxLayout, QGridLayout, QFrame, \
    QSpacerItem, QLineEdit, QApplication, QSizePolicy
from qgis.PyQt.QtGui import QColor

from qgis.core import QgsGeometry
from qgis.gui import QgsRubberBand

from .profilePlot import ProfilePlot
from .guiHelperFunctions import MyNavigationToolbar
from .mapMarker import QgsMovingCross

css = "QLineEdit {background-color: white;}"
cssErr = "QLineEdit {background-color: red;}"


class ProfileDialog(QDialog):
    def __init__(self, toolWindow, interface, projectHandler):
        QDialog.__init__(self, interface.mainWindow())
        # super().__init__()
        self.setWindowTitle("Höhenprofil")
        self.iface = interface
        self.canvas = self.iface.mapCanvas()
        self.profile = None
        self.toolWin = toolWindow
        self.projectHandler = projectHandler

        main_widget = QWidget(self)

        self.mapMarker = None
        self.pointsToDraw = []
        self.mapLines = []

        # Matplotlib diagrm
        self.sc = ProfilePlot(self)
        self.sc.setMinimumSize(QSize(600, 400))
        self.sc.setMaximumSize(QSize(600, 400))
        self.sc.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.sc.updateGeometry()
        # Pan/Zoom Tools for diagram
        bar = MyNavigationToolbar(self.sc, self)

        #
        self.gridM = QGridLayout()
        self.grid = QGridLayout()
        self.gridM.addLayout(self.grid, 0, 0, 1, 1)

        # GUI fields
        stueTitle = QLabel("<b>Stützenstandorte anpassen</b>")
        hbox = QHBoxLayout()
        line1 = QFrame()
        line1.setFrameShape(QFrame.HLine)
        line1.setFrameShadow(QFrame.Sunken)

        # Create lables and buttons
        self.fixStueAdd = QPushButton("Fixe Stütze definieren")
        self.noStueAdd = QPushButton("Abschnitte ohne Stützen definieren")
        spacerItem1 = QSpacerItem(40, 20, QSizePolicy.Expanding,
                                        QSizePolicy.Minimum)
        hbox.addWidget(self.fixStueAdd)
        hbox.addItem(spacerItem1)
        hbox.addWidget(self.noStueAdd)
        hbox.setAlignment(self.noStueAdd, Qt.AlignRight)
        self.buttonBox = QDialogButtonBox(main_widget)
        self.buttonBox.setStandardButtons(QDialogButtonBox.Cancel|
                                          QDialogButtonBox.Ok)
        # Build up GUI
        self.container = QVBoxLayout(main_widget)
        self.container.addWidget(self.sc)
        self.container.addWidget(bar)
        self.container.addWidget(line1)
        self.container.addWidget(stueTitle)
        self.container.addLayout(hbox)
        self.container.addLayout(self.gridM)
        self.container.addWidget(self.buttonBox)

        # Connect signals
        self.fixStueAdd.clicked.connect(self.sc.acitvateCrosshairPole)
        self.noStueAdd.clicked.connect(self.sc.activateCrosshairSection)
        self.buttonBox.rejected.connect(self.Reject)
        self.buttonBox.accepted.connect(self.Apply)
        self.setLayout(self.container)

        # Get fixed intermediate support data
        self.fixStueOld = {}
        self.fixStueProp = []
        self.menu = False
        
        self.initMenu()

    def setProfile(self, profile):
        self.profile = profile
        # Draw plofile in diagram
        self.sc.plotData(self.profile)
    
    def setFixedPoles(self):
        # TODO: GUI Felder löschen
        self.removeOldStue()
        # Get fixed intermediate support data
        self.fixStueOld = self.projectHandler.getFixedPoles()
        self.fixStueProp = []
        self.menu = False

        # If fixed intermediate supports where already defined, redraw them
        if len(self.fixStueOld) > 0:
            for key, values in self.fixStueOld.items():
                order = key-1
                [pointX, pointY, pointH] = values
                drawnPoint = self.sc.CreatePoint(int(pointX), int(pointY))
                self.CreateFixStue(pointX, pointY, drawnPoint, pointH, order)


    def CreateFixStue(self, pointX, pointY, drawnPoint, pointH = '', order=None):
        if not order:           # Position of field in list
            order = len(self.fixStueProp)

        guiPos, guiH, guiRemove = self.addRow2Grid(order)
        guiPos.setText(pointX)
        if pointH == '-1':
            pointH = ''
        guiH.setText(pointH)

        # Draw marker on canvas
        point = self.projectHandler.transform2MapCoords(float(pointX))
        self.toolWin.drawTool.drawStueMarker(point)
        # Save data of intermediate support
        self.addStueToDict(order, pointX, pointY, pointH, guiPos, guiH,
                           drawnPoint)
    
    def setNoPoleSections(self, sections):
        self.sc.noStue = sections
        # TODO: in Plot zeichnen

    def initMenu(self):
        spacerItem1 = QSpacerItem(40, 20, QSizePolicy.Expanding,
                                  QSizePolicy.Minimum)
        spacerItem2 = QSpacerItem(20, 40, QSizePolicy.Minimum,
                                  QSizePolicy.Expanding)
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
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
        self.container.insertWidget(self.container.count() - 1, line)
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
        guiPos.setObjectName('{:0>2}_guiPos'.format(row))

        # Field for support height
        guiH.setSizePolicy(sizePolicy)
        guiH.setMaximumSize(QSize(70, 16777215))
        guiH.setLayoutDirection(Qt.RightToLeft)
        guiH.setAlignment(Qt.AlignRight)
        guiH.setObjectName('{:0>2}_guiH'.format(row))

        # Button to remove row and support
        guiRemove = QPushButton("x")
        guiRemove.setMaximumSize(QSize(20, 20))
        guiRemove.setObjectName('{:0>2}_guiRemove'.format(row))

        # Connect signals
        guiPos.editingFinished.connect(self.fixStueChanged)
        guiH.editingFinished.connect(self.fixStueChanged)
        guiRemove.clicked.connect(lambda: self.removeStue(row))

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
                self.toolWin.drawTool.removeStueMarker(2+order)
                point = self.projectHandler.transform2MapCoords(float(newval))
                self.toolWin.drawTool.drawStueMarker(point)
            self.fixStueProp[order]['x'] = str(int(float(newval)))
        # If height has changed
        if fieldType == 'guiH':
            self.fixStueProp[order]['h'] = newval

    def removeStue(self, row):
        order = row
        # Remove point from plot and from canvas
        self.sc.DeletePoint(self.fixStueProp[row]['drawnPnt'])
        self.toolWin.drawTool.removeStueMarker(row)
        # Delete intermediate support data
        del self.fixStueProp[row]
        rowCount = len(self.fixStueProp)
        # Adjust GUI
        # Remove row of deleted support and all subsequent rows
        for elem in reversed(range(row+1, rowCount+2)):
            self.removeStueField(elem)
        # Subsequent rows move up
        for rowElem in range(order, rowCount):
            guiPos, guiH, guiRemove = self.addRow2Grid(rowElem)
            guiPos.setText(self.fixStueProp[rowElem]['x'])
            if self.fixStueProp[rowElem]['h']:
                guiH.setText(self.fixStueProp[rowElem]['h'])
            self.fixStueProp[rowElem]['guiPos'] = guiPos
            self.fixStueProp[rowElem]['guiH'] = guiH
            self.fixStueProp[rowElem]['guiRemove'] = guiRemove
        self.setLayout(self.container)
        # If only remaining row was deleted also delete header
        if rowCount == 0:
            self.grid.takeAt(1).widget().deleteLater()
            self.grid.takeAt(0).widget().deleteLater()
            self.menu = False
        self.setLayout(self.container)
    
    def removeOldStue(self):
        for row in reversed(range(len(self.fixStueProp))):
            self.removeStueField(row+1)

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
        self.mapMarker = QgsMovingCross(self.canvas)
        initPoint = self.projectHandler.transform2MapCoords(horiDist)
        self.mapMarker.setCenter(initPoint)

    def deactivateMapMarker(self):
        if self.mapMarker:
            self.canvas.scene().removeItem(self.mapMarker)
        self.mapMarker = None

    def updateMapMarker(self, horiDist):
        if not self.mapMarker:
            self.activateMapMarker(horiDist)
        newpnt = self.projectHandler.transform2MapCoords(horiDist)
        self.mapMarker.setCenter(newpnt)
        self.canvas.refresh()

    def activateMapMarkerLine(self, horiDist):
        self.deactivateMapMarker()
        # [x, y] = self.projectHandler.transform2MapCoords(horiDist)
        self.mapMarker = QgsMovingCross(self.canvas)
        self.mapMarker.setColor(QColor(249, 236, 0))

    def activateMapLine(self, horiDist):
        mapLine = QgsRubberBand(self.canvas, False)
        mapLine.setWidth(3)
        mapLine.setColor(QColor(255, 250, 90))
        self.mapLines.append(mapLine)
        self.pointsToDraw = []
        # Create first point
        initPoint = self.projectHandler.transform2MapCoords(horiDist)
        self.pointsToDraw.append(initPoint)

    def lineMoved(self, horiDist):
        newPnt = self.projectHandler.transform2MapCoords(horiDist)
        points = self.pointsToDraw + [newPnt]
        self.mapLines[-1].setToGeometry(QgsGeometry.fromPolylineXY(points), None)

    def finishLine(self, horiDist):
        endPoint = self.projectHandler.transform2MapCoords(horiDist)
        self.pointsToDraw.append(endPoint)
        self.mapLines[-1].setToGeometry(QgsGeometry.fromPolylineXY(
            self.pointsToDraw), None)
        self.pointsToDraw = []

    def removeLines(self):
        for line in self.mapLines:
            line.reset(False)

    def clearUnfinishedLines(self):
        if len(self.pointsToDraw) == 1:
            self.mapLines[-1].reset(False)
            self.mapLines.pop(-1)
            self.pointsToDraw = []

    ###########################################################################

    def getValues(self):
        return [self.dist, self.height]

    def Apply(self):
        self.projectHandler.setFixedPoles(self.fixStueProp)
        self.projectHandler.setNoPoleSection(self.sc.noStue)
        self.deactivateMapMarker()
        self.clearUnfinishedLines()
        self.close()

    def Reject(self):
        # TODO: Cancel: keine Änderungen speichern. D.h beim Öffnen jedes Mal Poles neu erstellen?
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





