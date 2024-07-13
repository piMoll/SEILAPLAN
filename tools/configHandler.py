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

from qgis.PyQt.QtCore import QSettings
from qgis.core import QgsSettings

from .configHandler_project import ProjectConfHandler
from .configHandler_params import ParameterConfHandler
from .outputReport import getTimestamp

# Constants
HOMEPATH = os.path.join(os.path.dirname(__file__))


class ConfigHandler(object):
    
    DEFAULT_SAVE_PATH = os.path.join(os.path.expanduser('~'), 'Seilaplan')
    SETTING_PREFIX = 'PluginSeilaplan/output/'
    TEMPLATES_URL = 'https://raw.githubusercontent.com/piMoll/SEILAPLAN/master/templates/'
    TEMPLATE_FILENAME = {
        'excelProtocol': {
            'de': 'DE_Vorlage_Feldaufnahmeprotokoll.xlsx',
            'en': 'EN_Template_field_survey_protocol.xlsx',
            'fr': 'FR_Modèle_protocol_de_relevé_sur_le_terrain.xlsx',
            'it': 'IT_Template_protocollo_di_rilievo_sul_terreno.xlsx',
        },
        'csvXyz': {
            'de': 'DE_Vorlage_Gelaendeprofil_XYZ.csv',
            'en': 'EN_Template_terrain_profile_XYZ.csv',
            'fr': 'FR_Modèle_profil_de_terrain_XYZ.csv',
            'it': 'IT_Template_profilo_del_terreno_XYZ.csv',
        }
    }
    
    def __init__(self):
        self._config = {}
        
        # User settings
        self.commonPaths = []
        self.outputOptions = {}
        self.userSettingsHaveChanged = False
        
        self.params = ParameterConfHandler()
        self.project = ProjectConfHandler(self.params)
        
        # Load parameter definitions and predefined parameter sets
        self.qgsSettingsMigrator()
        self.loadUserSettings()
        self.params.initParameters()
        self.params.loadPredefinedParametersets()
        self.params.loadParametersetsFromSettings()
        
        # Remember if this is data loaded from a project file. It's used to
        #  later show the correct message in the adjustment window
        self.fromSavedProject = False
    
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
        if success:
            self.fromSavedProject = True
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
            try:
                prLoadSuccessful = self.project.setConfigFromFile(settings)
                if not prLoadSuccessful:
                    return prLoadSuccessful
            except KeyError:
                return False
            
            # Parameters
            ##
            
            # Reset params to standard values
            self.params.setParameterSet(self.params.defaultSet)
            
            params = settings['params']
            
            # Parameter list
            for p in params['parameterList']:
                self.params.batchSetParameter(p['name'], p['value'])
            # Opt STA
            self.params.setOptSTA(params['optSTA'])

            # Set name
            if params['setname'] not in self.params.parameterSets.keys():
                # Save new parameter set
                self.params.saveParameterSet(params['setname'])
            self.params.currentSetName = params['setname']
        
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
                self.project.polesFromFile.append({
                    'idx': int(parts[0]),
                    'd': int(float(parts[1])),
                    'h': float(parts[2]),
                    'angle': float(parts[3]),
                    'manually': True if int(parts[4]) == 1 else False,
                    'poleType': parts[5],
                    'active': True if int(parts[6]) == 1 else False,
                    'name': parts[7]
                })

        self.project.polesFromFile = []
        lineCount = 0
        if os.path.exists(filename):
            with io.open(filename, encoding='utf-8') as f:
                allLines = f.read().splitlines()

                # Reset params to standard values. This will asure missing
                #  params will be reset or emptied (e.g. Anlagetyp)
                self.params.setParameterSet(self.params.defaultSet)
                
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
        # Read out output settings from QGIS settings, provide default value
        #  if settings key does not exist
        s = QgsSettings()
        self.outputOptions = {
            'report': s.value(f'{self.SETTING_PREFIX}report', 0, int),
            'shortReport': s.value(f'{self.SETTING_PREFIX}shortReport', 1, int),
            'plot': s.value(f'{self.SETTING_PREFIX}plot', 1, int),
            'birdView': s.value(f'{self.SETTING_PREFIX}birdView', 1, int),
            'birdViewLegend': s.value(f'{self.SETTING_PREFIX}birdViewLegend', 0, int),
            'shape': s.value(f'{self.SETTING_PREFIX}shape', 0, int),
            'csv': s.value(f'{self.SETTING_PREFIX}csv', 0, int),
            'kml': s.value(f'{self.SETTING_PREFIX}kml', 0, int),
            'dxf': s.value(f'{self.SETTING_PREFIX}dxf', 0, int),
        }
        for path in [
                s.value(f'{self.SETTING_PREFIX}savePath1'),
                s.value(f'{self.SETTING_PREFIX}savePath2'),
                s.value(f'{self.SETTING_PREFIX}savePath3')]:
            if path and os.path.exists(path):
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
        # Maximum length of drop down menu is 3 entries
        if len(self.commonPaths) > 3:
            del self.commonPaths[0]  # Delete oldest entry
        
        s = QgsSettings()
        s.setValue(f'{self.SETTING_PREFIX}report', self.outputOptions['report'])
        s.setValue(f'{self.SETTING_PREFIX}shortReport', self.outputOptions['shortReport'])
        s.setValue(f'{self.SETTING_PREFIX}plot', self.outputOptions['plot'])
        s.setValue(f'{self.SETTING_PREFIX}birdView', self.outputOptions['birdView'])
        s.setValue(f'{self.SETTING_PREFIX}birdViewLegend', self.outputOptions['birdViewLegend'])
        s.setValue(f'{self.SETTING_PREFIX}shape', self.outputOptions['shape'])
        s.setValue(f'{self.SETTING_PREFIX}csv', self.outputOptions['csv'])
        s.setValue(f'{self.SETTING_PREFIX}kml', self.outputOptions['kml'])
        s.setValue(f'{self.SETTING_PREFIX}dxf', self.outputOptions['dxf'])
        if len(self.commonPaths) > 0:
            s.setValue(f'{self.SETTING_PREFIX}savePath1', self.commonPaths[0])
        if len(self.commonPaths) > 1:
            s.setValue(f'{self.SETTING_PREFIX}savePath2', self.commonPaths[1])
        if len(self.commonPaths) > 2:
            s.setValue(f'{self.SETTING_PREFIX}savePath3', self.commonPaths[2])
    
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
    
    def getTemplateUrl(self, template):
        locale = 'en'
        qgisLocale = QSettings().value("locale/userLocale")
        if qgisLocale and len(qgisLocale) >= 2:
            locale = qgisLocale[0:2].lower()
            if locale not in self.TEMPLATE_FILENAME[template]:
                locale = 'en'
        filename = self.TEMPLATE_FILENAME[template][locale]
        url = self.TEMPLATES_URL + filename
        return url, filename
    
    def setOutputOptions(self, outputOptions):
        self.outputOptions = outputOptions
        self.userSettingsHaveChanged = True
    
    def checkValidState(self):
        return self.project.checkValidState() and self.params.checkValidState()
    
    def prepareForCalculation(self, runOptimization=False):
        """
        Updates some parameters and generates the subraster and profile line.
        Initializes pole data.
        :return:
        """
        success = self.params.prepareForCalculation()
        if success:
            success = self.project.prepareForCalculation(runOptimization)
        return success
    
    def prepareResultWithoutOptimization(self):
        self.project.updatePoles()
        return {
            'cableline': None,
            'optSTA': self.params.getTensileForce(),
            'optSTA_arr': [self.params.getTensileForce()],
            'force': None,
            'optLen': None,
            'duration': getTimestamp(time.time())
        }, 'savedFile' if self.fromSavedProject else 'jumpedOver'
    
    def reset(self):
        self.project.reset()
        self.params.reset()
        self.fromSavedProject = False
    
    def qgsSettingsMigrator(self):
        """Migrates settings to be up-to-date with the current Seilaplan
        version"""
        s = QgsSettings()
        migrations = [
            {'old': 'coords', 'new': 'csv', 'default': 0},
            {'old': 'geodata', 'new': 'shape', 'default': 0},
        ]
        
        for migration in migrations:
            newVal = s.value(f"{self.SETTING_PREFIX}{migration['new']}", -1, int)
            if newVal == -1:
                # New value not there yet, migrate!
                oldVal = s.value(f"{self.SETTING_PREFIX}{migration['old']}",
                                 migration['default'], int)
                # Update settings
                s.setValue(f"{self.SETTING_PREFIX}{migration['new']}", oldVal)
                # Delete old key
                s.remove(f"{self.SETTING_PREFIX}{migration['old']}")


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
