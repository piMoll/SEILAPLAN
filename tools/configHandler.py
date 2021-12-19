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
import numpy
import time
import json

from .projectHandler import ProjectConfHandler
from .paramHandler import ParameterConfHandler
from .outputReport import getTimestamp

# Constants
HOMEPATH = os.path.join(os.path.dirname(__file__))


class ConfigHandler(object):
    
    SETTINGS_FILE = os.path.join(HOMEPATH, '../config', 'commonPaths.txt')
    DEFAULT_SAVE_PATH = os.path.join(os.path.expanduser('~'), 'Seilaplan')
    
    def __init__(self):
        self._config = {}
        
        # User settings
        self.commonPaths = []
        self.outputOptions = {
            'report': 0,
            'plot': 1,
            'geodata': 0,
            'coords': 0,
            'shortReport': 1,
            'kml': 0
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
    
    def loadSettings(self, filename):
        """ Load settings from a json file (new since version 3.3) or an
        old-style text file."""
        success = False
        if filename.endswith('.txt'):
            # Backwards compatibility
            success = self.loadFromTxtFile(filename)
        elif filename.endswith('.json'):
            success = self.loadFromJsonFile(filename)
        return success
    
    def loadFromJsonFile(self, filename):
        """Read out settings from a strucutred json file."""
        if not os.path.exists(filename):
            return False
        
        with open(filename) as f:
            try:
                settings = json.load(f)
            except ValueError:
                return False
            
            # Projekt
            prLoadSuccessful = self.project.setConfigFromFile(settings)
            if not prLoadSuccessful:
                return prLoadSuccessful
            
            # Parameters
            ##
            params = settings['params']
            
            # Set name
            if params['setname'] not in self.params.parameterSets.keys():
                # Save new parameter set
                self.params.saveParameterSet(params['setname'])
            self.params.currentSetName = params['setname']
            # Opt STA
            self.params.setOptSTA(params['optSTA'])
            # Parameter list
            for p in params['parameterList']:
                self.params.batchSetParameter(p['name'], p['value'])
        
        success = self.params.checkValidState()
        return success

    def loadFromTxtFile(self, filename):
        """Old way of reading out settings from a text file."""
        
        def readOutProjectData(lines, lineNr):
            for line in lines[lineNr:]:
                lineNr += 1
                if line == '':
                    return lineNr
                parts = re.split(r'\s{3,}', line)
                [property_name, data] = parts
                self.project.setConfigFromFileOld(property_name, data)
        
        def readOutParamData(lines, lineNr):
            for line in lines[lineNr:]:
                lineNr += 1
                if line == '':
                    return lineNr
                part = re.split(r'\s{3,}', line)
                if len(part) <= 1:
                    continue
                if part[1] == '-':
                    part[1] = ''
                # Backwards compatibility to load older project files
                if part[0] == 'min_SK':
                    part[0] = 'SK'
                elif part[0] == 'optSTA':
                    self.params.setOptSTA(part[1])
                    continue
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
                if len(parts) != 8:
                    continue
                self.project.polesFromTxt.append({
                    'idx': int(parts[0]),
                    'd': int(float(parts[1])),
                    'h': float(parts[2]),
                    'angle': float(parts[3]),
                    'manually': True if int(parts[4]) == 1 else False,
                    'poleType': parts[5],
                    'active': True if int(parts[6]) == 1 else False,
                    'name': parts[7]
                })

        self.project.polesFromTxt = []
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
    
    def saveSettings(self, filename):
        """Save settings to json file."""
        projectSettings = self.project.getSettings()
        paramSettings = self.params.getSettings()
        settings = {**projectSettings, **paramSettings}
        
        if os.path.exists(filename):
            os.remove(filename)

        with open(filename, 'w', encoding='utf8') as f:
            json.dump(settings, f, ensure_ascii=False, indent=4, cls=OwnJsonEncoder)
    
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
                        'report': (outputOpts[0] if len(outputOpts) >= 0 else 0),
                        'plot': (outputOpts[1] if len(outputOpts) >= 1 else 1),
                        'geodata': (outputOpts[2] if len(outputOpts) >= 2 else 0),
                        'coords': (outputOpts[3] if len(outputOpts) >= 3 else 0),
                        'shortReport': (outputOpts[4] if len(outputOpts) >= 4 else 1),
                        'kml': (outputOpts[5] if len(outputOpts) >= 5 else 0),
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
                "{} {} {} {} {} {} {}".format(self.outputOptions['report'],
                                        self.outputOptions['plot'],
                                        self.outputOptions['geodata'],
                                        self.outputOptions['coords'],
                                        self.outputOptions['shortReport'],
                                        self.outputOptions['kml'],
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
        success = self.params.prepareForCalculation()
        if success:
            success = self.project.prepareForCalculation()
        return success
    
    def loadCableDataFromFile(self):
        status = 'jumpedOver'
        
        # If the project file already contains pole data from an earlier run,
        # load this data into Poles()
        status = self.project.updatePoles(status)
        
        # Set optimized cable tension
        if status == 'savedFile' and self.params.optSTA:
            # Use the saved parameter from save file
            optSTA = self.params.optSTA
        else:
            # Use machine parameter 'SK'
            optSTA = self.params.getParameter('SK')
            self.params.setOptSTA(optSTA)
        
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


class OwnJsonEncoder(json.JSONEncoder):
    """Used to serialize numpy int32 or float64 values to regular types
    so that they can be written to json file."""
    def default(self, obj):
        if isinstance(obj, numpy.integer):
            return int(obj)
        elif isinstance(obj, numpy.floating):
            return float(obj)
        elif isinstance(obj, numpy.ndarray):
            return obj.tolist()
        else:
            return super(OwnJsonEncoder, self).default(obj)
