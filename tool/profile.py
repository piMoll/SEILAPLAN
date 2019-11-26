from math import floor, ceil
import numpy as np


class Profile(object):
    
    SAMPLING_DISTANCE = 1
    
    def __init__(self, project):
        """
        Generates a profile with line sections of exactly 1 meter length. This
        means, that the end point is slightly moved to be part of the profile
        points. So xi[-1] and yi[-1] end point coordinates differ to the ones
        the user defined at the beginning.

        :type project: configHandler.ProjectConfHandler
        :return:
        """
        [self.Ax, self.Ay] = project.points['A']
        [self.Ex, self.Ey] = project.points['E']
        self.profileLength = project.profileLength
        self.params = project.params
        self.heightSource = project.heightSource

        self.dx = None
        self.dy = None
        
        self.xi = None
        self.yi = None
        self.zi = None
        self.di = None
        
        self.xi_disp = None
        self.yi_disp = None
        self.zi_disp = None
        self.di_disp = None
        
        self.zi_s = None
        self.di_s = None
        self.di_s_idx = None
        self.zi_n = None
        self.di_n = None
        
        self.sc = None
        self.sc_s = None
        self.befGSK = None
        self.befGSK_s = None
        
        self.peakLoc_x = None
        self.peakLoc_z = None
        
        self.generateProfile()
    
    def generateProfile(self):
        # Number of sampling points including start point but not end point.
        pCount = floor(self.profileLength / self.SAMPLING_DISTANCE)
        # Length of single line section between start and end point
        dp = self.profileLength / self.SAMPLING_DISTANCE
        # Line sections in x and y direction
        dx = (float(self.Ex) - float(self.Ax)) / dp
        dy = (float(self.Ey) - float(self.Ay)) / dp
    
        if dx == 0:
            xi = np.array([self.Ax] * pCount)
        else:
            # range max value (end point) is not included
            xi = np.arange(self.Ax, self.Ex, dx)
        if dy == 0:
            yi = np.array([self.Ay] * pCount)
        else:
            # range max value (end point) is not included
            yi = np.arange(self.Ay, self.Ey, dy)
    
        # Number of sampling points between start/end point and end of profile
        pCount_d = floor(self.heightSource.buffer / self.SAMPLING_DISTANCE)
    
        xiA_d = np.linspace(self.Ax - dx, self.Ax - pCount_d * dx, pCount_d)
        yiA_d = np.linspace(self.Ay - dy, self.Ay - pCount_d * dy, pCount_d)
        xiE_d = np.linspace(xi[-1] + dx, xi[-1] + pCount_d * dx, pCount_d)
        yiE_d = np.linspace(yi[-1] + dy, yi[-1] + pCount_d * dy, pCount_d)
    
        self.xi_disp = np.concatenate((xiA_d[::-1], xi, xiE_d))
        self.yi_disp = np.concatenate((yiA_d[::-1], yi, yiE_d))
        self.di_disp = np.arange(-1 * np.size(xiA_d), np.size(xi)
                                 + np.size(xiE_d), self.SAMPLING_DISTANCE)
    
        # Interpolate z values on raster
        coords = np.rollaxis(np.array([self.yi_disp, self.xi_disp]), 1)
        self.zi_disp = self.heightSource.getHeightAtPoints(coords)
        self.zi = self.zi_disp[pCount_d:-pCount_d]
        self.di = np.arange(np.size(xi) * self.SAMPLING_DISTANCE * 1.0)
        self.xi = xi
        self.yi = yi
        self.dx = dx
        self.dy = dy
    
        # Normalize height data
        self.zi_n = self.zi - self.zi[0]
        self.di_n = self.di
    
        # Simplify profile points: pole positions are only possible all deltaP
        # meters
        deltaL = self.params.getParameter('L_Delta')
        self.zi_s = self.zi[::deltaL]
        self.di_s = self.di[::deltaL]
        # Normalize
        self.zi_s = self.zi_s - self.zi_s[0]
        self.di_s = self.di_s - self.di_s[0]
        self.di_s_idx = np.arange(np.size(self.di))[::deltaL]  # ???
        
        # zi_n and zi_s in dm instead of m
        self.zi_s *= 10
        self.zi_n *= 10
    
    def analyseProfile(self, lenCableline):  # locb
        # Ground clearance (Bodenabstand)
        # TODO: Refactoring of old function in geoExtract.py
        groundclearance = self.params.getParameter('Bodenabst_min')
        clearA = self.params.getParameter('Bodenabst_A')
        clearE = self.params.getParameter('Bodenabst_E')
    
        di_cable = np.arange(lenCableline * 1)
        groundClear = np.ones(lenCableline) * groundclearance
        groundClear[di_cable <= clearA + 1] = 0
        groundClear[di_cable > (di_cable[-1] - clearE)] = 0
        self.sc = groundClear
        # self.sc_s = groundClear[locb]

        # Befahrbarkeit
        # befGSK_A = self.params.getParameter('Befahr_A')
        # befGSK_E = self.params.getParameter('Befahr_E')
        #
        # befahrbar = np.ones(lenCableline)
        # befahrbar[di_cable < befGSK_A + 1] = 0
        # befahrbar[di_cable > (di_cable[-1] - befGSK_E)] = 0
        # self.befGSK = befahrbar
    
    def updateProfileAnalysis(self, cableline, poles):
        # Update zi
        di_start = np.where(self.di_disp >= poles[1]['dtop'])[0][0]
        di_end = np.where(self.di_disp >= poles[-2]['dtop'])[0][0]
        self.zi = self.zi_disp[di_start:di_end + 1]
        
        # By moving the first or last pole, the cable line can become longer or
        # shorter than the initial solution. Ground clearance has to be
        # recalculated
        cableline_meter = cableline['load'][::10]  # cable data from dm to m
        lenCable = np.size(cableline_meter)
        self.analyseProfile(lenCable)
        
        gclear_xaxis = self.di_disp[di_start:di_end + 1]
        # gclear_cable is a virtual cable line under the actual cable line,
        # used in plot
        gclear_cable = cableline_meter - self.sc
        # Same as gclear_cable but only shown when min ground clearance is not
        # met, in absolute height values, used in plot
        gclear_abs = (gclear_cable < self.zi) * gclear_cable
        # Distance between cable and terrain where ground clearance has to be
        # kept, is used to check threshold in adjustment window
        gclear_rel = cableline_meter - self.zi
        
        # Make sections where ground clearance is not checked to nan
        gclear_cable[self.sc == 0] = np.nan
        gclear_abs[gclear_abs == 0] = np.nan
        try:
            gclear_abs[self.sc == 0] = np.nan
        except RuntimeWarning:
            pass
        gclear_rel[self.sc == 0] = np.nan

        cableline['groundclear_di'] = gclear_xaxis
        cableline['groundclear'] = gclear_cable
        cableline['groundclear_under'] = gclear_abs
        cableline['groundclear_rel'] = gclear_rel
    
    def setPeakLocations(self, peakLoc):
        self.peakLoc_x = peakLoc
        self.peakLoc_z = self.zi[self.peakLoc_x]
