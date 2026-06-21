from qgis.PyQt.QtCore import QSize, Qt, pyqtSignal
from qgis.PyQt.QtWidgets import QSizePolicy
from qgis.gui import QgsCheckableComboBox


class QgsCheckableComboBoxOwn(QgsCheckableComboBox):

    selectedItemsChanged = pyqtSignal()
    focus_in_signal = pyqtSignal()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setMinimumSize(QSize(200, 27))
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def hidePopup(self):
        super().hidePopup()

    def showPopup(self):
        super().showPopup()

    def focusInEvent(self, event):
        super(QgsCheckableComboBoxOwn, self).focusInEvent(event)
        super().focusInEvent(event)
        if event.reason() == Qt.FocusReason.PopupFocusReason:
            self.selectedItemsChanged.emit()
