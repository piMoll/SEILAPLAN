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
import os
import io
import re
from operator import itemgetter
import traceback
from math import atan2, pi, cos, sin
import time

from qgis.PyQt.QtWidgets import QMessageBox
from qgis.core import QgsPointXY, QgsDistanceArea

from .tool.heightSource import AbstractHeightSource, Raster, SurveyData
from .tool.profile import Profile
from .tool.poles import Poles
from .tool.outputReport import getTimestamp

# Constants
HOMEPATH = os.path.join(os.path.dirname(__file__))


def castToNum(formattedNum):
    if type(formattedNum) in [int, float]:
        return formattedNum
    try:
        num = float(formattedNum.replace("'", ''))
    except (ValueError, AttributeError):
        num = None
    return num


class AbstractConfHandler(object):
    
    def __init__(self):
        self.dialog = None
    
    def setDialog(self, dialog):
        self.dialog = dialog
    
    def onError(self, message=None, title='Fehler'):
        if not message:
            message = traceback.format_exc()
        QMessageBox.information(self.dialog, title, message,
                                QMessageBox.Ok)


# noinspection PyTypeChecker
class ProjectConfHandler(AbstractConfHandler):
    
    heightSource: AbstractHeightSource
    profile: Profile
    poles: Poles

    def __init__(self, params):
        """
        :type params: ParameterConfHandler
        """
        AbstractConfHandler.__init__(self)
        
        self.params = params
        
        # Project data
        self.projectName = None
        self.heightSource = None
        self.heightSourceType = None
        self.points = {
            'A': [None, None],
            'E': [None, None]
        }
        self.coordState = {
            'A': 'yellow',
            'E': 'yellow'
        }
        self.profileLength = None
        self.azimut = None
        self.fixedPoles = {
            'poles': [],
            'HM_fix_d': [],
            'HM_fix_h': []
        }
        self.noPoleSection = []
        
        # TODO: Translate
        self.header = {
            'projectname': 'Projektname',
            'dhm': 'Hoehenmodell',
            'survey': 'Laengsprofil',
            'A': 'Anfangspunkt',
            'E': 'Endpunkt',
            'fixedPoles': 'Fixe Stuetzen',
            'noPoleSection': 'Keine Stuetzen'
        }
        self.profile = None
        self.poles = None
    
    def setConfigFromFile(self, property_name, value):
        if property_name == self.header['projectname']:
            self.setProjectName(value)
        
        elif property_name == self.header['dhm']:
            self.setHeightSource(None, sourceType='dhm', sourcePath=value)
        
        elif property_name == self.header['survey']:
            self.setHeightSource(None, sourceType='survey', sourcePath=value)
        
        elif property_name in [self.header['A'], self.header['E']]:
            point = property_name[0]
            [x, y] = value.split('/')
            self.setPoint(point, [x, y])
        
        elif property_name == self.header['fixedPoles']:
            polesStr = value.split('/')[:-1]
            poleArray = []
            for stue in polesStr:
                [key, values] = stue.split(':')
                [poled, polez, poleh] = [string.strip() for string in
                                         values.split(',')]
                poleArray.append({
                    'd': int(poled),
                    'z': float(polez),
                    'h': float(poleh),
                    'name': key.strip()
                })
            
            self.setFixedPoles(poleArray)
        
        elif property_name == self.header['noPoleSection']:
            sections = value.split(';')
            sectionsArray = []
            for section in sections:
                dist = section.split(' - ')
                if len(dist) == 2:
                    sectionsArray.append([float(s) for s in dist])
            self.setNoPoleSection(sectionsArray)
    
    def getProjectName(self):
        return '' if self.projectName is None else self.projectName
    
    def setProjectName(self, value):
        if not value:
            self.projectName = None
        else:
            self.projectName = value
    
    def generateProjectName(self):
        """ Generate a unique project name."""
        import time
        now = time.time()
        timestamp = time.strftime("%d.%m_%H'%M", time.localtime(now))
        self.projectName = "seilaplan_{}".format(timestamp)
        return self.projectName
    
    def getHeightSourceAsStr(self):
        return self.heightSource.getAsStr()
    
    def setHeightSource(self, layer, sourceType='dhm', sourcePath=None):
        """Raster can be set by providing the QGIS Raster Layer or by giving
        the path to the raster file.
        :param layer: QGIS layer object
        :param sourceType: dhm or survey
        :param sourcePath: path to file
         """
        self.heightSource = None
        self.heightSourceType = None
        srs = None
        if sourceType == 'dhm':
            srs = Raster(layer, sourcePath)
        elif sourceType == 'survey':
            srs = SurveyData(sourcePath)
            if srs.valid:
                # TODO: Rückgängig machen wenn Problem mit Nullpunkt behoben
                # self.points = {
                #     'A': srs.getFirstPoint(),
                #     'E': srs.getLastPoint()
                # }
                self.points = {
                    'A': [None, None],
                    'E': [None, None]
                }
        if srs and srs.valid:
            self.heightSource = srs
            self.heightSourceType = sourceType
        elif srs.errorMsg:
            self.onError(srs.errorMsg)
        
        # Points are ether empty (raster) or they are the first and last point
        # of survey data
        self.setPoint('A', self.points['A'])
        self.setPoint('E', self.points['E'])
    
    def getPoint(self, pointType):
        return self.points[pointType], self.coordState
    
    def getPointAsStr(self, pointType):
        x = ''
        y = ''
        if self.points[pointType][0]:
            x = self.formatCoordinate(self.points[pointType][0])
        if self.points[pointType][1]:
            y = self.formatCoordinate(self.points[pointType][1])
        return [x, y]
    
    def setPoint(self, pointType, coords):
        hasChanged = False
        x = castToNum(coords[0])
        y = castToNum(coords[1])
        
        self.coordState[pointType] = self.checkCoordinatePoint([x, y])
        
        # Check if coordinates have actually changed
        if not (x == self.points[pointType][0]
                and y == self.points[pointType][1]):
            hasChanged = True
            self.setFixedPoles(None)
            self.setNoPoleSection([])
        
        self.points[pointType] = [x, y]
        self.setAzimut()
        self.setProfileLen()
        return self.points[pointType], self.coordState, hasChanged
    
    def checkCoordinatePoint(self, coords):
        [x, y] = coords
        state = 'yellow'
        
        if self.heightSource and self.heightSource.extent and \
                x is not None and y is not None:
            [extLx, extHy, extHx, extLy] = self.heightSource.extent
            
            # Round coordinates to avoid float imprecision
            if round(extLx, 3) <= round(x, 3) <= round(extHx, 3) \
                    and round(extLy, 3) <= round(y, 3) <= round(extHy, 3):
                state = 'green'
            else:
                state = 'red'
        return state
    
    # noinspection PyTypeChecker
    def transform2MapCoords(self, distance):
        x = self.points['A'][0] + distance * sin(self.azimut)
        y = self.points['A'][1] + distance * cos(self.azimut)
        return QgsPointXY(x, y)
    
    def profileIsValid(self):
        return self.coordState['A'] == self.coordState['E'] == 'green'
    
    def getAzimut(self):
        return '' if self.azimut is None else self.azimut
    
    def setAzimut(self):
        azimut = None
        if self.profileIsValid():
            azimut = atan2(self.points['E'][0] - self.points['A'][0],
                           self.points['E'][1] - self.points['A'][1])
            if self.points['E'][0] - self.points['A'][0] < 0:
                azimut += 2*pi
        self.azimut = azimut
    
    def getProfileLenAsStr(self):
        return '' if self.profileLength is None else f"{self.profileLength:.0f}"
    
    def setProfileLen(self):
        length = None
        if self.profileIsValid():
            crs = self.heightSource.spatialRef
            if crs and crs.isGeographic():
                # Create a measure object
                distance = QgsDistanceArea()
                ell = crs.ellipsoidAcronym()
                distance.setEllipsoid(ell)
                # Measure the distance
                length = distance.measureLine(QgsPointXY(*tuple(self.points['A'])),
                                              QgsPointXY(*tuple(self.points['E'])))
            else:
                length = ((self.points['E'][0] - self.points['A'][0])**2 +
                          (self.points['E'][1] - self.points['A'][1])**2)**0.5
        self.profileLength = length
    
    def getFixedPoles(self):
        return self.fixedPoles['poles']
    
    def setFixedPoles(self, value):
        self.fixedPoles = {
            'poles': [],
            'HM_fix_d': [],
            'HM_fix_h': []
        }
        if not value:
            return
        
        for pole in value:
            d = pole['d']
            z = pole['z']
            h = pole['h']
            name = pole['name']
            if not h:
                h = -1
            self.fixedPoles['poles'].append({
                'd': d,
                'z': z,
                'h': h,
                'name': name
            })
            self.fixedPoles['HM_fix_d'].append(d)
            self.fixedPoles['HM_fix_h'].append(h)
    
    def setNoPoleSection(self, noPoles):
        self.noPoleSection = noPoles
    
    def getConfigAsStr(self):
        # Reformat fixed poles
        fixPolesStr = ''
        for pole in self.fixedPoles['poles']:
            fixPolesStr += f"{pole['name']}: {pole['d']}, {pole['z']}, " \
                           f"{pole['h']}  /  "
        # Reformat sections without poles
        noPoleSectionStr = ''
        for section in self.noPoleSection:
            noPoleSectionStr += f"{section[0]} - {section[1]};"
        
        txt = [
            [self.header['projectname'], self.getProjectName()],
            [self.header[self.heightSourceType], self.heightSource.getAsStr()],
            [self.header['A'], '{0} / {1}'.format(*tuple(self.points['A']))],
            [self.header['E'], '{0} / {1}'.format(*tuple(self.points['E']))],
            [self.header['fixedPoles'], fixPolesStr],
            [self.header['noPoleSection'], noPoleSectionStr]
        ]
        formattedProjectInfo = []
        for title, info in txt:
            line = '{0: <17}{1}'.format(title, info)
            formattedProjectInfo += line + '\n'
        
        # Pole data
        formattedPoleData = ''
        if self.poles:
            formattedPoleData = [
                4 * '\n',
                'Stützendaten:\n',
                '\t'.join(['Nr.', 'Dist.', 'Höhe', 'Neigung', 'man.', 'Typ',
                           'Name']) + '\n',
                '-'*60 + '\n'
            ]
            idx = 0
            for p in self.poles.poles:
                poleData = [idx, p['d'], round(p['h'], 1), round(p['angle'], 1),
                            1 if p['manually'] else 0,
                           p['poleType'], p['name']]
                poleStr = [str(m) for m in poleData]
                formattedPoleData.append('\t'.join(poleStr) + '\n')
                idx += 1
        
        return formattedProjectInfo, formattedPoleData
    
    def checkValidState(self):
        msg = ''
        if not self.profileIsValid():
            msg = 'Bitte definieren Sie gültige Start- und Endkoordinaten'
        if not self.projectName:
            msg = 'Bitte definieren Sie einen Projektnamen'
        if msg:
            self.onError(msg, 'Unglültige Daten')
        return self.profileIsValid() and self.projectName

    @staticmethod
    def formatCoordinate(number):
        """Format big numbers with thousand separator"""
        if number is None:
            return ''
        # Format big numbers with thousand separator
        elif number >= 1000:
            return f"{number:,.0f}".replace(',', "'")
        else:
            return f"{number:,.6f}"
    
    def prepareForCalculation(self):
        # Prepare raster (create subraster) or interpolate survey data
        self.heightSource.prepareData(self.points, self.azimut)

        # From subraster or survey data create profile line
        self.profile = Profile(self)
        
        # Initialize pole data (start/end point and anchors)
        self.poles = Poles(self)
    
    def resetProfile(self):
        self.points = {
            'A': [None, None],
            'E': [None, None]
        }
        self.coordState = {
            'A': 'yellow',
            'E': 'yellow'
        }
        self.profileLength = None
        self.azimut = None
        self.fixedPoles = {
            'poles': [],
            'HM_fix_d': [],
            'HM_fix_h': []
        }
        self.noPoleSection = []
    
    def reset(self):
        self.poles = None


