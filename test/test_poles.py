from qgis.testing import unittest
from numpy import nan
from . import BASIC_PROJECT_FILE, MINIMAL_PROJECT_FILE, project_file_loader
from ._test_helper import calculate_cable_line
from SEILAPLAN.tools.configHandler import ConfigHandler
from SEILAPLAN.tools.configHandler_project import ProjectConfHandler
from SEILAPLAN.tools.configHandler_params import ParameterConfHandler
from SEILAPLAN.tools.poles import Poles


TEST_PROJECT_Bawald = project_file_loader('unittest_survey_excel_Wyss_Bawald.json')
TEST_PROJECT_A_A = project_file_loader('unittest_dhm_anchor_anchor_6_poles.json')
TEST_PROJECT_A_A_UPHILL = project_file_loader('unittest_dhm_anchor_anchor_4_poles_uphill.json')


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



if __name__ == '__main__':
    unittest.main()
