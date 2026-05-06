import os
from os.path import isfile
import unittest

import numpy as np
from qgis.core import QgsCoordinateReferenceSystem

from tools.outputGeo import saveLineGeometry, savePointGeometry

from . import TMP_DIR


class TestOutputGeo(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.spatialRef = QgsCoordinateReferenceSystem.fromEpsgId(2056)
        cls.poles = [
            {
                "BHD": 65,
                "abspann": None,
                "active": True,
                "angle": 0.0,
                "angriff": 17.14917174638964,
                "bundstelle": np.nan,
                "category": None,
                "coordx": 2601683.713114841,
                "coordy": 1199513.0586559088,
                "d": 0.0,
                "dtop": 0.0,
                "h": 0.0,
                "manually": False,
                "maxForce": [134.0, "Seilzugkraft"],
                "name": "Verankerung",
                "nr": "",
                "poleType": "pole_anchor",
                "position": None,
                "z": 556.179869791637,
                "ztop": 556.179869791637,
            },
            {
                "BHD": 65,
                "abspann": None,
                "active": True,
                "angle": 0.0,
                "angriff": 14.824818787223144,
                "bundstelle": np.nan,
                "category": None,
                "coordx": 2601595.9645735268,
                "coordy": 1199651.6089842997,
                "d": 164.0,
                "dtop": 164.0,
                "h": 0.0,
                "manually": False,
                "maxForce": [133.14392, "Seilzugkraft"],
                "name": "Verankerung",
                "nr": "",
                "poleType": "pole_anchor",
                "position": None,
                "z": 519.2054079372981,
                "ztop": 519.2054079372981,
            },
        ]
        cls.terrain = [
            [
                [2.60170512e06, 1.19947927e06, 5.58708864e02],
                [2.60170458e06, 1.19948011e06, 5.58704473e02],
                [2.60170405e06, 1.19948096e06, 5.58725810e02],
                [2.60170351e06, 1.19948180e06, 5.58637975e02],
                [2.60170297e06, 1.19948265e06, 5.58470438e02],
                [2.60170244e06, 1.19948349e06, 5.58245274e02],
                [2.60170190e06, 1.19948433e06, 5.58067420e02],
                [2.60170137e06, 1.19948518e06, 5.57933823e02],
            ]
        ]

    def test_geopackage_export_for_points(self):
        path = os.path.join(TMP_DIR, "test_outputGeo.gpkg")
        if isfile(path):
            os.remove(path)
        savePointGeometry(path, self.poles, self.spatialRef, "GPKG", "test_points")

    def test_geopackage_export_for_lines(self):
        path = os.path.join(TMP_DIR, "test_outputGeo.gpkg")
        saveLineGeometry(path, self.terrain, self.spatialRef, "GPKG", "test_lines")

    def test_shape_export_for_points(self):
        path = os.path.join(TMP_DIR, "test_points.shp")
        savePointGeometry(
            path, self.poles, self.spatialRef, "ESRI Shapefile", "test_points"
        )

    def test_shape_export_for_lines(self):
        path = os.path.join(TMP_DIR, "test_lines.shp")
        saveLineGeometry(
            path, self.terrain, self.spatialRef, "ESRI Shapefile", "test_lines"
        )

    def test_kml_export_for_points(self):
        path = os.path.join(TMP_DIR, "test_points.kml")
        savePointGeometry(path, self.poles, self.spatialRef, "KML", "test_points")

    def test_kml_export_for_lines(self):
        path = os.path.join(TMP_DIR, "test_lines.kml")
        saveLineGeometry(path, self.terrain, self.spatialRef, "KML", "test_lines")

    def test_dxf_export_for_points(self):
        path = os.path.join(TMP_DIR, "test_points.dxf")
        savePointGeometry(path, self.poles, self.spatialRef, "KML", "test_points")

    def test_dxf_export_for_lines(self):
        path = os.path.join(TMP_DIR, "test_lines.dxf")
        saveLineGeometry(path, self.terrain, self.spatialRef, "KML", "test_lines")
