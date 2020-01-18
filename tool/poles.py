from math import cos, sin, floor, radians
import numpy as np


class Poles(object):
    
    INIT_POLE_HEIGHT = 10.0
    INIT_POLE_ANGLE = 0.0
    POLE_DIST_STEP = 1.0
    POLE_HEIGHT_STEP = 0.1
    
    def __init__(self, project):
        """
        :type project: configHandler.ProjectConfHandler
        """
        self.params = project.params
        self.heightSource = project.heightSource
        [self.Ax, self.Ay] = project.points['A']
        self.azimut = project.azimut
        self.anchor = {}
        
        # Create anchors and start / end point
        self.poles = []
        # Length of first anchor field; is used to shift horizontal distances
        self.anchorA = self.params.getParameter('d_Anker_A')
        self.anchorE = self.params.getParameter('d_Anker_E')
        heightA = self.params.getParameter('HM_Anfang')
        heightE = self.params.getParameter('HM_Ende_max')
        # End point is slightly moved (less than a meter) so that it is the
        # last point on profile with step size of 1m
        self.profileLength = floor(project.profileLength)
        
        idx = 0
        if self.anchorA:
            # Anchor at start point
            self.add(idx, -1*self.anchorA, 0, poleType='anchor')
            idx = 1
        # First pole at 0 m horizontal distance
        self.add(idx, 0, heightA)
        # Last pole
        self.add(idx+1, self.profileLength, heightE)
        if self.anchorE:
            # Anchor at end point
            self.add(idx+2, self.profileLength + self.anchorE, 0,
                     poleType='anchor')
        
        self.calculateAnchorLength()
    
    def add(self, idx, d, h=INIT_POLE_HEIGHT, angle=INIT_POLE_ANGLE,
            manually=False, poleType='pole', name=''):
       
        d = float(d)
        if h == -1:
            h = self.INIT_POLE_HEIGHT
        h = float(h)
        x, y, z, dtop, ztop = self.derivePoleProperties(d, h, angle)
        if not name:
            name = f"{idx}. Stütze"
            if manually:
                name = 'neue Stütze'
            if poleType == 'anchor':
                name = 'Verankerung'
        
        self.poles.insert(idx, {
            'name': name,
            'poleType': poleType,
            'd': d,
            'z': z,
            'h': h,
            'angle': angle,
            'dtop': dtop,
            'ztop': ztop,
            'coordx': x,
            'coordy': y,
            'manually': manually
        })

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
    
    def derivePoleProperties(self, d, h, angle):
        x = self.Ax + float(d) * sin(self.azimut)
        y = self.Ay + float(d) * cos(self.azimut)
        z = self.heightSource.getHeightAtPoints([[y, x]])[0]
        dtop = d
        ztop = z + h
        if angle != 0:
            rad_angle = -1 * radians(angle)
            dtop = d - h * sin(rad_angle)
            ztop = z + h * cos(rad_angle)
        return x, y, z, dtop, ztop

    def updateAllPoles(self, status, poles):
        if status == 'optimization':
            # Reset all pole data
            self.poles = []
            idx = 0
            if self.anchorA:
                self.add(0, -1*self.anchorA, 0, poleType='anchor')
                idx = 1
            
            # Add calculated poles between start and end anchor
            for p in poles:
                self.add(idx, p['d'], p['h'], name=p['name'])
                idx += 1
            
            if self.anchorE:
                # Anchor at end point
                self.add(idx, self.profileLength + self.anchorE, 0,
                         poleType='anchor')
        
        elif status == 'savedFile':
            # User wants to jump over the optimization and has loaded a save
            # file with poles --> all poles are being replaced with new data
            self.poles = []
            for p in poles:
                self.add(p['idx'], p['dist'], p['height'], p['angle'],
                         p['manual'], p['pType'], name=p['name'])
        
        elif status == 'jumpedOver':
            # User wants to jump over the optimization but has not loaded a
            # save file with pole data. But since there are some fixed poles,
            # these are added in between first and last pole.
            idx = 1
            if self.anchorA:
                idx = 2
            for i, p in enumerate(poles):
                self.add(idx + i, p['d'], p['h'], name=p['name'])

        # Recalculate anchor data with updated pole data
        self.calculateAnchorLength()
    
    def getAsArray(self, withAnchor=False):
        d = []
        z = []
        h = []
        dtop = []
        ztop = []
        
        for i, pole in enumerate(self.poles):
            if not withAnchor and pole['poleType'] == 'anchor':
                continue
            d.append(pole['d'])
            z.append(pole['z'])
            h.append(pole['h'])
            dtop.append(pole['dtop'])
            ztop.append(pole['ztop'])

        d = np.array(d)
        z = np.array(z)
        h = np.array(h)
        dtop = np.array(dtop)
        ztop = np.array(ztop)
        return [d, z, h, dtop, ztop]
    
    def getFirstPole(self):
        for idx, pole in enumerate(self.poles):
            if pole['poleType'] == 'pole':
                return pole, idx
    
    def getLastPole(self):
        for idx, pole in enumerate(self.poles[::-1]):
            if pole['poleType'] == 'pole':
                return pole, len(self.poles) - 1 - idx

    def delete(self, idx):
        self.poles.pop(idx)
    
    def calculateAnchorLength(self):
        """ Calculate anchor cable line and interpolate ground points.
        """
        # Height difference between anchor point and top of first/last pole
        poleA_hz = 0
        poleE_hz = 0
        if self.anchorA:
            poleA_hz = self.poles[1]['ztop'] - self.poles[0]['ztop']
        if self.anchorE:
            poleE_hz = self.poles[-2]['ztop'] - self.poles[-1]['ztop']
    
        anchor_field = [self.anchorA, poleA_hz,
                        self.anchorE, poleE_hz]
        anchor_len = (self.anchorA ** 2 + poleA_hz ** 2) ** 0.5 + \
                     (self.anchorE ** 2 + poleE_hz ** 2) ** 0.5
    
        self.anchor = {
            'field': anchor_field,
            'len': anchor_len
        }

    def getCableFieldDimension(self):
        [_, _, _, dtop, ztop] = self.getAsArray()

        b = dtop[1:] - dtop[:-1]
        h = ztop[1:] - ztop[:-1]
        
        return b, h
    
    def getAnchorCable(self):
        anchorFieldA = None
        anchorFieldE = None
        [_, _, _, pole_dtop, pole_ztop] = self.getAsArray(True)
        
        if self.anchorA:
            anchorFieldA = {
                'd': pole_dtop[:2],
                'z': pole_ztop[:2]
            }
        if self.anchorE:
            anchorFieldE = {
                'd': pole_dtop[-2:],
                'z': pole_ztop[-2:]
            }
        return {
            'A': anchorFieldA,
            'E': anchorFieldE
        }
