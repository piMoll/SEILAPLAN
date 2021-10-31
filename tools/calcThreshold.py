import numpy as np
from math import floor
from qgis.PyQt.QtCore import QCoreApplication


class ThresholdUpdater:
    
    def __init__(self, layout, tblSize, updateCallback):
        self.layout = layout
        self.tblSize = tblSize
        self.callback = updateCallback
        self.rows = [['' for cell in range(self.tblSize[1])]
                     for row in range(self.tblSize[0])]
        self.plotLabels = []
        self.thresholds = []
        self.units = []
        self.poles = None

    def update(self, resultData, params, poles, noOpti):
        self.poles = poles
    
        if not self.thresholds:
            # Fill table with initial data
            self.initTableData(resultData, params, noOpti)
    
        else:
            # Cable was recalculated, update threshold values
            self.plotLabels = []
        
            # Check if Bodenabst_min was changed
            newBodenAbst = params.getParameter(
                'Bodenabst_min')
            if newBodenAbst != self.thresholds[0]:
                self.thresholds[0] = newBodenAbst
                self.rows[0][
                    2] = f"{newBodenAbst} {self.units[0]}"
                self.layout.updateData(0, 2,
                                       self.rows[0][2])
        
            # Update threshold for max. Seilzugkraft, this value is changed
            #  when altering parameter MBK, which updates zul_SK
            newZulSK = params.getParameter('zul_SK')
            if newZulSK != self.thresholds[1]:
                # Update threshold
                self.thresholds[1] = newZulSK
                # Update label
                self.rows[1][
                    2] = f"{newZulSK} {self.units[1]}"
                self.layout.updateData(1, 2,
                                       self.rows[1][2])
        
            for i in range(len(self.rows)):
                thresholdData = self.checkThresholds(i, resultData[i])
                val = ''
                color = [1]
                location = []
                plotLabels = []
                if len(thresholdData) == 4:
                    val, location, color, plotLabels = thresholdData
                self.layout.updateData(i, 4, val)
                self.layout.updateData(i, 5, {'loc': location, 'color': color})
                self.rows[i][4] = val
                self.rows[i][5] = {'loc': location, 'color': color}
                self.plotLabels.append(plotLabels)
    
        self.callback()

    def initTableData(self, resultData, params, noOpti):
        self.units = [
            params.params['Bodenabst_min']['unit'],
            params.params['SK']['unit'],
            params.params['SK']['unit'],
            '°',
            '°'
        ]
        # These are the thresholds we have to compare the received data with
        self.thresholds = [
            params.getParameter('Bodenabst_min'),
            float(params.getParameter('zul_SK')),
            None,
            [30, 60],
            [1, 3],
        ]
        tblHeader = [
            '',
            self.tr('Kennwert'),
            self.tr('Grenzwert'),
            self.tr('Optimierte Loesung'),
            self.tr('Aktuelle Loesung'),
            self.tr('Wo?')
        ]
        
        # Define data that is displayed in first three columns of threshold table
        self.rows[0][0:3] = [
            {
                'title': self.tr('Minimaler Bodenabstand'),
                'message': self.tr('Es wird der im Parameterset definierte minimale Bodenabstand mit einer Aufloesung von 1m getestet.'),
            },
            self.tr('Minimaler Bodenabstand'),
            f"{params.getParameterAsStr('Bodenabst_min')} {params.params['Bodenabst_min']['unit']}",
        ]
        self.rows[1][0:3] = [
            {
                'title': self.tr('Max. auftretende Seilzugkraft'),
                'message': self.tr('Es wird die maximal auftretende Seilzugkraft am Lastseil mit der Last in Feldmitte berechnet.'),
            },
            self.tr('Max. auftretende Seilzugkraft'),
            f"{params.getParameter('zul_SK')} {params.params['SK']['unit']}",
        ]
        self.rows[2][0:3] = [
            {
                'title': self.tr('Max. resultierende Sattelkraft'),
                'message': self.tr('Es wird die maximal resultierende Sattelkraft an befahrbaren Stuetzen mit der Last auf der Stuetze berechnet.'),
            },
            self.tr('Max. resultierende Sattelkraft'),
            '-',
        ]
        self.rows[3][0:3] = [
            {
                'title': self.tr('Max. Lastseilknickwinkel'),
                'message': self.tr('Groessere Knickwinkel reduzieren die Bruchlast des Tragseils und fuehren zu hoeheren Sattelkraeften.'),
            },
            self.tr('Max. Lastseilknickwinkel'),
            '30 / 60 °'
        ]
        self.rows[4][0:3] = [
            {
                'title': self.tr('Min. Leerseilknickwinkel'),
                'message': self.tr('Bei Knickwinkeln unter 2 besteht die Gefahr, dass das Tragseil beim Sattel abhebt (rot). Bei Knickwinkeln zwischen 2 und 4 muss das Tragseil mittels Niederhaltelasche gesichert werden (orange).'),
            },
            self.tr('Min. Leerseilknickwinkel'),
            '1 ; 3 °'
        ]

        # Where to put the current threshold values
        valColumn = 3
        emptyColumn = 4
        if noOpti:
            # No optimization was run, so no optimal solution
            valColumn = 4
            emptyColumn = 3
    
        for i in range(self.tblSize[0]):
            thresholdData = self.checkThresholds(i, resultData[i])
            val = ''
            color = [1]
            location = []
            plotLabels = []
            if len(thresholdData) == 4:
                val, location, color, plotLabels = thresholdData
            self.rows[i][valColumn] = val
            self.rows[i][emptyColumn] = ''
            self.rows[i][5] = {'loc': location, 'color': color}
            self.plotLabels.append(plotLabels)
    
        self.layout.populate(tblHeader, self.rows, valColumn)

    def checkThresholds(self, idx, data):
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
            color = 1  # ok
            maxVal = np.nanmin(data)
            # Replace nan so there is no Runtime Warning in np.argwhere()
            localCopy = np.copy(data)
            localCopy[np.isnan(localCopy)] = 100.0
            # Check where the minimal ground clearance is located
            location = np.ravel(np.argwhere(localCopy == maxVal))
            if location:
                plotLabel = [self.formatThreshold(loc, idx) for loc in localCopy[location]]
            location = [int(loc + self.poles.firstPole['d']) for loc in location]
            # Check if min value is smaller than ground clearance
            if maxVal < self.thresholds[idx]:
                color = 3  # red
            colorList = [color] * len(location)
    
        # Max force on cable
        elif idx == 1:
            maxVal = np.nanmax(data)
            for fieldIdx, force in enumerate(data):
                # NAN values will be ignored
                if np.isnan(force):
                    continue
                color = 1  # ok
                if force > self.thresholds[idx]:
                    color = 3  # red
                plotLabel.append(self.formatThreshold(force, idx))
                # Force is calculated in the middle of the field, so
                #  marker should also be in the middle between two poles
                leftPole = self.poles.poles[self.poles.idxA + fieldIdx]['d']
                rightPole = self.poles.poles[self.poles.idxA + fieldIdx + 1]['d']
                location.append(int(leftPole + floor((rightPole - leftPole) / 2)))
                colorList.append(color)
    
        elif idx == 2:
            localCopy = np.nan_to_num(data)
            maxVal = np.max(localCopy)
            for poleIdx, calcVal in enumerate(data):
                pole = self.poles.poles[self.poles.idxA + poleIdx]
                if not np.isnan(calcVal):
                    location.append(pole['d'])
                    plotLabel.append(self.formatThreshold(calcVal, idx))
                    colorList.append(1)  # ok
    
        # Lastseilknickwinkel
        elif idx == 3 and not np.all(np.isnan(data)):
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
                    if angle > self.thresholds[idx][1]:
                        color = 3  # red
                else:
                    # Check if current value is new max value
                    if not np.all(np.isnan([maxValArr[0], angle])):
                        maxValArr[0] = np.nanmax([maxValArr[0], angle])
                    if angle > self.thresholds[idx][0]:
                        color = 3  # red
            
                pole = self.poles.poles[self.poles.idxA + poleIdx]
                location.append(pole['d'])
                plotLabel.append(self.formatThreshold(angle, idx))
                colorList.append(color)
            # Format the two max values
            valStr = ' / '.join([self.formatThreshold(maxVal, idx) for maxVal in maxValArr])
    
        # Leerseilknickwinkel
        elif idx == 4 and not np.all(np.isnan(data)):
            # Get lowest value, ignore any nan values
            maxVal = np.nanmin(data)
            # Loop through all angles and test poles with thresholds
            for poleIdx, angle in enumerate(data):
                # NAN values will be ignored
                if np.isnan(angle):
                    continue
                color = 1  # ok
                # Angle under first threshold (1 to 3 degrees -> error level 'attention')
                if angle < self.thresholds[idx][1]:
                    color = 2  # orange
                    # Angle under second threshold
                    if angle < self.thresholds[idx][0]:
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
            return f"{round(val, 1)} {self.units[idx]}"
        else:
            return '-'

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
