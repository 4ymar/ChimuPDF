import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from chimupdf.nucleo.operaciones import unir_archivos

RUTA = Qt.ItemDataRole.UserRole


class DialogoUnir(QDialog):
    """Une varios PDFs en uno nuevo, en el orden de la lista."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Unir PDFs")
        self.resize(560, 420)
        self.resultado = None  # ruta del PDF generado

        self.lista = QListWidget()
        self.lista.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.lista.setDefaultDropAction(Qt.DropAction.MoveAction)

        b_agregar = QPushButton("Agregar...")
        b_quitar = QPushButton("Quitar")
        b_subir = QPushButton("Subir")
        b_bajar = QPushButton("Bajar")
        b_agregar.clicked.connect(self._agregar)
        b_quitar.clicked.connect(self._quitar)
        b_subir.clicked.connect(lambda: self._mover(-1))
        b_bajar.clicked.connect(lambda: self._mover(1))

        columna = QVBoxLayout()
        for b in (b_agregar, b_quitar, b_subir, b_bajar):
            columna.addWidget(b)
        columna.addStretch()

        centro = QHBoxLayout()
        centro.addWidget(self.lista, 1)
        centro.addLayout(columna)

        b_unir = QPushButton("Unir y guardar...")
        b_unir.setDefault(True)
        b_cerrar = QPushButton("Cerrar")
        b_unir.clicked.connect(self._unir)
        b_cerrar.clicked.connect(self.reject)
        pie = QHBoxLayout()
        pie.addStretch()
        pie.addWidget(b_unir)
        pie.addWidget(b_cerrar)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(
            "Agrega los PDFs y ordénalos (arrastrando o con Subir/Bajar).\n"
            "Se unirán de arriba hacia abajo."
        ))
        layout.addLayout(centro)
        layout.addLayout(pie)

    def _rutas(self):
        return [self.lista.item(i).data(RUTA) for i in range(self.lista.count())]

    def _agregar(self):
        rutas, _ = QFileDialog.getOpenFileNames(self, "Agregar PDFs", "", "Archivos PDF (*.pdf)")
        for ruta in rutas:
            item = QListWidgetItem(os.path.basename(ruta))
            item.setData(RUTA, ruta)
            item.setToolTip(ruta)
            self.lista.addItem(item)

    def _quitar(self):
        fila = self.lista.currentRow()
        if fila >= 0:
            self.lista.takeItem(fila)

    def _mover(self, delta):
        fila = self.lista.currentRow()
        nueva = fila + delta
        if fila < 0 or not 0 <= nueva < self.lista.count():
            return
        item = self.lista.takeItem(fila)
        self.lista.insertItem(nueva, item)
        self.lista.setCurrentRow(nueva)

    def _unir(self):
        rutas = self._rutas()
        if len(rutas) < 2:
            QMessageBox.warning(self, "Unir PDFs", "Agrega al menos dos PDFs.")
            return
        salida, _ = QFileDialog.getSaveFileName(
            self, "Guardar PDF unido como", "", "Archivos PDF (*.pdf)"
        )
        if not salida:
            return
        if not salida.lower().endswith(".pdf"):
            salida += ".pdf"
        originales = {os.path.normcase(os.path.abspath(r)) for r in rutas}
        if os.path.normcase(os.path.abspath(salida)) in originales:
            QMessageBox.warning(
                self, "Unir PDFs",
                "El archivo de salida no puede ser uno de los PDFs que estás uniendo.",
            )
            return
        try:
            unir_archivos(rutas, salida)
        except Exception as error:
            QMessageBox.critical(self, "Unir PDFs", f"No se pudo unir los PDFs:\n{error}")
            return
        self.resultado = salida
        self.accept()
