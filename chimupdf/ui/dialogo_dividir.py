import os

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QSpinBox,
    QVBoxLayout,
)

from chimupdf.nucleo.operaciones import grupos_cada_n, grupos_por_pagina, parsear_rangos


class DialogoDividir(QDialog):
    """Pide cómo dividir el documento. Al aceptar deja listos 'grupos' y 'carpeta'."""

    def __init__(self, total_paginas, carpeta_inicial, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Dividir PDF")
        self.resize(480, 260)
        self.total = total_paginas
        self.grupos = []
        self.carpeta = ""

        self.r_rangos = QRadioButton("Por rangos de páginas:")
        self.e_rangos = QLineEdit()
        self.e_rangos.setPlaceholderText("Ej.: 1-3, 4-10, 12")
        self.r_una = QRadioButton("Una página por archivo")
        self.r_cada = QRadioButton("Cada")
        self.s_cada = QSpinBox()
        self.s_cada.setRange(1, max(total_paginas, 1))
        self.s_cada.setValue(min(2, max(total_paginas, 1)))
        self.r_rangos.setChecked(True)
        self.e_rangos.textEdited.connect(lambda _t: self.r_rangos.setChecked(True))
        self.s_cada.valueChanged.connect(lambda _v: self.r_cada.setChecked(True))

        fila_cada = QHBoxLayout()
        fila_cada.addWidget(self.r_cada)
        fila_cada.addWidget(self.s_cada)
        fila_cada.addWidget(QLabel("páginas"))
        fila_cada.addStretch()

        self.e_carpeta = QLineEdit(carpeta_inicial)
        b_examinar = QPushButton("Examinar...")
        b_examinar.clicked.connect(self._examinar)
        fila_carpeta = QHBoxLayout()
        fila_carpeta.addWidget(self.e_carpeta, 1)
        fila_carpeta.addWidget(b_examinar)

        botones = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        botones.button(QDialogButtonBox.StandardButton.Ok).setText("Dividir")
        botones.button(QDialogButtonBox.StandardButton.Cancel).setText("Cancelar")
        botones.accepted.connect(self.accept)
        botones.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"El documento tiene {total_paginas} páginas."))
        layout.addWidget(self.r_rangos)
        layout.addWidget(self.e_rangos)
        layout.addWidget(self.r_una)
        layout.addLayout(fila_cada)
        layout.addWidget(QLabel("Guardar los archivos en la carpeta:"))
        layout.addLayout(fila_carpeta)
        layout.addStretch()
        layout.addWidget(botones)

    def _examinar(self):
        carpeta = QFileDialog.getExistingDirectory(self, "Carpeta de destino", self.e_carpeta.text())
        if carpeta:
            self.e_carpeta.setText(carpeta)

    def accept(self):
        carpeta = self.e_carpeta.text().strip()
        if not os.path.isdir(carpeta):
            QMessageBox.warning(self, "Dividir PDF", "Elige una carpeta de destino válida.")
            return
        try:
            if self.r_rangos.isChecked():
                grupos = parsear_rangos(self.e_rangos.text(), self.total)
            elif self.r_una.isChecked():
                grupos = grupos_por_pagina(self.total)
            else:
                grupos = grupos_cada_n(self.total, self.s_cada.value())
        except ValueError as error:
            QMessageBox.warning(self, "Dividir PDF", str(error))
            return
        self.grupos = grupos
        self.carpeta = carpeta
        super().accept()
