import os
import unittest

from SEILAPLAN.tools.raster import Raster
from qgis.core import QgsCoordinateReferenceSystem, QgsRasterLayer
from test import TESTDATA_DIR


class TestRaster(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        cls.spatialRef = QgsCoordinateReferenceSystem.fromEpsgId(2056)
        cls.rasterPath = os.path.join(TESTDATA_DIR, 'dhm.tiff')
        cls.raster = Raster(path=cls.rasterPath)
    
    @classmethod
    def tearDownClass(cls):
        pass
    
    def test_collect_raster_properties_from_path(self):
        self.assertEqual(self.raster.path, self.rasterPath)
        self.assertEqual(self.raster.cols, 2354)
        self.assertEqual(self.raster.rows, 1876)
        self.assertEqual(self.raster.cellsize, 0.5)
        self.assertEqual(self.raster.extent,
                         [2744155.5, 1190227.0, 2745332.5, 1189289.0])
        self.assertEqual(self.raster.spatialRef, self.spatialRef)
        self.assertTrue(self.raster.valid)
    
    def test_collect_raster_properties_from_qgis_layer(self):
        layer = QgsRasterLayer(self.rasterPath)
        raster = Raster(layer=layer)
        
        self.assertEqual(raster.layer, layer)
        self.assertEqual(raster.path, self.rasterPath)
        self.assertEqual(raster.cols, 2354)
        self.assertEqual(raster.rows, 1876)
        self.assertEqual(raster.cellsize, 0.5)
        self.assertEqual(raster.extent,
                         [2744155.5, 1190227.0, 2745332.5, 1189289.0])
        self.assertEqual(raster.spatialRef, self.spatialRef)
        self.assertTrue(raster.valid)
    
    def test_collect_raster_properties_from_xyz_file_path(self):
        raster = Raster(path=os.path.join(TESTDATA_DIR, 'dhm_UTM_32N.xyz'))
        # xyz file should be transformed to a tif first, so that we end up
        #  with a raster origin in the upper-left corner instead of lower-left.
        
        self.assertTrue('/vsimem/' in raster.path)
        self.assertEqual(raster.cols, 1001)
        self.assertEqual(raster.rows, 551)
        self.assertEqual(raster.cellsize, 1.0)
        self.assertEqual(raster.extent,
                         [454999.5, 5299000.5, 456000.5, 5298449.5])
        self.assertTrue(raster.valid)


if __name__ == '__main__':
    unittest.main()
