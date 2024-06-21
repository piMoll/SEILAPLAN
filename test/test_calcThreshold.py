from typing import List
from qgis.testing import unittest

from . import BASIC_PROJECT_FILE, MINIMAL_PROJECT_FILE
from SEILAPLAN.tools.calcThreshold import ThresholdUpdater, ThresholdItem
from SEILAPLAN.core.cablelineFinal import preciseCable
from SEILAPLAN.tools.configHandler import ConfigHandler


def helper_callback():
    pass


class TestCalcThreshold(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        pass
    
    @classmethod
    def tearDownClass(cls):
        pass
    
    @staticmethod
    def helper_calculate_cableline(project_file=BASIC_PROJECT_FILE):
        conf = ConfigHandler()
        conf.loadSettings(project_file)
        conf.prepareForCalculation()
        result, status = conf.loadCableDataFromFile()
        project = conf.project
        params = conf.params
        profile = project.profile
        poles = project.poles
        simpleParams = params.getSimpleParameterDict()
        cableline, force, seil_possible = preciseCable(simpleParams, poles, result['optSTA'])
        result['cableline'] = cableline
        result['force'] = force
        profile.updateProfileAnalysis(cableline)
        result['maxDistToGround'] = cableline['maxDistToGround']
        return result, params, poles, profile, status
    
    def test_threshold_update(self):
        result, params, poles, profile, status = self.helper_calculate_cableline()
        
        thdLayout = MockAdjustmentDialogThresholds()
        thdUpdater = ThresholdUpdater(thdLayout, helper_callback)
        thdUpdater.update(result, params, poles, profile, (status == 'optiSuccess'))
        
        items: ThresholdItem
        items: List[ThresholdItem] = thdUpdater.items
        
        rowData = items[0].getDataRow()
        markers = items[0].plotMarkers
        self.assertEqual(rowData[4], '6.0 m')
        self.assertEqual(items[0].getMaxColor(), 3)
        self.assertEqual([marker.label for marker in markers], ['8.0 m', '7.4 m', '9.1 m', '6.0 m', '9.0 m'])
        self.assertEqual([marker.x for marker in markers], [27, 74, 131, 222, 258])
        self.assertAlmostEqualList([marker.z for marker in markers], [1249.04, 1235.15, 1217.35, 1188.68, 1176.07])
        self.assertEqual([marker.color for marker in markers], [1, 1, 1, 3, 1])
        self.assertEqual([marker.alignment for marker in markers], ['bottom', 'bottom', 'bottom', 'bottom', 'bottom'])
        
        rowData = items[1].getDataRow()
        markers = items[1].plotMarkers
        self.assertEqual(rowData[4], '131.1 kN')
        self.assertEqual(items[1].getMaxColor(), 1)
        self.assertEqual([marker.label for marker in markers], ['109.9 kN', '119.6 kN', '131.1 kN', '121.5 kN', '106.0 kN', '83.5 kN', 'am hoechsten Punkt:\n132.0 kN'])
        self.assertEqual([marker.x for marker in markers], [20, 68, 139, 216, 270, 297, 0.0])
        self.assertAlmostEqualList([marker.z for marker in markers], [1248.95, 1235.63, 1211.94, 1191.59, 1164.86, 1153.03, 1265.91])
        self.assertEqual([marker.color for marker in markers], [1, 1, 1, 1, 1, 1, 1])
        self.assertEqual([marker.alignment for marker in markers], ['bottom', 'bottom', 'bottom', 'bottom', 'bottom', 'bottom', 'top'])
        
        rowData = items[2].getDataRow()
        markers = items[2].plotMarkers
        self.assertEqual(rowData[4], '43.4 ° / -')
        self.assertEqual(items[2].getMaxColor(), 3)
        self.assertEqual([marker.label for marker in markers], ['20.0 °', '19.1 °', '21.3 °', '25.5 °', '43.4 °'])
        self.assertEqual([marker.x for marker in markers], [40.0, 97.0, 182.0, 250.0, 290.0])
        self.assertAlmostEqualList([marker.z for marker in markers], [1243.49, 1226.79, 1203.73, 1178.07, 1156.16])
        self.assertEqual([marker.color for marker in markers], [1, 1, 1, 1, 3])
        self.assertEqual([marker.alignment for marker in markers], ['bottom', 'bottom', 'bottom', 'bottom', 'bottom'])
        
        rowData = items[3].getDataRow()
        markers = items[3].plotMarkers
        self.assertEqual(rowData[4], '1.6 °')
        self.assertEqual(items[3].getMaxColor(), 2)
        self.assertEqual([marker.label for marker in markers], ['1.6 °', '2.2 °', '6.1 °', '9.0 °', '24.4 °'])
        self.assertEqual([marker.x for marker in markers], [40.0, 97.0, 182.0, 250.0, 290.0])
        self.assertAlmostEqualList([marker.z for marker in markers], [1243.49, 1226.79, 1203.73, 1178.07, 1156.16])
        self.assertEqual([marker.color for marker in markers], [2, 2, 1, 1, 1])
        self.assertEqual([marker.alignment for marker in markers], ['bottom', 'bottom', 'bottom', 'bottom', 'bottom'])
    
    def test_threshold_update_with_empty_extrema(self):
        result, params, poles, profile, status = self.helper_calculate_cableline(MINIMAL_PROJECT_FILE)

        thdLayout = MockAdjustmentDialogThresholds()
        thdUpdater = ThresholdUpdater(thdLayout, helper_callback)
        thdUpdater.update(result, params, poles, profile, status == 'optiSuccess')
        
        items: ThresholdItem
        items: List[ThresholdItem] = thdUpdater.items
    
        for item in items[2:]:
            rowData = item.getDataRow()
            markers = item.plotMarkers
            maxCol = item.getMaxColor()
            
            self.assertEqual(rowData[4], '-')
            self.assertEqual(maxCol, 1)
            self.assertEqual([marker.label for marker in markers], [])
            self.assertEqual([marker.x for marker in markers], [])
            self.assertAlmostEqualList([marker.z for marker in markers], [])
            self.assertEqual([marker.color for marker in markers], [])
            self.assertEqual([marker.alignment for marker in markers], [])


    def assertAlmostEqualList(self, list1, list2, places=1):
        for locTrue, locTest in zip(list(list1), list(list2)):
            self.assertAlmostEqual(locTrue, locTest, places)

  
class MockAdjustmentDialogThresholds(object):
    
    def __init__(self):
        super().__init__()
    
    def initTableGrid(self, header, rowCount):
        pass
    
    def updateData(self, tblData, init=False):
        pass
    
    def colorBackground(self, row, col, color):
        pass
    
    def updateTabIcon(self, warn):
        pass

        
        

if __name__ == '__main__':
    unittest.main()
