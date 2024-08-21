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
from math import floor
import numpy as np
from .survey import SurveyData


class Profile(object):
    
    SAMPLING_DISTANCE = 1
    
    def __init__(self, project, sampling=SAMPLING_DISTANCE):
        """
        Generates a profile with line sections of exactly 1 meter length. This
        means, that the end point is slightly moved to be part of the profile
        points. So xi[-1] and yi[-1] end point coordinates differ to the ones
        the user defined at the beginning.

        :type project: projectHandler.ProjectConfHandler
        :return:
        """
        [self.Ax, self.Ay] = project.points['A']
        [self.Ex, self.Ey] = project.points['E']
        self.profileLength = project.profileLength
        self.params = project.params
        self.heightSource = project.heightSource
        self.anchorA = self.params.getParameter('d_Anker_A')
        self.anchorE = self.params.getParameter('d_Anker_E')
        self.direction = None     # 'down' or 'up'
        self.sampling_dist = sampling
        
        self.surveyPnts = None
        # In case of survey data, save survey points
        if isinstance(self.heightSource, SurveyData):
            self.surveyPnts = self.heightSource.plotPoints

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
        # Length of single line section between first and last pole
        dp = self.profileLength / self.sampling_dist
        # Number of sampling points including start point but not end point
        pCount = floor(dp)
        # Line sections in x and y direction
        dx = (float(self.Ex) - float(self.Ax)) / dp
        dy = (float(self.Ey) - float(self.Ay)) / dp
    
        if round(dx, 3) == 0:
            xi = np.array([self.Ax] * (pCount + 1))
        else:
            # range max value (end point) is not included
            xi = np.arange(self.Ax, self.Ex, dx)
        if round(dy, 3) == 0:
            yi = np.array([self.Ay] * (pCount + 1))
        else:
            # range max value (end point) is not included
            yi = np.arange(self.Ay, self.Ey, dy)
    
        # Number of sampling points between start/end point and end of profile
        pCount_dA_exact = self.heightSource.buffer[0] / self.sampling_dist
        pCount_dA = floor(pCount_dA_exact)
        # Since the end point is not included in the profile, we have to add the
        #  difference (dp - floor(dp)) to the end buffer
        pCount_dE_exact = (dp - floor(dp) + self.heightSource.buffer[1]) / self.sampling_dist
        pCount_dE = floor(pCount_dE_exact)
    
        xiA_d = np.linspace(self.Ax - dx, self.Ax - pCount_dA * dx, pCount_dA)
        yiA_d = np.linspace(self.Ay - dy, self.Ay - pCount_dA * dy, pCount_dA)
        xiE_d = np.linspace(xi[-1] + dx, xi[-1] + pCount_dE * dx, pCount_dE)
        yiE_d = np.linspace(yi[-1] + dy, yi[-1] + pCount_dE * dy, pCount_dE)
    
        self.xi_disp = np.concatenate((xiA_d[::-1], xi, xiE_d))
        self.yi_disp = np.concatenate((yiA_d[::-1], yi, yiE_d))
        self.di_disp = np.arange(0, np.size(self.xi_disp) * self.sampling_dist,
                                 self.sampling_dist) - pCount_dA*self.sampling_dist
    
        # Interpolate z values on raster
        coords = np.rollaxis(np.array([self.yi_disp, self.xi_disp]), 1)
        self.zi_disp = self.heightSource.getHeightAtPoints(coords)
        self.zi = np.copy(self.zi_disp)
        if pCount_dA > 0:
            self.zi = self.zi[pCount_dA:]
        if pCount_dE > 0:
            self.zi = self.zi[:-pCount_dE]
        self.di = np.arange(0, np.size(xi) * self.sampling_dist, self.sampling_dist)
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
        
        # Update profile direction
        self.direction = 'down'
        if self.zi[0] < self.zi[-1]:
            self.direction = 'up'
    
    def analyseProfile(self, lenCableline):  # locb
        # Ground clearance (Bodenabstand)
        # TODO: Refactoring of old function in terrainAnalysis.py
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
    
    def updateProfileAnalysis(self, cableline):
        # Cable line has a resolution of 10 cm, profile data has 1m. By
        #  choosing every 10th element in the cable line, we get the
        #  cable value for every terrain point.
        cableline_meter = cableline['load'][::10]
        
        # Get nearest point on horizontal axis of cable start and end point
        hdist_start = np.round(cableline['xaxis'][::10])[0]
        hdist_end = np.round(cableline['xaxis'][::10])[-1]
        # Index on display array
        di_start = np.where(self.di_disp == hdist_start)[0][0]
        di_end = np.where(self.di_disp == hdist_end)[0][0]
        # Update zi
        self.zi = self.zi_disp[di_start:di_end + 1]
        
        # By moving the first or last pole, the cable line can become longer or
        # shorter than the initial solution. Ground clearance has to be
        # recalculated
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

        # Calculate distance between cable and ground
        maxDistToGround = np.nanmax(cableline['empty'][::10] - self.zi)
        return {
            'groundclear_di': gclear_xaxis,
            'groundclear': gclear_cable,
            'groundclear_under': gclear_abs,
            'groundclear_rel': gclear_rel,
            'maxDistToGround': maxDistToGround,
        }
    
    def setPeakLocations(self, peakLoc):
        self.peakLoc_x = peakLoc
        if peakLoc.size > 0:
            self.peakLoc_z = self.zi[self.peakLoc_x]
        else:
            self.peakLoc_z = np.array([])
