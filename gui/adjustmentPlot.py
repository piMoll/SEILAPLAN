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
import numpy as np
from math import degrees
from qgis.PyQt.QtCore import Qt, QSize, QCoreApplication
from qgis.PyQt.QtWidgets import QSizePolicy

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.patches import Rectangle
from matplotlib.pyplot import imread
import matplotlib.patheffects as pe

from .plotting_tools import zoom_with_wheel
from SEILAPLAN.tools.birdViewSymbol import BirdViewSymbol, BirdViewSymbolLoader


class AdjustmentPlot(FigureCanvas):
    
    ZOOM_TO_DISTANCE = 20
    COLOR_MARKER = {
        0: '#696969',   # grey = neutral
        1: '#4a6b55',   # dark green = ok
        2: '#e38400',   # orange = attention
        3: '#e06767',   # red = error
    }
    
    def __init__(self, parent=None, width=5., height=4., dpi=72, withBirdView=False, profilePlotRatio=3):
        self.win = parent
        self.dpi = dpi
        self.fig = Figure(figsize=(width, height), dpi=self.dpi, facecolor='#efefef')
        
        FigureCanvas.__init__(self, self.fig)
        self.setParent(parent)
        
        self.axesBirdView = None
        self.birdViewMarkers = None
        
        if withBirdView:
            axes = self.fig.subplots(nrows=2, ncols=1, gridspec_kw={'height_ratios': [profilePlotRatio, 1]}, sharex=True)
            self.axes = axes[0]
            self.axesBirdView = axes[1]
            # Load markers
            loader = BirdViewSymbolLoader()
            self.birdViewMarkers = loader.loadSymbolFromArray()
            self.axesBirdView.set_aspect('equal')
            self.fig.subplots_adjust(hspace=0)
        else:
            self.axes = self.fig.add_subplot(111)
            self.fig.tight_layout(pad=0, w_pad=0.1, h_pad=0.1)
        
        # Profile plot should always be drawn with equal aspect
        self.axes.set_aspect('equal', 'datalim', share=True)
        
        self.xdata = None
        self.terrain = None
        self.tPoints = None
        self.peakLoc_x = None
        self.peakLoc_y = None
        self.data_xlow = 0
        self.data_xhi = 0
        self.data_ylow = 0
        self.data_yhi = 0
        self.labelBuffer = 1
        self.arrowMarker = []
        self.arrowLabel = []
        # Reference to navigation toolbar
        self.tbar = None
        
        self.currentPole = None
        self.isZoomed = False

        # Enable zoom with scroll wheel
        zoomFunc = zoom_with_wheel(self, self.axes, zoomScale=1.3)

        self.setFocusPolicy(Qt.ClickFocus)
        FigureCanvas.setSizePolicy(self, QSizePolicy.Expanding,
                                   QSizePolicy.Expanding)
        FigureCanvas.updateGeometry(self)

    def __setupAxes(self):
        direction = 'in'
        if self.axesBirdView:
            direction = 'inout'
        self.axes.ticklabel_format(style='plain', useOffset=False)
        self.axes.tick_params(axis="both", which="major", direction=direction,
                              length=5, width=1, bottom=True, top=False,
                              left=True, right=False)
        self.axes.minorticks_on()
        self.axes.tick_params(which="minor", direction=direction)
        
    def initData(self, xdata, terrain, peakLocation_x, peakLocation_y,
                 surveyPoints):
        self.xdata = xdata
        self.terrain = terrain
        self.peakLoc_x = peakLocation_x
        self.peakLoc_y = peakLocation_y
        self.data_xlow = np.min(self.xdata)
        self.data_xhi = np.max(self.xdata)
        self.data_ylow = np.min(self.terrain)
        # Add 40m to have space for poles
        self.data_yhi = np.max(self.terrain) + 40
        self.tPoints = surveyPoints
        
        rangeX = self.data_xhi - self.data_xlow
        rangeY = self.data_yhi - self.data_ylow
        ratio = rangeX / rangeY
        # Update figure size to fit data, height is a minimum of 330 px
        if not self.axesBirdView:
            minHeight = 330
            minLength = int(round(min(minHeight * ratio, 600)))
            self.setMinimumSize(QSize(minLength, minHeight))
        # Set label positioning by taking height of figure into account
        height_m2px = rangeY / self.height()
        self.labelBuffer = 5 * height_m2px

        self.data_ylow -= 8*self.labelBuffer
        self.data_yhi += 4*self.labelBuffer

    def setPlotLimits(self):
        """Only used when activating zoomTo functionality."""
        if self.isZoomed:
            d = self.currentPole['d']
            z = self.currentPole['z']
            h = self.currentPole['h']
            self.axes.set_xlim(d - AdjustmentPlot.ZOOM_TO_DISTANCE,
                               d + AdjustmentPlot.ZOOM_TO_DISTANCE)
            self.axes.set_ylim(
                (z + 0.5 * h) - AdjustmentPlot.ZOOM_TO_DISTANCE,
                (z + 0.5 * h) + AdjustmentPlot.ZOOM_TO_DISTANCE)
            self.labelBuffer = 0.2

        else:
            self.axes.set_xlim(self.data_xlow, self.data_xhi)
            self.axes.set_ylim(self.data_ylow, self.data_yhi)
        
    def updatePlot(self, poles, cable, printPdf=False):
        scale = 1
        legendCol = 4
        fontSize = 12
        if printPdf:
            legendCol = 3
            scale = 0.5
            fontSize = 8
        
        self.axes.clear()
        self.__setupAxes()
        # Terrain
        self.axes.plot(self.xdata, self.terrain, color='#a1d1ab',
                       linewidth=3.5*scale, zorder=1)
        # Mark survey points when working with CSV height data
        if self.tPoints is not None:
            # Add markers for survey points
            for pointX, pointY, idx, notes in zip(self.tPoints['d'],
                                                  self.tPoints['z'],
                                                  self.tPoints['nr'],
                                                  self.tPoints['notes']):
                self.axes.plot([pointX, pointX],
                               [pointY, pointY - 6 * self.labelBuffer * scale],
                               color='green', linewidth=1.5 * scale, zorder=2)
                labelText = f"{idx}"
                rot = 0
                ha = 'center'
                va = 'top'
                if notes:
                    labelText = f"{idx}{':' if notes else ''} {notes if len(notes) <= 25 else notes[:22] + '...'}"
                    # For less placement issues, labels are rotated 45°
                    rot = 55
                    ha = 'right'
                    va = 'center'
                    # Label rotation is switched if profile line inclines
                    if self.terrain[0] < self.terrain[-1]:
                        rot = 305
                        ha = 'left'
                self.axes.text(pointX, pointY - 7 * self.labelBuffer * scale,
                               labelText, ha=ha, va=va, fontsize=fontSize,
                               color='green', rotation=rot, rotation_mode='anchor')
        
        if not printPdf:
            # Well suited locations (peaks) for poles
            self.axes.scatter(self.peakLoc_x, self.peakLoc_y, marker='^',
                              color='#ffaa00', edgecolors='#496b48',
                              label=self.tr('Guenstige Gelaendeform'), zorder=3)
        # Cable lines
        self.axes.plot(cable['xaxis'], cable['empty'], color='#4D83B2',
                       linewidth=1.5*scale, label=self.tr('Leerseil'))
        self.axes.plot(cable['xaxis'], cable['load'], color='#FF4D44',
                       linewidth=1.5*scale, label=self.tr('Lastwegkurve nach Zweifel'))
        # Anchors
        if cable['anchorA']:
            self.axes.plot(cable['anchorA']['d'], cable['anchorA']['z'],
                           color='#a6a6a6', linewidth=1.5*scale)
        if cable['anchorE']:
            self.axes.plot(cable['anchorE']['d'], cable['anchorE']['z'],
                           color='#a6a6a6', linewidth=1.5*scale)
        # Ground clearance
        self.axes.plot(cable['groundclear_di'], cable['groundclear'],
                       color='#910000', linewidth=1*scale, linestyle=':',
                       label=self.tr('Min. Bodenabstand'))
        self.axes.plot(cable['groundclear_di'], cable['groundclear_under'],
                       color='#910000', linewidth=1*scale)
            
        # Poles
        [pole_d, pole_z, pole_h, pole_dtop, pole_ztop,
         pole_nr, poleType, category, position, abspann] = poles
        for i, d in enumerate(pole_d):
            self.axes.plot([pole_d[i], pole_dtop[i]], [pole_z[i], pole_ztop[i]],
                           color='#363432', linewidth=3.0*scale)
            if poleType[i] == 'crane':
                h = 3.5
                w = h * 1.8
                rect = Rectangle((pole_d[i] - w/2, pole_z[i]), w, h, ls='-',
                                 lw=3.0*scale, facecolor='black', ec='black', zorder=5)
                self.axes.add_patch(rect)
        # Vertical guide lines
        if self.isZoomed:
            d = self.currentPole['d']
            z = self.currentPole['z']
            ztop = self.currentPole['ztop']
            self.axes.axvline(lw=1, ls='dotted', color='black', x=d)
            self.axes.axhline(lw=1, ls='dotted', color='black', y=z)
            self.axes.axhline(lw=1, ls='dotted', color='black', y=ztop)
            
        if printPdf:
            # Make sure plot has enough buffer at start and end of cable line
            #  to fit bird view symbols.
            symbolBuffer = 40
            cableStart = cable['xaxis'][0]
            if cable['anchorA']:
                cableStart = cable['anchorA']['d'][0]
            cableEnd = cable['xaxis'][-1]
            if cable['anchorE']:
                cableEnd = cable['anchorE']['d'][-1]
            if abs(cableStart - self.axes.get_xlim()[0]) < symbolBuffer:
                self.axes.set_xlim(cableStart - symbolBuffer, self.axes.get_xlim()[1])
            if abs(cableEnd - self.axes.get_xlim()[1]) < symbolBuffer:
                self.axes.set_xlim(self.axes.get_xlim()[0], cableEnd + symbolBuffer)
        else:
            # Add labels
            self.placeLabels(pole_dtop, pole_ztop, pole_nr)
        # Legend
        self.axes.legend(loc='lower center', fontsize=fontSize,
                         bbox_to_anchor=(0.5, 0), ncol=legendCol)
        self.draw()
        # Set new plot extent as home extent (for home button)
        if not printPdf:
            self.tbar.update()
            self.tbar.push_current()
    
    def showMarkers(self, x, y, label, colorList, labelAlign):
        # Displays marker for thresholds
        self.removeMarkers()
        spacing = 3 * abs(self.axes.get_ylim()[0] - self.axes.get_ylim()[1]) / self.height()
        
        color = [self.COLOR_MARKER[col] for col in colorList]
        for i, xi in enumerate(x):
            textVa = 'top'
            marker = '^'
            markerPos = y[i] - spacing * 3
            labelPos = y[i] - spacing * 5
            if labelAlign[i] == 'top':
                textVa = 'bottom'
                marker = 'v'
                markerPos = y[i] + spacing * 7
                labelPos = y[i] + spacing * 9
        
            self.arrowMarker.append(
                self.axes.scatter(xi, markerPos, marker=marker, zorder=20,
                                  c=color[i], s=100))
            # Adds a label underneath marker with threshold value
            self.arrowLabel.append(
                self.axes.text(xi, labelPos, label[i], zorder=30, ha='center',
                               backgroundcolor='white', va=textVa,
                               color=color[i], fontweight='semibold'))
        self.draw()
    
    def removeMarkers(self):
        [arrow.remove() for arrow in self.arrowMarker]
        [label.remove() for label in self.arrowLabel]
        self.arrowMarker = []
        self.arrowLabel = []
        self.draw()

    def zoomTo(self, pole):
        self.isZoomed = True
        self.currentPole = pole
        self.setPlotLimits()
    
    def zoomOut(self):
        self.isZoomed = False
        self.currentPole = {}
        self.setPlotLimits()
        # Set new plot extent as home extent (for home button)
        self.tbar.update()
        self.tbar.push_current()
    
    def placeLabels(self, xdata, ydata, label):
        if self.isZoomed:
            d = self.currentPole['d']
            z = self.currentPole['z']
            h = self.currentPole['h']
            ztop = self.currentPole['ztop']
            pos_t_d = self.axes.get_xlim()[0]
            pos_t_z = z + self.labelBuffer
            pox_yp_z = ztop + self.labelBuffer
            pos_h_d = d
            pos_h_z = ztop + self.labelBuffer * 3
    
            self.axes.text(pos_t_d, pos_t_z, f'{round(z, 1)} m', ha='left')
            self.axes.text(pos_t_d, pox_yp_z, f'{round(ztop, 1)} m', ha='left')
            self.axes.text(pos_h_d, pos_h_z, f'{round(h, 1)} m', ha='center')
        else:
            for i in range(len(xdata)):
                self.axes.text(xdata[i], ydata[i] + self.labelBuffer, label[i],
                               fontsize=12, ha='center', fontweight='semibold',
                               color=self.COLOR_MARKER[0])
        
    def layoutDiagrammForPrint(self, title, poles, direction):
        self.axes.set_title(self.tr('Seilaplan Plot  -  {}').format(title),
                            fontsize=10, multialignment='center')
        if not self.axesBirdView:
            self.axes.set_xlabel(self.tr('Horizontaldistanz [m]'), fontsize=9)
        self.axes.set_ylabel(self.tr("Hoehe [m.ue.M]"), fontsize=9)
        self.axes.tick_params(labelsize=8)
        self.axes.tick_params(labelsize=8, labeltop=False, labelbottom=True)
        self.axes.grid(which='major', lw=0.5)
        self.axes.grid(which='minor', lw=0.5, linestyle=':')
        # Label poles
        # Halo effect around text for better readability
        haloEffect = [pe.withStroke(linewidth=2, foreground="white")]
        for idx, pole in enumerate(poles):
            # Don't label anchors
            if pole['poleType'] == 'anchor':
                continue
            poleNr = f"{pole['nr']}: " if pole['nr'] else ''
            poleName = pole['name'][:28].strip() + '…' if len(pole['name']) > 30 else pole['name']
            rotation = 30 if direction == 'downhill' else -30
            ha = 'left' if direction == 'downhill' else 'right'
            
            self.axes.text(pole['dtop'], pole['ztop'] + self.labelBuffer * 4,
                           f"{poleNr}{poleName}\nH = {pole['h']:.1f} m",
                           ha=ha, fontsize=7, rotation=rotation,
                           rotation_mode='anchor', transform_rotates_text=True,
                           path_effects=haloEffect)
        
    def createBirdView(self, poles, azimut):
        # Height of y-axis (+/- from x-axis) in meter
        yLim = 30
        # Set fixed limits of the vertical axis
        self.axesBirdView.set_ylim(-yLim, yLim)
        # Horizontal line symbolizing cable line from first to last pole
        self.axesBirdView.plot([poles[0]['d'], poles[-1]['d']], [0, 0], color='red', linewidth=2.5)
        
        # Calculate marker size by take the height of the drawn plot into account
        # First, draw it once to get the figures size
        self.fig.canvas.draw()
        figExtent = self.axesBirdView.get_window_extent()
        # Diameter of the marker in the plot (in meter). This is not really a
        #  meaningful number any more because the whole scaling has become a
        #  bit chaotic and empirical. There is just too much transformation
        #  between svg, matplotlib plot units, pixels and millimeters going on.
        markerDiameter = 35
        # Transform to marker size (in point) ... If we're lucky
        #  1 point = self.fig.dpi / 72 pixels
        markerSize = figExtent.height / (2*yLim / markerDiameter) * 72./self.fig.dpi
        # Vertical shift of poles that are not in the center (in meter)
        #  The 0.05 is also empirical...
        posShiftVertical = 0.05 * self.axesBirdView.axes.get_ylim()[1]*2
        # Halo effect around markers and north arrow for better readability
        haloEffect = [pe.withStroke(linewidth=3, foreground="white")]

        # Draw bird view markers
        defaultCircle: BirdViewSymbol = self.birdViewMarkers['default']
        for pole in poles:
            # Special symbol for option 'flach'
            if pole['abspann'] == 'flach':
                symbol: BirdViewSymbol = self.birdViewMarkers['dreizackiger_stern']
            elif pole['category']:
                symbol: BirdViewSymbol = self.birdViewMarkers[pole['category']]
            else:
                symbol: BirdViewSymbol = defaultCircle
            
            # Mirror symbol depending on whether pole is facing start or end
            #  and if it's left or right of cable
            if pole['abspann'] == 'anfang' and pole['position'] == 'rechts':
                # Mirror symbol on x and y-axis
                marker = symbol.mirror('xy')
            elif pole['abspann'] == 'anfang':
                # Mirror symbol on y-axis
                marker = symbol.mirror('y')
            elif pole['position'] == 'rechts':
                # Mirror symbol on x-axis
                marker = symbol.mirror('x')
            else:
                marker = symbol.mplPath
                
            # Move marker a bit up/or down depending on pole position
            yPos = 0
            if pole['position'] == 'links':
                yPos += posShiftVertical
            elif pole['position'] == 'rechts':
                yPos -= posShiftVertical
            
            # Plot the marker
            self.axesBirdView.plot(pole['d'], yPos, marker=marker,
                                   markersize=symbol.scale * markerSize,
                                   color=symbol.color, path_effects=haloEffect)
            # Add a brown center point where needed
            if symbol.centerPoint:
                self.axesBirdView.plot(pole['d'], yPos, marker=defaultCircle.mplPath,
                                       markersize=defaultCircle.scale * markerSize,
                                       color=defaultCircle.color, path_effects=haloEffect)
        
        # Add north arrow
        yMin, yMax = self.axesBirdView.get_ylim()
        xMin, xMax = self.axesBirdView.get_xlim()
        # Label font size for north arrow is fixed to 30
        labelSize = 25
        # Place arrow in upper right corner, with distance in points
        baseShiftInPointsY = 45
        baseShiftInPointsX = 40
        # Calculate shift in plot units
        labelXShift = (baseShiftInPointsX / figExtent.width) * (xMax - xMin)
        labelYShift = (baseShiftInPointsY / figExtent.height) * (yMax - yMin)
        self.axesBirdView.text(xMax - labelXShift, yMax - labelYShift,  s='➸',
                               fontsize=labelSize, color='black', ha='center',
                               va='center', rotation=degrees(azimut),
                               rotation_mode='anchor', path_effects=haloEffect)
        # Add title and axis labels
        self.layoutBirdViewForPrint()
        
        return self.axesBirdView.get_xlim(), self.axesBirdView.get_ylim()
    
    def layoutBirdViewForPrint(self):
        # Show ticks
        self.axesBirdView.tick_params(labelsize=8, labeltop=False, labelbottom=False)
        self.axesBirdView.ticklabel_format(style='plain', useOffset=False)
        self.axesBirdView.tick_params(axis="both", which="major", direction="inout",
                              length=5, width=1, bottom=False, top=True,
                              left=True, right=False)
        self.axesBirdView.minorticks_on()
        self.axesBirdView.tick_params(which="minor", direction="inout",
                                      bottom=False, top=True, left=False, right=False)
        # Add grid
        self.axesBirdView.grid(which='major', axis='x', lw=0.5)
        self.axesBirdView.grid(which='minor', axis='x', lw=0.5, linestyle=':')

    def addBackgroundMap(self, imgPath):
        xMin, xMax = self.axesBirdView.get_xlim()
        yMin, yMax = self.axesBirdView.get_ylim()
        img = imread(imgPath)
        self.axesBirdView.imshow(img, aspect='equal', extent=[xMin, xMax, yMin, yMax])

    def exportPdf(self, fileLocation):
        self.fig.tight_layout(pad=2)
        self.print_figure(fileLocation, self.dpi, facecolor='white')

    def setToolbar(self, tbar):
        self.tbar = tbar
    
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


