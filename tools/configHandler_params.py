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
from operator import itemgetter
from math import pi, sqrt
import copy

from qgis.core import QgsSettings

from .configHandler_abstract import AbstractConfHandler
from SEILAPLAN.gui.guiHelperFunctions import sanitizeFilename

# Constants
HOMEPATH = os.path.join(os.path.dirname(__file__))


class ParameterConfHandler(AbstractConfHandler):
    
    SEILSYS_TYPES = {
        0: 'Zweiseil-System',
        1: 'Mehrseil-System'
    }
    ANCHOR_LEN = 20
    SETS_PATH = os.path.join(HOMEPATH, '../config', 'parametersets')
    SETTING_PREFIX = 'PluginSeilaplan/parameterset/'
    
    def __init__(self):
        AbstractConfHandler.__init__(self)
        
        # Parameters
        self.params = {}
        self.derievedParams = {}
        self.paramOrder = []
        # Shorthand dictionary for use in algorithm
        self.p = {}
        # Optimal cable tension (result of optimization) - is None if
        #  optimization algorithm didn't run
        self.optSTA = None
        
        # Parameter sets
        self.currentSetName = ''
        self.parameterSets = {}
        self.defaultSet = self.tr('Standardparameter')

    # noinspection PyTypeChecker
    def initParameters(self):
        # Load parameter definitions and rules from text file
        parameterDef = self.readParamsFromTxt(
            os.path.join(HOMEPATH, '../config', 'params.txt'))
        
        for paramName in parameterDef.keys():
            # Set default value to None
            parameterDef[paramName]['value'] = None
            # Cast sort number to int
            parameterDef[paramName]['sort'] = int(parameterDef[paramName]['sort'])
        
        # Get the order of parameters for export to file
        orderedKeyList = []
        for property_name, info in parameterDef.items():
            orderedKeyList.append([property_name, int(info['sort'])])
        orderedParams = sorted(orderedKeyList, key=itemgetter(1))
        
        self.params = parameterDef
        self.paramOrder = [elem[0] for elem in orderedParams]
        
        # Initialize derived parameters
        self.derievedParams['d_Anker_A'] = {
            'value': self.ANCHOR_LEN
        }
        self.derievedParams['d_Anker_E'] = {
            'value': self.ANCHOR_LEN
        }

    def readParamsFromTxt(self, path):
        """Read txt files of parameter sets and save the key - value pairs to a
        dictionary."""
        fileData = {}
        if not os.path.exists(path) and os.path.isfile(path) \
                and path.lower().endswith('.txt'):
            msg = self.tr("Fehler in Parameterset '{}' gefunden. "
                          "Set kann nicht geladen werden.").format(path)
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
            return {}
    
    def getParameter(self, property_name):
        try:
            return self.params[property_name]['value']
        except KeyError:
            # Try to find parameter in derived parameter dictionary
            if property_name in self.derievedParams:
                return self.derievedParams[property_name]['value']
            else:
                return None
    
    def getParameterAsStr(self, property_name):
        p = self._getParameterInfo(property_name)
        if not p:
            self.onError()
            return ''
        value = p['value']
        if value is None:
            return ''
        if p['ftype'] == 'drop_field' and property_name == 'Seilsys':
            return self.SEILSYS_TYPES[int(value)]
        if p['dtype'] in ['int', 'float']:
            value = str(value)
        # Float values without decimal places are reformatted: 10.0 --> 10
        if value[-2:] == '.0':
            value = value[:-2]
        return value
    
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
        property_name, value = self.checkForDepricatedParams(property_name, value)
        p = self._getParameterInfo(property_name)
        if not p:
            self.onError(self.tr('Fehler beim Laden der Parameter, '
                'moeglicherweise sind sie in einem alten Format.'))
            raise KeyError(f'Unknown parameter {property_name}')

        if p and p['ftype'] == 'drop_field' and property_name == 'Seilsys':
            value = self.getSeilsysAsIdx(value)
        cval = self.castToNumber(p['dtype'], value)
        self.params[property_name]['value'] = cval
    
    @staticmethod
    def checkForDepricatedParams(property_name, value):
        """This will check for parameters that have been depricated since
        version 3.0. It's not going to try to fix parametersets from older
        Seilaplan parametersets."""
        
        if property_name == 'min_SK':
            property_name = 'SK'
    
        elif property_name == 'A':
            # Area to diameter
            property_name = 'D'
            value = 2 * sqrt(float(value) / pi)
            
        return property_name, value
    
    def checkRange(self, value, paramInfo):
        rMin = paramInfo['min']
        rMax = paramInfo['max']
        if rMin == '' or rMax == '':
            return True
        
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
            errorMsg = self.tr('Bitte geben Sie im Feld einen Wert ein').format(
                self.tr(paramInfo['label'], '@default'), rangeSet[0],
                rangeSet[1], paramInfo['unit'])
            self.onError(errorMsg, self.tr('Ungueltige Eingabe'))
            return False
        
        # Finally check range
        if value is None or not rangeSet[0] <= value <= rangeSet[1]:
            errorMsg = self.tr('Der Wert im Feld ist ungueltig').format(
                value, self.tr(paramInfo['label'], '@default'), rangeSet[0],
                rangeSet[1], paramInfo['unit'])
            self.onError(errorMsg, self.tr('Ungueltige Eingabe'))
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
        return success
    
    def checkBodenabstand(self):
        if self.params['Bodenabst_min']['value'] > self.params['HM_min']['value']:
            self.onError(self.tr("Der Parameter Minimaler Abstand Tragseil Boden darf nicht groesser als der Parameter Minimale Stuetzenhoehe sein."),
                         self.tr('Ungueltige Eingabe'))
            return False
        else:
            return True

    def getSettings(self):
        """Return settings in a structured dictionary to save to json file."""
        params = []
        for property_name in self.paramOrder:
            p = self.params[property_name]
            params.append({
                'name': property_name,
                'label': self.tr(p['label'], '@default'),
                'value': self.getParameterAsStr(property_name),
                'unit': p['unit']
            })
        return {
            'params': {
                'setname': self.currentSetName,
                'optSTA': self.optSTA,
                'parameterList': params
            }
        }
    
    def loadPredefinedParametersets(self):
        # Some predefined parametersets are provided by the plugin, they have
        #  to be loaded from text files
        for f in os.listdir(self.SETS_PATH):
            txtfile = os.path.join(self.SETS_PATH, f)
            if os.path.isfile(txtfile) and txtfile.lower().endswith('.txt'):
                params = self.readParamsFromTxt(txtfile)
                if not params:
                    break
                setname = params['label']
                if setname == 'Standardparameter':
                    setname = self.defaultSet       # Translated setname
                self.parameterSets[setname] = params
                del self.parameterSets[setname]['label']
    
    def getParametersetNames(self):
        return self.parameterSets.keys()
    
    def setParameterSet(self, setname):
        try:
            self.parameterSets[setname]
        except KeyError:
            msg = self.tr('Fehler in Parameterset gefunden').format(setname)
            self.onError(msg)
            return
        
        self.reset()
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
        
        self.saveParamSetToSettings(setname)
    
    def removeParameterSet(self, setname):
        fileName = sanitizeFilename(setname)
        savePath = os.path.join(self.SETS_PATH, f'{fileName}.txt')
        # If user wants to remove a predefined parameterset --> we do not allow this
        if os.path.isfile(savePath):
            return False
        else:
            # Remove from QgsSettings
            success = self.removeParamSetFromSettings(setname)
            
        if success:
            # Remove set from parameter handler
            del self.parameterSets[setname]
        return success
    
    def loadParametersetsFromSettings(self):
        """Load all user defined parameter sets from QGIS Settings DB."""
        s = QgsSettings()
        s.beginGroup(self.SETTING_PREFIX)
        for setname in s.childGroups():
            if setname in self.parameterSets.keys():
                continue
            # Start with default set and overwrite all properties
            params = copy.deepcopy(self.parameterSets[self.defaultSet])
            # Switch context to the parameter set
            s.beginGroup(setname)
            for prop in s.allKeys():
                params[prop] = s.value(prop)
            label = params['label']
            del params['label']
            self.parameterSets[label] = params
            # Close group, go back to '/parameterset' context
            s.endGroup()
        s.endGroup()
    
    def saveParamSetToSettings(self, setname):
        sanitizedSetname = sanitizeFilename(setname)
        prefix = f'{self.SETTING_PREFIX}{sanitizedSetname}/'

        s = QgsSettings()
        s.setValue(f'{prefix}label', setname)
        for property_name, value in self.parameterSets[setname].items():
            s.setValue(f'{prefix}{property_name}', value)
    
    def removeParamSetFromSettings(self, setname):
        """Remove a user defined parameter set from the QGIS settings DB."""
        sanitizedSetname = sanitizeFilename(setname)
        if not sanitizedSetname:
            return
        s = QgsSettings()
        s.remove(f'{self.SETTING_PREFIX}{sanitizedSetname}')
        return not s.contains(f'{self.SETTING_PREFIX}{sanitizedSetname}/label')
    
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
            self.onError(self.tr('Bitte geben Sie eine gueltige Zahl ein.'))
            return None
        return cval
    
    def getSeilsysAsIdx(self, sysStr):
        # If Seilsys was saved as text instead of index number (when loading
        #  project files)
        if isinstance(sysStr, str) and len(sysStr) > 1:
            for key, ptype in self.SEILSYS_TYPES.items():
                if ptype == sysStr:
                    return key
        else:
            return sysStr

    def setOptSTA(self, optSTA):
        if optSTA is None or int(round(float(optSTA))) == self.getParameter('SK'):
            # Don't set optSTA if it is equal to the base tensile force parameter.
            #  This will be the case when loading project files because optSTA
            #  was set fromthe parameterset value SK in previous versions.
            self.optSTA = None
        else:
            self.optSTA = int(round(float(optSTA)))
    
    def getTensileForce(self):
        # This will either return the tensile force calculated by the optimization
        #  algorithm (optSTA) or the base tensile force (Grundspannung) defined
        #  by the parameter set.
        return self.optSTA or self.getParameter('SK')
    
    def prepareForCalculation(self, profileDirection=None):
        # Define min_SK as 15% lower as the machine parameter 'SK'
        SK = self.getParameter('SK')
        self.derievedParams['min_SK'] = {
            'value': int(round(SK * 0.85))
        }
        # Derive zul_SK from parameters MBK and SF_T
        mbk = self.getParameter('MBK')
        sft = self.getParameter('SF_T')
        # 'maximal zulaessige Seilzugkraft'
        self.derievedParams['zul_SK'] = {
            'value': int(round(mbk / sft))
        }
        # Derive cable area from diameter and fuellfaktor
        diameter = self.getParameter('D')
        fuellF = self.getParameter('FuellF')
        self.derievedParams['A'] = {
            'value': pi * (diameter * 0.5)**2 * fuellF
        }
        if profileDirection:
            # If the direction of the profile is already known, we can set
            #  the correct rope weights
            self.setPullRope(profileDirection)
            
        return True
            
    def updateAnchorLen(self, buffer, poletype_A, poletype_E):
        # Check buffer length
        anchor_A = self.ANCHOR_LEN if buffer[0] > self.ANCHOR_LEN else buffer[0]
        anchor_E = self.ANCHOR_LEN if buffer[1] > self.ANCHOR_LEN else buffer[1]
        # Check pole type
        if poletype_A in ['crane', 'pole_anchor']:
            anchor_A = 0
        if poletype_E == 'pole_anchor':
            anchor_E = 0
            
        self.derievedParams['d_Anker_A'] = {
            'value': anchor_A
        }
        self.derievedParams['d_Anker_E'] = {
            'value': anchor_E
        }
        
    def setPullRope(self, direction):
        seilsys = self.getParameter('Seilsys')
        qZ = self.getParameter('qZ')
        qR = self.getParameter('qR')
        if direction == 'up':
            if seilsys == 1:    # Mehrseil-System
                qz1 = qZ
                qz2 = qR
            else:               # Zweiseil-System
                msg = self.tr('Kein Zweiseil-System moeglich')
                self.onError(msg)
                return False
        elif direction == 'down':
            if seilsys == 1:    # Mehrseil-System
                qz1 = qZ
                qz2 = qR
            else:               # Zweiseil-System
                qz1 = qZ
                qz2 = 0
        else:
            return False
        self.derievedParams['qz1'] = {
            'value': qz1
        }
        self.derievedParams['qz2'] = {
            'value': qz2
        }
        return True
    
    def getSimpleParameterDict(self):
        # Shorthand dictionary for use in algorithm
        self.p = {}
        for key, p in self.params.items():
            self.p[key] = p['value']
        for key, p in self.derievedParams.items():
            self.p[key] = p['value']
        return self.p
    
    def reset(self):
        self.optSTA = None
