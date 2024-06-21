from typing import List
import numpy as np
from math import floor
from copy import deepcopy
from qgis.PyQt.QtCore import QCoreApplication

from SEILAPLAN.gui.adjustmentPlot import PlotMarker
from SEILAPLAN.gui.adjustmentDialog_thresholds import AdjustmentDialogThresholds


class ThresholdUpdater:
    
    def __init__(self, layout: AdjustmentDialogThresholds, updateCallback):
        self.layout: AdjustmentDialogThresholds = layout
        self.callback = updateCallback
        self.items: List[ThresholdItem] = []
        self.poles = None
        self.profile = None
        self.tblHeader = [
            '',
            self.tr('Kennwert'),
            self.tr('Grenzwert'),
            self.tr('Optimierte Loesung'),
            self.tr('Aktuelle Loesung')
        ]

    def update(self, resultData, params, poles, profile, resultFromOptimization):
        self.poles = poles
        self.profile = profile
        firstRun = False
    
        if not self.items:
            # Create threshold item objects
            self.initThresholdItems(params)
            firstRun = True
        
        self.setThreshold(params)
        
        for item in self.items:
            item.reset()
            item.isOpti = resultFromOptimization
            # Calculate new extrema
            self.checkThreshold(item, resultData)
        
        # Update layout with new extrema
        if firstRun:
            self.layout.initTableGrid(self.tblHeader, len(self.items))
        
        tblData = [item.getDataRow() for item in self.items]
        self.layout.updateData(tblData, firstRun)
        # Update cell color
        for row, item in enumerate(self.items):
            self.layout.colorBackground(row, item.getColumnIndexToColor(), item.getMaxColor())
        
        # Update warn icon of the tap title
        self.layout.updateTabIcon(any([item.exceedsThreshold for item in self.items]))
    
        self.callback()
    
    def setThreshold(self, params):
        for item in self.items:
            if item.id == 'bodenabstand':
                item.threshold = params.getParameter('Bodenabst_min')
            if item.id == 'seilzugkraft':
                item.threshold = params.getParameter('zul_SK')
            if item.id == 'sattelkraft':
                item.threshold = None
            if item.id == 'lastseilknickwinkel':
                item.threshold = [30, 60]
            if item.id == 'leerseilknickwinkel':
                item.threshold = [1, 3]

    def initThresholdItems(self, params):
        # Define thresholds that should be checked
        bodenabst = ThresholdItem(
            ident='bodenabstand',
            name=self.tr('Minimaler Bodenabstand'),
            unit=params.params['Bodenabst_min']['unit'],
            description={
              'title': self.tr('Minimaler Bodenabstand'),
              'message': self.tr('Es wird der im Parameterset definierte minimale Bodenabstand mit einer Aufloesung von 1m getestet.'),
            },
        )
        seilzugkraft = ThresholdItem(
            ident='seilzugkraft',
            name=self.tr('Max. auftretende Seilzugkraft'),
            unit=params.params['SK']['unit'],
            description={
                'title': self.tr('Max. auftretende Seilzugkraft'),
                'message': self.tr('Es wird die maximal auftretende Seilzugkraft am Lastseil mit der Last in Feldmitte berechnet.'),
            },
        )
        sattelkraft = ThresholdItem(
            ident='sattelkraft',
            name=self.tr('Max. resultierende Sattelkraft'),
            unit=params.params['SK']['unit'],
            description={
                'title': self.tr('Max. resultierende Sattelkraft'),
                'message': self.tr('Es wird die maximal resultierende Sattelkraft an befahrbaren Stuetzen mit der Last auf der Stuetze berechnet.'),
            },
        )
        lastseilknickwinkel = ThresholdItem(
            ident='lastseilknickwinkel',
            name=self.tr('Max. Lastseilknickwinkel'),
            unit='°',
            description={
                'title': self.tr('Max. Lastseilknickwinkel'),
                'message': self.tr('Groessere Knickwinkel reduzieren die Bruchlast des Tragseils und fuehren zu hoeheren Sattelkraeften.'),
            },
        )
        leerseilknickwinkel = ThresholdItem(
            ident='leerseilknickwinkel',
            name=self.tr('Min. Leerseilknickwinkel'),
            unit='°',
            description={
                'title': self.tr('Min. Leerseilknickwinkel'),
                'message': self.tr('Bei Knickwinkeln unter 2 besteht die Gefahr, dass das Tragseil beim Sattel abhebt (rot). Bei Knickwinkeln zwischen 2 und 4 muss das Tragseil mittels Niederhaltelasche gesichert werden (orange).'),
            },
        )
        self.items = [bodenabst, seilzugkraft, sattelkraft, lastseilknickwinkel, leerseilknickwinkel]

    def checkThreshold(self, item, resultData):
        item: ThresholdItem
        
        # Ground clearance
        if item.id == 'bodenabstand':
            data = resultData['cableline']['groundclear_rel']
            if np.isnan(data).all():
                return
            item.currentExtrema = np.nanmin(data)
            # Replace nan so there is no Runtime Warning in np.argwhere()
            localCopy = np.copy(data)
            localCopy[np.isnan(localCopy)] = 100.0
            # Check where the minimal ground clearance is located
            xLocations = np.ravel(np.argwhere(localCopy == item.currentExtrema))
            # Check if min value is smaller than ground clearance
            if item.currentExtrema < item.threshold:
                item.exceedsThreshold = True
            for x in xLocations:
                z = self.getZCoordinateFromTerrain(x)
                item.createPlotMarker(localCopy[x], int(x + self.poles.firstPole['d']), z)
            
    
        # Max force on cable
        elif item.id == 'seilzugkraft':
            maxCableForce = resultData['force']['MaxSeilzugkraft'][0]           # Max force on cable
            item.currentExtrema = np.nanmax(maxCableForce)
            for fieldIdx, maxValPerField in enumerate(maxCableForce):
                # NAN values will be ignored
                if np.isnan(maxValPerField):
                    continue
                if maxValPerField > item.threshold:
                    item.exceedsThreshold = True
                # Force is calculated in the middle of the field, so
                #  marker should also be in the middle between two poles
                leftPole = self.poles.poles[self.poles.idxA + fieldIdx]['d']
                rightPole = self.poles.poles[self.poles.idxA + fieldIdx + 1]['d']
                x = int(leftPole + floor((rightPole - leftPole) / 2))
                z = self.getZCoordinateFromTerrain(x)
                item.createPlotMarker(maxValPerField, x, z)
            
            # Add a special threshold for the value at the highest point
            forceAtHighestPoint = resultData['force']['MaxSeilzugkraft_L'][0]   # Cable force at highest point
            plotLabel = self.tr('am hoechsten Punkt:') + '\n' + item.formatValue(forceAtHighestPoint)
            xHighest, zHighest = self.poles.getHighestPole()
            color = 1  # ok
            if forceAtHighestPoint > item.threshold:
                color = 3  # red
            item.createPlotMarker(plotLabel, xHighest, zHighest, color, 'top')
    
        elif item.id == 'sattelkraft':
            # TODO Remove
            data = resultData['force']['Sattelkraft_Total'][0],  # Max force on pole
            localCopy = np.nan_to_num(data)
            item.currentExtrema = np.max(localCopy)
            for poleIdx, calcVal in enumerate(data[0]):
                pole = self.poles.poles[self.poles.idxA + poleIdx]
                if not np.isnan(calcVal):
                    item.createPlotMarker(calcVal, pole['d'], pole['z'])
    
        # Lastseilknickwinkel
        elif item.id == 'lastseilknickwinkel':
            data = resultData['force']['Lastseilknickwinkel'],  # Cable angle on pole
            if np.all(np.isnan(data)):
                return
            maxValArr = [np.nan, np.nan]
            # Loop through all angles and test poles in between start and end
            #   with threshold 1, start and end pole with threshold 2
            for poleIdx, angle in enumerate(data[0]):
                # NAN values will be ignored
                if np.isnan(angle):
                    continue
                color = 1  # ok
                # Test first and last pole of optimization with second threshold
                if poleIdx + self.poles.idxA in [self.poles.idxA, self.poles.idxE]:
                    # Check if current value is new max value
                    if not np.all(np.isnan([maxValArr[1], angle])):
                        maxValArr[1] = np.nanmax([maxValArr[1], angle])
                    # Check if angle is higher than second threshold
                    if angle > item.threshold[1]:
                        color = 3  # red
                        item.exceedsThreshold = True
                else:
                    # Check if current value is new max value
                    if not np.all(np.isnan([maxValArr[0], angle])):
                        maxValArr[0] = np.nanmax([maxValArr[0], angle])
                    if angle > item.threshold[0]:
                        color = 3  # red
                        item.exceedsThreshold = True
                
                item.currentExtrema = maxValArr
                pole = self.poles.poles[self.poles.idxA + poleIdx]
                item.createPlotMarker(angle, pole['d'], pole['z'], color)
    
        # Leerseilknickwinkel
        elif item.id == 'leerseilknickwinkel':
            data = resultData['force']['Leerseilknickwinkel'],  # Cable angle on pole
            if np.all(np.isnan(data)):
                return
            # Get lowest value, ignore any nan values
            item.currentExtrema = np.nanmin(data)
            # Loop through all angles and test poles with thresholds
            for poleIdx, angle in enumerate(data[0]):
                # NAN values will be ignored
                if np.isnan(angle):
                    continue
                color = 1  # ok
                # Angle under first threshold (1 to 3 degrees -> error level 'attention')
                if angle < item.threshold[1]:
                    color = 2  # orange
                    # Angle under second threshold
                    if angle < item.threshold[0]:
                        color = 3
                        item.exceedsThreshold = True
                
                pole = self.poles.poles[self.poles.idxA + poleIdx]
                item.createPlotMarker(angle, pole['d'], pole['z'], color)
        
        if item.isOpti:
            item.optiExtrema = deepcopy(item.currentExtrema)
        
        return item
    
    def getZCoordinateFromTerrain(self, xLocation):
        return self.profile.zi_disp[np.argwhere(self.profile.di_disp == xLocation)[0][0]]

    # noinspection PyMethodMayBeStatic
    def tr(self, message, **kwargs):
        return QCoreApplication.translate(type(self).__name__, message)


