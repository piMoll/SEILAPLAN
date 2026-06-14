import unittest

from core.terrainAnalysis import stuePos

from SEILAPLAN.core.mainSeilaplan import main
from SEILAPLAN.tests import project_file_loader
from SEILAPLAN.tests._test_helper import MockTask
from SEILAPLAN.tools.configHandler import ConfigHandler

# Flat terrain, 111m cable line
TEST_PROJECT_flat_terrain = project_file_loader("unittest_peakdetect_flat_surface.json")
# Steep hill but uniform terrain
TEST_PROJECT_uniform_terrain = project_file_loader(
    "unittest_peakdetect_uniform_surface.json"
)


class TestTerrainAnalysis(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        pass

    @classmethod
    def tearDownClass(cls):
        pass

    def test_peak_detect_horizontal_line_fails_with_pole_anchors(self):
        conf: ConfigHandler = ConfigHandler()
        success = conf.loadSettings(TEST_PROJECT_flat_terrain)
        if not success:
            raise Exception("Not able to load project file")
        conf.project.A_type = "pole_anchor"
        conf.project.E_type = "pole_anchor"
        conf.prepareForCalculation(True)
        task = MockTask(conf)
        result = main(task, conf.project)

        self.assertFalse(result)
        self.assertIn("Aufgrund der Gelaendeform", task.exception)

    def test_peak_detect_horizontal_line_fails_with_poles(self):
        conf: ConfigHandler = ConfigHandler()
        success = conf.loadSettings(TEST_PROJECT_flat_terrain)
        if not success:
            raise Exception("Not able to load project file")
        conf.project.A_type = "pole"
        conf.project.E_type = "pole"
        conf.prepareForCalculation(True)
        task = MockTask(conf)
        result = main(task, conf.project)

        self.assertFalse(result)
        self.assertIn("Aufgrund der Gelaendeform", task.exception)

    def test_peak_detect_horizontal_line_fails_with_poles_and_low_ground_distance(self):
        conf: ConfigHandler = ConfigHandler()
        success = conf.loadSettings(TEST_PROJECT_flat_terrain)
        if not success:
            raise Exception("Not able to load project file")
        conf.project.A_type = "pole"
        conf.project.E_type = "pole"
        conf.params.setParameter("Bodenabst_min", 1.0)
        conf.prepareForCalculation(True)
        task = MockTask(conf)
        result = main(task, conf.project)

        self.assertFalse(result)
        self.assertIn("Aufgrund der Gelaendeform", task.exception)

    def test_peak_detect_finds_maxima(self):
        conf: ConfigHandler = ConfigHandler()
        success = conf.loadSettings(TEST_PROJECT_uniform_terrain)
        if not success:
            raise Exception("Not able to load project file")
        conf.prepareForCalculation(False)

        gp, StuetzenPos, diIdx, R_R = stuePos(
            conf.params.getSimpleParameterDict(),
            conf.project.profile,
            conf.project.noPoleSection,
            conf.project.fixedPoles,
        )
        self.assertEqual(conf.project.profile.peakLoc_x[0], 30)
        self.assertEqual(conf.project.profile.peakLoc_x[1], 69)
        self.assertEqual(conf.project.profile.peakLoc_x[2], 90)

    def test_peak_detect_horizontal_line_sandbox_setup(self):
        """This is a test setup to see what parameters influence the optimization
        in what way when calculating on a flat surface.
        The current setup tests what HM max value influences the optimization."""

        # Remove this line to run the test
        return

        for hm_max in range(17, 24):
            conf: ConfigHandler = ConfigHandler()
            success = conf.loadSettings(TEST_PROJECT_flat_terrain)
            if not success:
                raise Exception("Not able to load project file")
            conf.project.A_type = "pole"
            conf.project.E_type = "pole"
            # conf.params.setParameter("SF_T", 3)
            # conf.params.setParameter("Bodenabst_min", 1)
            # conf.params.setParameter("Befahr_A", 1)
            conf.params.setParameter("Befahr_E", 1)
            conf.params.setParameter("HM_Delta", 1)
            conf.params.setParameter("HM_min", 5)
            conf.params.setParameter("HM_max", hm_max)
            conf.params.setParameter("HM_nat", 30)
            conf.prepareForCalculation(True)
            task = MockTask(conf)
            result = main(task, conf.project)
            if result:
                print(
                    "hm_max: ",
                    hm_max,
                    "optSTA:",
                    result["optSTA_arr"],
                    "HM dist: ",
                    conf.project.poles.getAsArray(False)[0],
                    "HM h: ",
                    conf.project.poles.getAsArray(False)[2],
                    "error: ",
                    task.status,
                )
            else:
                print("hm_max: ", hm_max, "non-successful")


if __name__ == "__main__":
    unittest.main()
