import numpy as np
from math import floor


class ThresholdUpdater:
    def __init__(self):
        pass

    def update(self):
        resultData = [
            self.cableline['groundclear_rel'],  # Distance cable - terrain
            self.result['force']['MaxSeilzugkraft'][0],  # Max force on cable
            self.result['force']['Sattelkraft_Total'][0],  # Max force on pole
            self.result['force']['Lastseilknickwinkel'],  # Cable angle on pole
            self.result['force']['Leerseilknickwinkel'],  # Cable angle on pole
        ]
    
        if not self.thData:
            # Fill table with initial data
            self.initThresholdData(resultData)
    
        else:
            # Cable was recalculated, update threshold values
            self.thData['plotLabels'] = []
        
            # Check if Bodenabst_min was changed
            newBodenAbst = self.confHandler.params.getParameter(
                'Bodenabst_min')
            if newBodenAbst != self.thData['thresholds'][0]:
                self.thData['thresholds'][0] = newBodenAbst
                self.thData['rows'][0][
                    2] = f"{newBodenAbst} {self.thData['units'][0]}"
                self.thresholdLayout.updateData(0, 2,
                                                self.thData['rows'][0][2])
        
            # Update threshold for max. Seilzugkraft, this value is changed
            #  when altering parameter MBK, which updates zul_SK
            newZulSK = self.confHandler.params.getParameter('zul_SK')
            if newZulSK != self.thData['thresholds'][1]:
                # Update threshold
                self.thData['thresholds'][1] = newZulSK
                # Update label
                self.thData['rows'][1][
                    2] = f"{newZulSK} {self.thData['units'][1]}"
                self.thresholdLayout.updateData(1, 2,
                                                self.thData['rows'][1][2])
        
            for i in range(len(self.thData['rows'])):
                thresholdData = self.checkThresholdAndLocation(i,
                                                               resultData[i])
                val = ''
                color = [1]
                location = []
                plotLabels = []
                if len(thresholdData) == 4:
                    val, location, color, plotLabels = thresholdData
                self.thresholdLayout.updateData(i, 4, val)
                self.thresholdLayout.updateData(i, 5, {'loc': location,
                                                       'color': color})
                self.thData['rows'][i][4] = val
                self.thData['rows'][i][5] = {'loc': location, 'color': color}
                self.thData['plotLabels'].append(plotLabels)
    
        self.showThresholdInPlot()

    def initThresholdData(self, resultData):
        params = self.confHandler.params
        rows = [['' for cell in range(self.thSize[1])]
                for row in range(self.thSize[0])]
        header = [
            '',
            self.tr('Kennwert'),
            self.tr('Grenzwert'),
            self.tr('Optimierte Loesung'),
            self.tr('Aktuelle Loesung'),
            self.tr('Wo?')
        ]
        infoText = [
            {
                'title': self.tr('Minimaler Bodenabstand'),
                'message': self.tr(
                    'Es wird der im Parameterset definierte minimale Bodenabstand mit einer Aufloesung von 1m getestet.'),
            },
            {
                'title': self.tr('Max. auftretende Seilzugkraft'),
                'message': self.tr(
                    'Es wird die maximal auftretende Seilzugkraft am Lastseil mit der Last in Feldmitte berechnet.'),
            },
            {
                'title': self.tr('Max. resultierende Sattelkraft'),
                'message': self.tr(
                    'Es wird die maximal resultierende Sattelkraft an befahrbaren Stuetzen mit der Last auf der Stuetze berechnet.'),
            },
            {
                'title': self.tr('Max. Lastseilknickwinkel'),
                'message': self.tr(
                    'Groessere Knickwinkel reduzieren die Bruchlast des Tragseils und fuehren zu hoeheren Sattelkraeften.'),
            },
            {
                'title': self.tr('Min. Leerseilknickwinkel'),
                'message': self.tr(
                    'Bei Knickwinkeln unter 2 besteht die Gefahr, dass das Tragseil beim Sattel abhebt (rot). Bei Knickwinkeln zwischen 2 und 4 muss das Tragseil mittels Niederhaltelasche gesichert werden (orange).'),
            },
        ]
    
        units = [
            params.params['Bodenabst_min']['unit'],
            params.params['SK']['unit'],
            params.params['SK']['unit'],
            '°',
            '°'
        ]
        thresholds = [
            params.getParameter('Bodenabst_min'),
            float(params.getParameter('zul_SK')),
            None,
            [30, 60],
            [1, 3],
        ]
        self.thData = {
            'header': header,
            'rows': rows,
            'units': units,
            'thresholds': thresholds,
            'plotLabels': []
        }
        label = [
            self.tr('Minimaler Bodenabstand'),
            self.tr('Max. auftretende Seilzugkraft'),
            self.tr('Max. resultierende Sattelkraft'),
            self.tr('Max. Lastseilknickwinkel'),
            self.tr('Min. Leerseilknickwinkel')
        ]
        thresholdStr = [
            f"{params.getParameterAsStr('Bodenabst_min')} {units[0]}",
            f"{params.getParameter('zul_SK')} {units[1]}",
            '-',
            '30 / 60 °',
            '1 ; 3 °'
        ]
        # Where to put the current threshold values
        valColumn = 3
        emptyColumn = 4
        if self.status in ['jumpedOver', 'savedFile']:
            # No optimization was run, so no optimal solution
            valColumn = 4
            emptyColumn = 3
    
        for i in range(self.thSize[0]):
            thresholdData = self.checkThresholdAndLocation(i, resultData[i])
            val = ''
            color = [1]
            location = []
            plotLabels = []
            if len(thresholdData) == 4:
                val, location, color, plotLabels = thresholdData
            self.thData['rows'][i][0] = infoText[i]
            self.thData['rows'][i][1] = label[i]
            self.thData['rows'][i][2] = thresholdStr[i]
            self.thData['rows'][i][valColumn] = val
            self.thData['rows'][i][emptyColumn] = ''
            self.thData['rows'][i][5] = {'loc': location, 'color': color}
            self.thData['plotLabels'].append(plotLabels)
    
        self.thresholdLayout.populate(header, self.thData['rows'], valColumn)

    def checkThresholdAndLocation(self, idx, data):
        maxVal = None
        # Formatted value to insert into threshold table
        valStr = ""
        # Location in relation to origin on horizontal axis (needed for
        #  plotting)
        location = []
        # Color of marked threshold
        colorList = []
        # Formatted threshold value to show in plot
        plotLabel = []
    
        # Ground clearance
        if idx == 0:
            if np.isnan(data).all():
                return valStr, location
            color = 1  # neutral
            maxVal = np.nanmin(data)
            # Replace nan so there is no Runtime Warning in np.argwhere()
            localCopy = np.copy(data)
            localCopy[np.isnan(localCopy)] = 100.0
            # Check where the minimal ground clearance is located
            location = np.ravel(np.argwhere(localCopy == maxVal))
            if location:
                plotLabel = [self.formatThreshold(loc, idx) for loc in
                             localCopy[location]]
            location = [int(loc + self.poles.firstPole['d']) for loc in
                        location]
            # Check if min value is smaller than ground clearance
            if maxVal < self.thData['thresholds'][idx]:
                color = 3  # red
            colorList = [color] * len(location)
    
        # Max force on cable
        elif idx == 1:
            maxVal = np.nanmax(data)
            for fieldIdx, force in enumerate(data):
                # NAN values will be ignored
                if np.isnan(force):
                    continue
                color = 1  # neutral
                if force > self.thData['thresholds'][idx]:
                    color = 3  # red
                plotLabel.append(self.formatThreshold(force, idx))
                # Force is calculated in the middle of the field, so
                #  marker should also be in the middle between two poles
                leftPole = self.poles.poles[self.poles.idxA + fieldIdx]['d']
                rightPole = self.poles.poles[self.poles.idxA + fieldIdx + 1][
                    'd']
                location.append(
                    int(leftPole + floor((rightPole - leftPole) / 2)))
                colorList.append(color)
    
        elif idx == 2:
            localCopy = np.nan_to_num(data)
            maxVal = np.max(localCopy)
            for poleIdx, calcVal in enumerate(data):
                pole = self.poles.poles[self.poles.idxA + poleIdx]
                if not np.isnan(calcVal):
                    location.append(pole['d'])
                    plotLabel.append(self.formatThreshold(calcVal, idx))
                    colorList.append(1)  # neutral
    
        # Lastseilknickwinkel
        elif idx == 3 and not np.all(np.isnan(data)):
            maxValArr = [np.nan, np.nan]
            # Loop through all angles and test poles in between start and end
            #   with threshold 1, start and end pole with threshold 2
            for poleIdx, angle in enumerate(data):
                # NAN values will be ignored
                if np.isnan(angle):
                    continue
                color = 1  # neutral
                # Test first and last pole of optimization with second threshold
                if poleIdx + self.poles.idxA in [self.poles.idxA,
                                                 self.poles.idxE]:
                    # Check if current value is new max value
                    if not np.all(np.isnan([maxValArr[1], angle])):
                        maxValArr[1] = np.nanmax([maxValArr[1], angle])
                    # Check if angle is higher than second threshold
                    if angle > self.thData['thresholds'][idx][1]:
                        color = 3  # red
                else:
                    # Check if current value is new max value
                    if not np.all(np.isnan([maxValArr[0], angle])):
                        maxValArr[0] = np.nanmax([maxValArr[0], angle])
                    if angle > self.thData['thresholds'][idx][0]:
                        color = 3  # red
            
                pole = self.poles.poles[self.poles.idxA + poleIdx]
                location.append(pole['d'])
                plotLabel.append(self.formatThreshold(angle, idx))
                colorList.append(color)
            # Format the two max values
            valStr = ' / '.join(
                [self.formatThreshold(maxVal, idx) for maxVal in maxValArr])
    
        # Leerseilknickwinkel
        elif idx == 4 and not np.all(np.isnan(data)):
            # Get lowest value, ignore any nan values
            maxVal = np.nanmin(data)
            # Loop through all angles and test poles with thresholds
            for poleIdx, angle in enumerate(data):
                # NAN values will be ignored
                if np.isnan(angle):
                    continue
                color = 1  # neutral
                # Angle under first threshold (1 to 3 degrees -> error level 'attention')
                if angle < self.thData['thresholds'][idx][1]:
                    color = 2  # orange
                    # Angle under second threshold
                    if angle < self.thData['thresholds'][idx][0]:
                        color = 3  # red
            
                pole = self.poles.poles[self.poles.idxA + poleIdx]
                location.append(pole['d'])
                plotLabel.append(self.formatThreshold(angle, idx))
                colorList.append(color)
    
        if isinstance(maxVal, float) and not np.isnan(maxVal):
            valStr = self.formatThreshold(maxVal, idx)
    
        return valStr, location, colorList, plotLabel

    def formatThreshold(self, val, idx):
        if isinstance(val, float) and not np.isnan(val):
            return f"{round(val, 1)} {self.thData['units'][idx]}"
        else:
            return '-'

    def showThresholdInPlot(self, row=None):
        # Click on row was emitted but row is already selected -> deselect
        if row is not None and row == self.selectedThresholdRow:
            # Remove markers from plot
            self.plot.removeMarkers()
            self.selectedThresholdRow = None
            return
        # There was no new selection but a redraw of the table was done, so
        #  current selection has to be added to the plot again
        if row is None:
            if self.selectedThresholdRow is not None:
                row = self.selectedThresholdRow
            # Nothing is selected at the moment
            else:
                return
    
        location = self.thData['rows'][row][5]['loc']
        color = self.thData['rows'][row][5]['color']
        arrIdx = []
        # Get index of horizontal distance so we know which height value to
        #  chose
        for loc in location:
            arrIdx.append(np.argwhere(self.profile.di_disp == loc)[0][0])
        z = self.profile.zi_disp[arrIdx]
    
        self.plot.showMarkers(location, z, self.thData['plotLabels'][row],
                              color)
        self.selectedThresholdRow = row
