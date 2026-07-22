from qgis.gui import QgsCheckableComboBox
from qgis.PyQt.QtCore import pyqtSignal, QSize, Qt
from qgis.PyQt.QtWidgets import QSizePolicy


class QgsCheckableComboBoxOwn(QgsCheckableComboBox):

    selectedItemsChanged = pyqtSignal()
    focus_in_signal = pyqtSignal()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setMinimumSize(QSize(200, 27))
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        # Disable auto scrolling so the user isn't confused about missing items
        #  at the beginning of the list
        self.view().setAutoScroll(False)

    def hidePopup(self):
        super().hidePopup()

    def showPopup(self):
        super().showPopup()

    def focusInEvent(self, event):
        super(QgsCheckableComboBoxOwn, self).focusInEvent(event)
        super().focusInEvent(event)
        if event.reason() == Qt.FocusReason.PopupFocusReason:
            self.selectedItemsChanged.emit()
