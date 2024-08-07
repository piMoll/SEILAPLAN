from . import BASIC_PROJECT_FILE
from SEILAPLAN.core.cablelineFinal import preciseCable
from SEILAPLAN.tools.configHandler import ConfigHandler
from SEILAPLAN.tools.configHandler_project import ProjectConfHandler
from SEILAPLAN.tools.configHandler_params import ParameterConfHandler



def calculate_cable_line(conf, project_file=BASIC_PROJECT_FILE):
    conf.loadSettings(project_file)
    conf.prepareForCalculation()
    result, resultQuality = conf.prepareResultWithoutOptimization()
    project: ProjectConfHandler = conf.project
    params: ParameterConfHandler = conf.params
    profile = project.profile
    poles = project.poles
    simpleParams = params.getSimpleParameterDict()
    cableline, force, seil_possible = preciseCable(simpleParams, poles, result['optSTA'])
    groundClear = profile.updateProfileAnalysis(cableline)
    cableline = {**cableline, **groundClear}
    result['cableline'] = cableline
    result['force'] = force
    return result, params, poles, profile, resultQuality
