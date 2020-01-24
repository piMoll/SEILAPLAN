from math import cos, sin, floor, radians
import numpy as np


class Poles(object):
    
    INIT_POLE_HEIGHT = 12.0
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
        
        # Length of first anchor field; is used to shift horizontal distances
        self.anchorA = self.params.getParameter('d_Anker_A')
        self.anchorE = self.params.getParameter('d_Anker_E')
        heightA = self.params.getParameter('HM_Anfang')
        heightE = 0 if self.E_type == 'pole_anchor' else self.INIT_POLE_HEIGHT
        # End point is slightly moved (less than a meter) so that it is the
        # last point on profile with step size of 1m
        self.profileLength = floor(project.profileLength)
        
        idx = 0
        if self.A_type == 'pole':
            # Anchor at start point
            self.add(idx, -1*self.anchorA, 0, poleType='anchor')
            idx = 1
        # First pole at 0 m horizontal distance
        self.add(idx, 0, heightA, poleType=self.A_type)
        # Last pole
        self.add(idx+1, self.profileLength, heightE, poleType=self.E_type)
        if self.E_type == 'pole':
            # Anchor at end point
            self.add(idx+2, self.profileLength + self.anchorE, 0,
                     poleType='anchor')
        self.updateAnchorStatus()
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
            if poleType in ['anchor', 'pole_anchor']:
                name = 'Verankerung'
            elif poleType == 'crane':
                name = 'Seilkran'
        
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
            'manually': manually,
            'active': True
        })
        self.updateFirstLastPole()

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
        self.updateFirstLastPole()
    
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
            # Update height of start and end point
            self.update(self.idxA, 'h', poles[0]['h'])
            self.update(self.idxE, 'h', poles[-1]['h'])
            
            # Add the newly calculated poles between start and end point
            idx = self.idxA + 1
            for p in poles[1:-1]:
                self.add(idx, p['d'], p['h'], name=p['name'])
                idx += 1
            # Update name of last pole
            self.update(self.idxE, 'name', f'{idx}. Stütze')
            self.updateAnchorStatus()
        
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
            if self.A_type == 'pole':
                idx = 2
            for i, p in enumerate(poles):
                self.add(idx + i, p['d'], p['h'], name=p['name'])

        self.updateFirstLastPole()
        # Recalculate anchor data with updated pole data
        self.calculateAnchorLength()
    
    def getAsArray(self, withAnchor=False, withDeactivated=False):
        d = []
        z = []
        h = []
        dtop = []
        ztop = []
        
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

        d = np.array(d)
        z = np.array(z)
        h = np.array(h)
        dtop = np.array(dtop)
        ztop = np.array(ztop)
        return [d, z, h, dtop, ztop]
    
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

    def delete(self, idx):
        self.poles.pop(idx)
        self.updateFirstLastPole()
    
    def calculateAnchorLength(self):
        """ Calculate anchor cable line and interpolate ground points.
        """
        # Height difference between anchor point and top of first/last pole
        poleA_hz = 0
        poleE_hz = 0
        if self.poles[0]['poleType'] == 'anchor' and self.poles[0]['active']:
            poleA_hz = self.poles[1]['ztop'] - self.poles[0]['ztop']
        if self.poles[-1]['poleType'] == 'anchor' and self.poles[-1]['active']:
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
        [_, _, _, dtop, ztop] = self.getAsArray(withAnchor=True, withDeactivated=True)

        b = dtop[self.idxA+1:self.idxE+1] - dtop[self.idxA:self.idxE]
        h = ztop[self.idxA+1:self.idxE+1] - ztop[self.idxA:self.idxE]
        
        return b, h
    
    def getAnchorCable(self):
        anchorFieldA = None
        anchorFieldE = None
        [_, _, _, pole_dtop, pole_ztop] = self.getAsArray(True, False)
        
        if self.poles[0]['poleType'] == 'anchor' and self.poles[0]['active']:
            anchorFieldA = {
                'd': pole_dtop[:2],
                'z': pole_ztop[:2]
            }
        if self.poles[-1]['poleType'] == 'anchor' and self.poles[-1]['active']:
            anchorFieldE = {
                'd': pole_dtop[-2:],
                'z': pole_ztop[-2:]
            }
        return {
            'A': anchorFieldA,
            'E': anchorFieldE
        }

    def updateAnchorStatus(self):
        # If first or last pole has height = 0, anchors are deactivated
        if self.firstPole['h'] == 0 and self.poles[0]['poleType'] == 'anchor':
            self.update(0, 'active', False)
        if self.lastPole['h'] == 0 and self.poles[-1]['poleType'] == 'anchor':
            self.update(self.idxE + 1, 'active', False)
