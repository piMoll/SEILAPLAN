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
from qgis.PyQt.QtGui import QIcon, QPixmap

from .profilePlot import ProfilePlot
from .plotting_tools import MyNavigationToolbar
from .customWidgets import CustomPoleWidget


class ProfileDialog(QDialog):
    def __init__(self, parent, interface, drawTool, projectHandler):
        """
        :type drawTool: gui.mapMarker.MapMarkerTool
        :type projectHandler: configHandler.ProjectConfHandler
        """
        QDialog.__init__(self, parent)
        self.iface = interface
        self.projectHandler = projectHandler
        self.drawTool = drawTool
        self.setWindowTitle("Höhenprofil")
        self.setWindowModality(Qt.WindowModal)
        
        self.profile = None
        # Array with properties fixed poles
        self.poleData = []
        # Array with sections without poles
        self.noPoleSection = []
        # Profile data
        self.xdata = None
        self.zdata = None
        self.profileMin = 0
        self.profileMax = None
        # Control variable to know when data was set
        self.dataSet = False

        # Plot
        self.sc = ProfilePlot(self)
        # Pan/Zoom Tools for diagram
        tbar = MyNavigationToolbar(self.sc, self)
        tbar.pan()
        self.sc.setToolbar(tbar)

        # Layout
        main_widget = QWidget(self)
        self.container = QVBoxLayout(main_widget)
        self.outerLayout = QVBoxLayout()

        # GUI fields
        stueTitle = QLabel("<b>Stützenoptimierung einschränken</b>")
        hbox = QHBoxLayout()
        line1 = QFrame()
        line1.setFrameShape(QFrame.HLine)
        line1.setFrameShadow(QFrame.Sunken)

        # Create labels and buttons
        self.fixStueAdd = QPushButton("Fixe Stütze definieren")
        self.noStueAdd = QPushButton("Abschnitt ohne Stützen definieren")
        self.noStueDel = QPushButton()
        icon = QIcon()
        icon.addPixmap(
            QPixmap(":/plugins/SeilaplanPlugin/gui/icons/icon_bin.png"),
            QIcon.Normal, QIcon.Off)
        self.noStueDel.setIcon(icon)
        self.noStueDel.setIconSize(QSize(16, 16))
        self.fixStueAdd.setToolTip('Fixe Stützen werden vom '
            'Optimierungsalgorithmus als bereits vorhandene Stützen '
            'berücksichtigt.')
        self.noStueAdd.setToolTip('Abschnitte, in denen während der '
            'Optimierung keine Stützen platziert werden.')
        self.noStueDel.setToolTip('Abschnitte löschen')
        spacerItem1 = QSpacerItem(40, 20, QSizePolicy.Expanding,
                                        QSizePolicy.Minimum)
        hbox.addWidget(self.fixStueAdd)
        hbox.addItem(spacerItem1)
        hbox.addWidget(self.noStueAdd)
        hbox.addWidget(self.noStueDel)
        hbox.setAlignment(self.noStueAdd, Qt.AlignRight)
        btnBoxSpacer = QSpacerItem(40, 40, QSizePolicy.Fixed,
                                        QSizePolicy.Fixed)
        self.buttonBox = QDialogButtonBox(main_widget)
        self.buttonBox.setStandardButtons(QDialogButtonBox.Ok)
        # Build up Gui
        self.container.addWidget(self.sc)
        self.container.addWidget(tbar, alignment=Qt.AlignHCenter | Qt.AlignTop)
        self.container.addWidget(line1)
        self.container.addWidget(stueTitle)
        self.container.addLayout(hbox)
        self.container.addLayout(self.outerLayout)
        self.container.addItem(btnBoxSpacer)
        self.container.addWidget(self.buttonBox)

        # Connect signals
        self.fixStueAdd.clicked.connect(self.sc.acitvateCrosshairPole)
        self.noStueAdd.clicked.connect(self.sc.activateCrosshairSection)
        self.noStueDel.clicked.connect(self.deleteSections)
        self.buttonBox.accepted.connect(self.Apply)
        self.setLayout(self.container)
        
        # Gui functionality for fixed pole gui fields
        self.buildPoleHeader()
        self.poleLayout = CustomPoleWidget(self, self.outerLayout)
        self.poleLayout.sig_updatePole.connect(self.updatePole)
        self.poleLayout.sig_deletePole.connect(self.deletePole)

    def setProfile(self, profile):
        self.profile = profile
        self.xdata = self.profile.di
        self.zdata = self.profile.zi
        self.profileMax = floor(self.xdata[-1])
        # Draw profile in diagram
        self.sc.plotData(self.profile)
    
    def reset(self):
        """Resets the window and remove all pole layouts. Markers do not have
        to be deleted, they are reset when new profile line is drawn. Plot
        points are reset when plot is cleared at next setProfile()."""
        # Delete pole rows in gui
        self.poleLayout.removeAll()
        self.poleData = []
        self.noPoleSection = []
        self.profileMax = None

    def setPoleData(self, poles, sections):
        """Fills gui, plot and map with data of fixed poles and pole
        sections."""
        self.poleLayout.setInitialGui([self.profileMin, self.profileMax])
        for pole in poles:
            self.addPole(pole['d'], pole['z'], pole['h'], name=pole['name'])
        for section in sections:
            # Draw line onto map
            self.activateMapLine(section[0])
            self.finishLine(section[1])
            # Plot section in plot
            for x in section:
                z = self.getZValue(x)
                self.sc.drawSection(x, z)
            self.sc.draw()
        # Window is ready to show new data
        self.dataSet = True

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
    
    def addPole(self, d, z, h=None, name='', angle=False):
        """Called when user clicks onto plot window to create fixed pole.
        Function creates a new row in gui with properties of pole, creates a
        point in the plot and a marker on the map."""
        idx = 0
        for i, pole in enumerate(reversed(self.poleData)):
            if pole['d'] <= d:
                idx = len(self.poleData) - i
                break
        if not z:
            z = self.getZValue(d)
        if not name:
            name = 'fixe Stütze'
        # Draw point on plot
        drawnPoint = self.sc.createPoint(d, z)
        # Draw marker onto map
        self.createMapMarker(d, idx+1)
        # Save new fixed pole in list
        self.poleData.insert(idx, {
            'name': name,
            'poleType': 'fixed',
            'd': d,
            'z': z,
            'h': h,
            'angle': angle,
            'plotPoint': drawnPoint
        })
        # Add layout row to gui
        lowerRange = self.profileMin
        upperRange = self.profileMax
        if idx > 0:
            lowerRange = self.poleData[idx - 1]['d']
        if idx < len(self.poleData)-1:
            upperRange = self.poleData[idx + 1]['d']
            
        self.poleLayout.addRow(idx, name, d, lowerRange, upperRange,
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
        self.poleLayout.changeRow(idx, property_name, val)
    
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
        self.noPoleSection.append([horiDist, None])
        initPoint = self.projectHandler.transform2MapCoords(horiDist)
        self.drawTool.activateSectionLine(initPoint)

    def lineMoved(self, horiDist):
        point = self.projectHandler.transform2MapCoords(horiDist)
        self.drawTool.updateSectionLine(point)

    def finishLine(self, horiDist):
        self.noPoleSection[-1][1] = horiDist
        endPoint = self.projectHandler.transform2MapCoords(horiDist)
        self.drawTool.updateSectionLine(endPoint)
        self.drawTool.deactivateCursor()
    
    def deleteSections(self):
        if self.noPoleSection:
            # Redraw profile
            self.sc.plotData(self.profile)
            # Redraw markers of pole
            for pole in self.poleData:
                pole['plotPoint'] = self.sc.createPoint(pole['d'], pole['z'])
            # Delete all sections in map
            self.drawTool.deleteSectionLines()
            self.noPoleSection = []
    
    def stopActiveEdits(self):
        self.deactivateMapCursor()
        self.drawTool.clearUnfinishedLines()
        # Remove last section if its not finished
        if self.noPoleSection and not self.noPoleSection[-1][1]:
            self.noPoleSection.pop(-1)

    def Apply(self):
        self.close()
    
    def closeEvent(self, event):
        self.stopActiveEdits()
        self.projectHandler.setFixedPoles(self.poleData)
        self.projectHandler.setNoPoleSection(self.noPoleSection)
        self.dataSet = False
        # Reset gui since this can only be done when the window is still open
        self.reset()
