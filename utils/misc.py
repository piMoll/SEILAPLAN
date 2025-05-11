from SEILAPLAN import DEBUG, __version__ as current_version
from qgis.core import QgsMessageLog, QgsSettings

QGIS_SETTINGS_GROUP_PLUGINS = 'app/plugin_repositories'
SEILAPLAN_PLUGIN_REPO = 'https://raw.githubusercontent.com/piMoll/SEILAPLAN/master/plugin.xml'


def versionAsInteger(version=current_version):
    """
    Converts a version string in the format 'x.y.z' into an integer for
    easier comparison.
    """
    if len(version.split('.')) != 3:
        raise ValueError
    return int(''.join([f'{int(n):02d}' for n in version.split('.')]))


def removeOldSeilaplanPluginRepo():
    """
    Removes the SEILAPLAN plugin repository from the QGIS plugin settings
     after version 3.7.0 of SEILAPLAN. This is due to SEILAPLAN moving from its
     own GitHub-based repository to the official QGIS plugin repository.
    """
    if versionAsInteger() <= versionAsInteger('3.7.0'):
        return
    
    settings = QgsSettings()
    settings.beginGroup(QGIS_SETTINGS_GROUP_PLUGINS)
    for key in settings.childGroups():
        url = settings.value(key + "/url", "", type=str)
        if url == SEILAPLAN_PLUGIN_REPO:
            if DEBUG:
                msg = f'Found SEILAPLAN plugin repository at {key}!'
            else:
                settings.remove(key)
                msg = f'Removing old SEILAPLAN plugin repository at {url}'
            QgsMessageLog.logMessage(msg, 'SEILAPLAN', QgsMessageLog.INFO)
            break
