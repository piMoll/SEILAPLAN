"""
/***************************************************************************
 SeilaplanPlugin
                                 A QGIS plugin
 Seilkran-Layoutplaner
                              -------------------
        begin                : 2013
        copyright            : (C) 2023 by ETH Zürich
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
import os
from math import degrees, radians
from qgis.core import (QgsGeometry, QgsPrintLayout, QgsLayoutItemMap, QgsPointXY,
                       QgsLayoutExporter, QgsLayoutSize, QgsProject, QgsRectangle)


def extractMapBackground(savePath, xlim, ylim, startPoint, azimut):
    xMin, xMax = xlim
    yMin, yMax = ylim
    eCoord, nCoord = startPoint
    # Calculate necessary rotation of viewport from horizontal (east-west)
    #  to correct orientation of the cable line
    rotation = azimut - radians(90)
    rotation = rotation + radians(180) if rotation < 0 else rotation
    
    # Dimension of viewport
    width = xMax - xMin
    height = yMax - yMin
    
    # First we create the viewport that contains the start point and is
    #  orientated perfectly east-west
    lowerLeft = QgsPointXY(eCoord + xMin, nCoord + yMin)
    upperRight = QgsPointXY(eCoord + xMin + width, nCoord + yMax)
    viewportHori = QgsRectangle(lowerLeft, upperRight)
    # When rotating a geometry, we need a QgsGeometry instead of a rectangle
    viewportPolygon = QgsGeometry.fromRect(viewportHori)
    viewportPolygon.rotate(degrees(rotation), QgsPointXY(*startPoint))
    # Extract the center of this rotated geometry by calculating the center
    #  of the diagonal
    polyPoints = viewportPolygon.asPolygon()[0]
    corner1 = QgsPointXY(polyPoints[0])
    corner2 = QgsPointXY(polyPoints[2])
    eCenter = corner1.x() + (corner2.x() - corner1.x()) / 2
    nCenter = corner1.y() + (corner2.y() - corner1.y()) / 2
    
    # Extract new lower left and upper right and go back from polygon to rectangle
    # TODO: Remove this part
    polyPoints = viewportPolygon.asPolygon()[0]
    lowerLeftR = QgsPointXY(polyPoints[0])
    upperRightR = QgsPointXY(polyPoints[2])
    rectangleR = QgsRectangle(lowerLeftR, upperRightR)
    # Now we can extract the center of the rotated map extent
    center = rectangleR.center()
    eCenterTest = center.x()
    nCenterTest = center.y()
    
    if round(eCenter, 2) != round(eCenterTest, 2):
        print('Center not identical')
    if round(nCenter, 2) != round(nCenterTest, 2):
        print('Center not identical')
    # Create the final viewport as a rectangle with center in the middle of
    #  the bird view image and with the necessary image dimensions.
    #  Placing the viewport in the center is necessary, because in the subsequent
    #  map rotation, the rotation is applied to the center of the map extract / viewport.
    viewport = QgsRectangle.fromCenterAndSize(QgsPointXY(eCenter, nCenter), width, height)

    # Create the QGIS print layout
    project = QgsProject.instance()
    layout = QgsPrintLayout(project)
    layout.initializeDefaults()
    # # If we want to see the layout, we can give it a name and add it to the manager
    # layout.setName("Seilaplan BirdView Layout")
    # project.layoutManager().addLayout(layout)
    
    # Create a map item
    mapExtract = QgsLayoutItemMap(layout)
    # Item needs a fixed size that is the same as the bird view plot
    ratio = width / 290
    mapExtract.setFixedSize(QgsLayoutSize(width / ratio, height / ratio))
    mapExtract.zoomToExtent(viewport)
    # Rotate the map so the cable line becomes horizontal
    mapRotation = radians(90) - azimut
    mapExtract.setMapRotation(degrees(mapRotation))
    # Add the map to the layout
    layout.addLayoutItem(mapExtract)
    
    # Export the layout to an image file
    exporter = QgsLayoutExporter(layout)
    imgOpt = exporter.ImageExportSettings()
    imgOpt.cropToContents = True
    imgOpt.dpi = 300
    imgOpt.exportMeta = False
    
    saveFile = os.path.join(savePath, 'temp_birdview.png')
    exporter.exportToImage(saveFile, imgOpt)
    # Cleanup
    del layout
    return saveFile

