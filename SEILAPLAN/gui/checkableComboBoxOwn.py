from qgis.PyQt.QtWidgets import QSizePolicy
from qgis.PyQt.QtCore import Qt, pyqtSignal, QSize
from qgis.gui import QgsCheckableComboBox


class QgsCheckableComboBoxOwn(QgsCheckableComboBox):

    selectedItemsChanged = pyqtSignal()
    focus_in_signal = pyqtSignal()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
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
