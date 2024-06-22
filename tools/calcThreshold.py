from typing import List
import numpy as np
from math import floor
from copy import deepcopy
from qgis.PyQt.QtCore import QCoreApplication

from SEILAPLAN.gui.adjustmentPlot import PlotMarker
from SEILAPLAN.gui.adjustmentDialog_thresholds import AdjustmentDialogThresholds


class ThresholdUpdater:
    
    def __init__(self, layout: AdjustmentDialogThresholds):
        self.layout: AdjustmentDialogThresholds = layout
        # Displayed in the threshold tab
        self.topics: List[PlotTopic] = []
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
    
        if not self.topics:
            # Create threshold item objects
            self.initThresholdItems(params)
            firstRun = True
        
        self.setThreshold(params)
        
        for topic in self.topics:
            topic.reset()
            topic.isOpti = resultFromOptimization
            # Calculate new extrema
            self.checkThreshold(topic, resultData)
        
        # Update layout with new extrema
        if firstRun:
            self.layout.initTableGrid(self.tblHeader, len(self.getThresholdTopics()))
        
        tblData = [item.getDataRow() for item in self.getThresholdTopics()]
        self.layout.updateData(tblData, firstRun)
        # Update cell color
        for row, topic in enumerate(self.getThresholdTopics()):
            self.layout.colorBackground(row, topic.getColumnIndexToColor(), topic.getMaxColor())
        
        # Update warn icon of the tap title
        self.layout.updateTabIcon(any([item.exceedsThreshold for item in self.getThresholdTopics()]))
    
    def setThreshold(self, params):
        for topic in self.topics:
            if topic.id == 'bodenabstand':
                topic.threshold = params.getParameter('Bodenabst_min')
            if topic.id == 'seilzugkraft':
                topic.threshold = params.getParameter('zul_SK')
            if topic.id == 'lastseilknickwinkel':
                topic.threshold = [30, 60]
            if topic.id == 'leerseilknickwinkel':
                topic.threshold = [1, 3]

    def initThresholdItems(self, params):
        # Define thresholds that should be checked
        bodenabst = PlotTopic(
            ident='bodenabstand',
            name=self.tr('Minimaler Bodenabstand'),
            unit=params.params['Bodenabst_min']['unit'],
            description={
              'title': self.tr('Minimaler Bodenabstand'),
              'message': self.tr('Es wird der im Parameterset definierte minimale Bodenabstand mit einer Aufloesung von 1m getestet.'),
            },
        )
        seilzugkraft = PlotTopic(
            ident='seilzugkraft',
            name=self.tr('Max. auftretende Seilzugkraft'),
            unit=params.params['SK']['unit'],
            description={
                'title': self.tr('Max. auftretende Seilzugkraft'),
                'message': self.tr('Es wird die maximal auftretende Seilzugkraft am Lastseil mit der Last in Feldmitte berechnet.'),
            },
        )
        lastseilknickwinkel = PlotTopic(
            ident='lastseilknickwinkel',
            name=self.tr('Max. Lastseilknickwinkel'),
            unit='°',
            description={
                'title': self.tr('Max. Lastseilknickwinkel'),
                'message': self.tr('Groessere Knickwinkel reduzieren die Bruchlast des Tragseils und fuehren zu hoeheren Sattelkraeften.'),
            },
        )
        leerseilknickwinkel = PlotTopic(
            ident='leerseilknickwinkel',
            name=self.tr('Min. Leerseilknickwinkel'),
            unit='°',
            description={
                'title': self.tr('Min. Leerseilknickwinkel'),
                'message': self.tr('Bei Knickwinkeln unter 2 besteht die Gefahr, dass das Tragseil beim Sattel abhebt (rot). Bei Knickwinkeln zwischen 2 und 4 muss das Tragseil mittels Niederhaltelasche gesichert werden (orange).'),
            },
        )
        # TODO: Translations
        sattelkraft = PlotTopic(
            ident='sattelkraft',
            name=self.tr('Max. resultierende Sattelkraft'),
            unit=params.params['SK']['unit'],
            description={
                'title': self.tr('Max. resultierende Sattelkraft'),
                'message': self.tr('Es wird die maximal resultierende Sattelkraft an befahrbaren Stuetzen mit der Last auf der Stuetze berechnet.'),
            },
        )
        bhd = PlotTopic(
            ident='bhd',
            name=self.tr('BHD'),
            unit='cm',
            description={
                'title': self.tr('BHD'),
                'message': self.tr(''),
            },
        )
        leerseildurchhang = PlotTopic(
            ident='leerseildurchhang',
            name=self.tr('Leerseildurchhang'),
            unit='m',
            description={
                'title': self.tr('Leerseildurchhang'),
                'message': self.tr(''),
            },
        )
        lastseildurchhang = PlotTopic(
            ident='lastseildurchhang',
            name=self.tr('Lastseildurchhang'),
            unit='m',
            description={
                'title': self.tr('Lastseildurchhang'),
                'message': self.tr(''),
            },
        )
        
        self.topics = [bodenabst, seilzugkraft, sattelkraft, bhd, leerseildurchhang, lastseildurchhang, leerseilknickwinkel, lastseilknickwinkel]
    
    def getThresholdTopics(self):
        return [topic for topic in self.topics if topic.threshold is not None]

    def getPlotTopicById(self, ident):
        try:
            return [topic for topic in self.topics if topic.id == ident][0]
        except IndexError:
            return None
    
    def checkThreshold(self, topic, resultData):
        topic: PlotTopic
        
        # Ground clearance
        if topic.id == 'bodenabstand':
            data = resultData['cableline']['groundclear_rel']
            if np.isnan(data).all():
                return
            topic.currentExtrema = np.nanmin(data)
            # Replace nan so there is no Runtime Warning in np.argwhere()
            localCopy = np.copy(data)
            localCopy[np.isnan(localCopy)] = 100.0
            
            d = self.poles.getAsArray()[0]
            for idx, poleDist in enumerate(d[:-1]):
                fieldStartIdx = np.ravel(np.argwhere(resultData['cableline']['groundclear_di'] == int(poleDist)))[0]
                fieldEndIdx = np.ravel(np.argwhere(resultData['cableline']['groundclear_di'] == int(d[idx + 1])))[0]
                # Search for the minimal value in the current cable field
                localMinima = np.nanmin(localCopy[fieldStartIdx:fieldEndIdx])
                # NAN values will be ignored
                if np.isnan(localMinima):
                    continue
                color = 1
                # Check if local minima exceeds threshold
                if localMinima < topic.threshold:
                    topic.exceedsThreshold = True
                    color = 3
                # Check where the minimal ground clearance per field is located
                localMinIdx = np.ravel(np.argwhere(resultData['cableline']['groundclear_rel'][fieldStartIdx:fieldEndIdx] == localMinima))
                xLoc = resultData['cableline']['groundclear_di'][fieldStartIdx:fieldEndIdx][localMinIdx]
                zLoc = resultData['cableline']['groundclear'][fieldStartIdx:fieldEndIdx][localMinIdx]
                for x, z in zip(xLoc, zLoc):
                    topic.createPlotMarker(localMinima, x, z, color)
    
        # Max force on cable
        elif topic.id == 'seilzugkraft':
            maxCableForce = resultData['force']['MaxSeilzugkraft'][0]           # Max force on cable
            topic.currentExtrema = np.nanmax(maxCableForce)
            for fieldIdx, maxValPerField in enumerate(maxCableForce):
                # NAN values will be ignored
                if np.isnan(maxValPerField):
                    continue
                if maxValPerField > topic.threshold:
                    topic.exceedsThreshold = True
                # Force is calculated in the middle of the field, so
                #  marker should also be in the middle between two poles
                x, z = self.getLocationInFieldCenter(fieldIdx)
                topic.createPlotMarker(maxValPerField, x, z)
            
            # Add a special threshold for the value at the highest point
            forceAtHighestPoint = resultData['force']['MaxSeilzugkraft_L'][0]   # Cable force at highest point
            plotLabel = self.tr('am hoechsten Punkt:') + '\n' + topic.formatValue(forceAtHighestPoint)
            xHighest, zHighest = self.poles.getHighestPole()
            color = 1  # ok
            if forceAtHighestPoint > topic.threshold:
                color = 3  # red
            topic.createPlotMarker(plotLabel, xHighest, zHighest, color, 'top')
    
        # Lastseilknickwinkel
        elif topic.id == 'lastseilknickwinkel':
            data = resultData['force']['Lastseilknickwinkel']  # Cable angle on pole
            if np.all(np.isnan(data)):
                return
            maxValArr = [np.nan, np.nan]
            # Loop through all angles and test poles in between start and end
            #   with threshold 1, start and end pole with threshold 2
            for poleIdx, angle in enumerate(data):
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
                    if angle > topic.threshold[1]:
                        color = 3  # red
                        topic.exceedsThreshold = True
                else:
                    # Check if current value is new max value
                    if not np.all(np.isnan([maxValArr[0], angle])):
                        maxValArr[0] = np.nanmax([maxValArr[0], angle])
                    if angle > topic.threshold[0]:
                        color = 3  # red
                        topic.exceedsThreshold = True
                
                topic.currentExtrema = maxValArr
                pole = self.poles.poles[self.poles.idxA + poleIdx]
                topic.createPlotMarker(angle, pole['d'], pole['z'], color)
    
        # Leerseilknickwinkel
        elif topic.id == 'leerseilknickwinkel':
            data = resultData['force']['Leerseilknickwinkel']  # Cable angle on pole
            if np.all(np.isnan(data)):
                return
            # Get lowest value, ignore any nan values
            topic.currentExtrema = np.nanmin(data)
            # Loop through all angles and test poles with thresholds
            for poleIdx, angle in enumerate(data):
                # NAN values will be ignored
                if np.isnan(angle):
                    continue
                color = 1  # ok
                # Angle under first threshold (1 to 3 degrees -> error level 'attention')
                if angle < topic.threshold[1]:
                    color = 2  # orange
                    # Angle under second threshold
                    if angle < topic.threshold[0]:
                        color = 3
                        topic.exceedsThreshold = True
                
                pole = self.poles.poles[self.poles.idxA + poleIdx]
                topic.createPlotMarker(angle, pole['d'], pole['z'], color)
        
        elif topic.id == 'sattelkraft':
            data = resultData['force']['Sattelkraft_Total'][0]  # Max force on pole
            for poleIdx, calcVal in enumerate(data):
                pole = self.poles.poles[self.poles.idxA + poleIdx]
                if not np.isnan(calcVal):
                    topic.createPlotMarker(calcVal, pole['d'], pole['z'])
                
        elif topic.id == 'bhd':
            for i, pole in enumerate(self.poles.poles):
                if not np.isnan(pole['BHD']):
                    topic.createPlotMarker(pole['BHD'], pole['d'], pole['z'])
                
        elif topic.id == 'leerseildurchhang':
            data = resultData['force']['Durchhang'][0]
            for fieldIdx, calcVal in enumerate(data):
                if not np.isnan(calcVal):
                    x, z = self.getLocationInFieldCenter(fieldIdx)
                    topic.createPlotMarker(calcVal, x, z)
                
        elif topic.id == 'lastseildurchhang':
            data = resultData['force']['Durchhang'][1]
            for fieldIdx, calcVal in enumerate(data):
                if not np.isnan(calcVal):
                    x, z = self.getLocationInFieldCenter(fieldIdx)
                    topic.createPlotMarker(calcVal, x, z)
        
        if topic.isOpti:
            topic.optiExtrema = deepcopy(topic.currentExtrema)
        
        return topic
    
    def getZCoordinateFromTerrain(self, xLocation):
        return self.profile.zi_disp[np.argwhere(self.profile.di_disp == xLocation)[0][0]]
    
    def getLocationInFieldCenter(self, fieldIdx):
        leftPole = self.poles.poles[self.poles.idxA + fieldIdx]['d']
        rightPole = self.poles.poles[self.poles.idxA + fieldIdx + 1]['d']
        x = int(leftPole + floor((rightPole - leftPole) / 2))
        z = self.getZCoordinateFromTerrain(x)
        return x, z

    # noinspection PyMethodMayBeStatic
    def tr(self, message, **kwargs):
        return QCoreApplication.translate(type(self).__name__, message)


class PlotTopic(object):
    
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


