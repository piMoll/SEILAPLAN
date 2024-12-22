import os
import unittest
import numpy as np
from test import TESTDATA_DIR
from tools.importCsvXyz import CsvXyzReader
from . import TMP_DIR


class TestCsvXyzReader(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        # Define paths for test files
        cls.valid_csv_path = os.path.join(TMP_DIR, "tmp_valid.csv")
        cls.invalid_csv_path = os.path.join(TMP_DIR, "tmp_invalid.csv")
        cls.insufficient_csv_path = os.path.join(TMP_DIR, "tmp_insufficient.csv")
        cls.empty_csv_path = os.path.join(TMP_DIR, "tmp_empty.csv")
        cls.csv_semicolons_path = os.path.join(TESTDATA_DIR, 'Gelaendeprofil_XYZ.csv')
        cls.csv_with_comments_path = os.path.join(TESTDATA_DIR, 'Gelaendeprofil_XYZ_with_comments.csv')
        
        # Write valid CSV file
        with open(cls.valid_csv_path, 'w') as file:
            file.write("X,Y,Z\n1.0,2.0,3.0\n4.0,5.0,6.0\n")
        
        # Write invalid CSV file
        with open(cls.invalid_csv_path, 'w') as file:
            file.write("A,B,C\n1.0,2.0,3.0\n")
        
        # Create CSV file with insufficient data
        with open(cls.insufficient_csv_path, 'w') as file:
            file.write("X,Y,Z\n1,2.123,3\n")
        
        # Create empty CSV file
        with open(cls.empty_csv_path, 'w') as file:
            file.write("\n")
    
    def test_check_structure_valid_csv(self):
        reader = CsvXyzReader(self.valid_csv_path)
        self.assertTrue(reader.valid)
        self.assertEqual(reader.sep, ',')
        self.assertEqual(reader.idxX, 0)
        self.assertEqual(reader.idxY, 1)
        self.assertEqual(reader.idxZ, 2)
    
    def test_check_structure_invalid_csv(self):
        reader = CsvXyzReader(self.invalid_csv_path)
        self.assertFalse(reader.valid)
    
    def test_check_structure_empty_csv(self):
        reader = CsvXyzReader(self.empty_csv_path)
        self.assertFalse(reader.valid)
    
    def test_read_out_data_valid_csv(self):
        reader = CsvXyzReader(self.valid_csv_path)
        result = reader.readOutData()
        self.assertTrue(result)
        self.assertIn('x', reader.surveyPoints)
        self.assertIn('y', reader.surveyPoints)
        self.assertIn('z', reader.surveyPoints)
        self.assertTrue(
            np.array_equal(reader.surveyPoints['x'], np.array([1.0, 4.0])))
        self.assertTrue(
            np.array_equal(reader.surveyPoints['y'], np.array([2.0, 5.0])))
        self.assertTrue(
            np.array_equal(reader.surveyPoints['z'], np.array([3.0, 6.0])))
    
    def test_read_out_data_insufficient_points(self):
        reader = CsvXyzReader(self.insufficient_csv_path)
        result = reader.readOutData()
        self.assertFalse(result)
    
    def test_read_out_data_empty_csv(self):
        reader = CsvXyzReader(self.empty_csv_path)
        result = reader.readOutData()
        self.assertFalse(result)

    def test_csv_with_semicolons(self):
        reader = CsvXyzReader(self.csv_semicolons_path)
        result = reader.readOutData()
        self.assertTrue(result)
        self.assertIn('x', reader.surveyPoints)
        self.assertIn('y', reader.surveyPoints)
        self.assertIn('z', reader.surveyPoints)
        self.assertTrue(
            np.array_equal(reader.surveyPoints['x'], np.array([
                2600000, 2600012, 2600048, 2600261, 2600264, 2600270, 2600591, 2600715, 2600721, 2600744, 2600811])))
        self.assertTrue(
            np.array_equal(reader.surveyPoints['y'], np.array([
                1200000, 1200012, 1200048, 1200261, 1200264, 1200270, 1200591, 1200715, 1200721, 1200744, 1200811])))
        self.assertTrue(
            np.array_equal(reader.surveyPoints['z'], np.array([
                200, 212, 248, 461, 464, 470, 791, 915, 921, 944, 1011])))
    
    def test_csv_with_comments(self):
        reader = CsvXyzReader(self.csv_with_comments_path)
        reader.readOutData()
        self.assertTrue(
            np.array_equal(reader.surveyPoints['x'], np.array([
                2600000, 2600012, 2600048, 2600261, 2600264, 2600270, 2600591, 2600715, 2600721, 2600744, 2600811])))
        self.assertTrue(
            np.array_equal(reader.surveyPoints['y'], np.array([
                1200000, 1200012, 1200048, 1200261, 1200264, 1200270, 1200591, 1200715, 1200721, 1200744, 1200811])))
        self.assertTrue(
            np.array_equal(reader.surveyPoints['z'], np.array([
                200, 212, 248, 461, 464, 470, 791, 915, 921, 944, 1011])))


if __name__ == '__main__':
    unittest.main()
