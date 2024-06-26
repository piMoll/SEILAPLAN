from math import cos, sin, atan, floor, radians, degrees
import numpy as np
from qgis.PyQt.QtCore import QCoreApplication


# Notwendiger BHD [cm]: { Angriffswinkel (kleiner als 10) [°]: Tragkraft Ankerbaum [kn], ...}
#   Angriffswinkel 0 - 10°: guenstig
#   Angriffswinkel 10 - 25°: normal
#   Angriffswinkel 25 - 45°: kritisch
BHD_ANCHOR = {
    10: {29: 24, 51: 32, 80: 40, 115: 48, 135: 52, 157: 56, 169: 58, 190: 60, 215: 65},
    25: {19: 24, 34: 32, 53: 40, 77: 48, 90: 52, 105: 56, 112: 58, 120: 60, 145: 65},
    45: {15: 24, 25: 32, 40: 40, 55: 48, 65: 52, 80: 56, 85: 58, 90: 60, 110: 65}
}

# Sattelkraft [kN]: { Hoehe_Stuetze [m]: Durchmesser Bundstelle [cm]}
BHD_POLE = {
    10: {5: 11, 6: 12, 7: 13, 8: 13, 9: 14, 10: 14, 11: 15, 12: 15, 13: 16, 14: 16, 15: 16, 16: 16, 17: 17, 18: 17, 19: 17, 20: 17, 22: 18, 24: 18, 26: 18, 28: 18, 30: 18},
    20: {5: 14, 6: 15, 7: 16, 8: 17, 9: 17, 10: 18, 11: 19, 12: 19, 13: 20, 14: 20, 15: 21, 16: 21, 17: 21, 18: 22, 19: 22, 20: 22, 22: 23, 24: 23, 26: 24, 28: 24, 30: 24},
    30: {5: 16, 6: 17, 7: 18, 8: 19, 9: 20, 10: 20, 11: 21, 12: 22, 13: 22, 14: 23, 15: 23, 16: 24, 17: 24, 18: 25, 19: 25, 20: 26, 22: 26, 24: 27, 26: 28, 28: 28, 30: 28},
    40: {5: 17, 6: 18, 7: 19, 8: 20, 9: 21, 10: 22, 11: 23, 12: 24, 13: 24, 14: 25, 15: 26, 16: 26, 17: 27, 18: 27, 19: 28, 20: 28, 22: 29, 24: 30, 26: 31, 28: 31, 30: 31},
    50: {5: 18, 6: 19, 7: 21, 8: 22, 9: 23, 10: 24, 11: 25, 12: 25, 13: 26, 14: 27, 15: 28, 16: 28, 17: 29, 18: 29, 19: 30, 20: 30, 22: 31, 24: 32, 26: 33, 28: 34, 30: 34},
    60: {5: None, 6: 20, 7: 22, 8: 23, 9: 24, 10: 25, 11: 26, 12: 27, 13: 28, 14: 29, 15: 29, 16: 30, 17: 31, 18: 31, 19: 32, 20: 32, 22: 33, 24: 34, 26: 35, 28: 36, 30: 36},
    70: {5: None, 6: 21, 7: 23, 8: 24, 9: 25, 10: 26, 11: 27, 12: 28, 13: 29, 14: 30, 15: 31, 16: 31, 17: 32, 18: 33, 19: 33, 20: 34, 22: 35, 24: 36, 26: 37, 28: 38, 30: 38},
    80: {5: None, 6: None, 7: 24, 8: 25, 9: 26, 10: 27, 11: 28, 12: 29, 13: 30, 14: 31, 15: 32, 16: 33, 17: 34, 18: 34, 19: 35, 20: 36, 22: 37, 24: 38, 26: 39, 28: 40, 30: 40},
    90: {5: None, 6: None, 7: 24, 8: 26, 9: 27, 10: 28, 11: 29, 12: 30, 13: 31, 14: 32, 15: 33, 16: 34, 17: 35, 18: 36, 19: 36, 20: 37, 22: 38, 24: 39, 26: 40, 28: 41, 30: 42},
    100: {5: None, 6: None, 7: 25, 8: 27, 9: 28, 10: 29, 11: 30, 12: 31, 13: 32, 14: 33, 15: 34, 16: 35, 17: 36, 18: 37, 19: 37, 20: 38, 22: 39, 24: 41, 26: 42, 28: 43, 30: 43},
    110: {5: None, 6: None, 7: None, 8: 27, 9: 29, 10: 30, 11: 31, 12: 32, 13: 33, 14: 34, 15: 35, 16: 36, 17: 37, 18: 38, 19: 39, 20: 39, 22: 41, 24: 42, 26: 43, 28: 44, 30: 45},
    120: {5: None, 6: None, 7: None, 8: 28, 9: 29, 10: 31, 11: 32, 12: 33, 13: 34, 14: 35, 15: 36, 16: 37, 17: 38, 18: 39, 19: 40, 20: 40, 22: 42, 24: 43, 26: 44, 28: 45, 30: 46},
    130: {5: None, 6: None, 7: None, 8: 29, 9: 30, 10: 31, 11: 33, 12: 34, 13: 35, 14: 36, 15: 37, 16: 38, 17: 39, 18: 40, 19: 41, 20: 41, 22: 43, 24: 44, 26: 45, 28: 47, 30: 47},
    140: {5: None, 6: None, 7: None, 8: None, 9: 31, 10: 32, 11: 34, 12: 35, 13: 36, 14: 37, 15: 38, 16: 39, 17: 40, 18: 41, 19: 42, 20: 42, 22: 44, 24: 45, 26: 47, 28: 48, 30: 48},
    150: {5: None, 6: None, 7: None, 8: None, 9: 31, 10: 33, 11: 34, 12: 35, 13: 36, 14: 38, 15: 39, 16: 40, 17: 41, 18: 41, 19: 42, 20: 43, 22: 45, 24: 46, 26: 48, 28: 49, 30: 49}
}
BHD_POLE_Force = np.array(list(BHD_POLE.keys()))


