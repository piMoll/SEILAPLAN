import unittest
import numpy as np
import sys

# from qgis.core import QgsApplication, QgsProcessingFeedback
from tool.geoExtract import generateDhm, interpolateProfilePointsGRASS # interpolateProfilePointsScipy, \


from qgis.core import QgsApplication

class TestCalcProfile(unittest.TestCase):
    
    
    @classmethod
    def setUpClass(cls):
        
        if 'linux' in sys.platform:
            QgsApplication.setPrefixPath('/usr', True)
        elif 'win' in sys.platform:
            pass
        
        cls.qgs = QgsApplication([], False)
        cls.qgs.initQgis()
    
        import processing
        from processing.core.Processing import Processing
        Processing.initialize()
        
        rasterdata = {
            'path': '/home/pi/Projects/seilaplan/geodata/dhm_foersterschule_mels.txt',
            'spatialRef': 'EPSG:21781'
        }

        # Small /home/pi/.local/share/QGIS/QGIS3/profiles/default/python/pluginstest line
        inputPoints = [746425, 212938, 745954, 212970]
        [Xa, Ya, Xe, Ye] = inputPoints

        subraster = generateDhm(rasterdata, inputPoints)
        
        cls.dhm = subraster['subraster']
        [xMin, xMax, yMin, yMax] = subraster['extent']
        cellsize = subraster['cellsize']
        [cls.Xa, cls.Ya, cls.Xe, cls.Ye] = inputPoints


        # Koordinatenarrays des DHMs
        cls.coordX = np.arange(xMin, xMax, cellsize)
        cls.coordY = np.arange(yMax - cellsize, yMin - cellsize, -cellsize)

        xDist = Xe - Xa
        yDist = Ye - Ya
        ganzdist = (xDist ** 2 + yDist ** 2) ** 0.5
        zwischendist = 1
        anzTeilstuecke = ganzdist / zwischendist
        zwischendistX = xDist / anzTeilstuecke
        zwischendistY = yDist / anzTeilstuecke
        
        cls.xi = np.arange(Xa, Xe, zwischendistX)
        cls.yi = np.arange(Ya, Ye, zwischendistY)
        
        
    @classmethod
    def tearDownClass(cls):
        if cls.qgs:
            cls.qgs.exitQgis()
    
    
    # def test_interpolate_points_scipy(self):
    #     """ Tests the inerpolation and point extraction along a short line."""
    #
    #     spline, zi = interpolateProfilePointsScipy(self.coordX, self.coordY,
    #                                                self.dhm, self.xi, self.yi)
    #
    #     self.assertEqual(round(zi[0], 3), round(10960.52295, 3))
    #     self.assertEqual(round(zi[100], 3), round(11204.43060, 3))
    #     self.assertEqual(round(zi[200], 3), round(11491.60786, 3))
    #     self.assertEqual(round(zi[300], 3), round(11783.44036, 3))
    #     self.assertEqual(round(zi[400], 3), round(11987.95942, 3))
    #     self.assertEqual(round(zi[-1], 3), round(12213.99030, 3))
    #     self.assertEqual(round(zi[-2], 3), round(12208.83662, 3))

    def test_interpolate_points_grass(self):
        """ Tests the interpolation and point extraction along a short line."""
        
        # alg = QgsApplication.processingRegistry().createAlgorithmById(
        #     'grass7:v.sample')
        # canExecute, errorMessage = alg.canExecute()
        #
        # if not canExecute:
        #     raise ImportError('Grass7 nicht')
            
        spline, zi = interpolateProfilePointsGRASS(self.coordX, self.coordY,
                                               self.dhm, self.xi, self.yi)

            
        # for val_z in zi[0::10]:
        #     self.assertEqual(round(val_z, 3), round(10960.52295, 3))

        self.assertEqual(round(zi[0], 3), round(10960.52295, 3))
        self.assertEqual(round(zi[100], 3), round(11204.43060, 3))
        self.assertEqual(round(zi[200], 3), round(11491.60786, 3))
        self.assertEqual(round(zi[300], 3), round(11783.44036, 3))
        self.assertEqual(round(zi[400], 3), round(11987.95942, 3))
        self.assertEqual(round(zi[-1], 3), round(12213.99030, 3))
        self.assertEqual(round(zi[-2], 3), round(12208.83662, 3))


if '__name__' == '__main__':
    unittest.main()