def calculatePlotDimensions(xData, yData):
    # Landscape A4 dimensions
    width, height = 11.69, 8.27  # A4 dimensions in inch
    # Define height to width ratio and reduce it by 4% to make up for empty
    #  space between subplots
    pageHeightRatio = (height / width) * 0.96
    
    # Data ranges
    data_xlow = np.min(xData)
    data_xhi = np.max(xData)
    data_ylow = np.min(yData)
    # Add another 40 m because there will be poles and labels
    data_yhi = np.max(yData) + 40
    ratio = (data_yhi - data_ylow) / 60
    
    # Height to width ration of data
    dataHeightRatio = (data_yhi - data_ylow) / (data_xhi - data_xlow)

    # If the data does not fit on the landscape page, we turn the page to portrait
    if dataHeightRatio > pageHeightRatio:
        height, width = 11.69, 8.27
        ratio = (data_yhi - data_ylow) / 60
        
    return width, height, ratio


def saveImgAsPdfWithMpl(imgPath, savePath, dpi=300):
    """ Loads an image into a plot and saves it as a pdf. This is a workaround
    to be able to save PDF without an additional library."""
    height, width = 11.69, 8.27  # A4 dimensions in inch
    fig = Figure(figsize=(width, height), dpi=dpi)
    axis = fig.add_subplot(111)
    img = imread(imgPath)
    axis.imshow(img, aspect='equal')
    # Remove axis ticks
    axis.tick_params(axis="both", which="both", bottom=False, top=False,
                     left=False, right=False)
    # Remove axis labels
    axis.xaxis.set_ticklabels([])
    axis.yaxis.set_ticklabels([])
    # Save to pdf
    canvas = FigureCanvas(fig)
    canvas.print_figure(savePath, dpi, facecolor='white')
    