class Poles(object):
    
    INIT_POLE_HEIGHT = 12.0
    INIT_POLE_ANGLE = 0.0
    POLE_DIST_STEP = 1.0
    POLE_HEIGHT_STEP = 0.1
    POLE_NAME_MAX_LENGTH = 42
    
    def __init__(self, project):
        """
        :type project: projectHandler.ProjectConfHandler
        """
        self.params = project.params
        self.heightSource = project.heightSource
        [self.Ax, self.Ay] = project.points['A']
        [self.Ex, self.Ey] = project.points['E']
        self.azimut = project.azimut
        self.A_type = project.A_type
        self.E_type = project.E_type
        self.anchor = {}
        self.poles = []
        self.firstPole = None
        self.lastPole = None
        self.idxA = None
        self.idxE = None
        self.hasAnchorA = False
        self.hasAnchorE = False
        self.direction = None
        
        # Default height for different pole types
        height = {
            'pole': self.INIT_POLE_HEIGHT,
            'pole_anchor': 0,
            'crane': self.params.getParameter('HM_Kran')
        }
        self.anchorA = self.params.getParameter('d_Anker_A')
        self.anchorE = self.params.getParameter('d_Anker_E')
        
        # End point is slightly moved (less than a meter) so that it is the
        # last point on profile with step size of 1m
        self.profileLength = floor(project.profileLength)
        
        idx = 0
        nameA = self.tr('Anfangsstuetze') if self.A_type == 'pole' else None
        nameE = self.tr('Endstuetze') if self.E_type == 'pole' else None
        if self.A_type == 'pole':
            # Anchor at start point
            self.add(idx, -1*self.anchorA, 0, poleType='anchor', refresh=False)
            idx = 1
        # First pole at 0 m horizontal distance
        self.add(idx, 0, height[self.A_type], poleType=self.A_type, name=nameA,
                 refresh=False)
        # Last pole
        self.add(idx+1, self.profileLength, height[self.E_type],
                 poleType=self.E_type, name=nameE, refresh=False)
        if self.E_type == 'pole':
            # Anchor at end point
            self.add(idx+2, self.profileLength + self.anchorE, 0,
                     poleType='anchor', refresh=False)
        self.refresh()

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

    def add(self, idx, d, h=INIT_POLE_HEIGHT, angle=INIT_POLE_ANGLE,
            manually=False, poleType='pole', active=True, name='',
            category=None, position=None, abspann=None, refresh=True):
       
        if d is None:
            leftPole = self.poles[idx-1]['d']
            rightPole = self.poles[idx]['d']
            distRange = rightPole - leftPole
            d = floor(leftPole + 0.5 * distRange)
        d = float(d)
        
        if h == -1:
            h = self.INIT_POLE_HEIGHT
        h = float(h)
        
        x, y, z, dtop, ztop = self.derivePoleProperties(d, h, angle)
        if not name:
            name = self.tr('Stuetze')
            if manually:
                name = self.tr('neue Stuetze')
            if poleType in ['anchor', 'pole_anchor']:
                name = self.tr('Verankerung')
            elif poleType == 'crane':
                name = self.tr('Seilkran')
        
        self.poles.insert(idx, {
            'name': name,
            'nr': str(idx),
            'poleType': poleType,
            'd': d,
            'z': z,
            'h': h,
            'angle': angle,
            'dtop': dtop,
            'ztop': ztop,
            'coordx': x,
            'coordy': y,
            'manually': manually,
            'active': active,
            'category': category,
            'position': position,
            'abspann': abspann,
            'BHD': np.nan,
            'bundstelle': np.nan,
            'angriff': np.nan,
            'maxForce': np.nan,
        })
        if refresh:
            self.refresh()

    def update(self, idx, property_name, newVal):
        self.poles[idx][property_name] = newVal
        if property_name in ['d', 'h', 'z', 'angle']:
            x, y, z, dtop, \
                ztop = self.derivePoleProperties(self.poles[idx]['d'],
                                                 self.poles[idx]['h'],
                                                 self.poles[idx]['angle'])
            self.poles[idx]['coordx'] = x
            self.poles[idx]['coordy'] = y
            self.poles[idx]['z'] = z
            self.poles[idx]['dtop'] = dtop
            self.poles[idx]['ztop'] = ztop
        
        # Deactivate anchor if first/last pole's height becomes 0
        if property_name == 'h' and newVal == 0:
            if idx == self.idxA and self.hasAnchorA:
                self.poles[0]['active'] = False
            elif idx == self.idxE and self.hasAnchorE:
                self.poles[-1]['active'] = False
        
        if property_name in ['category', 'position', 'abspann']:
            self.poles[idx][property_name] = newVal
        
        self.refresh()

        # When an anchor gets reactivated we have to make sure that the
        #  distance is higher / lower than the neighbouring pole
        if property_name == 'active' and newVal is True:
            dist = None
            if idx == 0:
                if self.firstPole['d'] <= self.poles[0]['d']:
                    dist = self.firstPole['d'] - self.POLE_DIST_STEP
            elif idx == len(self.poles)-1:
                if self.lastPole['d'] >= self.poles[-1]['d']:
                    dist = self.lastPole['d'] + self.POLE_DIST_STEP
            if dist:
                # Update new distance value
                self.update(idx, 'd', dist)
        
    def derivePoleProperties(self, d, h, angle):
        x = self.Ax + float(d) * sin(self.azimut)
        y = self.Ay + float(d) * cos(self.azimut)
        if angle != 0:
            angle = -1 * radians(angle)
        dtop = d - h * sin(angle)
        try:
            z = self.heightSource.getHeightAtPoints([[y, x]])[0]
            ztop = z + h * cos(angle)
        except ValueError:
            # Anchor is outside of profile data. This can happen when working
            #  with survey data. In this case, we use height of first/last
            #  pole as anchor height.
            if d < 0:
                z = self.heightSource.getHeightAtPoints([[self.Ay, self.Ax]])[0]
            else:
                z = self.heightSource.getHeightAtPoints([[self.Ey, self.Ex]])[0]
            ztop = z
        return x, y, z, dtop, ztop

    def updateAllPoles(self, status, poles):
        if status == 'optimization':
            # Update height of start point
            self.update(self.idxA, 'h', poles[0]['h'])
            # Optimization was successful, line reaches end point
            if int(poles[-1]['d']) == int(self.lastPole['d']):
                # Update optimized height of end point
                self.update(self.idxE, 'h', poles[-1]['h'])
            # Optimization was not successful, last pole is not at end point
            else:
                if self.lastPole['poleType'] == 'pole':
                    # Delete former end point (dont delete if its a pole_anchor)
                    self.poles.pop(self.idxE)
                # Deactivate anchor next to end point
                if self.hasAnchorE:
                    self.poles[-1]['active'] = False
                # Add dummy entry so that all relevant poles get added in the
                #  following for loop
                poles.append({})
            
            # Add the newly calculated poles between start and end point
            idx = self.idxA + 1
            for p in poles[1:-1]:
                self.add(idx, p['d'], p['h'], name=p['name'], refresh=False)
                idx += 1
        
        elif status == 'savedFile':
            # User wants to jump over the optimization and has loaded a save
            # file with poles --> all poles are being replaced with new data
            self.poles = []
            for p in poles:
                self.add(p['idx'], p['d'], p['h'], p['angle'],
                         p['manually'], p['poleType'], p['active'], p['name'],
                         p['category'] if 'category' in p else None,
                         p['position'] if 'position' in p else None,
                         p['abspann'] if 'abspann' in p else None, False)
        
        elif status == 'jumpedOver':
            # User wants to jump over the optimization but has not loaded a
            # save file with pole data. But since there are some fixed poles,
            # these are added in between first and last pole.
            idx = 1
            if self.A_type == 'pole':
                idx = 2
            for i, p in enumerate(poles):
                self.add(idx + i, p['d'], p['h'], name=p['name'], refresh=False)

        self.refresh()
    
    def getAsArray(self, withAnchor=False, withDeactivated=False):
        d = []
        z = []
        h = []
        dtop = []
        ztop = []
        number = []
        types = []
        category = []
        position = []
        abspann = []
        
        for i, pole in enumerate(self.poles):
            if not withAnchor and pole['poleType'] == 'anchor':
                continue
            if not pole['active'] and not withDeactivated:
                continue
            d.append(pole['d'])
            z.append(pole['z'])
            h.append(pole['h'])
            dtop.append(pole['dtop'])
            ztop.append(pole['ztop'])
            number.append(pole['nr'])
            types.append(pole['poleType'])
            category.append(pole['category'])
            position.append(pole['position'])
            abspann.append(pole['abspann'])

        d = np.array(d)
        z = np.array(z)
        h = np.array(h)
        dtop = np.array(dtop)
        ztop = np.array(ztop)
        return [d, z, h, dtop, ztop, number, types, category, position, abspann]
    
    def getHighestPole(self):
        [_, _, _, dtop, ztop, _, _, _, _, _] = self.getAsArray()
        ztopHighest = np.max(ztop)
        dtopHighest = dtop[np.argwhere(ztop == ztopHighest)[0][0]]
        return dtopHighest, ztopHighest

    def refresh(self):
        self.updateFirstLastPole()
        self.updateAnchorState()
        self.updateAnchorType()
        self.numberPoles()
        self.calculateAnchorLength()
        self.setDirection()
    
    def updateFirstLastPole(self):
        for idx, pole in enumerate(self.poles):
            if pole['poleType'] != 'anchor':
                self.firstPole = pole
                self.idxA = idx
                break
        
        for idx, pole in enumerate(self.poles[::-1]):
            if pole['poleType'] != 'anchor':
                self.lastPole = pole
                self.idxE = len(self.poles) - 1 - idx
                break
    
    def numberPoles(self):
        i = 1
        for idx, pole in enumerate(self.poles):
            if pole['poleType'] in ['anchor', 'pole_anchor']:
                self.poles[idx]['nr'] = ''
            else:
                self.poles[idx]['nr'] = str(i)
                i += 1
    
    def setDirection(self):
        self.direction = None
        if self.firstPole and self.lastPole:
             self.direction = 'downhill' if self.firstPole['ztop'] > self.lastPole['ztop'] else 'uphill'
            

    def delete(self, idx):
        self.poles.pop(idx)
        self.refresh()
    
    def calculateAnchorLength(self):
        """ Calculate anchor cable line and interpolate ground points. This
        values do only have to be calculated when anchors are active
        (poleType == anchor)
        """
        anchorA = self.poles[0]
        anchorE = self.poles[-1]
        
        poleA_ztop_diff = 0
        poleA_dtop_diff = 0
        poleE_ztop_diff = 0
        poleE_dtop_diff = 0

        if self.hasAnchorA:
            poleA_ztop_diff = self.firstPole['ztop'] - anchorA['ztop']
            poleA_dtop_diff = self.firstPole['dtop'] - anchorA['dtop']

        if self.hasAnchorE:
            poleE_ztop_diff = self.lastPole['ztop'] - anchorE['ztop']
            poleE_dtop_diff = anchorE['dtop'] - self.lastPole['dtop']

        anchor_field = [poleA_dtop_diff, poleA_ztop_diff,
                        poleE_dtop_diff, poleE_ztop_diff]
        anchor_len = (poleA_dtop_diff ** 2 + poleA_ztop_diff ** 2) ** 0.5 + \
                     (poleE_dtop_diff ** 2 + poleE_ztop_diff ** 2) ** 0.5

        self.anchor = {
            'field': anchor_field,
            'len': anchor_len
        }
    
    def getAnchorAngle(self, anchor, neighbourPole):
        """Calculate 'Angriffwinkel' for anchors and pole_anchors"""
        ztop_diff = neighbourPole['ztop'] - anchor['ztop']
        z_diff = neighbourPole['z'] - anchor['z']
        dtop_diff = neighbourPole['dtop'] - anchor['dtop']
        d_diff = neighbourPole['d'] - anchor['d']
        
        # end point
        if anchor['d'] > neighbourPole['d']:
            dtop_diff *= -1
            d_diff *= -1
        
        if anchor['poleType'] == 'anchor':
            # Angle between anchor -> pole top point and anchor -> pole
            # ground point
            if d_diff == 0 or ztop_diff == 0:
                # If anchor and pole are at the same horizontal distance or
                # at the same height, angle calculation is not meaningfull
                return np.nan
            try:
                return degrees(atan(ztop_diff / dtop_diff) - atan(z_diff / d_diff))
            except ZeroDivisionError:
                return np.nan
        
        elif anchor['poleType'] == 'pole_anchor':
            # Partial angle from horizontal line to terrain line, this will be
            #  used to correct the already calculated outgoing angle that
            #  is calculated from horizontal line to cable.
            if d_diff == 0:
                return np.nan
            return degrees(atan(z_diff / d_diff))
            

    def getCableFieldDimension(self):
        [_, _, _, dtop, ztop,
         _, _, _, _, _] = self.getAsArray(withAnchor=True, withDeactivated=True)

        b = dtop[self.idxA+1:self.idxE+1] - dtop[self.idxA:self.idxE]
        h = ztop[self.idxA+1:self.idxE+1] - ztop[self.idxA:self.idxE]
        
        return b, h
    
    def getAnchorCable(self):
        anchorFieldA = None
        anchorFieldE = None
        [_, _, _, pole_dtop, pole_ztop,
         _, _, _, _, _] = self.getAsArray(True, False)
        
        if self.hasAnchorA:
            anchorFieldA = {
                'd': pole_dtop[:2],
                'z': pole_ztop[:2]
            }
        if self.hasAnchorE:
            anchorFieldE = {
                'd': pole_dtop[-2:],
                'z': pole_ztop[-2:]
            }
        return {
            'A': anchorFieldA,
            'E': anchorFieldE
        }
    
    def updateAnchorState(self):
        self.hasAnchorA = self.poles[0]['poleType'] == 'anchor' and \
                          self.poles[0]['active']
        self.hasAnchorE = self.poles[-1]['poleType'] == 'anchor' and \
                          self.poles[-1]['active']

    def updateAnchorType(self):
        # If anchor is active, there can be no pole_anchor
        if self.hasAnchorA:
            self.poles[self.idxA]['poleType'] = 'pole'
        # If first pole has not height = 0, there can be no pole_anchor
        elif self.firstPole['h'] != 0 and self.firstPole['poleType'] != 'crane':
            self.poles[self.idxA]['poleType'] = 'pole'
        # Only if anchor is deactivated AND pole height = 0 it's a pole_anchor
        elif (not self.hasAnchorA) and self.firstPole['h'] == 0:
            self.poles[self.idxA]['poleType'] = 'pole_anchor'
        
        # If anchor is active, there can be no pole_anchor
        if self.hasAnchorE:
            self.poles[self.idxE]['poleType'] = 'pole'
        # If last pole has not height = 0, there can be no pole_anchor
        elif self.lastPole['h'] != 0:
            self.poles[self.idxE]['poleType'] = 'pole'
        # Only if anchor is deactivated AND pole height = 0 it's a pole_anchor
        elif not self.hasAnchorE and self.lastPole['h'] == 0:
            self.poles[self.idxE]['poleType'] = 'pole_anchor'

    def calculateAdvancedProperties(self, forces, bundstelle):
        """ Calculates additional pole properties that are used in the report.
        - Angriffswinkel for anchors
        - Max force and force type
        - BHD
        """
        for j, pole in enumerate(self.poles):
            bhd = np.nan
            bundst = np.nan
            angle = np.nan
            maxForce = np.nan
            maxForceName = 'Sattelkraft'
            
            if not pole['active']:
                continue
            
            # Anchor outside of optimization -> not passable
            if pole['poleType'] == 'anchor':
                maxForceName = 'Seilzugkraft'
                # Anchor next to start point
                if j < self.idxA:
                    angle = self.getAnchorAngle(pole, self.poles[j+1])
                    maxForce = forces['MaxSeilzugkraft_L'][3]
                # Anchor next to end point
                else:
                    angle = self.getAnchorAngle(pole, self.poles[j-1])
                    maxForce = forces['MaxSeilzugkraft_L'][4]
                
                bhd = self.getBhdForAnchor(angle, maxForce)

            # Start or end pole with h == 0 -> not passable
            elif pole['poleType'] == 'pole_anchor':
                maxForceName = 'Seilzugkraft'
                if pole == self.firstPole:
                    maxForce = forces['MaxSeilzugkraft_L'][1]       # Tmax,A
                    angleTerrain = self.getAnchorAngle(pole, self.poles[j+1])
                    # Add alpha LE: outgoing angle (idx=1) of first pole (idx=0)
                    angle = forces['Anlegewinkel_Leerseil'][1][0] - angleTerrain
                else:
                    maxForce = forces['MaxSeilzugkraft_L'][2]       # Tmax,E
                    angleTerrain = self.getAnchorAngle(pole, self.poles[j-1])
                    # Add alpha LA: incoming angle (idx=0) of last pole (idx=-1)
                    angle = forces['Anlegewinkel_Leerseil'][0][-1] - angleTerrain
    
                bhd = self.getBhdForAnchor(angle, maxForce)

            # Start or end pole with h > 0 --> not passable
            elif pole['poleType'] == 'pole' and pole in [self.firstPole, self.lastPole]:
                # Check if first pole and array has non nan values
                if pole == self.firstPole:
                    # A: Max(F_Sa_NBefRes li/re)
                    # Check if array only contains nan values
                    if not np.all(np.isnan(forces['Sattelkraft_beiStuetze'][0][0:2])):
                        maxForce = np.nanmax(forces['Sattelkraft_beiStuetze'][0][0:2])
                # Check if last pole and array has non nan values
                elif pole == self.lastPole:
                    # E: Max(F_Sa_NBefRes li/re)
                    # Check if array only contains nan values
                    if not np.all(np.isnan(forces['Sattelkraft_beiStuetze'][0][-2:])):
                        maxForce = np.nanmax(forces['Sattelkraft_beiStuetze'][0][-2:])
                if maxForce:
                    [bhd, bundst] = self.getBhdForPole(pole['h'], maxForce, bundstelle)

            # pole in between --> passable
            elif pole['poleType'] == 'pole':
                # Shift index to first pole that is fully passable
                idx = j - self.idxA
                # Poles in between start and end
                # Max(F_Sa_NBefRes, F_Sa_BefRes)
                maxForceB = np.max(forces['Sattelkraft_Total'][0][idx])
                # Check if array only contains nan values
                if not np.all(np.isnan(forces['Sattelkraft_beiStuetze'][0][idx*2:idx*2+2])):
                    maxForceNB = np.nanmax(forces['Sattelkraft_beiStuetze'][0][idx*2:idx*2+2])
                    maxForce = max(maxForceNB, maxForceB)
                else:
                    maxForce = maxForceB
                
                [bhd, bundst] = self.getBhdForPole(pole['h'], maxForce, bundstelle)
              
            # Special crane start pole with h: > 0 --> not passable
            elif pole['poleType'] == 'crane':
                # Crane is first pole of cable line
                # A: Max(F_Sa_NBefRes li/re)
                if not np.all(np.isnan(forces['Sattelkraft_beiStuetze'][0][0:2])):
                    maxForce = np.nanmax(forces['Sattelkraft_beiStuetze'][0][0:2])
                bhd = np.nan

            self.poles[j]['BHD'] = bhd
            self.poles[j]['bundstelle'] = bundst
            self.poles[j]['angriff'] = angle
            self.poles[j]['maxForce'] = [maxForce, maxForceName]
    
    @staticmethod
    def getBhdForAnchor(angle, max_force):
        if angle < 10:
            angle = 10
        elif angle < 25:
            angle = 25
        elif angle < 45:
            angle = 45
        else:
            return np.nan
        
        force_array = np.array(list(BHD_ANCHOR[angle].keys()))
        force_idx = (np.abs(force_array - max_force)).argmin()
        return BHD_ANCHOR[angle][force_array[force_idx]]
    
    @staticmethod
    def getBhdForPole(height, max_force, bundstelle):
        idx_force = (np.abs(BHD_POLE_Force - max_force)).argmin()
        height_array = np.array(list(BHD_POLE[BHD_POLE_Force[idx_force]].keys()))
        # Bundstelle is above cable, default 3m
        height += bundstelle
        idx_height = (np.abs(height_array - height)).argmin()
        # Diameter of tree next to cable
        bundst = BHD_POLE[BHD_POLE_Force[idx_force]][height_array[idx_height]]
        # Diameter at 1.3m over ground
        if bundst:
            diam = int(round(bundst + (height - 1.5), 0))
        else:
            diam = np.nan
            bundst = np.nan
        return [diam, bundst]
    
    def getSettings(self):
        propList = ['name', 'poleType', 'd', 'h', 'z', 'angle',
                    'manually', 'active', 'category', 'position', 'abspann']
        settings = []
        for idx, p in enumerate(self.poles):
            pole = {'idx': idx}
            for prop in propList:
                pole[prop] = p[prop]
            settings.append(pole)
        return settings
