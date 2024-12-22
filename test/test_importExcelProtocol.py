import os
import unittest
from copy import deepcopy

import numpy as np
from unittest import mock
from test import TESTDATA_DIR
from tools.importExcelProtocol import ExcelProtocolReader


class TestExcelProtocolReader(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        # Define paths for test files
        cls.testfile_missing_first_distance = os.path.join(TESTDATA_DIR, "Protocol_missing_first_distance.xlsx")
        cls.testfile_ok_abs_point_at_end = os.path.join(TESTDATA_DIR, "Protocol_ok_abs_point_at_end.xlsx")
        cls.testfile_abs_point_outside_measures = os.path.join(TESTDATA_DIR, "Protocol_abs_point_outside_measures.xlsx")
        cls.testfile_missing_x_in_abs_point = os.path.join(TESTDATA_DIR, "Protocol_missing_x_in_abs_point.xlsx")
        cls.testfile_missing_z_in_abs_point = os.path.join(TESTDATA_DIR, "Protocol_missing_z_in_abs_point.xlsx")
        cls.testfile_full_protocol = os.path.join(TESTDATA_DIR, "Protocol_ok.xlsx")
        
        cls.mock_protocol = {
            'G3': 'v3.4', 'C4': 'Value1', 'C6': 'Value2', 'G6': 'Value3',
            'G8': 'Value4', 'C10': 'Value5', 'C8': 'Value6',
            # Abs point coordinates
            'C14': '2600000', 'E14': '1200000', 'G14': '300.0',
            'C16': '0',     # Abs point number
            'C18': '0',   # Azimut: going perfectly east
            # Measurements: dist, incline, note
            'B21': '10.0',      'C21': '0.0',    'D21': 'first note',      'A22': '1',
            'B23': '10.0',      'C23': '0',      'D23': 'second note',    'A24': '2',
            'B25': '20.0',      'C25': '0',      'D25': '',               'A26': '3',
        }
    
    @mock.patch('tools.importExcelProtocol.xl.readxl')
    def test_check_structure_valid_template(self, mock_readxl):
        mock_sheet = mock.Mock()
        mock_sheet.address.return_value = 'v3.4'
        mock_readxl.return_value.ws.return_value = mock_sheet
        
        reader = ExcelProtocolReader('mock/path')
        reader.checkStructure()
        
        self.assertTrue(reader.valid)
    
    @mock.patch('tools.importExcelProtocol.xl.readxl')
    def test_check_structure_invalid_template(self, mock_readxl):
        mock_sheet = mock.Mock()
        mock_sheet.address.side_effect = ValueError
        mock_readxl.return_value.ws.return_value = mock_sheet
        
        reader = ExcelProtocolReader('mock/path')
        reader.checkStructure()
        
        self.assertFalse(reader.valid)
    
    @mock.patch('tools.importExcelProtocol.xl.readxl')
    def test_readOutData_minimal_valid_protocol(self, mock_readxl):
        mock_sheet = mock.Mock()
        mock_sheet.address.side_effect = lambda address: {
            'G3': 'v3.4',
            'C14': '2600000', 'E14': '1200000',
            'C16': '0',     # Abs point number
            'C18': '0',     # Azimut
            'A21': '1', 'B21': '100.0', 'C21': '0.0',
        }.get(address, '')
        mock_readxl.return_value.ws.return_value = mock_sheet
        
        reader = ExcelProtocolReader('mock/path')
        result = reader.readOutData()
        
        self.assertTrue(result)
        self.assertTrue(np.array_equal(reader.surveyPoints['x'], np.array([2600000, 2600000])))
        self.assertTrue(np.array_equal(reader.surveyPoints['y'], np.array([1200000, 1200100])))
        self.assertTrue(np.array_equal(reader.surveyPoints['z'], np.array([0, 0])))
    
    @mock.patch('tools.importExcelProtocol.xl.readxl')
    def test_readOutData_invalid_abs_point_coordinates(self, mock_readxl):
        mock_sheet = mock.Mock()
        mock_protocol = deepcopy(self.mock_protocol)
        # Change E coord abs point
        mock_protocol[ExcelProtocolReader.CELL_Y] = '3.ABC'
        mock_sheet.address.side_effect = lambda address: mock_protocol.get(address, '')
        mock_readxl.return_value.ws.return_value = mock_sheet
        
        reader = ExcelProtocolReader('mock/path')
        result = reader.readOutData()
        
        self.assertFalse(result)
        self.assertEqual(reader.errorMsg, 'Koordinatenwerte sind ungueltig')
    
    @mock.patch('tools.importExcelProtocol.xl.readxl')
    def test_readOutData_invalid_template_version(self, mock_readxl):
        mock_sheet = mock.Mock()
        mock_protocol = deepcopy(self.mock_protocol)
        # Change template version
        mock_protocol[ExcelProtocolReader.CELL_VERSION] = 'v2.0'
        mock_sheet.address.side_effect = lambda address: mock_protocol.get(address, '')
        mock_readxl.return_value.ws.return_value = mock_sheet
        
        reader = ExcelProtocolReader('mock/path')
        result = reader.readOutData()
        
        self.assertFalse(result)
        self.assertEqual(
            reader.errorMsg,
            'Veraltetes Template, Daten koennen nicht eingelesen werden'
        )
    
    @mock.patch('tools.importExcelProtocol.xl.readxl')
    def test_readOutData_invalid_abs_point_number(self, mock_readxl):
        mock_sheet = mock.Mock()
        mock_protocol = deepcopy(self.mock_protocol)
        # Change E coord abs point
        mock_protocol[ExcelProtocolReader.CELL_NR] = '999'
        mock_sheet.address.side_effect = lambda address: mock_protocol.get(address, '')
        mock_readxl.return_value.ws.return_value = mock_sheet
        
        reader = ExcelProtocolReader('mock/path')
        result = reader.readOutData()
        
        self.assertFalse(result)
        self.assertEqual(reader.errorMsg, 'Punkt-Nr. nicht in Protokoll vorhanden')
    
    @mock.patch('tools.importExcelProtocol.xl.readxl')
    def test_readOutData_incomplete_first_measurements(self, mock_readxl):
        mock_sheet = mock.Mock()
        mock_protocol = deepcopy(self.mock_protocol)
        # Remove first slope value
        mock_protocol['C21'] = ''
        mock_sheet.address.side_effect = lambda address: mock_protocol.get(address, '')
        mock_readxl.return_value.ws.return_value = mock_sheet
        
        reader = ExcelProtocolReader('mock/path')
        result = reader.readOutData()
        
        self.assertFalse(result)
        self.assertIn(f'Fehlende oder fehlerhafte Werte fuer Distanz oder Neigung auf Zeile {ExcelProtocolReader.ROW_START}', reader.errorMsg)
        
    @mock.patch('tools.importExcelProtocol.xl.readxl')
    def test_readOutData_azimut_full_100(self, mock_readxl):
        mock_sheet = mock.Mock()
        mock_protocol_azi_100 = deepcopy(self.mock_protocol)
        mock_protocol_azi_100['C18'] = '100'
        mock_sheet.address.side_effect = lambda address: mock_protocol_azi_100.get(address, '')
        mock_readxl.return_value.ws.return_value = mock_sheet
        
        reader = ExcelProtocolReader('mock/path')
        result = reader.readOutData()
        
        self.assertTrue(result)
        self.assertTrue(np.array_equal(reader.surveyPoints['x'], np.array([2600000, 2600010, 2600020, 2600040])))
        self.assertTrue(np.array_equal(reader.surveyPoints['y'], np.array([1200000, 1200000, 1200000, 1200000])))
        self.assertTrue(np.array_equal(reader.surveyPoints['z'], np.array([300, 300, 300, 300])))
    
    @mock.patch('tools.importExcelProtocol.xl.readxl')
    def test_readOutData_azimut_full_300(self, mock_readxl):
        mock_sheet = mock.Mock()
        mock_protocol_azi_300 = deepcopy(self.mock_protocol)
        mock_protocol_azi_300['C18'] = '300'
        mock_sheet.address.side_effect = lambda address: mock_protocol_azi_300.get(address, '')
        mock_readxl.return_value.ws.return_value = mock_sheet
        
        reader = ExcelProtocolReader('mock/path')
        result = reader.readOutData()
        
        self.assertTrue(result)
        self.assertTrue(np.array_equal(reader.surveyPoints['x'], np.array([2600000, 2599990, 2599980, 2599960])))
        self.assertTrue(np.array_equal(reader.surveyPoints['y'], np.array([1200000, 1200000, 1200000, 1200000])))
        self.assertTrue(np.array_equal(reader.surveyPoints['z'], np.array([300, 300, 300, 300])))
        
    @mock.patch('tools.importExcelProtocol.xl.readxl')
    def test_readOutData_azimut_full_400(self, mock_readxl):
        mock_sheet = mock.Mock()
        mock_protocol_azi_400 = deepcopy(self.mock_protocol)
        mock_protocol_azi_400['C18'] = '400'
        mock_sheet.address.side_effect = lambda address: mock_protocol_azi_400.get(address, '')
        mock_readxl.return_value.ws.return_value = mock_sheet
        
        reader = ExcelProtocolReader('mock/path')
        result = reader.readOutData()
        
        self.assertTrue(result)
        self.assertTrue(np.array_equal(reader.surveyPoints['x'], np.array([2600000, 2600000, 2600000, 2600000])))
        self.assertTrue(np.array_equal(reader.surveyPoints['y'], np.array([1200000, 1200010, 1200020, 1200040])))
        self.assertTrue(np.array_equal(reader.surveyPoints['z'], np.array([300, 300, 300, 300])))
        
    @mock.patch('tools.importExcelProtocol.xl.readxl')
    def test_readOutData_read_notes(self, mock_readxl):
        mock_sheet = mock.Mock()
        mock_protocol = deepcopy(self.mock_protocol)
        mock_sheet.address.side_effect = lambda address: mock_protocol.get(address, '')
        mock_readxl.return_value.ws.return_value = mock_sheet
    
        reader = ExcelProtocolReader('mock/path')
        result = reader.readOutData()
    
        self.assertTrue(result)
        self.assertTrue(np.array_equal(reader.nr, np.array([0, 1, 2, 3])))
        self.assertEqual(reader.notes['onPoint'], ['', '', '', ''])
        self.assertEqual(reader.notes['between'], ['first note', 'second note', ''])

    #
    # Next few tests load actual excel files
    
    def test_file_missing_first_distance(self):
        reader = ExcelProtocolReader(self.testfile_missing_first_distance)
        result = reader.readOutData()
        self.assertFalse(result)
        self.assertIn(f'Fehlende oder fehlerhafte Werte fuer Distanz oder Neigung auf Zeile {ExcelProtocolReader.ROW_START}', reader.errorMsg)
    
    def test_file_abs_point_at_end(self):
        reader = ExcelProtocolReader(self.testfile_ok_abs_point_at_end)
        result = reader.readOutData()
        self.assertTrue(result)
        self.assertEqual(reader.surveyPoints['x'][-1], 2640272)
        self.assertEqual(reader.surveyPoints['y'][-1], 1202143.3)
        self.assertEqual(reader.surveyPoints['z'][-1], 900)
        self.assertEqual(reader.nr[-1], 23)
    
    def test_file_abs_point_outside_measures(self):
        reader = ExcelProtocolReader(self.testfile_abs_point_outside_measures)
        result = reader.readOutData()
        self.assertFalse(result)
        self.assertIn(f'Punkt-Nr. nicht in Protokoll vorhanden', reader.errorMsg)
    
    def test_file_missing_x_in_abs_point(self):
        reader = ExcelProtocolReader(self.testfile_missing_x_in_abs_point)
        result = reader.readOutData()
        self.assertFalse(result)
        self.assertEqual(reader.errorMsg, 'Koordinatenwerte sind ungueltig')
    
    def test_file_missing_z_in_abs_point(self):
        reader = ExcelProtocolReader(self.testfile_missing_z_in_abs_point)
        result = reader.readOutData()
        self.assertTrue(result)
    
    def test_file_full_protocol(self):
        reader = ExcelProtocolReader(self.testfile_full_protocol)
        result = reader.readOutData()
        self.assertTrue(result)
        self.assertTrue(np.array_equal(np.round(reader.surveyPoints['x'], 3),
            np.array([
                2700020.873, 2700004.233, 2700000.000, 2699994.262, 2699983.595, 2699978.864,
                2699972.092, 2699969.575, 2699962.217, 2699951.550, 2699946.818, 2699940.122,
                2699937.605, 2699930.246, 2699919.397, 2699914.666, 2699907.969, 2699905.452,
                2699898.094, 2699887.426, 2699882.695, 2699875.999, 2699873.482, 2699866.123
            ])))
        self.assertTrue(np.array_equal(np.round(reader.surveyPoints['y'], 3),
            np.array([
                1299988.094, 1299997.586, 1300000.000, 1300003.273, 1300009.357, 1300012.056,
                1300015.918, 1300017.354, 1300021.551, 1300027.636, 1300030.334, 1300034.154,
                1300035.590, 1300039.787, 1300045.975, 1300048.674, 1300052.493, 1300053.929,
                1300058.126, 1300064.211, 1300066.910, 1300070.729, 1300072.165, 1300076.362
            ])))
        self.assertTrue(np.array_equal(np.round(reader.surveyPoints['z'], 3),
           np.array([
               993.132, 998.879, 1000.000, 1001.123, 1003.456, 1004.219, 1005.497, 1006.274,
               1009.002, 1011.335, 1012.098, 1013.824, 1014.601, 1017.329, 1016.829, 1017.592,
               1019.319, 1020.095, 1022.823, 1025.156, 1025.919, 1027.646, 1028.422, 1031.150
           ])))
        
        self.assertAlmostEqual(reader.nr[-1], 23)
        self.assertEqual(reader.notes['between'][0], 'Bach')
        self.assertEqual(reader.notes['between'][-1], 'Strasse')
        self.assertEqual(reader.notes['onPoint'][0], '')
        self.assertEqual(reader.notes['onPoint'][1], 'Anker')
        self.assertEqual(reader.notes['onPoint'][-1], '')
        self.assertEqual(reader.notes['onPoint'][-2], 'Anker')


if __name__ == "__main__":
    unittest.main()
