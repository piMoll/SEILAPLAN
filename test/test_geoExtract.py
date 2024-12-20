import os
from qgis.testing import unittest
import numpy as np

from . import BASIC_PROJECT_FILE, TESTDATA_DIR
from SEILAPLAN.tools.configHandler import ConfigHandler
from SEILAPLAN.tool_.mainSeilaplan import checkInputParams
from SEILAPLAN.tool_.geoExtract import (generateDhm, calcProfile, calcAnker, updateAnker)


@unittest.skip("deprecated, needs to be rewritten")
class TestCalcProfile(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        # Old calc
        ##
        cls.conf_ = ConfigHandler()
        cls.conf_.loadSettings(BASIC_PROJECT_FILE)
        cls.conf_.prepareForCalculation()
        proj_ = cls.conf_.project
        param_ = cls.conf_.params.getSimpleParameterDict()

        cls.projInfo_ = {
            'Anfangspunkt': proj_.getPoint('A')[0],
            'Endpunkt': proj_.getPoint('E')[0],
            'Projektname': proj_.getProjectName() + '_old',
            'Hoehenmodell': {
                'path': proj_.getHeightSourceAsStr()
            }
        }
        cls.inputData_ = {}
        for key, val in param_.items():
            cls.inputData_[key] = [val]
        cls.inputData_['HM_fix_d'] = proj_.fixedPoles['HM_fix_d']
        cls.inputData_['HM_fix_h'] = proj_.fixedPoles['HM_fix_h']
        cls.inputData_['noStue'] = proj_.noPoleSection
        cls.inputData_['HM_Anfang'] = [10]
        cls.inputData_['HM_Ende_max'] = [15]
        cls.inputData_ = checkInputParams(cls.inputData_)
        
        # New calc
        cls.conf = ConfigHandler()
        cls.params = cls.conf.params
        cls.project = cls.conf.project
        cls.conf.loadSettings(BASIC_PROJECT_FILE)
        cls.conf.prepareForCalculation()

        cls.dhm = cls.project.heightSource
        cls.profile = cls.project.profile
        cls.poles = cls.project.poles
        cls.deltaP = cls.profile.SAMPLING_DISTANCE
        cls.points = cls.project.points['A'] \
                     + cls.project.points['E']

    @classmethod
    def tearDownClass(cls):
        pass

    def test_subraster_creation(self):
        """ Check subraster creation: coordinate extent, size and values."""
        oldRas = generateDhm(self.projInfo_['Hoehenmodell'], self.points)

        oldRas = oldRas['clip']
        newRas = self.dhm.subraster
        # Flip raster to match orientation of new raster
        oldRasFlip = np.flip(oldRas['raster'], 0) / 10

        # Extent of subraster is equal
        self.assertEqual(oldRas['extent'][0], newRas['extent'][0])
        self.assertEqual(oldRas['extent'][1], newRas['extent'][1])
        # Size and shape of subraster are equal: Not anymore because subraster
        # creation rounds down instead of up --> no influence on algorithm
        # self.assertTupleEqual(np.shape(oldRasFlip), np.shape(newRas['z']))
        
        # Raster are equal
        self.assertTrue(np.allclose(oldRasFlip[0], newRas['z'][0], 3))
        self.assertTrue(np.allclose(oldRasFlip[-1], newRas['z'][-1], 3))

    def test_profile_generation(self):
        """ End point is not part of profile points but the equidistance is
        exactly 1 meter.
        """
        
        # coeff = int(self.inputData_["L_Delta"][0] / 1)
        # 
        # oldRas = generateDhm(self.projInfo_['Hoehenmodell'], self.points)
        # 
        # gp, zi_disp, di_ind = calcProfile(self.points, oldRas,
        #                                   self.inputData_, 1, coeff)
        
        # np.save(os.path.join(TESTDATA_DIR, 'geoExtract_legacy_raster_zi_disp'), zi_disp)
    
        # Load legacy data from disk
        xi = np.load(os.path.join(TESTDATA_DIR, 'geoExtract_legacy_raster_xi.npy'))
        xi_disp = np.load(os.path.join(TESTDATA_DIR, 'geoExtract_legacy_raster_xi_disp.npy'))
        di_s = np.load(os.path.join(TESTDATA_DIR, 'geoExtract_legacy_raster_di_s.npy'))
        zi_s = np.load(os.path.join(TESTDATA_DIR, 'geoExtract_legacy_raster_zi_s.npy'))
        zi_n = np.load(os.path.join(TESTDATA_DIR, 'geoExtract_legacy_raster_zi_n.npy'))
        zi_disp = np.load(os.path.join(TESTDATA_DIR, 'geoExtract_legacy_raster_zi_disp.npy'))
        
        # TODO: New *_disp arrays are longer than old ones
        
        # Same amount of points in profile sampling
        self.assertEqual(np.size(xi), np.size(self.profile.xi))
        # Same sampling point x,z-coordinates
        self.assertTrue(np.allclose(xi, self.profile.xi, atol=0.001))
        self.assertTrue(np.allclose(xi_disp, self.profile.xi_disp, atol=0.001))
        self.assertTrue(np.allclose(zi_disp/10, self.profile.zi_disp, atol=0.001))
        self.assertTrue(np.allclose(di_s, self.profile.di_s, atol=0.001))
        self.assertTrue(np.allclose(zi_s, self.profile.zi_s, atol=0.001))
        self.assertTrue(np.allclose(zi_n, self.profile.zi_n, atol=0.001))

    def test_anchor_calculation(self):
        """ Test calculation of anchor fields, anchor length an z-Values.
        Both mehtods calcAnker and update Anker are tested."""
        coeff = int(self.inputData_["L_Delta"][0] / 1)

        oldRas = generateDhm(self.projInfo_['Hoehenmodell'], self.points)

        gp, zi_disp, di_ind = calcProfile(self.points, oldRas,
                                          self.inputData_, 1, coeff)
        
        first_anchor = calcAnker(self.inputData_, self.points, oldRas, gp)
        first_anchor_ = {
            'field': first_anchor[0],
            'len': first_anchor[1],
            'z': first_anchor[2]
        }

        # New calc
        self.poles.calculateAnchorLength()

        # Tests
        # Compare interpolated z values of anchors
        self.assertAlmostEqual(first_anchor_['z'][0] / 10, self.poles.poles[0]['z'], 3)
        self.assertAlmostEqual(first_anchor_['z'][1] / 10, self.poles.poles[1]['z'], 3)
        self.assertAlmostEqual(first_anchor_['z'][2] / 10, self.poles.poles[-2]['z'], 3)
        # TODO: Ankerpunkt am Ende ist nicht gleich, weil bisher mit den neuen bseude Endpunkten (vielfaches von 1m Profil-Sektor) gerechtnet wurde --> Xe_, Ye_
        self.assertAlmostEqual(first_anchor_['z'][3] / 10, self.poles.poles[-1]['z'], 3)
        # Compare anchor fields
        self.assertAlmostEqual(first_anchor_['field'][0], self.poles.anchor['field'][0], 3)
        self.assertAlmostEqual(first_anchor_['field'][1], self.poles.anchor['field'][1], 3)
        self.assertAlmostEqual(first_anchor_['field'][2], self.poles.anchor['field'][2], 3)
        self.assertAlmostEqual(first_anchor_['field'][3], self.poles.anchor['field'][3], 3)
        # Compare length
        self.assertAlmostEqual(first_anchor_['len'], self.poles.anchor['len'], 3)

        # Simulate changed poles
        self.poles.poles[-2]['h'] = 15
        poles = [self.poles.poles[1]['h'], self.poles.poles[-2]['h']]
        poleIdx = [self.poles.poles[1]['d'], self.poles.poles[-2]['d']]
        updated_anchor = updateAnker(first_anchor, poles, poleIdx)
        updated_anchor = {
            'field': updated_anchor[0],
            'len': updated_anchor[1],
            'z': updated_anchor[2]
        }
        self.poles.calculateAnchorLength()

        # Tests
        # Compare anchor fields
        self.assertAlmostEqual(updated_anchor['field'][0], self.poles.anchor['field'][0], 3)
        self.assertAlmostEqual(updated_anchor['field'][1], self.poles.anchor['field'][1], 3)
        self.assertAlmostEqual(updated_anchor['field'][2], self.poles.anchor['field'][2], 3)
        self.assertAlmostEqual(updated_anchor['field'][3], self.poles.anchor['field'][3], 3)
        # Compare length
        self.assertAlmostEqual(updated_anchor['len'], self.poles.anchor['len'], 3)
    
        
if __name__ == '__main__':
    unittest.main()
