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
from math import atan, pi, cos, sin
import numpy as np

from qgis.PyQt.QtWidgets import QMessageBox
from qgis.core import QgsPointXY

from .tool.raster import Raster
from .tool.profile import Profile
from .tool.poles import Poles

# Constants
HOMEPATH = os.path.join(os.path.dirname(__file__))


def readParamsFromTxt(path):
    """Read txt files of parameter sets and save the key - value pairs to a
    dictionary."""
    fileData = {}
    if not os.path.exists(path) and os.path.isfile(path) \
            and path.lower().endswith('.txt'):
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


def formatNum(number):
    """Layout Coordinates with thousand markers."""
    if number is None:
        return ''
    roundNum = int(round(number))
    strNum = str(roundNum)
    if roundNum > 999:
        b, c = divmod(roundNum, 1000)
        if b > 999:
            a, b = divmod(b, 1000)
            strNum = "{:0d}'{:0>3n}'{:0>3n}".format(a, b, c)
        else:
            strNum = "{:0n}'{:0>3n}".format(b, c)
    return strNum


def castToNum(formattedNum):
    if type(formattedNum) == int or type(formattedNum) == float:
        return formattedNum
    try:
        num = int(formattedNum.replace("'", ''))
    except (ValueError, AttributeError):
        num = None
    return num


class AbstractConfHandler(object):
    
    def __init__(self):
        self.dialog = None
    
    def setDialog(self, dialog):
        self.dialog = dialog
    
    def onError(self, message=None):
        if not message:
            message = traceback.format_exc()
        QMessageBox.information(self.dialog, 'Fehler', message,
                                QMessageBox.Ok)


