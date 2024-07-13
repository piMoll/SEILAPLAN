from . import BASIC_PROJECT_FILE, TMP_FILE_PREFIX
from SEILAPLAN.core.cablelineFinal import preciseCable
from SEILAPLAN.tools.configHandler import ConfigHandler
from SEILAPLAN.tools.configHandler_project import ProjectConfHandler
from SEILAPLAN.tools.configHandler_params import ParameterConfHandler



def calculate_cable_line(conf, project_file=BASIC_PROJECT_FILE):
    conf.loadSettings(project_file)
    conf.prepareForCalculation()
    result, status = conf.prepareResultWithoutOptimization()
    project: ProjectConfHandler = conf.project
    params: ParameterConfHandler = conf.params
    profile = project.profile
    poles = project.poles
    simpleParams = params.getSimpleParameterDict()
    cableline, force, seil_possible = preciseCable(simpleParams, poles, result['optSTA'])
    result['cableline'] = cableline
    result['force'] = force
    profile.updateProfileAnalysis(cableline)
    result['maxDistToGround'] = cableline['maxDistToGround']
    return result, params, poles, profile, status
