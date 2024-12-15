from typing import List
import unittest
from . import MINIMAL_PROJECT_FILE
from ._test_helper import calculate_cable_line
from SEILAPLAN.tools.globals import ResultQuality
from SEILAPLAN.tools.calcThreshold import ThresholdUpdater, PlotTopic
from SEILAPLAN.tools.configHandler import ConfigHandler


class TestCalcThreshold(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        pass
    
    @classmethod
    def tearDownClass(cls):
        pass
    
    def test_threshold_update(self):
        conf: ConfigHandler = ConfigHandler()
        result, params, poles, profile, quality = calculate_cable_line(conf)
        
        thdLayout = MockAdjustmentDialogThresholds()
        thdUpdater = ThresholdUpdater(thdLayout)
        thdUpdater.update(result, params, poles, profile, (quality == ResultQuality.SuccessfulOptimization))
        
        topic: PlotTopic
        for topic in thdUpdater.topics:

            rowData = topic.getDataRow()
            markers = topic.plotMarkers
            
            if topic.id == 'bodenabstand':
                self.assertEqual(rowData[4], '6.0 m')
                self.assertEqual(topic.getMaxColor(), 3)
                self.assertEqual([marker.label for marker in markers], ['8.0 m', '7.4 m', '9.1 m', '6.0 m', '9.0 m'])
                self.assertEqual([marker.x for marker in markers], [27, 74, 131, 222, 258])
                self.assertAlmostEqualList([marker.z for marker in markers], [1249.04, 1235.15, 1217.35, 1188.68, 1176.07])
                self.assertEqual([marker.color for marker in markers], [1, 1, 1, 3, 1])
                self.assertEqual([marker.alignment for marker in markers], ['bottom', 'bottom', 'bottom', 'bottom', 'bottom'])
            
            if topic.id == 'seilzugkraft':
                self.assertEqual(rowData[4], '131.1 kN')
                self.assertEqual(topic.getMaxColor(), 1)
                self.assertEqual([marker.label for marker in markers], ['109.9 kN', '119.6 kN', '131.1 kN', '121.5 kN', '106.0 kN', '83.5 kN', 'am hoechsten Punkt:\n132.0 kN'])
                self.assertEqual([marker.x for marker in markers], [20, 68, 139, 216, 270, 297, 0.0])
                self.assertAlmostEqualList([marker.z for marker in markers], [1248.95, 1235.63, 1211.94, 1191.59, 1164.86, 1153.03, 1265.91])
                self.assertEqual([marker.color for marker in markers], [1, 1, 1, 1, 1, 1, 1])
                self.assertEqual([marker.alignment for marker in markers], ['bottom', 'bottom', 'bottom', 'bottom', 'bottom', 'bottom', 'top'])
            
            if topic.id == 'lastseilknickwinkel':
                self.assertEqual(rowData[4], '43.4 ° / -')
                self.assertEqual(topic.getMaxColor(), 3)
                self.assertEqual([marker.label for marker in markers], ['20.0 °', '19.1 °', '21.3 °', '25.5 °', '43.4 °'])
                self.assertEqual([marker.x for marker in markers], [40.0, 97.0, 182.0, 250.0, 290.0])
                self.assertAlmostEqualList([marker.z for marker in markers], [1243.49, 1226.79, 1203.73, 1178.07, 1156.16])
                self.assertEqual([marker.color for marker in markers], [1, 1, 1, 1, 3])
                self.assertEqual([marker.alignment for marker in markers], ['bottom', 'bottom', 'bottom', 'bottom', 'bottom'])
            
            if topic.id == 'leerseilknickwinkel':
                self.assertEqual(rowData[4], '1.6 °')
                self.assertEqual(topic.getMaxColor(), 2)
                self.assertEqual([marker.label for marker in markers], ['1.6 °', '2.2 °', '6.1 °', '9.0 °', '24.4 °'])
                self.assertEqual([marker.x for marker in markers], [40.0, 97.0, 182.0, 250.0, 290.0])
                self.assertAlmostEqualList([marker.z for marker in markers], [1243.49, 1226.79, 1203.73, 1178.07, 1156.16])
                self.assertEqual([marker.color for marker in markers], [2, 2, 1, 1, 1])
                self.assertEqual([marker.alignment for marker in markers], ['bottom', 'bottom', 'bottom', 'bottom', 'bottom'])
                    
            if topic.id == 'sattelkraft':
                self.assertEqual(topic.getMaxColor(), 1)
                self.assertEqual([marker.label for marker in markers], ['38.2 kN', '39.7 kN', '44.6 kN', '47.3 kN', '61.6 kN'])
                self.assertEqual([marker.x for marker in markers], [40.0, 97.0, 182.0, 250.0, 290.0])
                self.assertAlmostEqualList([marker.z for marker in markers], [1243.49, 1226.79, 1203.73, 1178.07, 1156.16])
                self.assertEqual([marker.color for marker in markers], [1, 1, 1, 1, 1])
                self.assertEqual([marker.alignment for marker in markers], ['bottom', 'bottom', 'bottom', 'bottom', 'bottom'])
            
            if topic.id == 'bhd':
                self.assertEqual(topic.getMaxColor(), 1)
                self.assertEqual([marker.label for marker in markers], ['36 cm', '39 cm', '36 cm', '39 cm', '40 cm', '65 cm'])
                self.assertEqual([marker.x for marker in markers], [40.0, 97.0, 182.0, 250.0, 290.0, 305.0])
                self.assertAlmostEqualList([marker.z for marker in markers], [1243.49, 1226.79, 1203.73, 1178.07, 1156.16, 1148.56])
                self.assertEqual([marker.color for marker in markers], [1, 1, 1, 1, 1, 1])
                self.assertEqual([marker.alignment for marker in markers], ['bottom', 'bottom', 'bottom', 'bottom', 'bottom', 'bottom'])
            
            if topic.id == 'leerseildurchhang':
                self.assertEqual(topic.getMaxColor(), 1)
                self.assertEqual([marker.label for marker in markers], ['0.1 m', '0.1 m', '0.3 m', '0.2 m', '0.1 m', '0.0 m'])
                self.assertEqual([marker.x for marker in markers], [20, 68, 139, 216, 270, 297])
                self.assertAlmostEqualList([marker.z for marker in markers], [1248.95, 1235.63, 1211.94, 1191.59, 1164.86, 1153.03])
                self.assertEqual([marker.color for marker in markers], [1, 1, 1, 1, 1, 1])
                self.assertEqual([marker.alignment for marker in markers], ['bottom', 'bottom', 'bottom', 'bottom', 'bottom', 'bottom'])
            
            if topic.id == 'lastseildurchhang':
                self.assertEqual(topic.getMaxColor(), 1)
                self.assertEqual([marker.label for marker in markers], ['3.3 m', '4.4 m', '6.3 m', '5.2 m', '3.8 m', '2.6 m'])
                self.assertEqual([marker.x for marker in markers], [20, 68, 139, 216, 270, 297])
                self.assertAlmostEqualList([marker.z for marker in markers], [1248.95, 1235.63, 1211.94, 1191.59, 1164.86, 1153.03])
                self.assertEqual([marker.color for marker in markers], [1, 1, 1, 1, 1, 1])
                self.assertEqual([marker.alignment for marker in markers], ['bottom', 'bottom', 'bottom', 'bottom', 'bottom', 'bottom'])
        
    def test_threshold_update_with_empty_extrema(self):
        conf: ConfigHandler = ConfigHandler()
        result, params, poles, profile, quality = calculate_cable_line(conf, MINIMAL_PROJECT_FILE)

        thdLayout = MockAdjustmentDialogThresholds()
        thdUpdater = ThresholdUpdater(thdLayout)
        thdUpdater.update(result, params, poles, profile, quality == ResultQuality.SuccessfulOptimization)
        
        items: PlotTopic
        items: List[PlotTopic] = thdUpdater.getThresholdTopics()
    
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
        self.assertEqual(len(list1), len(list2))
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