class ParameterConfHandler(AbstractConfHandler):
    
    SETS_PATH = os.path.join(HOMEPATH, 'config', 'parametersets')
    
    def __init__(self):
        AbstractConfHandler.__init__(self)
        
        # Parameters
        self.params = {}
        self.paramOrder = []
        # Short-hand dictionary for use in algorithm
        self.p = {}
        
        # Parameter sets
        self.currentSetName = ''
        self.parameterSets = {}
    
    def initParameters(self):
        # Load parameter definitions and rules from text file
        parameterDef = self.readParamsFromTxt(
            os.path.join(HOMEPATH, 'config', 'params.txt'))
        
        for key, pDef in parameterDef.items():
            parameterDef[key]['value'] = None
            # Cast numeric information to int / float
            
            for field in ['std_val', 'sort']:
                if not pDef[field].isalpha():
                    parameterDef[key][field] = self.castToNumber(
                        pDef['dtype'], pDef[field])
            
            if parameterDef[key]['std_val']:
                parameterDef[key]['value'] = parameterDef[key]['std_val']
        
        # Get the order of parameters for export to file
        orderedKeyList = []
        for property_name, info in parameterDef.items():
            orderedKeyList.append([property_name, int(info['sort'])])
        orderedParams = sorted(orderedKeyList, key=itemgetter(1))
        
        self.params = parameterDef
        self.paramOrder = [elem[0] for elem in orderedParams]

    def readParamsFromTxt(self, path):
        """Read txt files of parameter sets and save the key - value pairs to a
        dictionary."""
        fileData = {}
        if not os.path.exists(path) and os.path.isfile(path) \
                and path.lower().endswith('.txt'):
            msg = f"Fehler in Parameterset '{path}' " \
                  f"gefunden. Set kann nicht geladen werden."
            self.onError(msg)
            return False
    
        with io.open(path, encoding='utf-8') as f:
            lines = f.read().splitlines()
            header = lines[0].split('\t')
            for line in lines[1:]:
                if line == '':
                    break
                line = line.split('\t')
                row = {}
                key = line[0]
                # if txtfile has structure key, value (= parameter set)
                if len(header) == 2:
                    row = line[1]
                # if txtfile has structure key, value1, value2, value3
                # (= params.txt)
                else:
                    for i in range(1, len(header)):
                        row[header[i]] = line[i]
                fileData[key] = row
    
        return fileData
    
    def _getParameterInfo(self, property_name):
        try:
            return self.params[property_name]
        except KeyError:
            self.onError()
            return {}
    
    def getParameter(self, property_name):
        return self.params[property_name]['value']
    
    def getParameterAsStr(self, property_name):
        p = self._getParameterInfo(property_name)
        if not p:
            return ''
        value = p['value']
        if value is None:
            return ''
        if p['dtype'] in ['int', 'float']:
            value = str(value)
        # Float values without decimal places are reformatted: 10.0 --> 10
        if value[-2:] == '.0':
            value = value[:-2]
        return value
    
    def getParameterTooltip(self, property_name):
        p = self._getParameterInfo(property_name)
        if not p:
            return ''
        else:
            return p['tooltip']
    
    def setParameter(self, property_name, value):
        p = self._getParameterInfo(property_name)
        if not p:
            return False
        
        # Cast value to correct type
        cval = self.castToNumber(p['dtype'], value)
        
        # Check input value
        if cval is not None and cval != self.params[property_name]['value']:
            
            # Check value range
            if p['ftype'] not in ['drop_field', 'no_field']:
                valid = self.checkRange(cval, p)
                if not valid:
                    return False
            
            if self.currentSetName and cval != \
                    self.parameterSets[self.currentSetName][property_name]:
                self.currentSetName = ''
        
        self.params[property_name]['value'] = cval
        
        return self.getParameterAsStr(property_name)
    
    def batchSetParameter(self, property_name, value):
        """Set parameter without checking if it is valid. Method is needed
        when a whole parameterset is set or parameters are loaded from a txt
        file. Checks are done after all parameters have been set.
        """
        p = self._getParameterInfo(property_name)
        if not p:
            return False
        cval = self.castToNumber(p['dtype'], value)
        self.params[property_name]['value'] = cval
    
    def checkRange(self, value, paramInfo):
        rMin = paramInfo['min']
        rMax = paramInfo['max']
        
        rangeSet = []
        for rangeItem in [rMin, rMax]:
            
            # If range is a variable name
            if any(r.isalpha() for r in rangeItem):
                # Read out value of variable name that defines range
                rangeParam = self._getParameterInfo(rangeItem)
                if not rangeParam:
                    return False
                rangeVal = self.castToNumber(rangeParam['dtype'],
                                             rangeParam['value'])
            else:
                # Range is a value
                rangeVal = self.castToNumber(paramInfo['dtype'], rangeItem)
            
            rangeSet.append(rangeVal)
        
        # Check if value is defined
        if value is None:
            errorMsg = (f"Bitte geben Sie im Feld {paramInfo['label']} einen "
                        f"Wert zwischen {rangeSet[0]} und {rangeSet[1]} "
                        f"{paramInfo['unit']} ein.")
            self.onError(errorMsg, 'Ungültige Eingabe')
            return False
        
        # Finally check range
        if value is None or not rangeSet[0] <= value <= rangeSet[1]:
            errorMsg = (f"Der Wert {value} im Feld {paramInfo['label']} ist "
                        f"ungültig. Bitte wählen Sie einen Wert zwischen "
                        f"{rangeSet[0]} und {rangeSet[1]} {paramInfo['unit']}.")
            self.onError(errorMsg, 'Ungültige Eingabe')
            return False
        return True
    
    def checkAnchorDependency(self):
        if self.params['HM_Anfang']['value'] == 0 \
                and self.params['d_Anker_A']['value'] != 0:
            msg = (f"Der Wert {self.params['d_Anker_A']['value']} im Feld "
                   f"'{self.params['d_Anker_A']['label']}' ist ungültig. "
                   f"Ein Ankerfeld ist nur dann möglich, wenn die Anfangstütze "
                   f"grösser als 0 Meter ist.")
            self.onError(msg, 'Ungültige Eingabe')
            return False
        
        if self.params['HM_Ende_max']['value'] == 0 \
                and self.params['d_Anker_E']['value'] != 0:
            msg = (f"Der Wert {self.params['d_Anker_E']['value']} im Feld "
                   f"'{self.params['d_Anker_E']['label']}' ist ungültig. "
                   f"Ein Ankerfeld ist nur dann möglich, wenn die Endstütze "
                   f"grösser als 0 Meter sein darf.")
            self.onError(msg, 'Ungültige Eingabe')
            return False
        return True
    
    def checkValidState(self):
        """ Check whole parameterset for valid values."""
        # Check value range
        success = True
        for property_name, paramInfo in self.params.items():
            
            if paramInfo['ftype'] not in ['drop_field', 'no_field']:
                valid = self.checkRange(paramInfo['value'], paramInfo)
                if not valid:
                    self.params[property_name]['value'] = None
                    success = False
        
        # Check anchor parameter dependence
        success = False if not self.checkAnchorDependency() else success
        return success
    
    def getParametersAsStr(self):
        """ """
        txt = [
            '{5}{5}{0}{5}{1: <17}{2: <12}{3: <45}{4: <9} {5:-<84}{5}'.format(
                'Parameter:', 'Name', 'Wert', 'Label', 'Einheit', '\n')]
        for property_name in self.paramOrder:
            p = self.params[property_name]
            # Get correctly formatted string of value
            value = self.getParameterAsStr(property_name)
            # Combine label, value and units
            line = '{0: <17}{1: <12}{2: <45}{3: <9}{4}'.format(property_name,
                                    value, p['label'], p['unit'], '\n')
            txt.append(line)
        txt.append('{0: <17}{1: <12}'.format('Parameterset:', self.currentSetName))
        return txt
    
    def loadPredefinedParametersets(self):
        for f in os.listdir(self.SETS_PATH):
            txtfile = os.path.join(self.SETS_PATH, f)
            if os.path.isfile(txtfile) and txtfile.lower().endswith('.txt'):
                params = self.readParamsFromTxt(txtfile)
                if not params:
                    break
                setname = params['label']
                self.parameterSets[setname] = params
                del self.parameterSets[setname]['label']
    
    def getParametersetNames(self):
        return self.parameterSets.keys()
    
    def setParameterSet(self, setname):
        try:
            self.parameterSets[setname]
        except KeyError:
            msg = (f"Fehler in Parameterset '{setname}' gefunden. "
                   f"Set kann nicht geladen werden.")
            self.onError(msg)
            return
        
        for property_name, value in self.parameterSets[setname].items():
            self.batchSetParameter(property_name, value)
        self.currentSetName = setname
        self.checkValidState()
    
    def saveParameterSet(self, setname):
        if not setname:
            return
        # Save parameter set
        self.parameterSets[setname] = {}
        for property_name, p in self.params.items():
            self.parameterSets[setname][property_name] = p['value']
        
        # Write parameter set out to file
        savePath = os.path.join(self.SETS_PATH, f'{setname}.txt')
        # TODO: Check if file can be written to disk (filename, write access)
        with io.open(savePath, encoding='utf-8', mode='w') as f:
            # Write header
            f.writelines('name\tvalue\n')
            f.writelines('label\t' + setname + '\n')
            # Write parameter values
            for property_name, value in self.parameterSets[setname].items():
                f.writelines(f"{property_name}\t{value}\n")
    
    def castToNumber(self, dtype, value):
        # Cast value to correct type
        if value == '' and dtype != 'string':
            return None
        try:
            if dtype == 'string':
                cval = value
                # result = True
            elif dtype == 'float':
                cval = float(value)
            else:  # int
                cval = int(float(value))
        except ValueError:
            self.onError('Bitte geben Sie eine gültige Zahl ein.')
            return None
        return cval
    
    def prepareForCalculation(self):
        pass
    
    def getSimpleParameterDict(self):
        # Short-hand dictionary for use in algorithm
        self.p = {}
        for key, p in self.params.items():
            self.p[key] = p['value']
        return self.p
    
    def reset(self):
        pass


