from qgis.PyQt.QtCore import QSize, Qt
from qgis.PyQt.QtWidgets import ( QSizePolicy, QDoubleSpinBox,
                                 QSpinBox, QPushButton, QLineEdit, QHBoxLayout,
                                 QSpacerItem)
from qgis.PyQt.QtGui import QIcon, QPixmap



class AdjustmentDialogPoles(object):
    
    def __init__(self, dialog):
        # AdjustmentDialog.__init__(self, toolWindow, interface)

        self.dialog = dialog
        self.poleDist = dialog.data['poleDist']
        self.poleHeight = dialog.data['poleHeight']

        # Pole Input fields
        self.poleListing = {}
        self.dialog.addBtnVGrid.setAlignment(Qt.AlignTop)
        self.addPolesToGui()

    
    def addPolesToGui(self):
        rangeBuffer = 10
        poleCount = len(self.poleDist)
        
        # Ankerfeld start
        self.addAnker(0, -7.0, [-1 * rangeBuffer, 0])
        
        # Poles
        for idx in range(poleCount):
            delBtn = False
            addBtn = False
            lowerRange = self.poleDist[idx - 1] if idx > 0 else 0
            upperRange = self.poleDist[idx + 1] if idx < poleCount - 1 \
                            else self.poleDist[idx] + rangeBuffer
            
            # Delete Buttons vor all but the first and last pole
            if idx != 0 and idx != poleCount - 1:
                delBtn = True
            # Add Button for all but the last pole
            if idx != poleCount - 1:
                addBtn = True
            
            self.addPole(idx + 1, self.poleDist[idx], [lowerRange, upperRange],
                         self.poleHeight[idx], delBtn, addBtn)
        
        # Ankerfeld end
        self.addAnker(poleCount + 1, 327.0, [327.0, 327.0 + rangeBuffer])
    
    def addAnker(self, idx, dist, distRange):
        row = self.addRow(idx)
        self.addPoleAddBtn(False)
        self.addPoleName(row, idx, 'Verankerung')
        self.addPoleHDist(row, idx, dist, distRange)  # TODO: Wert aus IS auslesen
    
    
    def addPole(self, poleNr, dist, distRange, height, delBtn, addBtn):
        row = self.addRow(poleNr)
        self.addPoleName(row, poleNr, f'{poleNr}. Stütze')
        self.addPoleHDist(row, poleNr, dist, distRange)
        self.addPoleHeight(row, poleNr, height)
        self.addPoleAngle(row, poleNr, 0)
        
        if delBtn:
            self.addPoleDel(row, poleNr)
        if addBtn:
            self.addPoleAddBtn(poleNr)

    def addRow(self, idx):
        rowLayout = QHBoxLayout()
        rowLayout.setAlignment(Qt.AlignLeft)
        # if last position in grid addLayout, else insertLayout
        if self.dialog.poleVGrid.count() == idx + 1:
            self.dialog.poleVGrid.addLayout(rowLayout)
        else:
            self.dialog.poleVGrid.insertLayout(idx, rowLayout)
    
        self.poleListing[idx] = {}
        return rowLayout
    
    def addPoleAddBtn(self, idx):
        # Placeholder for add Button
        if not idx:
            placeholder = QSpacerItem(5, 31 + 20, QSizePolicy.Fixed,
                                      QSizePolicy.Fixed)
            self.dialog.addBtnVGrid.addItem(placeholder)
            return
        
        btn = QPushButton(self.dialog.tabPoles)
        btn.setMaximumSize(QSize(19, 19))
        btn.setText("")
        icon = QIcon()
        icon.addPixmap(
            QPixmap(":/plugins/SeilaplanPlugin/gui/icons/icon_plus.png"),
            QIcon.Normal, QIcon.Off)
        btn.setIcon(icon)
        btn.setIconSize(QSize(16, 16))
        self.dialog.addBtnVGrid.addWidget(btn)
        margin = QSpacerItem(5, 6, QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.dialog.addBtnVGrid.addItem(margin)
        self.poleListing[idx]['add'] = btn
    
    
    def addPoleName(self, row, idx, value):
        field = QLineEdit(self.dialog.tabPoles)
        field.setFixedWidth(180)  # TODO: Soltle wachsen können
        field.setText(value)
        self.poleListing[idx]['name'] = field
        row.addWidget(field)
    
    
    def addPoleHDist(self, row, idx, value, valRange):
        field = QDoubleSpinBox(self.dialog.tabPoles)
        field.setDecimals(1)
        field.setSingleStep(0.5)
        field.setSuffix(" m")
        field.setFixedWidth(95)
        field.setRange(float(valRange[0]), float(valRange[
                                                     1]))  # TODO Range ist von der vorherigen und nachherigen Stütze abhängig
        field.setValue(float(value))
        row.addWidget(field)
        self.poleListing[idx]['dist'] = field
    
    
    def addPoleHeight(self, row, idx, value):
        field = QDoubleSpinBox(self.dialog.tabPoles)
        field.setDecimals(1)
        field.setSingleStep(0.1)
        field.setSuffix(" m")
        field.setFixedWidth(85)
        field.setRange(0.0, 50.0)
        field.setValue(float(value))
        row.addWidget(field)
        self.poleListing[idx]['height'] = field
    
    
    def addPoleAngle(self, row, idx, value):
        field = QSpinBox(self.dialog.tabPoles)
        field.setSuffix(" °")
        field.setFixedWidth(60)
        field.setRange(-180, 180)
        field.setValue(value)
        row.addWidget(field)
        self.poleListing[idx]['angle'] = field
    
    
    def addPoleDel(self, row, idx):
        btn = QPushButton(self.dialog.tabPoles)
        btn.setMaximumSize(QSize(27, 27))
        icon = QIcon()
        icon.addPixmap(
            QPixmap(":/plugins/SeilaplanPlugin/gui/icons/icon_bin.png"),
            QIcon.Normal, QIcon.Off)
        btn.setIcon(icon)
        btn.setIconSize(QSize(16, 16))
        row.addWidget(btn)
        self.poleListing[idx]['del'] = btn