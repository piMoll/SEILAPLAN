from qgis.testing import unittest
from numpy import nan
from . import BASIC_PROJECT_FILE, MINIMAL_PROJECT_FILE, project_file_loader
from ._test_helper import calculate_cable_line
from SEILAPLAN.tools.configHandler import ConfigHandler
from SEILAPLAN.tools.configHandler_project import ProjectConfHandler
from SEILAPLAN.tools.configHandler_params import ParameterConfHandler
from SEILAPLAN.tools.poles import Poles


TEST_PROJECT = project_file_loader('unittest_survey_excel_Wyss_Bawald.json')
TEST_PROJECT_2 = project_file_loader('unittest_dhm_anchor_anchor_6_poles.json')


class TestPoles(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        pass
    
    @classmethod
    def tearDownClass(cls):
        pass
        
    def test_angriffswinkel_anchor_anchor(self):
        conf: ConfigHandler = ConfigHandler()
        poles: Poles
        result, params, poles, profile, status = calculate_cable_line(conf, TEST_PROJECT_2)
        firstPole = poles.poles[0]
        lastPoles = poles.poles[-1]
        
        # No Angriffswinkel for start point because it's a cran
        self.assertAlmostEqual(firstPole['angriff'], 21.0, 1)
        self.assertAlmostEqual(lastPoles['angriff'], 24.4, 1)
    
    def test_angriffswinkel_crane_pole_anchor(self):
        conf: ConfigHandler = ConfigHandler()
        poles: Poles
        result, params, poles, profile, status = calculate_cable_line(conf)
        firstPole = poles.poles[0]
        lastPoles = poles.poles[-1]
        
        # No Angriffswinkel for start point because it's a cran
        self.assertIs(firstPole['angriff'], nan)
        # TODO: This one is wrong
        self.assertAlmostEqual(lastPoles['angriff'], -79.3, 1)
    
    def test_angriffswinkel_pole_anchors(self):
        conf: ConfigHandler = ConfigHandler()
        poles: Poles
        result, params, poles, profile, status = calculate_cable_line(conf, TEST_PROJECT)
        firstPole = poles.poles[0]
        lastPoles = poles.poles[-1]
        
        self.assertAlmostEqual(firstPole['angriff'], 9.0, 1)
        # TODO: This one is wrong
        self.assertAlmostEqual(lastPoles['angriff'], -53.3, 1)



if __name__ == '__main__':
    unittest.main()
