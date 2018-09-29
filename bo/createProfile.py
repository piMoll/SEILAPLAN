# -*- coding: utf-8 -*-

try:
    from shapely.wkb import loads
    from shapely.wkb import dumps
    from shapely.geometry import Point
    import shapely.geos
except ImportError:
    pass
except:
    pass
from .settings import enumVertexType
#from bo.line import Line
from .profile import Profile
from .segment import Segment
from .vertex import Vertex
#from bo.zVal import ZVal
from qgis.core import QgsMessageLog, QgsGeometry
from math import sqrt


class CreateProfile:
    def __init__(self, interface, line, raster):
        self.iface = interface
        self.line = line
        self.raster = raster

    def create(self):
        profiles = []
        profiles.append(self.processFeature(None, 1, 1, self.line))
        return profiles

    def processFeature(self, fields, profileId, layerId, feat):
        geom = feat.geometry()
        # if QGis.QGIS_VERSION_INT < 10900:
        #     segments = self.processVertices(fields, feat.attributeMap(), profileId, geom, layerId, feat.id())
        # else:
        segments = self.processVertices(fields, feat.attributes(), profileId, geom, layerId, feat.id())
        return Profile(profileId, segments)

    def processVertices(self, fields, attribMap, profileId, qgGeom, layerId, featId):
        step = 1
        segmentCnter = 1
        segments = []
        segmentvertices = []
        distSegment = 0
        distTotal = 0
        qgPntOld = None
        vtxType = None
        vtxId = 1

        qgLineVertices = qgGeom.asPolyline()
        shplyGeom = loads(qgGeom.asWkb())
        shplyVertices = []
        #for shplyV in shplyGeom.coords:
        for idxV in range(1, len(shplyGeom.coords) - 1):
            #shplyVertices.append(Point(shplyV[0], shplyV[1]))
            shplyVertices.append(Point(shplyGeom.coords[idxV][0], shplyGeom.coords[idxV][1]))

        #erster, echter Punkt der Geometrie
        qgPntOld = qgLineVertices[0]
        vtxType = enumVertexType.node
        newVtx = Vertex(fields, attribMap, vtxType, qgLineVertices[0].x(),
                        qgLineVertices[0].y(), profileId, layerId, featId,
                        segmentCnter, vtxId, distTotal, distSegment,
                        self.__getValsAtPoint(qgLineVertices[0]))
        segmentvertices.append(newVtx)

        while distTotal < shplyGeom.length:

            distSegment += step
            distTotal += step

            #überprüfen, ob echter Vertex zwischen den
            # zu berechnenden Ṕrofilpunkten liegt
            #nur falls diese auch ausgegeben werden sollen
            if True:
                if distTotal > 0:
                    prevDist = distTotal - step
                    for v in shplyVertices:
                        vDist = shplyGeom.project(v)
                        if vDist > prevDist and vDist < distTotal:
                            qgPnt = self.__qgPntFromShplyPnt(v)
                            distQgVertices = sqrt(qgPnt.sqrDist(qgPntOld))
                            vtxType = enumVertexType.vertex
                            vtxId += 1
                            newVtx = Vertex(fields, attribMap, vtxType, v.x,
                                            v.y, profileId,layerId, featId,
                                            segmentCnter, vtxId, vDist,
                                            distQgVertices,
                                            self.__getValsAtPoint(qgPnt))
                            segmentvertices.append(newVtx)
                            segments.append(Segment(segmentCnter, segmentvertices))
                            #neues Segment beginnen
                            qgPntOld = self.__qgPntFromShplyPnt(v)
                            segmentvertices = []
                            distSegment -= distQgVertices
                            segmentCnter += 1

            #Profilpunkte berechnen
            #nur wenn noch unter Featurelaenge
            if distTotal < shplyGeom.length:
                shplyPnt = shplyGeom.interpolate(distTotal, False)
                vtxType = enumVertexType.point
                vtxId += 1
                newVtx = Vertex(fields, attribMap, vtxType, shplyPnt.x,
                                shplyPnt.y, profileId, layerId, featId,
                                segmentCnter, vtxId, distTotal, distSegment,
                                self.__getValsAtPoint(self.__qgPntFromShplyPnt(shplyPnt)))
                segmentvertices.append(newVtx)

        #letzter, echter Punkt der Geometrie
        qgLastPnt = qgLineVertices[len(qgLineVertices)-1]
        #keine echten Knoten, nur berechnete -> letzter Pkt entspricht kompletter Laenge der Geometrie

        vtxType = enumVertexType.node
        vtxId += 1
        newVtx = Vertex(fields, attribMap, vtxType, qgLastPnt.x(),
                        qgLastPnt.y(), profileId, layerId, featId,
                        segmentCnter, vtxId, shplyGeom.length, distSegment,
                        self.__getValsAtPoint(qgLastPnt))
        segmentvertices.append(newVtx)
        segments.append(Segment(segmentCnter, segmentvertices))

        return segments

    def __qgPntFromShplyPnt(self, shapelyPnt):
        wkbPnt = dumps(shapelyPnt)
        qgGeom = QgsGeometry()
        qgGeom.fromWkb(wkbPnt)
        return qgGeom.asPoint()

    def __getValsAtPoint(self, pnt):
        vals = []
        raster = self.raster
        #TODO!!!! QGIS BUG: QGIS 2.0.1: raster.noDataValue() = > AttributeError: 'QgsRasterLayer' object has no attribute 'noDataValue'
        # if QGis.QGIS_VERSION_INT < 10900:
        #     noDataVal, validNoData = raster.noDataValue()
        #     if validNoData:
        #         rasterVal = noDataVal
        #     else:
        #         #rasterVal = float('nan')
        #         rasterVal = -9999
        # else:
        #     rasterVal = -9999

        rasterVal = -9999

        # if QGis.QGIS_VERSION_INT < 10900:
        #     result, identifyDic = raster.identify(pnt)
        #     if result:
        #         for bandName, pixelValue in identifyDic.iteritems():
        #             #QgsMessageLog.logMessage('bandName:' + str(bandName), 'VoGis')
        #             if str(bandName) == raster.bandName(1):
        #                 try:
        #                     #QgsMessageLog.logMessage('pixelValue:' + str(pixelValue), 'VoGis')
        #                     rasterVal = float(pixelValue)
        #                 except ValueError:
        #                     #float('nan') #0
        #                     rasterVal = -9999
        #                     pass
        # else:
        identifyResult = raster.dataProvider().identify(pnt, 1)
        for bndNr, pixVal in identifyResult.results().items():
            if 1 == bndNr:
                try:
                    rasterVal = float(pixVal)
                #except ValueError:
                except:
                    QgsMessageLog.logMessage('pixVal Exception: ' + str(pixVal), 'VoGis')
                    rasterVal = -9999
                    pass
        vals.append(rasterVal)
        return vals
