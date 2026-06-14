from qgis._core import Qgis, QgsMessageLog

from SEILAPLAN import DEBUG


def log(msg, level=Qgis.MessageLevel.Info, debugMsg=False):
    if debugMsg:
        if not DEBUG:
            return
        msg = f"DEBUG {msg}"
    QgsMessageLog.logMessage(str(msg), "SEILAPLAN", level)
