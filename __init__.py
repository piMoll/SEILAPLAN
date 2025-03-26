# -*- coding: utf-8 -*-
"""
/***************************************************************************
 SeilaplanPlugin
                                 A QGIS plugin
 Seilkran-Layoutplaner
                             -------------------
        begin                : 2015-03-05
        copyright            : (C) 2015 by ETH Zürich
        email                : bontle@ethz.ch
        git sha              : $Format:%H$
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
 This script initializes the plugin, making it known to QGIS.
"""

__version__ = '3.6.4'

DEBUG = False


def classFactory(iface):
    """Load SeilaplanPlugin class from file SeilaplanPlugin.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    
    if DEBUG:
        from SEILAPLAN.scripts.prepare_ui_files import remove_resource_location
        remove_resource_location()
        
        # To allow remote debugging with PyCharm, add pydevd to the path
        import sys
        sys.path.append('/snap/pycharm-professional/current/debug-eggs/pydevd-pycharm.egg')
        try:
            import pydevd_pycharm
            pydevd_pycharm.settrace('localhost', port=53100,
                                    stdoutToServer=True, stderrToServer=True)
        except ConnectionRefusedError:
            pass
        except ImportError:
            pass
    
    from .seilaplanPlugin import SeilaplanPlugin
    return SeilaplanPlugin(iface)
