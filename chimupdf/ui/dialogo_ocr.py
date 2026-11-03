from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QRadioButton,
    QVBoxLayout,
)

from chimupdf.nucleo.ocr import nombre_idioma
from chimupdf.nucleo.operaciones import parsear_rangos


class DialogoOCR(QDialog):
    """Elige idioma(s) y páginas para el OCR.

    modo: "buscable" (alcance + omitir páginas con texto), "exportar" (alcance)
    o "copiar" (solo idioma). Al aceptar deja listos idioma, indices y omitir.
    """

    def __init__(self, parent, idiomas, total, actual, titulo, modo="buscable"):
        super().__init__(parent)
        self.setWindowTitle(titulo)
        self.setMinimumWidth(420)
        self.total = total
        self.actual = actual
        self.modo = modo
        self.idioma = ""
        self.indices = []
        self.omitir = True

        self.lista = QListWidget()
        self.lista.setMaximumHeight(120)
        for codigo in idiomas:
            item = QListWidgetItem(f"{nombre_idioma(codigo)} ({codigo})")
            item.setData(Qt.ItemDataRole.UserRole, codigo)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Unchecked)
            self.lista.addItem(item)
        preseleccion = "spa" if "spa" in idiomas else (idiomas[0] if idiomas else None)
        for i in range(self.lista.count()):
            if self.lista.item(i).data(Qt.ItemDataRole.UserRole) == preseleccion:
                self.lista.item(i).setCheckState(Qt.CheckState.Checked)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Idioma(s) del documento (puedes marcar más de uno):"))
        layout.addWidget(self.lista)

        if modo != "copiar":
            self.r_actual = QRadioButton(f"Página actual ({actual + 1})")
            self.r_todas = QRadioButton(f"Todas las páginas ({total})")
            self.r_rango = QRadioButton("Estas páginas:")
            self.e_rango = QLineEdit()
            self.e_rango.setPlaceholderText("Ej.: 1-3, 5")
            self.e_rango.textEdited.connect(lambda _t: self.r_rango.setChecked(True))
            self.r_todas.setChecked(True)
            grupo = QGroupBox("Páginas")
            caja = QVBoxLayout(grupo)
            caja.addWidget(self.r_actual)
            caja.addWidget(self.r_todas)
            fila = QHBoxLayout()
            fila.addWidget(self.r_rango)
            fila.addWidget(self.e_rango)
            caja.addLayout(fila)
            layout.addWidget(grupo)

        if modo == "buscable":
            self.c_omitir = QCheckBox("Omitir las páginas que ya tienen texto")
            self.c_omitir.setChecked(True)
            layout.addWidget(self.c_omitir)
            nota = QLabel(
                "Las páginas reconocidas se guardan como imagen (300 ppp) con una capa de texto "
                "invisible. Las anotaciones que tengan esas páginas quedan fijas en la imagen."
            )
            nota.setWordWrap(True)
            layout.addWidget(nota)

        botones = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        botones.button(QDialogButtonBox.StandardButton.Ok).setText("Iniciar")
        botones.button(QDialogButtonBox.StandardButton.Cancel).setText("Cancelar")
        botones.accepted.connect(self.accept)
        botones.rejected.connect(self.reject)
        layout.addWidget(botones)

    def accept(self):
        codigos = [
            self.lista.item(i).data(Qt.ItemDataRole.UserRole)
            for i in range(self.lista.count())
            if self.lista.item(i).checkState() == Qt.CheckState.Checked
        ]
        if not codigos:
            QMessageBox.warning(self, self.windowTitle(), "Marca al menos un idioma.")
            return
        if self.modo == "copiar":
            indices = [self.actual]
        elif self.r_actual.isChecked():
            indices = [self.actual]
        elif self.r_todas.isChecked():
            indices = list(range(self.total))
        else:
            try:
                rangos = parsear_rangos(self.e_rango.text(), self.total)
            except ValueError as error:
                QMessageBox.warning(self, self.windowTitle(), str(error))
                return
            indices = sorted({i for inicio, fin in rangos for i in range(inicio, fin + 1)})
        self.idioma = "+".join(codigos)
        self.indices = indices
        self.omitir = self.modo == "buscable" and self.c_omitir.isChecked()
        super().accept()