class ConfigHandler(object):
    
    SETTINGS_FILE = os.path.join(HOMEPATH, 'config', 'commonPaths.txt')
    DEFAULT_SAVE_PATH = os.path.join(os.path.expanduser('~'), 'Seilaplan')
    
    def __init__(self):
        self._config = {}
        
        # User settings
        self.commonPaths = []
        self.outputOptions = {
            'report': 1,
            'plot': 1,
            'geodata': 0,
            'coords': 0
        }
        self.userSettingsHaveChanged = False
        
        self.params = ParameterConfHandler()
        self.project = ProjectConfHandler(self.params)
        
        self.polesFromTxt = []
        
        # Load parameter definitions and predefined parameter sets
        self.loadUserSettings()
        self.params.initParameters()
        self.params.loadPredefinedParametersets()
    
    def setDialog(self, dialog):
        self.project.setDialog(dialog)
        self.params.setDialog(dialog)
    
    def loadFromFile(self, filename):
        
        def readOutProjectData(lines, lineNr):
            for line in lines[lineNr:]:
                lineNr += 1
                if line == '':
                    return lineNr
                property_name = line[:17].rstrip()
                data = line[17:]
                self.project.setConfigFromFile(property_name, data)
        
        def readOutParamData(lines, lineNr):
            for line in lines[lineNr:]:
                lineNr += 1
                part = re.split(r'\s{2,}', line)
                if len(part) <= 1:
                    continue
                if part[1] == '-':
                    part[1] = ''
                key = part[0]
                if key == 'Parameterset:':
                    setname = part[1]
                    if setname not in self.params.parameterSets.keys():
                        # Save new parameter set
                        self.params.saveParameterSet(setname)
                    self.params.currentSetName = setname
                    return lineNr
                self.params.batchSetParameter(key, part[1])
        
        def readOutPoleData(lines, lineNr):
            for line in lines[lineNr:]:
                lineNr += 1
                if line == '':
                    return lineNr
                parts = line.split('\t')
                if len(parts) != 7:
                    continue
                self.polesFromTxt.append({
                    'idx': int(parts[0]),
                    'dist': int(float(parts[1])),
                    'height': float(parts[2]),
                    'angle': float(parts[3]),
                    'manual': True if int(parts[4]) == 1 else False,
                    'pType': parts[5],
                    'name': parts[6]
                })

        lineCount = 0
        if os.path.exists(filename):
            with io.open(filename, encoding='utf-8') as f:
                allLines = f.read().splitlines()
                
                try:
                    for currLine in allLines:
                        if currLine.startswith('Projektname'):
                            lineCount = readOutProjectData(allLines, lineCount)
                            break
                        lineCount += 1
                    for currLine in allLines[lineCount:]:
                        if currLine.startswith('Parameter:'):
                            lineCount = readOutParamData(allLines, lineCount+3)
                            break
                        lineCount += 1
                    if lineCount < len(allLines):
                        for currLine in allLines[lineCount:]:
                            if currLine.startswith('Stützendaten:'):
                                readOutPoleData(allLines, lineCount+3)
                                break
                            lineCount += 1
                except Exception as e:
                    print(e)
                    return False

            success = self.params.checkValidState()
            return success
        else:
            return False
    
    def saveToFile(self, filename):
        projectStr, poleStr = self.project.getConfigAsStr()
        paramsStr = self.params.getParametersAsStr()
        
        if os.path.exists(filename):
            os.remove(filename)
        with io.open(filename, encoding='utf-8', mode='w') as f:
            # Write project info
            f.writelines(projectStr)
            f.writelines('\n')
            # Write parameter values
            f.writelines(paramsStr)
            # Write pole info
            f.writelines(poleStr)
    
    def loadUserSettings(self):
        """Gets the output options and earlier used output paths and returns
        them."""
        
        if os.path.exists(self.SETTINGS_FILE):
            with io.open(self.SETTINGS_FILE, encoding='utf-8') as f:
                lines = f.read().splitlines()
                # First line contains output options
                try:
                    outputOpts = lines[0].split()
                    outputOpts = [int(x) for x in outputOpts]
                    self.outputOptions = {
                        'report': outputOpts[0],
                        'plot': outputOpts[1],
                        'geodata': outputOpts[2],
                        'coords': outputOpts[3],
                    }
                except IndexError:  # if file/fist line is empty
                    pass
                except ValueError:  # if there are letters instead of numbers
                    pass
                # Go through paths from most recent to oldest
                for path in lines[1:]:
                    if path == '':
                        continue
                    if os.path.exists(path):  # If path still exists
                        self.commonPaths.append(path)
        
        # If there are no paths defined by user (for example at first run),
        # try to create standard folder
        if not self.commonPaths:
            if os.path.exists(self.DEFAULT_SAVE_PATH):
                self.commonPaths.append(self.DEFAULT_SAVE_PATH)
            else:
                try:
                    os.mkdir(self.DEFAULT_SAVE_PATH)
                    self.commonPaths.append(self.DEFAULT_SAVE_PATH)
                except OSError:
                    self.commonPaths.append(os.path.expanduser('~'))
    
    def updateUserSettings(self):
        """ Update the user defined settings. """
        if not self.userSettingsHaveChanged:
            return
        # Maximum length of drop down menu is 6 entries
        if len(self.commonPaths) > 6:
            del self.commonPaths[0]  # Delete oldest entry
        
        if os.path.exists(self.SETTINGS_FILE):
            os.remove(self.SETTINGS_FILE)
        
        with io.open(self.SETTINGS_FILE, encoding='utf-8', mode='w+') as f:
            f.writelines(
                "{} {} {} {} {}".format(self.outputOptions['report'],
                                        self.outputOptions['plot'],
                                        self.outputOptions['geodata'],
                                        self.outputOptions['coords'],
                                        '\n'))
            for path in self.commonPaths:
                f.writelines(path + '\n')
    
    def getCurrentPath(self):
        try:
            return self.commonPaths[-1]
        except IndexError:
            return ''
    
    def addPath(self, path):
        if path != self.commonPaths[-1]:
            self.commonPaths.append(path)
        # Delete duplicates in list
        unique = []
        [unique.append(item) for item in reversed(self.commonPaths) if
         item not in unique]
        self.commonPaths = list(reversed(unique))
        self.userSettingsHaveChanged = True
    
    def getOutputOption(self, property_name):
        try:
            return self.outputOptions[property_name]
        except KeyError:
            return None
    
    def setOutputOptions(self, outputOptions):
        self.outputOptions = outputOptions
        self.userSettingsHaveChanged = True
    
    def checkValidState(self):
        return self.project.checkValidState() and self.params.checkValidState()
    
    def prepareForCalculation(self):
        """
        Updates some parameters and generates the subraster and profile line.
        Initializes pole data.
        :return:
        """
        self.params.prepareForCalculation()
        self.project.prepareForCalculation()
    
    def loadCableDataFromFile(self):
        self.prepareForCalculation()
        status = 'jumpedOver'
        
        # If the project file already contains pole data from an earlier run,
        # load this data into Poles()
        if self.polesFromTxt:
            status = 'savedFile'
            self.project.poles.updateAllPoles(status, self.polesFromTxt)
        # If instead user has defined some fixed poles, add these to Poles()
        elif self.project.fixedPoles:
            self.project.poles.updateAllPoles(status, self.project.fixedPoles['poles'])
        
        zulSK = self.params.params['zul_SK']['value']
        minSK = self.params.params['min_SK']['value']
        optSTA = int(minSK + (zulSK - minSK) / 2)
        
        return {
            'cableline': None,
            'optSTA': optSTA,
            'optSTA_arr': [optSTA],
            'force': None,
            'optLen': None,
            'duration': getTimestamp(time.time())
        }, status
    
    def reset(self):
        self.project.reset()
        self.params.reset()
