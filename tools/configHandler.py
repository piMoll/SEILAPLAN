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
import json

from qgis.PyQt.QtCore import QCoreApplication
from qgis.PyQt.QtWidgets import QMessageBox
from qgis.core import (QgsPointXY, QgsDistanceArea, QgsRasterLayer)

from .heightSource import AbstractHeightSource
from .raster import Raster
from .survey import SurveyData
from .profile import Profile
from .poles import Poles
from .outputReport import getTimestamp
from .outputGeo import createVirtualRaster
from ..gui.guiHelperFunctions import validateFilename
from .. import __version__ as version

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
    
    def onError(self, message=None, title=''):
        if not title:
            title = self.tr('Fehler')
        if not message:
            message = traceback.format_exc()
        QMessageBox.information(self.dialog, title, message,
                                QMessageBox.Ok)

    # noinspection PyMethodMayBeStatic
    def tr(self, message, context=None, **kwargs):
        """Get the translation for a string using Qt translation API.
        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString
        
        :param context: Context to find the translation string.
        :type context: str, QString

        :returns: Translated version of message.
        :rtype: QString

        Parameters
        ----------
        **kwargs
        """
        if not context:
            context = type(self).__name__
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate(context, message)


# noinspection PyTypeChecker
class ProjectConfHandler(AbstractConfHandler):
    
    POINT_TYPE = {
        0: 'pole',
        1: 'pole_anchor',
        2: 'crane'
    }
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
        self.virtRasterSource = []
        self.points = {
            'A': [None, None],
            'E': [None, None]
        }
        self.coordState = {
            'A': 'yellow',
            'E': 'yellow'
        }
        self.A_type = 'pole'     # pole, pole_anchor, crane
        self.E_type = 'pole'     # pole, pole_anchor
        self.profileLength = None
        self.azimut = None
        self.fixedPoles = {
            'poles': [],
            'HM_fix_d': [],
            'HM_fix_h': []
        }
        self.noPoleSection = []
        self.prHeader = {}
        
        self.profile = None
        self.poles = None
    
    def setConfigFromFile(self, settings):
        """Load configuration from json file."""
        self.setProjectName(settings['projectname'])
        self.setPrHeader(settings['header'])
        
        heightSource = settings['heightsource']
        self.setHeightSource(None, sourceType=heightSource['type'],
                             sourcePath=heightSource['source'])

        if self.heightSource and self.heightSourceType == 'survey':
            self.heightSource.reprojectToCrs(heightSource['crs'])

        self.setPoint('A', settings['profile']['start']['coordinates'])
        self.setPoint('E', settings['profile']['end']['coordinates'])
        self.A_type = settings['profile']['start']['type']
        self.E_type = settings['profile']['end']['type']

        self.setFixedPoles(settings['profile']['fixedPoles'])
        self.setNoPoleSection(settings['profile']['noPoleSection'])
    
    def setConfigFromFileOld(self, property_name, value):
        """Load settings from old style text file."""
        if property_name == 'Projektname':
            self.setProjectName(value)
        
        elif property_name == 'Hoehenmodell':
            self.setHeightSource(None, sourceType='dhm', sourcePath=value)
            
        elif property_name == 'Hoehnmodell-Liste':
            # More than one layer, saved as json array
            try:
                layerList = json.loads(value)
            except:
                self.onError(self.tr('Fehler beim Laden des Rasters'))
            else:
                self.setHeightSource(None, sourceType='dhm_list', sourcePath=layerList)
        
        elif property_name == 'Laengsprofil':
            self.setHeightSource(None, sourceType='survey', sourcePath=value)
        
        elif property_name == 'KBS':
            if self.heightSource and self.heightSourceType == 'survey':
                self.heightSource.reprojectToCrs(value)
        
        elif property_name in ['Anfangspunkt', 'Endpunkt']:
            point = property_name[0]
            [x, y] = value.split('/')
            self.setPoint(point, [x, y])
        
        elif property_name == 'Anfangspunkt-Typ':
            if value in self.POINT_TYPE.values():
                self.A_type = value
        
        elif property_name == 'Endpunkt-Typ':
            if value in self.POINT_TYPE.values():
                self.E_type = value
        
        elif property_name == 'Fixe Stuetzen':
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
        
        elif property_name == 'Keine Stuetzen':
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
    
    def getHeightSourceAsStr(self, source=False, formatting=None):
        """Get path of height model. If source is requested, return original
        raster files of virtual raster instead."""
        if source and self.virtRasterSource:
            if formatting == 'comma':
                return ', '.join(self.virtRasterSource)
            elif formatting == 'json':
                return self.virtRasterSource
            else:
                return self.virtRasterSource
        else:
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
        self.virtRasterSource = None
        srs = None
        if sourceType == 'dhm':
            srs = Raster(layer, sourcePath)
        elif sourceType == 'dhm_list':
            if layer:
                rasterList = layer
            else:
                rasterList = sourcePath
            if isinstance(rasterList, list):
                virtLayer = None
                if isinstance(rasterList[0], QgsRasterLayer):
                    # List of QGIS raster layers is provided
                    try:
                        virtLayer = createVirtualRaster(rasterList)
                        self.virtRasterSource = [
                            lyr.dataProvider().dataSourceUri() for lyr in
                            rasterList]
                    except RuntimeError:
                        self.onError(self.tr('Fehler beim Kombinieren der Rasterkacheln'))
                elif isinstance(rasterList[0], str):
                    # List of paths is provided because a project file is
                    #  loaded. We create layers first, then create virtual layer
                    layerlist = [QgsRasterLayer(path, f'Raster {i}') for i, path in enumerate(rasterList)]
                    try:
                        virtLayer = createVirtualRaster(layerlist)
                        self.virtRasterSource = rasterList
                    except RuntimeError:
                        self.onError(self.tr('Fehler beim Kombinieren der Rasterkacheln.'))
                srs = Raster(virtLayer)
        elif sourceType == 'survey':
            srs = SurveyData(sourcePath)
            if srs.valid:
                self.points = {
                    'A': [None, None],
                    'E': [None, None]
                }
        if srs and srs.valid:
            self.heightSource = srs
            self.heightSourceType = sourceType
        elif srs and srs.errorMsg:
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

    def getSettings(self):
        """Return settings in a dictionary form to save to json file."""
        return {
            'projectname': self.getProjectName(),
            'version': version,
            'header': self.prHeader,
            'heightsource': {
                'type': self.heightSourceType,
                'source': self.getHeightSourceAsStr(source=True, formatting='json'),
                'crs': self.heightSource.spatialRef.authid()
            },
            'profile': {
                'start': {
                    'coordinates': self.points['A'],
                    'type': self.A_type
                },
                'end': {
                    'coordinates': self.points['E'],
                    'type': self.E_type
                },
                'fixedPoles': self.fixedPoles['poles'],
                'noPoleSection': self.noPoleSection
            },
            'poles': self.poles.getSettings() if self.poles else []
        }
    
    def checkValidState(self):
        msg = ''
        if not self.profileIsValid():
            msg = self.tr('Bitte definieren Sie gueltige Start- und Endkoordinaten')
        if not self.projectName:
            msg = self.tr('Bitte definieren Sie einen Projektnamen')
        if msg:
            self.onError(msg, self.tr('Ungueltige Daten'))
        return self.profileIsValid() and self.projectName
    
    def getPointTypeAsIdx(self, point):
        if point == 'A':
            currentPtype = self.A_type
        elif point == 'E':
            currentPtype = self.E_type
        else:
            return False
        for key, ptype in self.POINT_TYPE.items():
            if currentPtype == ptype:
                return key
    
    def setPointType(self, point, typeIdx):
        if isinstance(typeIdx, int):
            pType = self.POINT_TYPE[typeIdx]
        else:
            pType = typeIdx
        if point == 'A':
            self.A_type = pType
        elif point == 'E':
            self.E_type = pType

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
    
    def preparePreviewProfile(self):
        if not self.profileIsValid():
            return False
        self.heightSource.prepareData(self.points, self.azimut, self.params.ANCHOR_LEN)
        try:
            profile = Profile(self)
        except ValueError:
            self.onError(self.tr('Unerwarteter Fehler bei der Erstellung des Profils.'))
            return False
        if self.heightSource.errorMsg:
            self.onError(self.heightSource.errorMsg)
        return profile

    def setPrHeader(self, prHeaderData):
        self.prHeader = prHeaderData
    
    def prepareForCalculation(self):
        success = True
        # Prepare raster (create subraster) or interpolate survey data
        self.heightSource.prepareData(self.points, self.azimut,
                                      self.params.ANCHOR_LEN)
        
        # Anchor length is shortened in case the height source has not enough
        #  data to extract terrain data for anchor field. Also, anchor is
        #  0m when pole type is crane or anchor.
        self.params.updateAnchorLen(self.heightSource.buffer, self.A_type, self.E_type)

        # Create profile line from subraster or survey data
        try:
            self.profile = Profile(self)
        except ValueError:
            self.onError(self.tr('Unerwarteter Fehler bei Erstellung des Profils'))
            return False
        if self.heightSource.errorMsg:
            self.onError(self.heightSource.errorMsg)
            return False
        # Now that height of point A and B is known, pull rope forces are
        #  calculated
        if not self.params.setPullRope(self.profile.direction):
            return False
        
        # Initialize pole data (start/end point and anchors)
        try:
            self.poles = Poles(self)
        except ValueError:
            self.onError(self.tr('Unerwarteter Fehler bei Erstellung des Profils'))
            return False
        return success
    
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
    
    SEILSYS_TYPES = {
        0: 'Zweiseil-System',
        1: 'Mehrseil-System'
    }
    ANCHOR_LEN = 20
    SETS_PATH = os.path.join(HOMEPATH, '../config', 'parametersets')
    
    def __init__(self):
        AbstractConfHandler.__init__(self)
        
        # Parameters
        self.params = {}
        self.derievedParams = {}
        self.paramOrder = []
        # Short-hand dictionary for use in algorithm
        self.p = {}
        # Optimal cable tension (result of optimization or user input)
        self.optSTA = None
        
        # Parameter sets
        self.currentSetName = ''
        self.parameterSets = {}
        self.defaultSet = self.tr('Standardparameter')
    
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
            self.onError()
            return {}
    
    def getParameter(self, property_name):
        try:
            return self.params[property_name]['value']
        except KeyError:
            # Try to find parameter in derived parameter dictionary
            return self.derievedParams[property_name]['value']
    
    def getParameterAsStr(self, property_name):
        p = self._getParameterInfo(property_name)
        if not p:
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
        p = self._getParameterInfo(property_name)
        if not p:
            return False
        if p['ftype'] == 'drop_field' and property_name == 'Seilsys':
            value = self.getSeilsysAsIdx(value)
        cval = self.castToNumber(p['dtype'], value)
        self.params[property_name]['value'] = cval
    
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
        fileName = validateFilename(setname)
        savePath = os.path.join(self.SETS_PATH, f'{fileName}.txt')
        with io.open(savePath, encoding='utf-8', mode='w') as f:
            # Write header
            f.writelines('name\tvalue\n')
            f.writelines('label\t' + setname + '\n')
            # Write parameter values
            for property_name, value in self.parameterSets[setname].items():
                f.writelines(f"{property_name}\t{value}\n")
    
    def removeParameterSet(self, setname):
        fileName = validateFilename(setname)
        savePath = os.path.join(self.SETS_PATH, f'{fileName}.txt')
        if not os.path.isfile(savePath):
            return False
        # Remove file on disk
        os.remove(savePath)
        # Remove set from parameter handler
        del self.parameterSets[setname]
        return True
    
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
        if optSTA:
            self.optSTA = int(round(float(optSTA)))
    
    def prepareForCalculation(self):
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
        # Short-hand dictionary for use in algorithm
        self.p = {}
        for key, p in self.params.items():
            self.p[key] = p['value']
        for key, p in self.derievedParams.items():
            self.p[key] = p['value']
        return self.p
    
    def reset(self):
        self.optSTA = None


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
        
        self.polesFromTxt = []
        
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
            self.project.setConfigFromFile(settings)
            
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
                
            # Poles
            self.polesFromTxt = settings['poles']
        
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
                self.polesFromTxt.append({
                    'idx': int(parts[0]),
                    'd': int(float(parts[1])),
                    'h': float(parts[2]),
                    'angle': float(parts[3]),
                    'manually': True if int(parts[4]) == 1 else False,
                    'poleType': parts[5],
                    'active': True if int(parts[6]) == 1 else False,
                    'name': parts[7]
                })

        self.polesFromTxt = []
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
            json.dump(settings, f, ensure_ascii=False, indent=4)
    
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
        if self.polesFromTxt:
            status = 'savedFile'
            self.project.poles.updateAllPoles(status, self.polesFromTxt)
        # If instead user has defined some fixed poles, add these to Poles()
        elif len(self.project.fixedPoles['poles']) > 0:
            self.project.poles.updateAllPoles(status, self.project.fixedPoles['poles'])
        
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
