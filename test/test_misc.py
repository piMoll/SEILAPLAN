import unittest

from utils.misc import versionAsInteger


class TestVersionAsInteger(unittest.TestCase):
    def test_valid_version(self):
        version = "1.2.3"
        expected_result = 10203
        self.assertEqual(versionAsInteger(version), expected_result)
    
    def test_single_digit_version(self):
        version = "1.0.0"
        expected_result = 10000
        self.assertEqual(versionAsInteger(version), expected_result)
    
    def test_two_digit_version(self):
        version = "10.11.12"
        expected_result = 101112
        self.assertEqual(versionAsInteger(version), expected_result)
    
    def test_mixed_digit_version(self):
        version = "1.10.3"
        expected_result = 11003
        self.assertEqual(versionAsInteger(version), expected_result)
    
    def test_zero_in_version(self):
        version = "0.00.1"
        expected_result = 1
        self.assertEqual(versionAsInteger(version), expected_result)
    
    def test_version_with_more_segments(self):
        version = "1.2.3.4"
        with self.assertRaises(ValueError):
            versionAsInteger(version)
    
    def test_too_short_version(self):
        version = "11.12"
        with self.assertRaises(ValueError):
            versionAsInteger(version)


if __name__ == "__main__":
    unittest.main()
