
from qgis.PyQt.QtTest import QSignalSpy
from qgis.testing import unittest

from tools.calcThreshold import ThresholdUpdater
from core.cablelineFinal import preciseCable, updateWithCableCoordinates
from gui.adjustmentDialog_thresholds import AdjustmentDialogThresholds
from . import BASIC_PROJECT_FILE
from tools.configHandler import ConfigHandler



class TestCalcThreshold(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        cls.conf = ConfigHandler()
        cls.conf.loadSettings(BASIC_PROJECT_FILE)
        cls.conf.prepareForCalculation()
        cls.result, cls.status = cls.conf.loadCableDataFromFile()
        cls.params = cls.conf.params
        cls.project = cls.conf.project
        cls.dhm = cls.project.heightSource
        cls.profile = cls.project.profile
        cls.poles = cls.project.poles
        
        # Do an initial calculation se we get the complete data,
        #  since not everything is saved in the project file
        params = cls.params.getSimpleParameterDict()
        cls.cableline, force, seil_possible = preciseCable(params, cls.poles,
                                                           cls.result['optSTA'])
        cls.result['cableline'] = cls.cableline
        cls.result['force'] = force
        cls.profile.updateProfileAnalysis(cls.cableline)
        cls.result['maxDistToGround'] = cls.cableline['maxDistToGround']
    
    @classmethod
    def tearDownClass(cls):
        pass
    
    
    def test_threshold_update(self):
        # Threshold (thd) tab
        thdTblSize = [5, 6]
        
        def update_callback():
            pass
        
        thdLayout = MockAdjustmentDialogThresholds()
        thdUpdater = ThresholdUpdater(thdLayout, thdTblSize, update_callback)
        
        thdUpdater.update([
            self.cableline['groundclear_rel'],  # Distance cable - terrain
            [
                self.result['force']['MaxSeilzugkraft'][0],   # Max force on cable
                self.result['force']['MaxSeilzugkraft_L'][0]    # Cable force at highest point
            ],
            self.result['force']['Sattelkraft_Total'][0],  # Max force on pole
            self.result['force']['Lastseilknickwinkel'],  # Cable angle on pole
            self.result['force']['Leerseilknickwinkel']],  # Cable angle on pole
            self.params, self.poles, self.profile,
            (self.status in ['jumpedOver', 'savedFile'])
        )
        thdUpdater.update([
            self.cableline['groundclear_rel'],  # Distance cable - terrain
            [
                self.result['force']['MaxSeilzugkraft'][0],   # Max force on cable
                self.result['force']['MaxSeilzugkraft_L'][0]    # Cable force at highest point
            ],
            self.result['force']['Sattelkraft_Total'][0],  # Max force on pole
            self.result['force']['Lastseilknickwinkel'],  # Cable angle on pole
            self.result['force']['Leerseilknickwinkel']],  # Cable angle on pole
            self.params, self.poles, self.profile,
            (self.status in ['jumpedOver', 'savedFile'])
        )
        
        self.assertEqual(thdUpdater.rows[0][4], '6.0 m')
        self.assertEqual(thdUpdater.rows[1][4], '131.1 kN')
        self.assertEqual(thdUpdater.rows[2][4], '61.6 kN')
        self.assertEqual(thdUpdater.rows[3][4], '43.4 ° / -')
        self.assertEqual(thdUpdater.rows[4][4], '1.6 °')
     
        self.assertEqual(thdUpdater.rows[0][5]['xLoc'], [222])
        self.assertEqual(thdUpdater.rows[1][5]['xLoc'], [20, 68, 139, 216, 270, 297, 0.0])
        self.assertEqual(thdUpdater.rows[2][5]['xLoc'], [40.0, 97.0, 182.0, 250.0, 290.0])
        self.assertEqual(thdUpdater.rows[3][5]['xLoc'], [40.0, 97.0, 182.0, 250.0, 290.0])
        self.assertEqual(thdUpdater.rows[4][5]['xLoc'], [40.0, 97.0, 182.0, 250.0, 290.0])
        
        self.assertAlmostEqualList(thdUpdater.rows[0][5]['zLoc'], [1189.51])
        self.assertAlmostEqualList(thdUpdater.rows[1][5]['zLoc'], [1248.95, 1235.63, 1211.94, 1191.59, 1164.86, 1153.03, 1265.91])
        self.assertAlmostEqualList(thdUpdater.rows[1][5]['zLoc'], [1248.95, 1235.63, 1211.94, 1191.59, 1164.86, 1153.03, 1265.91])
        self.assertAlmostEqualList(thdUpdater.rows[2][5]['zLoc'], [1243.49, 1226.79, 1203.73, 1178.07, 1156.16])
        self.assertAlmostEqualList(thdUpdater.rows[3][5]['zLoc'], [1243.49, 1226.79, 1203.73, 1178.07, 1156.16])
        self.assertAlmostEqualList(thdUpdater.rows[4][5]['zLoc'], [1243.49, 1226.79, 1203.73, 1178.07, 1156.16])
        
        self.assertEqual(thdUpdater.rows[0][5]['color'], [3])
        self.assertEqual(thdUpdater.rows[1][5]['color'], [1, 1, 1, 1, 1, 1, 1])
        self.assertEqual(thdUpdater.rows[2][5]['color'], [1, 1, 1, 1, 1])
        self.assertEqual(thdUpdater.rows[3][5]['color'], [1, 1, 1, 1, 3])
        self.assertEqual(thdUpdater.rows[4][5]['color'], [2, 2, 1, 1, 1])
        
        self.assertEqual(thdUpdater.rows[0][5]['labelAlign'], ['bottom'])
        self.assertEqual(thdUpdater.rows[1][5]['labelAlign'], ['bottom', 'bottom', 'bottom', 'bottom', 'bottom', 'bottom', 'top'])
        self.assertEqual(thdUpdater.rows[2][5]['labelAlign'], ['bottom', 'bottom', 'bottom', 'bottom', 'bottom'])
        self.assertEqual(thdUpdater.rows[3][5]['labelAlign'], ['bottom', 'bottom', 'bottom', 'bottom', 'bottom'])
        self.assertEqual(thdUpdater.rows[4][5]['labelAlign'], ['bottom', 'bottom', 'bottom', 'bottom', 'bottom'])

        self.assertEqual(thdUpdater.plotLabels, [
            ['6.0 m'], 
            ['109.9 kN', '119.6 kN', '131.1 kN', '121.5 kN', '106.0 kN', '83.5 kN', 'am hoechsten Punkt:\n132.0 kN'], 
            ['38.2 kN', '39.7 kN', '44.6 kN', '47.3 kN', '61.6 kN'], 
            ['20.0 °', '19.1 °', '21.3 °', '25.5 °', '43.4 °'], 
            ['1.6 °', '2.2 °', '6.1 °', '9.0 °', '24.4 °']
        ])

    def assertAlmostEqualList(self, list1, list2, places=1):
        for locTrue, locTest in zip(list(list1), list(list2)):
            self.assertAlmostEqual(locTrue, locTest, places)
        
class MockAdjustmentDialogThresholds():
    
    def __init__(self):
        super().__init__()
    
    def populate(self, header, rows, val):
        pass
    
    def updateData(self, idx, row, val):
        pass

        
        

if __name__ == '__main__':
    unittest.main()