# noinspection PyTypeChecker
class ProjectConfHandler(AbstractConfHandler):
    
    dhm: Raster
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
        self.dhm = None
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
            'HM_fix_d': [],
            'HM_fix_h': [],
            'asStr': {}
        }
        self.noPoleSection = []
        
        # TODO: Translate
        self.header = {
            'projectname': 'Projektname',
            'dhm': 'Hoehenmodell',
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
            self.setDhm(False, value)
        
        elif property_name in [self.header['A'], self.header['E']]:
            point = property_name[0]
            [x, y] = value.split('/')
            self.setPoint(point, [x, y])
        
        elif property_name == self.header['fixedPoles']:
            polesStr = value.split('/')[:-1]
            poleArray = []
            for stue in polesStr:
                [key, values] = stue.split(':')
                [polex, poley, poleh] = [string.strip() for string in
                                         values.split(',')]
                poleArray.append({'x': polex, 'y': poley, 'h': poleh})
            
            self.setFixedPoles(poleArray)
        
        elif property_name == self.header['noPoleSection']:
            sections = value.split('; ')
            pairArray = np.array([])
            for section in sections:
                dist = section.split(' - ')
                np.append(pairArray, [dist])
            self.setNoPoleSection(pairArray)
    
    def getProjectName(self):
        return '' if self.projectName is None else self.projectName
    
    def setProjectName(self, value):
        self.projectName = value
    
    def generateProjectName(self):
        """ Generate a unique project name."""
        import time
        now = time.time()
        timestamp = time.strftime("%d.%m_%H'%M", time.localtime(now))
        self.projectName = "seilaplan_{}".format(timestamp)
        return self.projectName
    
    def getDhmAsStr(self):
        return '' if not self.dhm else self.dhm.path
    
    def setDhm(self, rasterLyr, rasterPath=None):
        """Raster can be set by providing the QGIS Raster Layer or by giving
        the path to the raster file."""
        self.dhm = None
        rst = Raster(rasterLyr, rasterPath)
        if rst.valid:
            self.dhm = rst
        
        self.setPoint('A', self.points['A'])
        self.setPoint('E', self.points['E'])
    
    def getPoint(self, pointType):
        return self.points[pointType], self.coordState
    
    def getPointAsStr(self, pointType):
        x = ''
        y = ''
        if self.points[pointType][0]:
            x = formatNum(self.points[pointType][0])
        if self.points[pointType][1]:
            y = formatNum(self.points[pointType][1])
        return [x, y]
    
    def setPoint(self, pointType, coords):
        hasChanged = False
        x = castToNum(coords[0])
        y = castToNum(coords[1])
        
        self.coordState[pointType] = self.checkCoordinatePoint([x, y])
        
        # Only continue if coordinates where actually changed
        if not (x == self.points[pointType][0]
                and y == self.points[pointType][1]):
            hasChanged = True
            self.setFixedPoles(False)
        
        self.points[pointType] = [x, y]
        self.setAzimut()
        self.setProfileLen()
        return self.points[pointType], self.coordState, hasChanged
    
    def checkCoordinatePoint(self, coords):
        state = 'yellow'
        [x, y] = coords
        
        if self.dhm and coords[0] is not None and coords[1] is not None:
            [extLx, extHy, extHx, extLy] = self.dhm.extent
            
            if extLx <= x <= extHx and extLy <= y <= extHy:
                state = 'green'
            else:
                state = 'red'
        
        return state
    
    # noinspection PyTypeChecker
    def transform2MapCoords(self, distance):
        x = self.points['A'][0] + distance * cos(self.azimut)
        y = self.points['A'][1] + distance * sin(self.azimut)
        return QgsPointXY(x, y)
    
    def profileIsValid(self):
        return self.coordState['A'] == self.coordState['E'] == 'green'
    
    def getAzimut(self):
        return '' if self.azimut is None else self.azimut
    
    def setAzimut(self):
        azimut = None
        if self.profileIsValid():
            dx = (self.points['E'][0] - self.points['A'][0]) * 1.0
            dy = (self.points['E'][1] - self.points['A'][1]) * 1.0
            if dx == 0:
                dx = 0.0001
            azimut = atan(dy / dx)
            if dx > 0:
                azimut += 2 * pi
            else:
                azimut += pi
        self.azimut = azimut
    
    def getProfileLen(self):
        return self.profileLength
    
    def getProfileLenAsStr(self):
        return '' if self.profileLength is None else formatNum(self.profileLength)
    
    def setProfileLen(self):
        profileLen = None
        if self.profileIsValid():
            profileLen = ((self.points['E'][0] - self.points['A'][0]) ** 2
                          + (self.points['E'][1] - self.points['A'][1]) ** 2) ** 0.5
        self.profileLength = profileLen
    
    def getFixedPoles(self):
        return self.fixedPoles['asStr']
    
    def setFixedPoles(self, value):
        self.fixedPoles = {
            'HM_fix_d': [],
            'HM_fix_h': [],
            'asStr': {}
        }
        if not value:
            return
        
        for i, pole in enumerate(value):
            x = pole['x']
            y = pole['y']
            h = pole['h']
            if x == '' or x.isalpha():
                continue
            if h == '':
                h = '-1'
            self.fixedPoles['asStr'][i + 1] = [x, y, h]
            self.fixedPoles['HM_fix_d'].append(int(x))
            self.fixedPoles['HM_fix_h'].append(int(h))
    
    def setNoPoleSection(self, noPoles):
        self.noPoleSection = noPoles
    
    def getConfigAsStr(self):
        # Reformat fixed poles
        fixPolesStr = ''
        for key, values in list(self.fixedPoles['asStr'].items()):
            fixPolesStr += '{0:0>2}: {1: >7}, {2: >7}, {3: >4}  /  '.format(
                key, *tuple(values))
        # Reformat sections without poles
        noPoleSectionStr = ''
        for section in self.noPoleSection:
            noPoleSectionStr += f"{section[0]} - {section[1]};"
        
        txt = [
            [self.header['projectname'], self.getProjectName()],
            [self.header['dhm'], self.getDhmAsStr()],
            [self.header['A'], '{0} / {1}'.format(*tuple(self.getPointAsStr('A')))],
            [self.header['E'], '{0} / {1}'.format(*tuple(self.getPointAsStr('E')))],
            [self.header['fixedPoles'], fixPolesStr],
            [self.header['noPoleSection'], noPoleSectionStr]
        ]
        formattedProjectInfo = []
        for title, info in txt:
            line = '{0: <17}{1}'.format(title, info)
            formattedProjectInfo += line + os.linesep
        
        return formattedProjectInfo
    
    def checkValidState(self):
        return self.profileIsValid() and self.projectName
    
    def prepareForCalculation(self):
        # DHM: Define buffer for subraster creation depended on anchor length
        anchorLen = max([self.params.getParameter('d_Anker_A'),
                         self.params.getParameter('d_Anker_E')])
        # Create subraster
        self.dhm.setSubraster(self.points, anchorLen)
        
        # From subraster create profile line
        self.profile = Profile(self)
        
        # Initialize pole data (start/end point and anchors)
        self.poles = Poles(self)


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
        parameterDef = readParamsFromTxt(
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
    
    def _getParameterInfo(self, property_name):
        try:
            return self.params[property_name]
        except KeyError:
            # TODO QgsMessage:
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
        if cval != self.params[property_name]['value']:
            
            # Check value range
            if p['ftype'] not in ['drop_field', 'no_field']:
                valid = self.checkRange(cval, p)
                if not valid:
                    return False
            
            # Check anchor parameters
            if property_name in ['d_Anker_A', 'd_Anker_E', 'HM_Anfang',
                                 'HM_Ende_max']:
                valid = self.checkAnchorDependency(property_name, cval)
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
            # TODO QgsMessage:
            errorMsg = (f"Bitte geben Sie im Feld {paramInfo['label']} einen "
                        f"Wert zwischen {rangeSet[0]} und {rangeSet[1]} "
                        f"{paramInfo['unit']} ein.")
            self.onError(errorMsg)
            return False
        
        # Finally check range
        if value is None or not rangeSet[0] <= value <= rangeSet[1]:
            # TODO QgsMessage:
            errorMsg = (f"Der Wert {value} im Feld {paramInfo['label']} ist "
                        f"ungültig. Bitte wählen Sie einen Wert zwischen "
                        f"{rangeSet[0]} und {rangeSet[1]} {paramInfo['unit']}.")
            self.onError(errorMsg)
            return False
        return True
    
    def checkAnchorDependency(self, property_name=None, value=None):
        aParam = {
            'HM_Anfang': self.params['HM_Anfang']['value'],
            'd_Anker_A': self.params['d_Anker_A']['value'],
            'd_Anker_E': self.params['d_Anker_E']['value'],
            'HM_Ende_max': self.params['HM_Ende_max']['value'],
        }
        
        if property_name:
            aParam[property_name] = value
        
        if aParam['HM_Anfang'] == 0 and aParam['d_Anker_A'] != 0:
            msg = (f"Der Wert {value} im Feld "
                   f"'{self.params[property_name]['label']}' ist ungültig. "
                   f"Die Länge des Ankerfeldes und die Höhe der "
                   f"Anfangsstütze sind voneinander abhängig. Ein Ankerfeld "
                   f"ist nur dann möglich, wenn die Anfangstütze grösser als 0 Meter ist.")
            self.onError(msg)
            return False
        
        if aParam['HM_Ende_max'] == 0 and aParam['d_Anker_E'] != 0:
            msg = (f"Der Wert {value} im Feld "
                   f"'{self.params[property_name]['label']}' ist ungültig. "
                   f"Die Länge des Ankerfeldes und die maximale Höhe der Endstütze "
                   f"sind voneinander abhängig. Ein Ankerfeld "
                   f"ist nur dann möglich, wenn die Enstütze grösser als 0 Meter sein darf.")
            self.onError(msg)
            return False
        return True
    
    def checkValidState(self):
        """ Check whole parameterset for valid values."""
        # Check value range
        for property_name, paramInfo in self.params.items():
            
            if paramInfo['ftype'] not in ['drop_field', 'no_field']:
                valid = self.checkRange(paramInfo['value'], paramInfo)
                if not valid:
                    self.params[property_name]['value'] = None
        
        # Check anchor parameter dependence
        self.checkAnchorDependency()
        
        return True
    
    def getParametersAsStr(self):
        """ """
        txt = [
            '{5}{5}{0}{5}{1: <17}{2: <12}{3: <45}{4: <9} {5:-<84}{5}'.format(
                'Parameter:', 'Name', 'Wert', 'Label', 'Einheit', os.linesep)]
        for property_name in self.paramOrder:
            p = self.params[property_name]
            # Get correctly formatted string of value
            value = self.getParameterAsStr(property_name)
            # Combine label, value and units
            line = '{0: <17}{1: <12}{2: <45}{3: <9}{4}'.format(property_name,
                                    value, p['label'], p['unit'], os.linesep)
            txt.append(line)
        txt.append('{0: <17}{1: <12}'.format('Parameterset:', self.currentSetName))
        return txt
    
    def loadPredefinedParametersets(self):
        for f in os.listdir(self.SETS_PATH):
            txtfile = os.path.join(self.SETS_PATH, f)
            if os.path.isfile(txtfile) and txtfile.lower().endswith('.txt'):
                params = readParamsFromTxt(txtfile)
                if not params:
                    # TODO: QGIS Error Message
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
            # TODO QgsMessage
            self.onError()
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
        with io.open(savePath, encoding='utf-8', mode='w+') as f:
            # Write header
            f.writelines('name\tvalue' + os.linesep)
            f.writelines('label\t' + setname + os.linesep)
            # Write parameter values
            for property_name, value in self.parameterSets[setname].items():
                f.writelines(f"{property_name}\t{value}{os.linesep}")
    
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
                cval = int(value)
        except ValueError:
            # TODO QgsMessage
            self.onError()
            return None
        return cval
    
    def prepareForCalculation(self):
        # TODO: The Fuck did I do here?
        # Ankerpunkten den Anfangs-/Endstützen anpassen
        if self.params['HM_Anfang']['value'] < 1:
            self.params['d_Anker_A']['value'] = 0.0
        if self.params['HM_Ende_max']['value'] < 1:
            self.params['d_Anker_E']['value'] = 0.0
        
        # Seilzugkräfte müssen ganzzahlig sein, aber in float-Form
        # TODO: Warum nicht einfach Ganzzahlig definieren damit bereits bei der EIngabe klar ist, dass es nur Ganzzahlig geht?
        self.params['zul_SK']['value'] = round(self.params['zul_SK']['value'], 0)
        self.params['min_SK']['value'] = round(self.params['min_SK']['value'], 0)
    
    def getSimpleParameterDict(self):
        # Short-hand dictionary for use in algorithm
        self.p = {}
        for key, p in self.params.items():
            self.p[key] = p['value']
        return self.p


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
        
        # Load parameter definitions and predefined parameter sets
        self.loadUserSettings()
        self.params.initParameters()
        self.params.loadPredefinedParametersets()
    
    def setDialog(self, dialog):
        self.project.setDialog(dialog)
        self.params.setDialog(dialog)
    
    def loadFromFile(self, filename):
        if os.path.exists(filename):
            with io.open(filename, encoding='utf-8') as f:
                lines = f.read().splitlines()
                
                # Read out project data
                for hLine in lines[:6]:
                    # Dictionary keys cant be in unicode
                    property_name = hLine[:17].rstrip()
                    data = hLine[17:]
                    self.project.setConfigFromFile(property_name, data)
                
                # Read out parameter data
                for line in lines[11:]:
                    if line == '':
                        break
                    line = re.split(r'\s{2,}', line)
                    if len(line) <= 1:
                        continue
                    if line[1] == '-':
                        line[1] = ''
                    key = line[0]
                    if key == 'Parameterset:':
                        self.params.currentSetName = line[1]
                        continue
                    self.params.batchSetParameter(key, line[1])
            self.params.checkValidState()
        else:
            return False
        
        self.addPath(os.path.dirname(filename))
    
    def saveToFile(self, filename):
        projectStr = self.project.getConfigAsStr()
        paramsStr = self.params.getParametersAsStr()
        
        if os.path.exists(filename):
            os.remove(filename)
        with io.open(filename, encoding='utf-8', mode='w+') as f:
            # Write project info
            f.writelines(projectStr)
            f.writelines(os.linesep)
            # Write parameter values
            f.writelines(paramsStr)
        
        self.addPath(os.path.dirname(filename))
    
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
            try:
                os.mkdir(self.DEFAULT_SAVE_PATH)
                self.commonPaths.append(self.DEFAULT_SAVE_PATH)
            except OSError:
                pass
    
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
                                        os.linesep))
            for path in self.commonPaths:
                f.writelines(path + os.linesep)
    
    def getCurrentPath(self):
        return self.commonPaths[-1]
    
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
