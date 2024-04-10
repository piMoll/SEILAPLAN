import os
import matplotlib.pyplot as plt
from matplotlib import transforms
from matplotlib.path import Path
import numpy as np
try:
    from qgis.core import QgsMessageLog
except ImportError:
    pass

IMPORT_ERROR = False
try:
    from svgpath2mpl import parse_path
except ImportError:
    IMPORT_ERROR = True

ACCENT_COLOR = (0.39, 0.14, 0.0)

_HOME_PATH = os.path.dirname(os.path.dirname(__file__))
SVG_CENTER = [25, 25]
SVG_PROPS = {
    'default': [ACCENT_COLOR, 0.10, True],
    'fadenkreuz': ['black', 1.0, False],
    'mobiler_seilkran': ['black', 1.33, False],
    'vorziehstuetze_1': ['black', 1.33, True],
    'vorziehstuetze_2': ['black', 1.33, True],
    'dreizackiger_stern': ['black', 1.33, True],
    'vorgeneigte_stuetze': ['black', 1.23, True],
    'endmast_mit_zugseilleitrolle': ['black', 1.33, True],
    'endmast_ohne_zugseilleitrolle': ['black', 1.33, True],
    'endmast': ['black', 1.07, True],
    'normaler_ankerbaum': [ACCENT_COLOR, 0.10, True],
    'mehrbaumanker': ['black', 0.6, False],
    'totmannanker': [ACCENT_COLOR, 0.5, False],
    'verstaerkter_ankerbaum': ['black', 0.6, True],
}
SVG_PATHS = {
    'default': """m 27.657339,25.132973 a 2.5,2.5 0 0 1 -2.5,2.5 2.5,2.5 0 0 1 -2.5,-2.5 2.5,2.5 0 0 1 2.5,-2.5 2.5,2.5 0 0 1 2.5,2.5 z
    """,
    'fadenkreuz': """m 50.1355,25 h -50 m 25,-25 v 50""",
    'mobiler_seilkran': """m 40.769603,8.2000163 a 1,1 0 0 0 -1.000456,0.9999387 1,1 0 0 0 0.168984,0.5550051 l -9.877435,9.9838869 v -2.447913 h -9.849527 v 0.29869 15.11949 h 9.849527 v -2.361096 l 9.746176,10.016442 a 1,1 0 0 0 -0.174149,0.563274 1,1 0 0 0 1.000456,0.99994 1,1 0 0 0 0.999939,-0.99994 1,1 0 0 0 -0.999939,-0.99994 1,1 0 0 0 -0.54002,0.158647 L 30.060696,29.775959 v -3.395141 l 15.946315,3.802351 a 1,1 0 0 0 -0.0011,0.03204 1,1 0 0 0 0.99994,0.99994 1,1 0 0 0 0.999937,-0.99994 1,1 0 0 0 -0.999937,-0.99994 1,1 0 0 0 -0.906404,0.578776 L 30.060696,25.968441 v -1.938383 l 16.037782,-3.82819 a 1,1 0 0 0 0.905888,0.578259 1,1 0 0 0 0.999937,-0.999939 1,1 0 0 0 -0.999937,-0.999939 1,1 0 0 0 -0.999939,0.999939 1,1 0 0 0 0.0016,0.03307 L 30.060696,23.618196 V 20.306771 L 40.222868,10.036597 a 1,1 0 0 0 0.546735,0.163297 1,1 0 0 0 0.99994,-0.999939 1,1 0 0 0 -0.99994,-0.9999387 z M 20.810616,17.890381 h 8.648568 v 2.456181 l -3.775998,3.816821 a 1,1 0 0 0 -0.54777,-0.163298 1,1 0 0 0 -0.999939,0.999939 1,1 0 0 0 0.999939,0.999939 1,1 0 0 0 0.540019,-0.159163 l 3.783749,3.888651 v 2.379699 h -8.648568 z m 8.648568,3.024104 v 2.847372 l -3.417363,0.815454 a 1,1 0 0 0 -0.07493,-0.133325 z m 0,3.259233 v 1.651579 l -3.324862,-0.793234 a 1,1 0 0 0 10e-4,-0.03204 1,1 0 0 0 -5.29e-4,-0.03256 z m -3.417363,1.248502 3.417363,0.814938 v 2.92075 l -3.497461,-3.594611 a 1,1 0 0 0 0.0801,-0.141077 z
    """,
    'vorziehstuetze_1': """M 26.938925,2.1140828 A 1,1 0 0 0 25.938468,3.1140217 1,1 0 0 0 26.661422,4.07417 l -1.706356,21.068481 0.111621,0.0093 -0.111621,0.05323 9.005652,18.93631 a 1,1 0 0 0 -0.398426,0.797885 1,1 0 0 0 0.99994,1.000456 1,1 0 0 0 0.999937,-1.000456 1,1 0 0 0 -0.999937,-0.999939 1,1 0 0 0 -0.240813,0.02997 L 25.359692,25.124564 27.059847,4.1056925 A 1,1 0 0 0 27.938862,3.1140217 1,1 0 0 0 26.938925,2.1140828 Z
    """,
    'vorziehstuetze_2': """M 26.938925,2.1140828 A 1,1 0 0 0 25.938468,3.1140217 1,1 0 0 0 26.661422,4.07417 l -1.706356,21.068481 0.111621,0.0093 -0.111621,0.05323 9.005652,18.93631 a 1,1 0 0 0 -0.398426,0.797885 1,1 0 0 0 0.99994,1.000456 1,1 0 0 0 0.999937,-1.000456 1,1 0 0 0 -0.999937,-0.999939 1,1 0 0 0 -0.240813,0.02997 L 25.63306,25.699206 42.607219,37.276278 a 1,1 0 0 0 -0.07907,0.387572 1,1 0 0 0 0.999938,0.99994 1,1 0 0 0 0.999939,-0.99994 1,1 0 0 0 -0.999939,-0.999937 1,1 0 0 0 -0.696079,0.282667 L 25.366927,25.034131 27.059847,4.1056925 A 1,1 0 0 0 27.938862,3.1140217 1,1 0 0 0 26.938925,2.1140828 Z
    """,
    'dreizackiger_stern': """M 25.135933,2.0432861 A 1,1 0 0 0 24.135994,3.043225 1,1 0 0 0 24.935429,4.0224934 V 25.069271 L 14.458032,43.212866 a 1,1 0 0 0 -0.315743,-0.05168 1,1 0 0 0 -0.999939,1.000456 1,1 0 0 0 0.999939,0.999937 1,1 0 0 0 1.000456,-0.999937 1,1 0 0 0 -0.336414,-0.748276 L 25.13645,25.519372 35.517727,43.385983 a 1,1 0 0 0 -0.334346,0.745691 1,1 0 0 0 0.99994,0.999937 1,1 0 0 0 0.99994,-0.999937 1,1 0 0 0 -0.99994,-0.99994 1,1 0 0 0 -0.319876,0.05323 L 25.335921,25.066687 V 4.0224934 A 1,1 0 0 0 26.135872,3.043225 1,1 0 0 0 25.135933,2.0432861 Z
    """,
    'vorgeneigte_stuetze': """m 34.244938,3.7666951 a 1,1 0 0 0 -0.999939,0.999939 1,1 0 0 0 0.410826,0.8071858 L 24.978837,24.586096 6.6838297,35.656737 a 1,1 0 0 0 -0.7338054,-0.320911 1,1 0 0 0 -0.999939,0.99994 1,1 0 0 0 0.999939,1.000456 1,1 0 0 0 0.999939,-1.000456 1,1 0 0 0 -0.057878,-0.334862 L 24.703918,25.221199 16.595369,44.099633 a 1,1 0 0 0 -0.203088,-0.02016 1,1 0 0 0 -0.999939,0.999939 1,1 0 0 0 0.999939,0.999938 1,1 0 0 0 0.999939,-0.999938 1,1 0 0 0 -0.429431,-0.821655 l 8.237223,-19.172982 14.397053,15.312759 a 1,1 0 0 0 -0.183968,0.577225 1,1 0 0 0 0.99994,0.99994 1,1 0 0 0 0.999937,-0.99994 1,1 0 0 0 -0.999937,-0.999937 1,1 0 0 0 -0.525034,0.14986 L 25.374162,24.686348 34.021178,5.7407349 a 1,1 0 0 0 0.22376,0.025839 1,1 0 0 0 1.000456,-0.999939 1,1 0 0 0 -1.000456,-0.9999398 z
    """,
    'endmast_mit_zugseilleitrolle': """m 50.1355,25 h -50 m 25,-25 v 50
    """,    # TODO
    'endmast_ohne_zugseilleitrolle': """m 50.1355,25 h -50 m 25,-25 v 50
    """,    # TODO
    "endmast": """m 39.202775,7.0977579 a 1,1 0 0 0 -0.99994,0.999939 1,1 0 0 0 0.22221,0.6278687 l -13.442591,16.2667074 0.152962,0.12764 -0.152962,0.128158 13.442073,16.267742 a 1,1 0 0 0 -0.221692,0.627351 1,1 0 0 0 0.99994,1.000455 1,1 0 0 0 0.99994,-1.000455 1,1 0 0 0 -0.99994,-0.99994 1,1 0 0 0 -0.468707,0.117824 L 25.394832,25.119913 38.733552,8.9798135 a 1,1 0 0 0 0.469223,0.1178224 1,1 0 0 0 0.99994,-0.999939 1,1 0 0 0 -0.99994,-0.999939 z
    """,    # TODO: Seitenverkert
    'normaler_ankerbaum': """m 27.657339,25.132973 a 2.5,2.5 0 0 1 -2.5,2.5 2.5,2.5 0 0 1 -2.5,-2.5 2.5,2.5 0 0 1 2.5,-2.5 2.5,2.5 0 0 1 2.5,2.5 z
    """,
    'mehrbaumanker': """m 22.377445,17.049088 a 1,1 0 0 0 -0.999939,1.000456 1,1 0 0 0 0.167949,0.554488 l -6.242513,6.311243 a 0.22406473,0.22406473 0 0 0 -0.121957,0.199471 0.22406473,0.22406473 0 0 0 0.08475,0.1757 l 6.221325,6.398059 a 1,1 0 0 0 -0.173632,0.562756 1,1 0 0 0 0.999938,0.999939 1,1 0 0 0 1.000456,-0.999939 1,1 0 0 0 -1.000456,-0.99994 1,1 0 0 0 -0.538468,0.158131 l -5.710246,-5.87251 7.946285,2.398819 a 1,1 0 0 0 -0.0047,0.09095 1,1 0 0 0 0.999939,1.000455 1,1 0 0 0 0.999939,-1.000455 1,1 0 0 0 -0.999939,-0.999938 1,1 0 0 0 -0.88005,0.526066 L 16.071321,25.120946 24.12716,22.68957 a 1,1 0 0 0 0.879016,0.524516 1,1 0 0 0 0.999939,-0.999939 1,1 0 0 0 -0.999939,-0.999939 1,1 0 0 0 -0.999939,0.999939 1,1 0 0 0 0.0047,0.0925 l -7.933367,2.395202 5.753138,-5.816182 a 1,1 0 0 0 0.546736,0.163814 1,1 0 0 0 0.999939,-0.999939 1,1 0 0 0 -0.999939,-1.000456 z m 2.821017,7.706507 a 0.40604635,0.40604635 0 0 0 -0.406177,0.406176 0.40604635,0.40604635 0 0 0 0.406177,0.40566 0.40604635,0.40604635 0 0 0 0.406176,-0.40566 0.40604635,0.40604635 0 0 0 -0.406176,-0.406176 z
    """,
    'totmannanker': """m 23.136719,16.519531 v 17.201172 h 4 V 16.519531 Z
    """,
    'verstaerkter_ankerbaum': """m 34.166389,19.367293 a 1,1 0 0 0 -0.999937,0.999939 1,1 0 0 0 0.04031,0.279053 l -8.163842,4.296895 0.0925,0.176733 -0.0925,0.176734 8.163842,4.297411 a 1,1 0 0 0 -0.04031,0.27957 1,1 0 0 0 0.999937,1.000455 1,1 0 0 0 0.99994,-1.000455 1,1 0 0 0 -0.99994,-0.999938 1,1 0 0 0 -0.773597,0.367419 l -7.828461,-4.121196 7.82898,-4.119128 a 1,1 0 0 0 0.773078,0.366386 1,1 0 0 0 0.99994,-0.999939 1,1 0 0 0 -0.99994,-0.999939 z
    """,
}
    

