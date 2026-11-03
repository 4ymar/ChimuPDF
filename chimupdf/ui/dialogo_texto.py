from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)

from chimupdf.nucleo.edicion import BLANCO, FAMILIAS, NEGRO, EstiloTexto


def _estilo_boton(boton, color):
    r, g, b = (round(c * 255) for c in color)
    claro = (0.299 * r + 0.587 * g + 0.114 * b) > 140
    boton.setStyleSheet(f"background-color: rgb({r},{g},{b}); color: {'black' if claro else 'white'};")


def _elegir(parent, color, titulo):
    elegido = QColorDialog.getColor(QColor.fromRgbF(*color), parent, titulo)
    return (elegido.redF(), elegido.greenF(), elegido.blueF()) if elegido.isValid() else None


class SelectorEstilo(QWidget):
    """Fuente, tamaño, negrita, cursiva y color del texto."""

    def __init__(self, estilo=None, parent=None):
        super().__init__(parent)
        self._color = NEGRO
        self.familia = QComboBox()
        for nombre, codigo in FAMILIAS.items():
            self.familia.addItem(nombre, codigo)
        self.tamano = QDoubleSpinBox()
        self.tamano.setRange(4, 200)
        self.tamano.setDecimals(1)
        self.tamano.setSingleStep(0.5)
        self.tamano.setSuffix(" pt")
        self.negrita = QCheckBox("Negrita")
        self.cursiva = QCheckBox("Cursiva")
        self.b_color = QPushButton("Color")
        self.b_color.clicked.connect(self._cambiar_color)

        fila1 = QHBoxLayout()
        fila1.addWidget(self.familia, 1)
        fila1.addWidget(self.tamano)
        fila2 = QHBoxLayout()
        fila2.addWidget(self.negrita)
        fila2.addWidget(self.cursiva)
        fila2.addWidget(self.b_color)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(fila1)
        layout.addLayout(fila2)
        self.establecer(estilo or EstiloTexto())

    def establecer(self, estilo):
        indice = self.familia.findData(estilo.familia)
        self.familia.setCurrentIndex(max(indice, 0))
        self.tamano.setValue(estilo.tamano)
        self.negrita.setChecked(estilo.negrita)
        self.cursiva.setChecked(estilo.cursiva)
        self._color = tuple(estilo.color)
        _estilo_boton(self.b_color, self._color)

    def _cambiar_color(self):
        nuevo = _elegir(self, self._color, "Color del texto")
        if nuevo:
            self._color = nuevo
            _estilo_boton(self.b_color, nuevo)

    def estilo(self):
        return EstiloTexto(
            self.familia.currentData(), self.tamano.value(),
            self.negrita.isChecked(), self.cursiva.isChecked(), self._color,
        )


class DialogoTexto(QDialog):
    """Escribe el texto nuevo y ajusta su fuente. modo: 'reemplazar' o 'agregar'."""

    def __init__(self, parent, titulo, modo, zona=None, estilo=None):
        super().__init__(parent)
        self.setWindowTitle(titulo)
        self.setMinimumWidth(440)
        self.texto = ""
        self.estilo = None
        self.tapar_fondo = False
        self.modo = modo

        self.editor = QPlainTextEdit(zona.texto if zona else "")
        self.editor.setMinimumHeight(90)
        self.selector = SelectorEstilo(zona.estilo if zona and zona.tiene_texto else estilo)

        layout = QVBoxLayout(self)
        if modo == "reemplazar":
            if zona.tiene_texto:
                e = zona.estilo
                detalle = (
                    f"Fuente detectada: {self.selector.familia.currentText()}"
                    f"{', negrita' if e.negrita else ''}{', cursiva' if e.cursiva else ''}, {e.tamano:g} pt. "
                    "Si no se ve igual, cámbiala aquí abajo."
                )
            else:
                detalle = (
                    "No se detectó texto editable en esta zona (¿página escaneada?). "
                    "Si el texto es parte de una imagen, se tapará con blanco y se escribirá encima."
                )
            etiqueta = QLabel(detalle)
            etiqueta.setWordWrap(True)
            layout.addWidget(etiqueta)
        layout.addWidget(QLabel("Texto:"))
        layout.addWidget(self.editor)
        layout.addWidget(QLabel("Fuente del texto nuevo:"))
        layout.addWidget(self.selector)
        self.c_fondo = None
        if modo == "reemplazar":
            self.c_fondo = QCheckBox("Tapar el fondo con blanco (necesario en páginas escaneadas)")
            self.c_fondo.setChecked(not zona.tiene_texto)
            layout.addWidget(self.c_fondo)

        botones = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        botones.button(QDialogButtonBox.StandardButton.Ok).setText("Aplicar")
        botones.button(QDialogButtonBox.StandardButton.Cancel).setText("Cancelar")
        botones.accepted.connect(self.accept)
        botones.rejected.connect(self.reject)
        layout.addWidget(botones)

    def accept(self):
        texto = self.editor.toPlainText().strip("\n")
        if not texto.strip():
            QMessageBox.warning(self, self.windowTitle(), "Escribe el texto. Para borrar usa «Borrar/tapar».")
            return
        self.texto = texto
        self.estilo = self.selector.estilo()
        self.tapar_fondo = bool(self.c_fondo and self.c_fondo.isChecked())
        super().accept()


