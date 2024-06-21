import os
import sys
import SEILAPLAN
# Add shipped libraries to python path
libPath = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'lib')
if libPath not in sys.path:
    sys.path.insert(-1, libPath)


test_dir = os.path.dirname(__file__)
BASIC_PROJECT_FILE = os.path.join(test_dir, 'testdata', 'unittest_dhm_crane_anchor_6_poles.json')
MINIMAL_PROJECT_FILE = os.path.join(test_dir, 'testdata', 'unittest_dhm_anchor_anchor_0_poles.json')

SEILAPLAN.DEBUG = True
