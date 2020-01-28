from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT \
    as NavigationToolbar
from qgis.PyQt.QtCore import QSize


class MyNavigationToolbar(NavigationToolbar):
    """Navigation bar for plot with home button, pan and zoom."""
    toolitems = [t for t in NavigationToolbar.toolitems if
                 t[0] in ('Home', 'Pan', 'Zoom')]

    def __init__(self, *args, **kwargs):
        super(MyNavigationToolbar, self).__init__(*args, **kwargs)
        self.layout().takeAt(3)  # 3 = Amount of tools we need
        self.layout().setSpacing(5)
        self.setIconSize(QSize(20, 20))
        

def zoom_with_wheel(FigCanvas, ax, zoomScale):
    """Implements zooming in plot whith mouse wheel. The function itself has
    to be returned and saved to a variable, otherwise it could be garbage
    collected."""
    
    def zoomFunc(event):
        # Get the current x and y limits
        cur_xlim = ax.get_xlim()
        cur_ylim = ax.get_ylim()
        xdata = event.xdata  # Get event x location
        ydata = event.ydata  # Get event y location
        if event.button == 'up':
            # Deal with zoom in
            scale_factor = 1 / zoomScale
        elif event.button == 'down':
            # Deal with zoom out
            scale_factor = zoomScale
        else:
            scale_factor = 1
        # Set new limits
        ax.set_xlim([xdata - (xdata - cur_xlim[0]) * scale_factor,
                     xdata + (cur_xlim[1] - xdata) * scale_factor])
        ax.set_ylim([ydata - (ydata - cur_ylim[0]) * scale_factor,
                     ydata + (cur_ylim[1] - ydata) * scale_factor])
        FigCanvas.draw()

    # Get the figure of interest
    fig = ax.get_figure()
    # Attach the call back
    fig.canvas.mpl_connect('scroll_event', zoomFunc)
    return zoomFunc
