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

ACCENT_COLOR = 'saddlebrown'

_HOME_PATH = os.path.dirname(os.path.dirname(__file__))
SVG_CENTER = [25, 25]
SVG_PROPS = {
    'default': [ACCENT_COLOR, 0.23, True],
    'fadenkreuz': ['black', 1.0, False],
    'mobiler_seilkran': ['black', 1.33, False],
    'vorziehstuetze_1': ['black', 1.33, True],
    'vorziehstuetze_2': ['black', 1.33, True],
    'dreizackiger_stern': ['black', 1.33, True],
    'vorgeneigte_stuetze': ['black', 1.33, True],
    'mehrbaumanker': ['black', 1.33, True],
    'endmast_mit_zugseilrolle': ['black', 1.33, True],
    'endmast_ohne_zugseilrolle': ['black', 1.33, True],
    'totmannanker': [ACCENT_COLOR, 0.8, False],
    'verstaerkter_ankerbaum': ['black', 1, True],
    'normaler_ankerbaum': [ACCENT_COLOR, 0.23, True],
}
SVG_PATHS = {
    'default': """m 30.1355,25 a 5,5 0 0 1 -5,5 5,5 0 0 1 -5,-5 5,5 0 0 1 5,-5 5,5 0 0 1 5,5 z
    """,
    'fadenkreuz': """m 50.1355,25 h -50 m 25,-25 v 50""",
    'mobiler_seilkran': """m 40.770638,6.7008829 a 2.5,2.5 0 0 0 -2.500107,2.5001059 2.5,2.5 0 0 0 0.338998,1.2567712 l -5.451345,5.509741 V 13.611572 H 17.113167 v 0.65009 22.126814 h 16.045017 v -2.21175 l 5.326287,5.474084 a 2.5,2.5 0 0 0 -0.351399,1.276924 2.5,2.5 0 0 0 2.500107,2.49959 2.5,2.5 0 0 0 2.499587,-2.49959 2.5,2.5 0 0 0 -2.499587,-2.500106 2.5,2.5 0 0 0 -1.216465,0.317293 l -6.25853,-6.432166 v -4.730977 l 11.350209,2.706296 a 2.5,2.5 0 0 0 2.497524,2.427242 2.5,2.5 0 0 0 2.500106,-2.500106 2.5,2.5 0 0 0 -2.500106,-2.500106 2.5,2.5 0 0 0 -2.196767,1.309481 L 33.158184,26.244909 V 23.754105 L 44.80915,20.972363 a 2.5,2.5 0 0 0 2.195732,1.30793 2.5,2.5 0 0 0 2.500106,-2.500105 2.5,2.5 0 0 0 -2.500106,-2.500106 2.5,2.5 0 0 0 -2.497521,2.427759 L 33.158184,22.416719 V 17.81545 l 6.374804,-6.443018 a 2.5,2.5 0 0 0 1.23765,0.328146 2.5,2.5 0 0 0 2.49959,-2.4995892 2.5,2.5 0 0 0 -2.49959,-2.5001059 z M 18.413863,14.910201 h 13.443624 v 2.372465 l -5.48597,5.544364 a 2.5,2.5 0 0 0 -1.236101,-0.327112 2.5,2.5 0 0 0 -2.500105,2.500106 2.5,2.5 0 0 0 2.500105,2.500106 2.5,2.5 0 0 0 1.21698,-0.317294 l 5.505091,5.657535 v 2.249477 H 18.413863 Z m 13.443624,4.219897 v 3.59668 l -4.525307,1.080037 a 2.5,2.5 0 0 0 -0.03721,-0.06563 z m 0,4.934583 v 1.87017 l -3.917591,-0.934827 z m -4.526339,2.128035 4.526339,1.079004 v 3.704683 l -4.573366,-4.699971 a 2.5,2.5 0 0 0 0.04703,-0.08372 z
    """,
    'vorziehstuetze_1': """M 26.938925,0.61391601 A 2.5,2.5 0 0 0 24.438818,3.1140217 2.5,2.5 0 0 0 26.440763,5.5619342 L 25.179341,21.133077 a 3.9999999,3.9999999 0 0 0 -0.02222,0 3.9999999,3.9999999 0 0 0 -3.999756,3.999755 3.9999999,3.9999999 0 0 0 3.999756,4.000274 3.9999999,3.9999999 0 0 0 1.429371,-0.265101 l 6.639385,13.960906 a 2.5,2.5 0 0 0 -1.163751,2.110464 2.5,2.5 0 0 0 2.500106,2.500107 2.5,2.5 0 0 0 2.500104,-2.500107 2.5,2.5 0 0 0 -2.500104,-2.49959 2.5,2.5 0 0 0 -0.79375,0.130741 L 27.129094,28.612205 a 3.9999999,3.9999999 0 0 0 2.028299,-3.479373 3.9999999,3.9999999 0 0 0 -3.378605,-3.951179 L 27.038144,5.6099934 A 2.5,2.5 0 0 0 29.438512,3.1140217 2.5,2.5 0 0 0 26.938925,0.61391601 Z
    """,
    'vorziehstuetze_2': """M 26.938925,0.61391601 A 2.5,2.5 0 0 0 24.438818,3.1140217 2.5,2.5 0 0 0 26.440763,5.5619342 L 25.179341,21.133077 a 3.9999999,3.9999999 0 0 0 -0.02222,0 3.9999999,3.9999999 0 0 0 -3.999756,3.999755 3.9999999,3.9999999 0 0 0 3.999756,4.000274 3.9999999,3.9999999 0 0 0 1.429371,-0.265101 l 6.639385,13.960906 a 2.5,2.5 0 0 0 -1.163751,2.110464 2.5,2.5 0 0 0 2.500106,2.500107 2.5,2.5 0 0 0 2.500104,-2.500107 2.5,2.5 0 0 0 -2.500104,-2.49959 2.5,2.5 0 0 0 -0.79375,0.130741 L 27.129095,28.612205 a 3.9999999,3.9999999 0 0 0 1.154452,-0.984435 l 13.027112,8.88628 a 2.5,2.5 0 0 0 -0.282671,1.1498 2.5,2.5 0 0 0 2.500104,2.49959 2.5,2.5 0 0 0 2.500106,-2.49959 2.5,2.5 0 0 0 -2.500106,-2.500106 2.5,2.5 0 0 0 -1.879986,0.854728 L 28.621509,27.133227 a 3.9999999,3.9999999 0 0 0 0.535885,-2.000395 3.9999999,3.9999999 0 0 0 -3.378605,-3.951179 L 27.038145,5.6099934 A 2.5,2.5 0 0 0 29.438514,3.1140217 2.5,2.5 0 0 0 26.938926,0.61391601 Z
    """,
    'dreizackiger_stern': """M 25.135933,0.5431193 A 2.5,2.5 0 0 0 22.635827,3.043225 2.5,2.5 0 0 0 24.835693,5.5236937 V 21.131527 a 3.9999999,3.9999999 0 0 0 -3.700033,3.988903 3.9999999,3.9999999 0 0 0 1.745114,3.304191 l -7.75715,13.437423 a 2.5,2.5 0 0 0 -0.981335,-0.200504 2.5,2.5 0 0 0 -2.499589,2.500106 2.5,2.5 0 0 0 2.499589,2.499587 2.5,2.5 0 0 0 2.500106,-2.499587 2.5,2.5 0 0 0 -0.999422,-1.99988 l 7.759216,-13.436388 a 3.9999999,3.9999999 0 0 0 1.733744,0.395325 3.9999999,3.9999999 0 0 0 1.744596,-0.401527 l 7.79694,13.41882 a 2.5,2.5 0 0 0 -0.994254,1.993678 2.5,2.5 0 0 0 2.500106,2.500103 2.5,2.5 0 0 0 2.499587,-2.500103 2.5,2.5 0 0 0 -2.499587,-2.500106 2.5,2.5 0 0 0 -0.985986,0.204637 L 27.398326,28.418938 A 3.9999999,3.9999999 0 0 0 29.135689,25.12043 3.9999999,3.9999999 0 0 0 25.435657,21.132043 V 5.5236937 A 2.5,2.5 0 0 0 27.635522,3.043225 2.5,2.5 0 0 0 25.135933,0.5431193 Z
    """,
    'vorgeneigte_stuetze': """m 50.1355,25 h -50 m 25,-25 v 50
    """,    # TODO
    'mehrbaumanker': """m 40.770638,6.7008829 a 2.5,2.5 0 0 0 -2.500107,2.5001059 2.5,2.5 0 0 0 0.54002,1.5518432 L 27.727507,21.953698 a 3.9999999,3.9999999 0 0 0 -2.592091,-0.953946 3.9999999,3.9999999 0 0 0 -3.999756,4.000272 3.9999999,3.9999999 0 0 0 3.999756,3.999756 3.9999999,3.9999999 0 0 0 2.565218,-0.933278 L 38.68756,39.357805 a 2.5,2.5 0 0 0 -0.554488,1.569929 2.5,2.5 0 0 0 2.500107,2.49959 2.5,2.5 0 0 0 2.499587,-2.49959 2.5,2.5 0 0 0 -2.499587,-2.500106 2.5,2.5 0 0 0 -1.515671,0.513146 L 28.12955,27.648442 a 3.9999999,3.9999999 0 0 0 0.815454,-1.432472 l 15.578894,3.71657 a 2.5,2.5 0 0 0 -0.0181,0.28267 2.5,2.5 0 0 0 2.500106,2.500106 2.5,2.5 0 0 0 2.500106,-2.500106 2.5,2.5 0 0 0 -2.500106,-2.500106 2.5,2.5 0 0 0 -2.34301,1.632976 L 29.083497,25.633577 a 3.9999999,3.9999999 0 0 0 0.05219,-0.633553 3.9999999,3.9999999 0 0 0 -0.05116,-0.634586 l 15.576828,-3.717603 a 2.5,2.5 0 0 0 2.343525,1.632458 2.5,2.5 0 0 0 2.500106,-2.500105 2.5,2.5 0 0 0 -2.500106,-2.500106 2.5,2.5 0 0 0 -2.500106,2.500106 2.5,2.5 0 0 0 0.0181,0.28422 L 28.946046,23.783044 A 3.9999999,3.9999999 0 0 0 28.154365,22.375895 L 39.237409,11.174512 a 2.5,2.5 0 0 0 1.533239,0.526066 2.5,2.5 0 0 0 2.49959,-2.4995892 2.5,2.5 0 0 0 -2.49959,-2.5001059 z
    """,
    'endmast_mit_zugseilrolle': """m 50.1355,25 h -50 m 25,-25 v 50
    """,    # TODO
    'endmast_ohne_zugseilrolle': """m 50.1355,25 h -50 m 25,-25 v 50
    """,    # TODO
    'totmannanker': """m 22.634766,10.291016 v 29.658203 h 5 V 10.291016 Z
    """,
    'verstaerkter_ankerbaum': """m 40.769603,6.8207722 a 2.5,2.5 0 0 0 -2.500106,2.5001059 2.5,2.5 0 0 0 0.340032,1.2578039 L 27.45052,21.858097 a 3.9999999,3.9999999 0 0 0 -2.314587,-0.737423 3.9999999,3.9999999 0 0 0 -4.000273,3.999756 3.9999999,3.9999999 0 0 0 4.000273,4.000273 3.9999999,3.9999999 0 0 0 2.336291,-0.756545 l 11.186914,11.13834 a 2.5,2.5 0 0 0 -0.331245,1.242819 2.5,2.5 0 0 0 2.499588,2.499587 2.5,2.5 0 0 0 2.500106,-2.499587 2.5,2.5 0 0 0 -2.500106,-2.500106 2.5,2.5 0 0 0 -1.251604,0.336412 L 28.389482,27.443287 A 3.9999999,3.9999999 0 0 0 29.135689,25.12043 3.9999999,3.9999999 0 0 0 28.373461,22.772253 L 39.534539,11.493355 a 2.5,2.5 0 0 0 1.235064,0.327112 2.5,2.5 0 0 0 2.500106,-2.4995889 2.5,2.5 0 0 0 -2.500106,-2.5001059 z
    """,
    'normaler_ankerbaum': """m 30.1355,25 a 5,5 0 0 1 -5,5 5,5 0 0 1 -5,-5 5,5 0 0 1 5,-5 5,5 0 0 1 5,5 z
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
    
    def mirror(self):
        return self.mplPath.transformed(transforms.Affine2D().scale(-1, 1))
    

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
    
    