class ThresholdItem(object):
    
    def __init__(self, ident, name, unit, description):
        self.id = ident
        self.name = name
        self.unit = unit
        self.description = description
        
        self.threshold = None
        self.optiExtrema = None
        self.currentExtrema = None
        self.isOpti = False
        self.exceedsThreshold = False
        
        # Information for plotting
        self.plotMarkers: List[PlotMarker] = []
    
    def getFormatedValue(self, val):
        if isinstance(val, list):
            return ' / '.join([self.formatValue(maxVal) for maxVal in val])
        else:
            return self.formatValue(val)
    
    def formatValue(self, val):
        if isinstance(val, float) and not np.isnan(val):
            return f"{round(val, 1)} {self.unit}"
        elif isinstance(val, int):
            return f"{val} {self.unit}"
        else:
            return '-'
    
    def createPlotMarker(self, label, x, z, color=None, alignment='bottom'):
        if not isinstance(label, str):
            label = self.formatValue(label)
        if not color:
            color = 3 if self.exceedsThreshold else 1
        self.plotMarkers.append(PlotMarker(label, x, z, color, alignment))
    
    def getMaxColor(self):
        return max([marker.color for marker in self.plotMarkers] or [1])
        
    def getDataRow(self):
        if self.isOpti:
            return [self.description, self.name,
                    self.getFormatedValue(self.threshold),
                    self.getFormatedValue(self.optiExtrema), None]
        else:
            return [self.description, self.name,
                    self.getFormatedValue(self.threshold),
                    self.getFormatedValue(self.optiExtrema),
                    self.getFormatedValue(self.currentExtrema)]
    
    def getColumnIndexToColor(self):
        if self.isOpti:
            # When this value stems from the optimization, it's the fourth column
            return 3
        else:
            # When this value stems from a recalculations, it's the fifth column
            return 4
        
    def reset(self):
        self.currentExtrema = None
        self.isOpti = False
        self.exceedsThreshold = False
        self.plotMarkers = []