class DialogoBuscarReemplazar(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Buscar y reemplazar")
        self.setMinimumWidth(440)
        self.buscar = ""
        self.nuevo = ""
        self.estilo = None  # None = igualar la fuente original
        self.ajustar = True

        self.e_buscar = QLineEdit()
        self.e_nuevo = QLineEdit()
        formulario = QFormLayout()
        formulario.addRow("Buscar:", self.e_buscar)
        formulario.addRow("Reemplazar por:", self.e_nuevo)

        self.r_auto = QRadioButton("Igualar la fuente original (automático)")
        self.r_manual = QRadioButton("Usar esta fuente:")
        self.r_auto.setChecked(True)
        self.selector = SelectorEstilo()
        self.selector.setEnabled(False)
        self.r_manual.toggled.connect(self.selector.setEnabled)
        self.c_ajustar = QCheckBox("Reducir el tamaño si el texto nuevo es más ancho que el original")
        self.c_ajustar.setChecked(True)
        nota = QLabel("La búsqueda no distingue mayúsculas de minúsculas. Solo se reemplaza texto real; "
                      "en páginas escaneadas haz antes el OCR.")
        nota.setWordWrap(True)

        botones = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        botones.button(QDialogButtonBox.StandardButton.Ok).setText("Buscar")
        botones.button(QDialogButtonBox.StandardButton.Cancel).setText("Cancelar")
        botones.accepted.connect(self.accept)
        botones.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(formulario)
        layout.addWidget(self.r_auto)
        layout.addWidget(self.r_manual)
        layout.addWidget(self.selector)
        layout.addWidget(self.c_ajustar)
        layout.addWidget(nota)
        layout.addWidget(botones)

    def accept(self):
        if not self.e_buscar.text():
            QMessageBox.warning(self, self.windowTitle(), "Escribe el texto que quieres buscar.")
            return
        self.buscar = self.e_buscar.text()
        self.nuevo = self.e_nuevo.text()
        self.estilo = self.selector.estilo() if self.r_manual.isChecked() else None
        self.ajustar = self.c_ajustar.isChecked()
        super().accept()


class DialogoRelleno(QDialog):
    """Elige el color con que se cubre la zona eliminada."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Borrar o tapar zona")
        self.color = BLANCO
        self._otro = (0.8, 0.0, 0.0)

        self.r_blanco = QRadioButton("Borrar (relleno blanco)")
        self.r_negro = QRadioButton("Tapar (relleno negro)")
        self.r_otro = QRadioButton("Otro color:")
        self.r_blanco.setChecked(True)
        self.b_color = QPushButton("Color")
        self.b_color.clicked.connect(self._cambiar)
        _estilo_boton(self.b_color, self._otro)
        fila = QHBoxLayout()
        fila.addWidget(self.r_otro)
        fila.addWidget(self.b_color)
        fila.addStretch()
        nota = QLabel("Elimina de forma permanente el texto y las imágenes que haya bajo la zona.")
        nota.setWordWrap(True)

        botones = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        botones.button(QDialogButtonBox.StandardButton.Ok).setText("Aplicar")
        botones.button(QDialogButtonBox.StandardButton.Cancel).setText("Cancelar")
        botones.accepted.connect(self.accept)
        botones.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(nota)
        layout.addWidget(self.r_blanco)
        layout.addWidget(self.r_negro)
        layout.addLayout(fila)
        layout.addWidget(botones)

    def _cambiar(self):
        nuevo = _elegir(self, self._otro, "Color de relleno")
        if nuevo:
            self._otro = nuevo
            _estilo_boton(self.b_color, nuevo)
            self.r_otro.setChecked(True)

    def accept(self):
        self.color = BLANCO if self.r_blanco.isChecked() else NEGRO if self.r_negro.isChecked() else self._otro
        super().accept()
