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
from math import floor
from qgis.PyQt.QtCore import QSize, Qt
from qgis.PyQt.QtWidgets import (QDialog, QWidget, QLabel, QDialogButtonBox,
    QHBoxLayout, QPushButton, QVBoxLayout, QFrame, QSpacerItem, QSizePolicy)

from .profilePlot import ProfilePlot
from .guiHelperFunctions import MyNavigationToolbar
from .adjustmentDialog_poles import CustomPoleWidget


class ProfileDialog(QDialog):
    def __init__(self, interface, drawTool, projectHandler):
        """
        :type drawTool: gui.mapMarker.MapMarkerTool
        :type projectHandler: configHandler.ProjectConfHandler
        """
        QDialog.__init__(self, interface.mainWindow())
        self.iface = interface
        self.projectHandler = projectHandler
        self.drawTool = drawTool
        self.setWindowTitle("Höhenprofil")
        
        # Array with properties fixed poles
        self.poleData = []
        # Profile data
        self.xdata = None
        self.zdata = None
        self.profileMin = 0
        self.profileMax = None
        # Control variable to know when to reset gui and plot
        self.doReset = True

        # Plot
        self.sc = ProfilePlot(self)
        self.sc.setMinimumSize(QSize(600, 400))
        self.sc.setMaximumSize(QSize(600, 400))
        self.sc.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        # Pan/Zoom Tools for diagram
        bar = MyNavigationToolbar(self.sc, self)

        # Layout
        main_widget = QWidget(self)
        self.container = QVBoxLayout(main_widget)
        self.outerLayout = QVBoxLayout()

        # GUI fields
        stueTitle = QLabel("<b>Stützenstandorte anpassen</b>")
        hbox = QHBoxLayout()
        line1 = QFrame()
        line1.setFrameShape(QFrame.HLine)
        line1.setFrameShadow(QFrame.Sunken)

        # Create labels and buttons
        self.fixStueAdd = QPushButton("Fixe Stütze definieren")
        self.noStueAdd = QPushButton("Abschnitte ohne Stützen definieren")
        spacerItem1 = QSpacerItem(40, 20, QSizePolicy.Expanding,
                                        QSizePolicy.Minimum)
        hbox.addWidget(self.fixStueAdd)
        hbox.addItem(spacerItem1)
        hbox.addWidget(self.noStueAdd)
        hbox.setAlignment(self.noStueAdd, Qt.AlignRight)
        btnBoxSpacer = QSpacerItem(40, 40, QSizePolicy.Fixed,
                                        QSizePolicy.Fixed)
        self.buttonBox = QDialogButtonBox(main_widget)
        self.buttonBox.setStandardButtons(QDialogButtonBox.Cancel |
                                          QDialogButtonBox.Ok)
        # Build up Gui
        self.container.addWidget(self.sc)
        self.container.addWidget(bar)
        self.container.addWidget(line1)
        self.container.addWidget(stueTitle)
        self.container.addLayout(hbox)
        self.container.addLayout(self.outerLayout)
        self.container.addItem(btnBoxSpacer)
        self.container.addWidget(self.buttonBox)

        # Connect signals
        self.fixStueAdd.clicked.connect(self.sc.acitvateCrosshairPole)
        self.noStueAdd.clicked.connect(self.sc.activateCrosshairSection)
        self.buttonBox.rejected.connect(self.Reject)
        self.buttonBox.accepted.connect(self.Apply)
        self.setLayout(self.container)
        
        # Gui functionality for fixed pole gui fields
        self.buildPoleHeader()
        self.poleLayout = CustomPoleWidget(self, self.outerLayout)
        self.poleLayout.sig_updatePole.connect(self.updatePole)
        self.poleLayout.sig_deletePole.connect(self.deletePole)

    def setProfile(self, profile):
        self.reset()
        self.xdata = profile.xaxis
        self.zdata = profile.yaxis
        self.profileMax = floor(self.xdata[-1])
        # Draw profile in diagram
        self.sc.plotData(profile)
    
    def reset(self):
        """Resets the window, the plot and the map so that there are no poles
        present anymore."""
        # Delete pole rows in gui
        self.poleLayout.removeAll()
        # Remove marker in map and points in plot
        for idx, pole in enumerate(self.poleData):
            self.sc.deletePoint(self.poleData[idx]['plotPoint'])
            self.drawTool.removeMarker()
        self.poleData = []
        self.profileMax = None

    def setFixedPoles(self):
        """Fills gui, plot and map with data of fixed poles that where saved
        to a project file."""
        predefinedPoles = self.projectHandler.getFixedPoles()
        self.poleLayout.setInitialGui(self.poleData,
                                      [self.profileMin, self.profileMax])
        for i in range(len(predefinedPoles[0])):
            d = predefinedPoles[0][i]
            h = predefinedPoles[1][i]
            z = self.getZValue(d)
            self.addPole(d, z, h)
            
    def setNoPoleSections(self, sections):
        self.sc.noStue = sections
        # TODO: in Plot zeichnen

    def buildPoleHeader(self):
        headerRow = QHBoxLayout()
        spacerItemA = QSpacerItem(60, 20, QSizePolicy.Fixed,
                                 QSizePolicy.Minimum)
        spacerItemE = QSpacerItem(60, 20, QSizePolicy.Expanding,
                                 QSizePolicy.Minimum)
        headername = QLabel('Stützenbezeichnung')
        headername.setMinimumSize(QSize(180, 30))
        headerDist = QLabel('Distanz')
        headerDist.setMinimumSize(QSize(95, 30))
        headerHeight = QLabel('Höhe')
        headerHeight.setMinimumSize(QSize(85, 30))

        headerRow.addItem(spacerItemA)
        headerRow.addWidget(headername)
        headerRow.addWidget(headerDist)
        headerRow.addWidget(headerHeight)
        headerRow.addItem(spacerItemE)
        self.outerLayout.addLayout(headerRow)
    
    def addPole(self, d, z, h=None, angle=False):
        """Called when user clicks onto plot window to create fixed pole.
        Function creates a new row in gui with properties of pole, creates a
        point in the plot and a marker on the map."""
        idx = 0
        for i, pole in enumerate(reversed(self.poleData)):
            if pole['d'] <= d:
                idx = len(self.poleData) - i
                break
        # Draw point on plot
        drawnPoint = self.sc.createPoint(d, z)
        # Draw marker in map
        self.createMapMarker(d, idx+1)
        # Save new fixed pole in list
        self.poleData.insert(idx, {
            'name': 'fixe Stütze',
            'poleType': 'fixed',
            'd': d,
            'z': z,
            'h': h,
            'angle': angle,
            'plotPoint': drawnPoint
        })
        # Add layout row in gui
        lowerRange = self.profileMin
        upperRange = self.profileMax
        if idx > 0:
            lowerRange = self.poleData[idx - 1]['d']
        if idx < len(self.poleData)-1:
            upperRange = self.poleData[idx + 1]['d']
            
        self.poleLayout.addRow(idx, 'fixe Stütze', d, lowerRange, upperRange,
                               h, angle, poleType='fixed', delBtn=True,
                               addBtn=False)
        
    def updatePole(self, idx, property_name, val):
        """Called when user manually changes distance or height values in
        LineEdits. Function updates point in plot and marker on map."""
        if self.poleData[idx][property_name] == val:
            return
        if property_name == 'd':
            # Calculate z value
            self.poleData[idx]['z'] = self.getZValue(val)
            # Update in plot
            self.sc.deletePoint(self.poleData[idx]['plotPoint'])
            self.poleData[idx]['plotPoint'] = \
                self.sc.createPoint(val, self.poleData[idx]['z'])
            # Update on map
            marker = self.projectHandler.transform2MapCoords(float(val))
            self.drawTool.updateMarker(marker, idx+1)
        
        if property_name in ['d', 'h']:
            self.poleData[idx][property_name] = round(val, 0)
        else:
            self.poleData[idx][property_name] = val
        self.poleLayout.changeRow(idx, property_name, round(val, 0))
    
    def deletePole(self, idx):
        """Called when user clicks on delete button on pole row. Function
        removes point in plot, marker on map and row in gui."""
        self.sc.deletePoint(self.poleData[idx]['plotPoint'])
        self.drawTool.removeMarker(idx+1)
        distLower = self.profileMin
        distUpper = self.profileMax
        if idx > 0:
            distLower = self.poleData[idx - 1]['d']
        if idx < len(self.poleData) - 1:
            distUpper = self.poleData[idx + 1]['d']
        self.poleLayout.deleteRow(idx, distLower, distUpper)
        self.poleData.pop(idx)
    
    def getZValue(self, dist):
        return self.zdata[np.argmax(self.xdata >= dist)]
    
    def createMapMarker(self, horiDist, idx):
        point = self.projectHandler.transform2MapCoords(float(horiDist))
        self.drawTool.drawMarker(point, idx)
        
    def deactivateMapCursor(self):
        self.drawTool.deactivateCursor()

    def activateMapCursor(self, initPoint, color):
        self.updateMapCursor(initPoint, color)

    def updateMapCursor(self, horiDist, color):
        point = self.projectHandler.transform2MapCoords(horiDist)
        self.drawTool.updateCursor(point, color)

    def activateMapLine(self, horiDist):
        initPoint = self.projectHandler.transform2MapCoords(horiDist)
        self.drawTool.activateSectionLine(initPoint)

    def lineMoved(self, horiDist):
        point = self.projectHandler.transform2MapCoords(horiDist)
        self.drawTool.updateSectionLine(point)

    def finishLine(self, horiDist):
        endPoint = self.projectHandler.transform2MapCoords(horiDist)
        self.drawTool.updateSectionLine(endPoint)
        self.drawTool.deactivateCursor()

    def Apply(self):
        self.projectHandler.setFixedPoles(self.poleData)    # TODO
        self.projectHandler.setNoPoleSection(self.sc.noStue)
        self.deactivateMapCursor()
        self.drawTool.clearUnfinishedLines()
        self.close()

    def Reject(self):
        self.deactivateMapCursor()
        self.drawTool.clearUnfinishedLines()
        self.reset()
        self.close()

    # def mousePressEvent(self, event):
    #     focused_widget = QApplication.focusWidget()
    #     if isinstance(focused_widget, QLineEdit):
    #         focused_widget.clearFocus()
    #     QDialog.mousePressEvent(self, event)
