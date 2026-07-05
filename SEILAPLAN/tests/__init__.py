import os
import sys
import tempfile

from osgeo import gdal
from qgis.core import QgsApplication
from qgis.testing import unittest

import SEILAPLAN
from SEILAPLAN import PLUGIN_DIR

# Add shipped libraries to python path
libPath = os.path.join(PLUGIN_DIR, "lib")
if libPath not in sys.path:
    sys.path.insert(-1, libPath)

SEILAPLAN.DEBUG = True
gdal.UseExceptions()

TEST_DIR = os.path.dirname(__file__)
TESTDATA_DIR = os.path.join(str(TEST_DIR), "testdata")
TMP_DIR = os.path.join(str(TESTDATA_DIR), "tmp")

if not os.path.exists(TMP_DIR):
    os.makedirs(TMP_DIR)

QGIS_APP = QgsApplication([], False)
tmpdir = tempfile.mkdtemp("", "QGIS-PythonTestConfigPath-")
os.environ["QGIS_CUSTOM_CONFIG_PATH"] = tmpdir

QGIS_APP.initQgis()


def stopTestRun(_self):
    """Called once after all tests are executed."""
    if QGIS_APP:
        QGIS_APP.exitQgis()

    # Cleanup temporary project files
    for file in os.listdir(str(TMP_DIR)):
        os.remove(os.path.join(str(TMP_DIR), file))


setattr(unittest.TestResult, "stopTestRun", stopTestRun)


def project_file_loader(fileName):
    return os.path.join(str(TESTDATA_DIR), fileName)


BASIC_PROJECT_FILE = project_file_loader("unittest_dhm_crane_poleanchor_6_poles.json")
MINIMAL_PROJECT_FILE = project_file_loader(
    "unittest_dhm_poleanchor_poleanchor_0_poles.json"
)
