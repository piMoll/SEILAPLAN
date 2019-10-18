from math import cos, sin, floor, radians
import numpy as np


class Poles(object):
    
    INIT_POLE_HEIGHT = 10
    INIT_POLE_ANGLE = 0
    POLE_DIST_STEP = 1
    POLE_HEIGHT_STEP = 0.1
    
    def __init__(self, project):
        """

        :type project: configHandler.ProjectConfHandler
        """
        self.params = project.params
        self.dhm = project.dhm
        [self.Ax, self.Ay] = project.points['A']
        [self.Ex, self.Ey] = project.points['E']
        self.azimut = project.azimut
        self.anchor = {}
        
        # Create anchors and start / end point
        self.poles = []
        # Anchor at start point
        self.add(0, -1 * self.params.getParameter('d_Anker_A'), 0)
        # First pole at start point
        self.add(1, 0, self.params.getParameter('HM_Anfang'))
        # Last pole at end point
        # End point is slightly moved (less than a meter) so that it is the
        # last point on profile with resolution 1m
        self.add(2, floor(project.profileLength),
                 self.params.getParameter('HM_Ende_max'))
        # Anchor at end point
        self.add(3, floor(project.profileLength) +
                 self.params.getParameter('d_Anker_E'), 0)
        self.update(0, 'name', 'Verankerung')
        self.update(0, 'poleType', 'anchor')
        self.update(3, 'name', 'Verankerung')
        self.update(3, 'poleType', 'anchor')
        self.calculateAnchor()
    
    def add(self, idx, d, h=INIT_POLE_HEIGHT, angle=INIT_POLE_ANGLE, manually=False):
        x, y, z, dtop, ztop = self.derivePoleProperties(d, h, angle)
        name = f"{idx}. Stütze"
        if manually:
            name = 'neue Stütze'
        poleType = 'pole'
        
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
        x = self.Ax + float(d) * cos(self.azimut)
        y = self.Ay + float(d) * sin(self.azimut)
        z = self.dhm.getInterpolatedHeightAtPoints([y, x])[0]
        dtop = d
        ztop = z + h
        if angle != 0:
            rad_angle = -1 * radians(angle)
            dtop = d - round(h * sin(rad_angle), 1)
            ztop = z + round(h * cos(rad_angle), 1)
        return x, y, z, dtop, ztop

    def addPolesFromOptimization(self, pole_dist, pole_h):
        # Remove all poles except start anchor
        anchor_start = self.poles[0]
        anchor_end = self.poles[-1]
        self.poles = [anchor_start]
        
        # Add calculated poles
        for i in range(len(pole_dist)):
            self.add(i + 1, pole_dist[i], pole_h[i])
        # Add anchor at end point
        self.poles.append(anchor_end)

        # Recalculate anchor data with new end point pole
        self.calculateAnchor()
    
    def getAsArray(self, withAnchor=False):
        poles = self.poles[:]
        arrLen = len(self.poles)
        if not withAnchor:
            poles = self.poles[1:-1]
            arrLen -= 2
        
        d = np.empty(arrLen)
        z = np.empty(arrLen)
        h = np.empty(arrLen)
        dtop = np.empty(arrLen)
        ztop = np.empty(arrLen)
        
        for i, pole in enumerate(poles):
            d[i] = pole['d']
            z[i] = pole['z']
            h[i] = pole['h']
            dtop[i] = pole['dtop']
            ztop[i] = pole['ztop']
        return [d, z, h, dtop, ztop]

    def delete(self, idx):
        self.poles.pop(idx)
    
    def calculateAnchor(self):
        """ Calculate anchor cable line and interpolate ground points.
        """
        d_Anchor_A = self.params.getParameter('d_Anker_A')
        d_Anchor_E = self.params.getParameter('d_Anker_E')
    
        # Height of first and last pole (not anchor) seen from point of anchor
        poleA_hz = self.poles[1]['h'] + (self.poles[1]['z'] - self.poles[0]['z'])
        poleE_hz = self.poles[-2]['h'] + (self.poles[-2]['z'] - self.poles[-1]['z'])
    
        # If anchor field has length 0, the first/last pole becomes the anchor
        if self.poles[0]['d'] == 0:
            poleA_hz = 0.0
        if self.poles[-1]['d'] == self.poles[-2]['d']:
            poleE_hz = 0.0
        if self.poles[-2]['h'] == 0:
            poleE_hz = 0.0
    
        anchor_field = [d_Anchor_A, poleA_hz,
                        d_Anchor_E, poleE_hz]
        anchor_len = (d_Anchor_A ** 2 + poleA_hz ** 2) ** 0.5 + \
                     (d_Anchor_E ** 2 + poleE_hz ** 2) ** 0.5
    
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
        [_, _, _, pole_dtop, pole_ztop] = self.getAsArray(True)
        return {
            'd': pole_dtop[[0, 1, -2, -1]],
            'z': pole_ztop[[0, 1, -2, -1]]
        }
