import unittest
from unittest import mock
from tools.importExcelProtocol import ExcelProtocolReader


class TestExcelProtocolReader(unittest.TestCase):
    
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
    def test_readOutData_valid_protocol(self, mock_readxl):
        mock_sheet = mock.Mock()
        mock_sheet.address.side_effect = lambda address: {
            'G3': 'v3.4', 'C4': 'Value1', 'C6': 'Value2', 'G6': 'Value3',
            'G8': 'Value4', 'C10': 'Value5', 'C8': 'Value6',
            'C14': '10.0', 'E14': '20.0', 'G14': '0.0',
            'C16': '0',
            'C18': '200',
            'B21': '100.0', 'C21': '10.0',
            'A23': '2', 'B23': '', 'C23': '',
        }.get(address, '')
        mock_readxl.return_value.ws.return_value = mock_sheet
        
        reader = ExcelProtocolReader('mock/path')
        result = reader.readOutData()
        
        self.assertTrue(result)
        self.assertIn('x', reader.surveyPoints)
        self.assertIn('y', reader.surveyPoints)
        self.assertIn('z', reader.surveyPoints)
    
    @mock.patch('tools.importExcelProtocol.xl.readxl')
    def test_readOutData_invalid_coordinates(self, mock_readxl):
        mock_sheet = mock.Mock()
        mock_sheet.address.side_effect = lambda address: {
            'G3': 'v3.4', 'C4': 'Value1', 'C6': 'Value2', 'G6': 'Value3',
            'G8': 'Value4', 'C10': 'Value5', 'C8': 'Value6',
            'C14': '200.0', 'E14': 'ABD.0', 'G14': '',
            'C16': '1',
            'C18': '200'
        }.get(address, '')
        mock_readxl.return_value.ws.return_value = mock_sheet
        
        reader = ExcelProtocolReader('mock/path')
        result = reader.readOutData()
        
        self.assertFalse(result)
        self.assertEqual(reader.errorMsg, 'Koordinatenwerte sind ungueltig')
    
    @mock.patch('tools.importExcelProtocol.xl.readxl')
    def test_readOutData_invalid_template_version(self, mock_readxl):
        mock_sheet = mock.Mock()
        mock_sheet.address.side_effect = lambda address: {
            'G3': 'v2.0'
        }.get(address, '')
        mock_readxl.return_value.ws.return_value = mock_sheet
        
        reader = ExcelProtocolReader('mock/path')
        result = reader.readOutData()
        
        self.assertFalse(result)
        self.assertEqual(
            reader.errorMsg,
            'Veraltetes Template, Daten koennen nicht eingelesen werden'
        )
    
    @mock.patch('tools.importExcelProtocol.xl.readxl')
    def test_readOutData_invalid_point_number(self, mock_readxl):
        mock_sheet = mock.Mock()
        mock_sheet.address.side_effect = lambda address: {
            'G3': 'v3.4', 'C4': 'Value1', 'C6': 'Value2', 'G6': 'Value3',
            'G8': 'Value4', 'C10': 'Value5', 'C8': 'Value6',
            'C14': '10.0', 'E14': '20.0', 'G14': '0.0',
            'C16': '9999',
            'C18': '200',
            'B21': '100.0', 'C21': '10.0',
            'A23': '2', 'B23': '', 'C23': '',
        }.get(address, '')
        mock_readxl.return_value.ws.return_value = mock_sheet
        
        reader = ExcelProtocolReader('mock/path')
        result = reader.readOutData()
        
        self.assertFalse(result)
        self.assertEqual(reader.errorMsg,
                         'Punkt-Nr. nicht in Protokoll vorhanden')
    
    @mock.patch('tools.importExcelProtocol.xl.readxl')
    def test_readOutData_incomplete_measurements(self, mock_readxl):
        mock_sheet = mock.Mock()
        mock_sheet.address.side_effect = lambda address: {
            'G3': 'v3.4',
            'C14': '10.0', 'E14': '20.0', 'G14': '0.0',
            'C16': '1',
            'C18': '200',
            f'B{ExcelProtocolReader.ROW_START}': '',  # Missing distance
            f'C{ExcelProtocolReader.ROW_START}': '10.0',  # Incomplete row
        }.get(address, '')
        mock_readxl.return_value.ws.return_value = mock_sheet
        
        reader = ExcelProtocolReader('mock/path')
        result = reader.readOutData()
        
        self.assertFalse(result)
        self.assertIn('Fehlende oder fehlerhafte Werte fuer Distanz oder Neigung auf Zeile _rowIdx_'.replace('_rowIdx_', str(ExcelProtocolReader.ROW_START)), reader.errorMsg)


if __name__ == "__main__":
    unittest.main()
