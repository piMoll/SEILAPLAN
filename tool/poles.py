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
        heightA = self.params.getParameter('HM_Anfang')
        anchorE = self.params.getParameter('d_Anker_E')
        heightE = self.params.getParameter('HM_Ende_max')
        # Anchor at start point
        self.add(0, 0, 0, poleType='anchor')
        # First pole
        self.add(1, self.anchorA, heightA)
        # Last pole at end point
        # End point is slightly moved (less than a meter) so that it is the
        # last point on profile with resolution 1m
        self.add(2, floor(project.profileLength) - anchorE, heightE)
        # Anchor at end point
        self.add(3, floor(project.profileLength), 0, poleType='anchor')
        self.calculateAnchor()
    
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
            # Optimization has run without an error, optimized poles are
            # added to anchor points.
            anchor_start = self.poles[0]
            anchor_end = self.poles[-1]
            self.poles = [anchor_start]
            # Add calculated poles between start and end anchor
            for idx, p in enumerate(poles):
                self.add(idx + 1, p['d'] + self.anchorA, p['h'], name=p['name'])
            # Add anchor at end point
            self.poles.append(anchor_end)
        
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
            for idx, p in enumerate(poles):
                self.add(idx + 2, p['d'], p['h'], name=p['name'])

        # Recalculate anchor data with updated pole data
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
        # TODO: Wenn Ankerfeld = 0m oder Stützenhöhe = 0m, dann muss Anker
        #  entfernt werden und 1. Stütze auf 0m eingestellt werden
        if self.poles[0]['d'] == self.poles[1]['d']:
            poleA_hz = 0.0
        if self.poles[-1]['d'] == self.poles[-2]['d']:
            poleE_hz = 0.0
        if self.poles[-2]['h'] == 0:        # last pole has height = 0
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
