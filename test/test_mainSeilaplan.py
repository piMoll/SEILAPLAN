from qgis.testing import unittest
import numpy as np
from qgis.core import QgsTask
from qgis.PyQt.QtCore import pyqtSignal

from . import BASIC_PROJECT_FILE
from SEILAPLAN.tools.configHandler import ConfigHandler
from SEILAPLAN.tool_.mainSeilaplan import main as main_
from SEILAPLAN.core.mainSeilaplan import main as main


class ProcessingTask(QgsTask):
    """ Dummy Class to handle the progress information events from the
    algorithm """
    # Signals
    sig_jobEnded = pyqtSignal(bool)
    sig_jobError = pyqtSignal(str)
    sig_value = pyqtSignal(float)
    sig_range = pyqtSignal(list)
    sig_text = pyqtSignal(str)
    sig_result = pyqtSignal(list)
    
    def __init__(self, confHandler, description="Dummy"):
        super().__init__(description, QgsTask.CanCancel)
        self.state = False
        self.exception = None
        self.confHandler = confHandler
        self.projInfo = confHandler.project
        self.resultStatus = None
        self.result = None
    
    def isCanceled(self):
        return
    
    def emit(*args):
        return
    
    def cancel(self):
        super().cancel()


class TestMainResults(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        
        # Old calc
        ##
        cls.conf_ = ConfigHandler()
        cls.conf_.loadSettings(BASIC_PROJECT_FILE)
        cls.conf_.prepareForCalculation()
        proj_ = cls.conf_.project
        param_ = cls.conf_.params.getSimpleParameterDict()

        cls.projInfo_ = {
            'Anfangspunkt': proj_.getPoint('A')[0],
            'Endpunkt': proj_.getPoint('E')[0],
            'Projektname': proj_.getProjectName() + '_old',
            'Hoehenmodell': {
                'path': proj_.getHeightSourceAsStr()
            }
        }
        cls.inputData_ = {}
        for key, val in param_.items():
            cls.inputData_[key] = [val]
        cls.inputData_['HM_fix_d'] = proj_.fixedPoles['HM_fix_d']
        cls.inputData_['HM_fix_h'] = proj_.fixedPoles['HM_fix_h']
        cls.inputData_['noStue'] = proj_.noPoleSection
        
        # New calc
        ##
        cls.conf = ConfigHandler()
        cls.conf.loadSettings(BASIC_PROJECT_FILE)
        cls.conf.prepareForCalculation()
    
        # import processing
        # from processing.core.Processing import Processing
        # Processing.initialize()

    @classmethod
    def tearDownClass(cls):
        # if cls.qgs:
        #     cls.qgs.exitQgis()
        pass
    
    def test_inputParameter(self):
        params_ = self.conf_.params.getSimpleParameterDict()
        params = self.conf.params.getSimpleParameterDict()
        
        self.assertDictEqual(params_, params)

    @unittest.skip("deprecated, needs to be rewritten")
    def test_results(self):
        # Old calc
        # Dummy conf
        conf_ = ConfigHandler()
        conf_.loadSettings(BASIC_PROJECT_FILE)
        conf_.prepareForCalculation()
        rslt_ = main_(ProcessingTask(conf_), self.inputData_, self.projInfo_)
        result_, resultStatus_ = rslt_
        [t_start_, disp_data_, seilDaten_, profile_, HM_, IS_, kraft_,
         optSTA_, optiLen_] = result_

        # New calc
        poles = self.conf.project.poles
        profile = self.conf.project.profile
        rslt = main(ProcessingTask(self.conf), self.conf.project)
        resultStatus, result = rslt
        [t_start, cableline, kraft, optSTA, optiLen] = result

        # Poles
        self.assertEqual(len(HM_['h']), len(poles.poles)-2)
        for i in range(len(HM_['h'])):
            # Check pole height
            self.assertEqual(HM_['h'][i], poles.poles[i + 1]['h'])
            # Check pole distance
            self.assertEqual(HM_['idx'][i], poles.poles[i + 1]['d'])
            # Check pole z value
            self.assertAlmostEqual(HM_['z'][i], poles.poles[i + 1]['ztop'], 3)

        # Possible pole positions
        self.assertTrue(np.allclose(profile_['di_s'], profile.di_s, atol=0.001))
        self.assertTrue(np.allclose(profile_['zi_s'], profile.zi_s, atol=0.001))

        # Cable line
        self.assertTrue(np.allclose(seilDaten_['x'], profile.xi, atol=0.001))
        # self.assertTrue(np.allclose(seilDaten_['y'], profile.yi, atol=0.001))
        self.assertTrue(np.allclose(seilDaten_['z_Leer'], cableline['empty'], atol=0.001))
        self.assertTrue(np.allclose(seilDaten_['z_Zweifel'], cableline['load'], atol=0.001))
        self.assertTrue(np.allclose(seilDaten_['l_coord'], cableline['xaxis'], atol=0.001))

        # Optimization parameters
        # self.assertDictEqual(kraft_, kraft)
        self.assertTrue(np.allclose(optSTA_, optSTA, atol=0.001))
        self.assertTrue(np.allclose(optiLen_, optiLen))


if __name__ == '__main__':
    unittest.main()
