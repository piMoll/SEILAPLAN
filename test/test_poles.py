from qgis.testing import unittest
from qgis.core import QgsCoordinateReferenceSystem
from numpy import nan
from copy import deepcopy
import copyreg
from . import project_file_loader
from ._test_helper import calculate_cable_line
from SEILAPLAN.tools.configHandler import ConfigHandler
from SEILAPLAN.tools.poles import Poles, BRUSTHOEHE
from SEILAPLAN.core.cablelineFinal import preciseCable


TEST_PROJECT_Bawald = project_file_loader('unittest_survey_excel_Wyss_Bawald.json')
TEST_PROJECT_A_A = project_file_loader('unittest_dhm_anchor_anchor_6_poles.json')
TEST_PROJECT_A_A_UPHILL = project_file_loader('unittest_dhm_anchor_anchor_4_poles_uphill.json')

# deepcopy cant copy QgsCoordinateReferenceSystem because it's not pickleable.
#  This will instead create a new instance of QgsCoordinateReferenceSystem
#  when deepcopying
# https://stackoverflow.com/questions/34152758/how-to-deepcopy-when-pickling-is-not-possible
def pickle_QgsCoordinateRef(do):
    return QgsCoordinateReferenceSystem, ()

copyreg.pickle(QgsCoordinateReferenceSystem, pickle_QgsCoordinateRef)


class TestPolesAngriffswinkel(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        pass
    
    @classmethod
    def tearDownClass(cls):
        pass
        
    def test_anchor_anchor(self):
        conf: ConfigHandler = ConfigHandler()
        poles: Poles
        result, params, poles, profile, status = calculate_cable_line(conf, TEST_PROJECT_A_A)
        firstPole = poles.poles[0]
        lastPoles = poles.poles[-1]
        
        self.assertAlmostEqual(firstPole['angriff'], 21.0, 1)
        self.assertAlmostEqual(lastPoles['angriff'], 24.4, 1)
    
    def test_anchor_anchor_uphill(self):
        conf: ConfigHandler = ConfigHandler()
        poles: Poles
        result, params, poles, profile, status = calculate_cable_line(conf, TEST_PROJECT_A_A_UPHILL)
        firstPole = poles.poles[0]
        lastPoles = poles.poles[-1]
        
        self.assertAlmostEqual(firstPole['angriff'], 23.6, 1)
        self.assertAlmostEqual(lastPoles['angriff'], 33.3, 1)
    
    def test_crane_pole_anchor(self):
        conf: ConfigHandler = ConfigHandler()
        poles: Poles
        result, params, poles, profile, status = calculate_cable_line(conf)
        firstPole = poles.poles[0]
        lastPoles = poles.poles[-1]
        
        # No Angriffswinkel for start point because it's a cran
        self.assertIs(firstPole['angriff'], nan)
        # Last point is a pole anchor
        self.assertAlmostEqual(lastPoles['angriff'], 25.6, 1)
    
    def test_pole_anchors(self):
        conf: ConfigHandler = ConfigHandler()
        poles: Poles
        result, params, poles, profile, status = calculate_cable_line(conf, TEST_PROJECT_Bawald)
        firstPole = poles.poles[0]
        lastPoles = poles.poles[-1]
        
        self.assertAlmostEqual(firstPole['angriff'], 9.0, 1)
        self.assertAlmostEqual(lastPoles['angriff'], 10.8, 1)



class TestPolesBundstelleAndBHD(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        cls.conf: ConfigHandler = ConfigHandler()
        cls.poles: Poles
        (cls.result, cls.params,
         cls.poles, cls.profile,
         cls.status) = calculate_cable_line(cls.conf, TEST_PROJECT_A_A)
    
    @classmethod
    def tearDownClass(cls):
        pass
    
    def test_getBhdForAnchor(self):
        angle = 10
        maxForce = 101
        bhd = self.poles.getBhdForAnchor(angle, maxForce)
        self.assertEqual(bhd, 56)
        
        angle = 27
        maxForce = 83
        bhd = self.poles.getBhdForAnchor(angle, maxForce)
        self.assertEqual(bhd, 58)
    
        
    def test_getBhdForPole(self):
        poleHeight = 10
        maxForce = 50
        bundstelle = 3
        [bhd, bundst] = self.poles.getBhdForPole(poleHeight, maxForce, bundstelle)
        self.assertEqual(bundst, 26)
        self.assertEqual(bhd, 26 + (poleHeight + bundstelle - 1))
        
        poleHeight = 18
        maxForce = 140
        bundstelle = 2
        [bhd, bundst] = self.poles.getBhdForPole(poleHeight, maxForce, bundstelle)
        self.assertEqual(bundst, 42)
        self.assertEqual(bhd, 42 + (poleHeight + bundstelle - 1))
        
    
    def test_bundstelle_increases_with_pole_height(self):
        bundstelleBefore1 = self.poles.poles[1]['bundstelle']
        bundstelleBefore2 = self.poles.poles[2]['bundstelle']
        
        updatedPoles = deepcopy(self.poles)
        updatedPoles.update(1, 'h', 25)
        updatedPoles.update(2, 'h', 28)
        simpleParams = self.params.getSimpleParameterDict()
        _, _, _ = preciseCable(simpleParams, updatedPoles, self.result['optSTA'])
        
        self.assertGreater(updatedPoles.poles[1]['bundstelle'], bundstelleBefore1)
        self.assertGreater(updatedPoles.poles[2]['bundstelle'], bundstelleBefore2)


if __name__ == '__main__':
    unittest.main()
