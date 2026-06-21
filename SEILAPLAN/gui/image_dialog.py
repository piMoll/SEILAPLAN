from qgis.PyQt.QtCore import QSize, Qt
from qgis.PyQt.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QLayout,
    QVBoxLayout,
    QWidget,
)


class DialogWithImage(QDialog):
    def __init__(self):
        QDialog.__init__(self)
        self.main_widget = QWidget(self)
        self.main_widget.setMinimumSize(QSize(100, 100))
        self.label = QLabel()
        self.buttonBox = QDialogButtonBox(self.main_widget)
        self.buttonBox.setStandardButtons(QDialogButtonBox.StandardButton.Ok)
        self.buttonBox.accepted.connect(self.Apply)
        # Access the layout of the MessageBox to add the checkbox
        self.container = QVBoxLayout(self.main_widget)
        self.container.addWidget(self.label)
        self.container.addWidget(self.buttonBox)
        self.container.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.container.setSizeConstraint(QLayout.SizeConstraint.SetFixedSize)
        self.setLayout(self.container)

    def Apply(self):
        self.close()
