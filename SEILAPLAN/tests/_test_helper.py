from qgis.PyQt.QtCore import pyqtSignal
from qgis.core import QgsTask
from tools.configHandler import ConfigHandler

from SEILAPLAN.core.cablelineFinal import preciseCable
from SEILAPLAN.tools.configHandler_params import ParameterConfHandler
from SEILAPLAN.tools.configHandler_project import ProjectConfHandler

from . import BASIC_PROJECT_FILE


def calculate_cable_line(conf: ConfigHandler, project_file=BASIC_PROJECT_FILE):
    success = conf.loadSettings(project_file)
    if not success:
        raise Exception("Not able to load project file")
    conf.prepareForCalculation()
    result, resultQuality = conf.prepareResultWithoutOptimization()
    project: ProjectConfHandler = conf.project
    params: ParameterConfHandler = conf.params
    profile = project.profile
    poles = project.poles
    simpleParams = params.getSimpleParameterDict()
    cableline, force, seil_possible = preciseCable(
        simpleParams, poles, result["optSTA"]
    )
    groundClear = profile.updateProfileAnalysis(cableline)
    cableline = {**cableline, **groundClear}
    result["cableline"] = cableline
    result["force"] = force
    return result, params, poles, profile, resultQuality


class MockTask(QgsTask):
    """Dummy Class to handle the progress information events from the algorithm"""

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
        self.status = []

    def isCanceled(self):
        return

    def emit(*args):
        return

    def cancel(self):
        super().cancel()
