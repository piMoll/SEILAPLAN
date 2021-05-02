from qgis.PyQt.QtCore import pyqtSignal
from qgis.gui import QgsCheckableComboBox


class QgsCheckableComboBoxOwn(QgsCheckableComboBox):

    selectedItemsChanged = pyqtSignal()
    focus_in_signal = pyqtSignal()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def hidePopup(self):
        super().hidePopup()

    def showPopup(self):
        super().showPopup()

    def focusInEvent(self, event):
        super(QgsCheckableComboBoxOwn, self).focusInEvent(event)
        super().focusInEvent(event)
        if event.reason() == 4:     # Qt::PopupFocusReason
            self.selectedItemsChanged.emit()
