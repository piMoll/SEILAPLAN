from qgis.core import ( QgsGeometry, QgsMapSettings, QgsPrintLayout, QgsMapSettings,
                        QgsMapRendererParallelJob, QgsLayoutItemLabel, QgsLayoutItemLegend,
                        QgsLayoutItemMap, QgsPointXY,
                        QgsLayoutExporter, QgsLayoutItem, QgsLayoutSize,
                        QgsUnitTypes, QgsProject,QgsLayoutItemPage,
                        QgsRectangle)
from math import sin, cos, degrees, radians, pi
import numpy as np
import matplotlib.pyplot as plt


def calculateMapExtent(xlim, ylim, startPoint, endPoint, azimut):
    xMin, xMax = xlim
    yMin, yMax = ylim
    eCoord, nCoord = startPoint
    eEndCoord, nEndCoord = endPoint
    # Rotation from an east orientated line
    rotation = azimut - radians(90)
    rotation = rotation + radians(180) if rotation < 0 else rotation
    
    imgWidthInMapUnits = xMax - xMin
    imgHeightInMapUnits = yMax - yMin
    
    # eCenter = eCoord + xMin + (imgWidthInMapUnits / 2)
    # nCenter = nCoord
    # eCenter = eCoord + ((xMin + 0.5 * imgWidthInMapUnits) * cos(rotation))
    # nCenter = nCoord + ((0.5 * imgWidthInMapUnits) * sin(rotation))
    
    # # Clockwise rotation
    # rot = np.array([[np.cos(rotation), np.sin(rotation)],
    #                 [-np.sin(rotation), np.cos(rotation)]])
    # 
    # vector2llCorner = np.array([xMin, yMin])
    # vector2ulCorner = np.array([xMin, yMax])
    # 
    # vector2llCornerR = np.dot(rot, vector2llCorner)
    # vector2ulCornerR = np.dot(rot, vector2ulCorner)


    # eCoordMin = eCoord - (abs(xMin) * cos(rotation))
    # eCoordMax = eCoordMin + (imgWidthInMapUnits * cos(rotation))
    # nCoordMin = nCoord - (abs(yMin) * sin(rotation))
    # nCoordMax = nCoordMin + (imgHeightInMapUnits * sin(rotation))
    
    # NO ROTATION: xMin
    # rectangle = (xMin: float, yMin: float = 0, xMax: float = 0, yMax: float = 0) 
    
    # First we create a map extent that contains the start point and is
    #  orientated perfectly in east-west direction
    lowerLeft = QgsPointXY(eCoord + xMin, nCoord + yMin)
    upperRight = QgsPointXY(eCoord + xMin + imgWidthInMapUnits, nCoord + yMax)
    rectangle = QgsRectangle(lowerLeft, upperRight)
    polygon = QgsGeometry.fromRect(rectangle)
    # Rotate the rectangle with center in start point
    polygon.rotate(degrees(rotation), QgsPointXY(*startPoint))
    # Extract new lower left and upper right and go back from polygon to rectangle
    polyPoints = polygon.asPolygon()[0]
    lowerLeftR = QgsPointXY(polyPoints[0])
    upperRightR = QgsPointXY(polyPoints[2])
    rectangleR = QgsRectangle(lowerLeftR, upperRightR)
    # Now we can extract the center of the rotated map extent
    center = rectangleR.center()
    eCenter = center.x()
    nCenter = center.y()
    
    # Create a map extent that has the same center but is orientated again in east-west direction
    #  This will be the rectangle that is used to set the extent of the map extract
    #  Because this has its center in the center of the bird view image, it will
    #  rotate perfectly around this center.
    rect = QgsRectangle.fromCenterAndSize(center, imgWidthInMapUnits, imgHeightInMapUnits)


    widthRotExtent = 30 / cos(radians(90) - rotation)
    heightRotExtent = widthRotExtent
    lowerLeftN = QgsPointXY(eCenter - (0.5 * widthRotExtent), nCenter - (0.5 * heightRotExtent))
    upperRightN = QgsPointXY(eCenter + (0.5 * widthRotExtent), nCenter + (0.5 * heightRotExtent))
    
    # lowerLeft = QgsPointXY(eCenter - (0.5 * imgWidthInMapUnits), nCenter + yMin)
    # upperRight = QgsPointXY(eCenter + (0.5 * imgWidthInMapUnits), nCenter + yMax)


    rectangleN = QgsRectangle(lowerLeftN, upperRightN)

    
    
    
    
    
    
    # rectangleCenter = QgsRectangle(
    #     QgsPointXY(eCenter - 30, nCenter - 30),
    #     QgsPointXY(eCenter + 30, nCenter + 30))
    # polyCenter = QgsGeometry.fromRect(rectangleCenter)
    
    # r = QgsRubberBand(canvas, QgsWkbTypes.PolygonGeometry)  # polygon
    # r.setToGeometry(polygon, None)
    
    
    # plt.scatter([xMin, xMax], [yMin, yMax], color='black')
    # plt.scatter(eCoord - vector2llCorner[0], nCoord - vector2llCorner[1], color='lightblue')
    # plt.scatter(eCoord - vector2ulCorner[0], nCoord + vector2ulCorner[1], color='blue')
    # plt.scatter(eCoord, nCoord, color='grey')
    # plt.scatter(eCoord - xMin + imgWidthInMapUnits, nCoord, color='grey')
    # plt.scatter([eCoord, eEndCoord], [nCoord, nEndCoord], color='green')
    # plt.scatter(eCoord - vector2llCornerR[0], nCoord - vector2llCornerR[1], color='orange')
    # plt.scatter(eCoord - vector2ulCornerR[0], nCoord + vector2ulCornerR[1], color='red')
    # plt.show()
    
    

    
    # TODO:  Not necessary. We can move an turn QgsLayoutItemMap instead of canvas!
    # canvas.setCenter(QgsPointXY(eCenterCoord, nCenterCoord))
    # # Map must show horizontal line instead
    # canvas.setRotation(degrees(mapRotation))
    # canvas.refresh()

    project = QgsProject.instance()
    layout = QgsPrintLayout(project)
    layout.initializeDefaults()


    mapExtract = QgsLayoutItemMap(layout)
    # map.setExtent(QgsRectangle(xMin, yMin, xMax, yMax))
    # TODO change in unit types in v 3.30
    ratio = imgWidthInMapUnits / 290
    # mapExtract.attemptResize(QgsLayoutSize(imgWidthInMapUnits / ratio, imgHeightInMapUnits / ratio))
    # mapExtract.setExtent(rectangleR)
    mapExtract.setFixedSize(QgsLayoutSize(imgWidthInMapUnits / ratio, imgHeightInMapUnits / ratio))
    mapExtract.zoomToExtent(rect)
    # TODO: Rotate will not work because it will not rotate AROUND the start point
    # Line has to be horizontal (90°)
    # 1) Difference from azimut to 90°
    mapRotation = radians(90) - azimut
    mapExtract.setMapRotation(degrees(mapRotation))
    
    layout.addLayoutItem(mapExtract)
    
    exporter = QgsLayoutExporter(layout)
    imgOpt = exporter.ImageExportSettings()
    imgOpt.cropToContents = True
    imgOpt.dpi = 300
    imgOpt.exportMeta = False
    path = '/home/pi/Seilaplan/Vogelperspektive/MapOut.png'
    exporter.exportToImage(path, imgOpt)
    return '/home/pi/Seilaplan/Vogelperspektive/MapOut.png'


if __name__ == '__main__':
    xlim = (-100.25, 565.25)
    ylim = (-30.0, 30.0)
    startPoint = (750574.2304142229, 214162.83784612562)
    endPoint = (750931.7729826102, 213864.88570580288)
    azimut = 2.26553460299168
    calculateMapExtent(xlim, ylim, startPoint, endPoint, azimut)