class BirdViewSymbol:
    
    ACCENT_COLOR = ACCENT_COLOR
    
    def __init__(self, name, mplPath, scale, color, centerPoint):
        self.name = name
        self.mplPath = mplPath
        self.scale = scale
        self.color = color
        self.centerPoint = centerPoint
    
    def mirror(self, axis='y'):
        if axis == 'y':
            return self.mplPath.transformed(transforms.Affine2D().scale(-1, 1))
        elif axis == 'x':
            return self.mplPath.transformed(transforms.Affine2D().scale(1, -1))
        elif axis == 'xy':
            return self.mplPath.transformed(transforms.Affine2D().scale(-1, 1)).transformed(transforms.Affine2D().scale(1, -1))


class BirdViewSymbolLoader:
    
    def __init__(self):
        self.symbols = {}
    
    def loadSymbolFromArray(self, path=r'config/birdView'):
        """ Loads symbols from matplotlib Path object saved as numpy save files. """
        for symbolName, svgProp in SVG_PROPS.items():
            color = svgProp[0]
            scale = svgProp[1]
            centerPoint = svgProp[2]
            try:
                vertices = np.load(os.path.join(_HOME_PATH, path, f'{symbolName}_vertices.npy'))
                codes = np.load(os.path.join(_HOME_PATH, path, f'{symbolName}_codes.npy'))
            except (OSError, EOFError) as e:
                QgsMessageLog.logMessage('{} {}'.format(self.__class__.__name__, e), 'QgsSettingManager')
                continue
            mplPath = Path(vertices, codes)
            self.symbols[symbolName] = BirdViewSymbol(symbolName, mplPath, scale, color, centerPoint)
        return self.symbols
        
    def loadSymbolsFromSvgText(self):
        """ Only used during development to alter / create new symbols."""
        if IMPORT_ERROR:
            print('DEPENDENCIES NOT MET. Has to be run in conda "svg2mpl" env')
            return
        
        for symbolName, svgProp in SVG_PROPS.items():
            color = svgProp[0]
            scale = svgProp[1]
            centerPoint = svgProp[2]
            mplPath = parse_path(SVG_PATHS[symbolName])
            # Move center of svg to center of marker
            mplPath = mplPath.transformed(transforms.Affine2D().translate(-1 * SVG_CENTER[0], -1 * SVG_CENTER[1]))
            
            self.symbols[symbolName] = BirdViewSymbol(symbolName, mplPath, scale, color, centerPoint)
    
    def previewSymbols(self, symbolName=None):
        if symbolName:
            marker: BirdViewSymbol = self.symbols[symbolName]
            plt.plot(0, 0, marker=marker.mplPath, markersize=marker.scale * 200, color=marker.color)
        else:
            for key, marker in self.symbols.items():
                plt.plot(0, 0, marker=marker.mplPath, markersize=marker.scale * 200, color=marker.color)
        plt.show()
    
    def saveSymbolsAsPaths(self, savePath=r'config/birdView'):
        for symbolName, symbol in self.symbols.items():
            np.save(os.path.join(_HOME_PATH, savePath, f'{symbolName}_vertices'), symbol.mplPath.vertices)
            np.save(os.path.join(_HOME_PATH, savePath, f'{symbolName}_codes'), symbol.mplPath.codes)


if __name__ == '__main__':
    # For development purposes only, not ment to be run during regular use!
    #  This will load svg strings, transform them into matplotlib Path objects
    #  and save them as numpy save files. During a regular run, matplotlib Path
    #  objects are created directly from the numpy save files.
    symbols = BirdViewSymbolLoader()
    symbols.loadSymbolsFromSvgText()
    symbols.previewSymbols()
    symbols.saveSymbolsAsPaths()
     
    # Default usage and behaviour of this class is demonstrated here:
    #
    # symbols2 = BirdViewSymbolLoader()
    # symbols2.loadSymbolFromArray()
    # # symbols2.previewSymbols('mehrbaumanker')
    # symbols2.previewSymbols()
    
    
