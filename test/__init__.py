import os
import sys
from qgis.testing import unittest
from qgis.core import QgsApplication
import SEILAPLAN

# Add shipped libraries to python path
libPath = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'lib')
if libPath not in sys.path:
    sys.path.insert(-1, libPath)

TMP_FILE_PREFIX = 'tmp_'

SEILAPLAN.DEBUG = True


def startTestRun(self):
    """Runs once before any test."""
    QGIS = QgsApplication([], False)
    QGIS.initQgis()


setattr(unittest.TestResult, 'startTestRun', startTestRun)


def stopTestRun(self):
    """Called once after all tests are executed."""
    
    # Cleanup temporary project files that got created via project_file_loader()
    test_dir = os.path.dirname(__file__)
    for file in os.listdir(os.path.join(test_dir, 'testdata')):
        if file.startswith(TMP_FILE_PREFIX):
            os.remove(os.path.join(test_dir, 'testdata', file))


setattr(unittest.TestResult, 'stopTestRun', stopTestRun)


def project_file_loader(fileName):
    test_dir = os.path.dirname(__file__)
    file_path = os.path.join(test_dir, 'testdata', fileName)
    file_path_tmp = os.path.join(test_dir, 'testdata', TMP_FILE_PREFIX + fileName)
    # Replace any path placeholders with absolute path
    with open(file_path, 'r') as f:
        project_content = f.read()
    project_content = project_content.replace('{HOMEPATH}', os.path.abspath(os.path.dirname(test_dir)))
    with open(file_path_tmp, 'w') as f:
        f.write(project_content)
    return file_path_tmp



BASIC_PROJECT_FILE = project_file_loader('unittest_dhm_crane_poleanchor_6_poles.json')
MINIMAL_PROJECT_FILE = project_file_loader('unittest_dhm_poleanchor_poleanchor_0_poles.json')
