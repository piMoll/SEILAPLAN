"""
/***************************************************************************
 SeilaplanPlugin
                                 A QGIS plugin
 Seilkran-Layoutplaner
                              -------------------
        begin                : 2013
        copyright            : (C) 2015 by ETH Zürich
        email                : seilaplanplugin@gmail.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
import traceback

from qgis.PyQt.QtCore import QCoreApplication
from qgis.PyQt.QtWidgets import QMessageBox


class AbstractConfHandler(object):
    
    def __init__(self):
        self.dialog = None
    
    def setDialog(self, dialog):
        self.dialog = dialog
    
    def onError(self, message=None, title=''):
        if not title:
            title = self.tr('Fehler', 'AbstractConfHandler')
        if not message:
            message = traceback.format_exc()
        QMessageBox.information(self.dialog, title, message,
                                QMessageBox.StandardButton.Ok)

    def tr(self, message, context=None, **kwargs):
        """Get the translation for a string using Qt translation API.
        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString
        
        :param context: Context to find the translation string.
        :type context: str, QString

        :returns: Translated version of message.
        :rtype: QString

        Parameters
        ----------
        **kwargs
        """
        if not context:
            context = type(self).__name__
        return QCoreApplication.translate(context, message)
