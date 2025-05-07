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
from math import atan2, pi, cos, sin
import json
from qgis.core import (QgsPointXY, QgsDistanceArea, QgsRasterLayer)
from .configHandler_abstract import AbstractConfHandler
from .configHandler_params import ParameterConfHandler
from .heightSource import AbstractHeightSource
from .raster import Raster
from .survey import SurveyData
from .profile import Profile
from .poles import Poles
from .outputGeo import createVirtualRaster
from .globals import PolesOrigin
from SEILAPLAN import __version__ as version


def castToNum(formattedNum):
    if type(formattedNum) in [int, float]:
        return formattedNum
    try:
        num = float(formattedNum.replace("'", ''))
    except (ValueError, AttributeError):
        num = None
    return num


class ProjectConfHandler(AbstractConfHandler):
    
    # Order of pole types in drop down list
    POINT_TYPE = {
        0: 'pole_anchor',
        1: 'pole',
        2: 'crane'
    }

    def __init__(self, params: ParameterConfHandler):
        """
        :type params: tools.configHandler_params.ParamConfHandler
        """
        AbstractConfHandler.__init__(self)
        
        self.params: ParameterConfHandler = params
        
        # Project data
        self.projectName = None
        self.heightSource: AbstractHeightSource = None
        self.heightSourceType = None
        self.surveyType = None
        self.virtRasterSource = []
        self.points = {
            'A': [None, None],
            'E': [None, None]
        }
        self.coordState = {
            'A': 'yellow',
            'E': 'yellow'
        }
        self.A_type = 'pole_anchor'     # pole_anchor, pole, crane
        self.E_type = 'pole_anchor'     # pole_anchor, pole,
        self.profileLength = None
        self.azimut = None
        self.fixedPoles = {
            'poles': [],
            'HM_fix_d': [],
            'HM_fix_h': []
        }
        self.noPoleSection = []
        self.prHeader = {}
        
        self.profile: Profile = None
        self.poles: Poles = None
        # Poles from a loaded project file
        self.polesFromFile = []
    
    def setConfigFromFile(self, settings):
        """Load configuration from json file."""
        self.setProjectName(settings['projectname'])
        self.setPrHeader(settings['header'])
        
        heightSource = settings['heightsource']
        surveyType = None
        if 'surveyType' in heightSource:
            surveyType = heightSource['surveyType']
        self.setHeightSource(None, sourceType=heightSource['type'],
                             sourcePath=heightSource['source'],
                             surveySourceType=surveyType)
        
        if self.heightSource and self.heightSourceType == 'survey':
            self.heightSource: SurveyData
            self.heightSource.reprojectToCrs(heightSource['crs'])

        self.setPoint('A', settings['profile']['start']['coordinates'])
        self.setPoint('E', settings['profile']['end']['coordinates'])
        self.A_type = settings['profile']['start']['type']
        self.E_type = settings['profile']['end']['type']

        self.setFixedPoles(settings['profile']['fixedPoles'])
        self.setNoPoleSection(settings['profile']['noPoleSection'])
        
        self.polesFromFile = settings['poles']
        return True
    
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
                self.heightSource: SurveyData
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
        timestamp = time.strftime("%Y%m%d_%H%M", time.localtime(now))
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
    
    def setHeightSource(self, layer, sourceType='dhm', sourcePath=None,
                        surveySourceType=None):
        """Raster can be set by providing the QGIS Raster Layer or by giving
        the path to the raster file.
        :param layer: QGIS layer object
        :param sourceType: dhm or survey
        :param sourcePath: path to file
        :param surveySourceType: Type of survey file to load
         """
        self.resetHeightSource()
        heights = None
        if sourceType == 'dhm':
            heights = Raster(layer, sourcePath)
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
                    layerlist = []
                    for i, path in enumerate(rasterList):
                        if not os.path.exists(path):
                            self.onError(self.tr("Raster-Datei _path_ ist "
                                "nicht vorhanden, Raster kann nicht geladen "
                                "werden.").replace('_path_', path))
                            break
                        else:
                            layerlist.append(QgsRasterLayer(path, f'Raster {i}'))
                    try:
                        if layerlist:
                            virtLayer = createVirtualRaster(layerlist)
                            self.virtRasterSource = rasterList
                    except RuntimeError:
                        self.onError(self.tr('Fehler beim Kombinieren der Rasterkacheln.'))
                heights = Raster(virtLayer)
        elif sourceType == 'survey':
            heights = SurveyData(sourcePath, surveySourceType)
            if heights.valid:
                self.points = {
                    'A': [None, None],
                    'E': [None, None]
                }
                self.surveyType = heights.sourceType
                if heights.prHeaderData:
                    self.setPrHeader(heights.prHeaderData['Header'])
                    self.params.setParameter('Anlagetyp', heights.prHeaderData['Anlagetyp'])
                
        if heights and heights.valid:
            self.heightSource = heights
            self.heightSourceType = sourceType
        if heights and heights.errorMsg:
            self.onError(heights.errorMsg)
            heights.errorMsg = ''
        
        # Points are either empty (raster) or they are the first and last point
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
    
    def profilePointsAreValid(self):
        return self.coordState['A'] == self.coordState['E'] == 'green'
    
    def getAzimut(self):
        return '' if self.azimut is None else self.azimut

    # noinspection PyUnresolvedReferences
    def setAzimut(self):
        azimut = None
        if self.profilePointsAreValid():
            azimut = atan2(self.points['E'][0] - self.points['A'][0],
                           self.points['E'][1] - self.points['A'][1])
            if self.points['E'][0] - self.points['A'][0] < 0:
                azimut += 2*pi
        self.azimut = azimut
    
    def getProfileLenAsStr(self):
        return '' if self.profileLength is None else f"{self.profileLength:.0f}"

    # noinspection PyUnresolvedReferences
    def setProfileLen(self):
        length = None
        if self.profilePointsAreValid():
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
                'surveyType': self.surveyType,
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
        if not self.projectName:
            msg = self.tr('Bitte definieren Sie einen Projektnamen')
        elif not self.heightSource:
            msg = self.tr('Bitte definieren Sie Terraindaten')
        elif not self.profilePointsAreValid():
            if self.heightSourceType == 'survey':
                msg = self.tr('Bitte zeichnen Sie Start- und Endpunkt der Seillinie in die Karte ein (Schaltflaeche zeichnen)')
            else:
                msg = self.tr('Bitte zeichnen Sie die Seillinie in die Karte (Schaltflaeche zeichnen) oder definieren sie Start- und Endkoordinaten manuell')
        if msg:
            self.onError(msg, self.tr('Ungueltige Daten'))
        return self.profilePointsAreValid() and self.projectName
    
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
        
        # Reset in-between poles, so they don't hang around after start or
        #  end pole has been changed
        self.resetPoles()
        
    @staticmethod
    def formatCoordinate(number, digits=1):
        """Format coordinates to one digit except otherwise"""
        if number is None:
            return ''
        try:
            return str(round(number, digits))
        except ValueError:
            return ''
    
    def preparePreviewProfile(self):
        if not self.profilePointsAreValid():
            return False
        self.heightSource.prepareData(self.points, self.azimut, self.params.ANCHOR_LEN)
        try:
            profile = Profile(self)
        except Exception as e:
            self.onError(f"{self.tr('Unerwarteter Fehler bei der Erstellung des Profils.')}\n{e}")
            return False
        if self.heightSource.errorMsg:
            self.onError(self.heightSource.errorMsg)
        return profile

    def setPrHeader(self, prHeaderData):
        self.prHeader = {}
        if not isinstance(prHeaderData, dict):
            return
        for propName, value in prHeaderData.items():
            try:
                self.prHeader[propName] = str(value)
            except ValueError:
                self.prHeader[propName] = ''
    
    def prepareForCalculation(self, runOptimization):
        success = True
        # Prepare raster (create subraster) or interpolate survey data
        try:
            self.heightSource.prepareData(self.points, self.azimut,
                                          self.params.ANCHOR_LEN)
        except Exception:
            self.onError(self.tr('Unerwarteter Fehler bei Erstellung des Profils'))
            return False
        
        # Anchor length is shortened in case the height source has not enough
        #  data to extract terrain data for anchor field. Also, anchor is
        #  0m when pole type is crane or anchor.
        self.params.updateAnchorLen(self.heightSource.buffer, self.A_type, self.E_type)

        # Create profile line from subraster or survey data
        try:
            self.profile = Profile(self)
        except Exception:
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
            if not runOptimization:
                self.updatePoles()
        except ValueError:
            self.onError(self.tr('Unerwarteter Fehler bei Erstellung der Stuetzen'))
            return False
        return success
    
    def updatePoles(self):
        """Create poles from a saved project or from fixed poles. Don't call
        this function if the optimization algorithm is going to run."""
        if self.polesFromFile:
            self.poles.updateAllPoles(PolesOrigin.SavedFile, self.polesFromFile)
        # If instead user has defined some fixed poles, add these to Poles()
        #  (if the saved file included fixed poles, they would already be part of self.poles)
        elif len(self.fixedPoles['poles']) > 0:
            self.poles.updateAllPoles(PolesOrigin.OnlyStartEnd, self.fixedPoles['poles'])
    
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
        self.resetPoles()
    
    def resetHeightSource(self):
        del self.heightSource
        self.heightSource = None
        self.heightSourceType = None
        self.surveyType = None
        self.virtRasterSource = None
    
    def resetPoles(self):
        self.poles = None
        self.polesFromFile = []
