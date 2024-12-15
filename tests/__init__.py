import os
import sys
import tempfile
from qgis.core import QgsApplication
from qgis.testing import unittest
import SEILAPLAN

# Add shipped libraries to python path
libPath = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'lib')
if libPath not in sys.path:
    sys.path.insert(-1, libPath)

SEILAPLAN.DEBUG = True

TEST_DIR = os.path.dirname(__file__)
TESTDATA_DIR = os.path.join(TEST_DIR, 'testdata')
TMP_FILE_PREFIX = 'tmp_'

# Was necessary at one point, not anymore though
# os.environ["XDG_SESSION_TYPE"] = "xcb"

QGIS_APP = QgsApplication([], False)
tmpdir = tempfile.mkdtemp('', 'QGIS-PythonTestConfigPath-')
os.environ['QGIS_CUSTOM_CONFIG_PATH'] = tmpdir

QGIS_APP.initQgis()


def stopTestRun(self):
    """Called once after all tests are executed."""
    if QGIS_APP:
        QGIS_APP.exitQgis()
    
    # Cleanup temporary project files that got created via project_file_loader()
    for file in os.listdir(TESTDATA_DIR):
        if file.startswith(TMP_FILE_PREFIX):
            os.remove(os.path.join(TESTDATA_DIR, file))


setattr(unittest.TestResult, 'stopTestRun', stopTestRun)


def project_file_loader(fileName):
    file_path = os.path.join(TESTDATA_DIR, fileName)
    file_path_tmp = os.path.join(TESTDATA_DIR, TMP_FILE_PREFIX + fileName)
    # Replace any path placeholders with absolute path
    with open(file_path, 'r') as f:
        project_content = f.read()
    project_content = project_content.replace('{HOMEPATH}', SEILAPLAN.PLUGIN_DIR)
    with open(file_path_tmp, 'w') as f:
        f.write(project_content)
    return file_path_tmp


BASIC_PROJECT_FILE = project_file_loader('unittest_dhm_crane_poleanchor_6_poles.json')
MINIMAL_PROJECT_FILE = project_file_loader('unittest_dhm_poleanchor_poleanchor_0_poles.json')
