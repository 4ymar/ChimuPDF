import os

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QPushButton, QVBoxLayout, QWidget

from chimupdf.nucleo import config

from .recursos import ruta_recurso

RUTA = Qt.ItemDataRole.UserRole
ANCHO_LISTA = 460
ALTO_MAX_LISTA = 340


class PantallaInicio(QWidget):
    """Pantalla de bienvenida: logo, botón Abrir y archivos recientes."""

    abrir_solicitado = Signal()
    abrir_reciente = Signal(str)
    unir_solicitado = Signal()
    dividir_solicitado = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("PantallaInicio")

        logo = QLabel()
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pm = QPixmap(ruta_recurso("chimupdf.png"))
        if not pm.isNull():
            logo.setPixmap(pm.scaled(120, 120, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))

        titulo = QLabel("ChimuPDF")
        titulo.setObjectName("TituloInicio")
        titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitulo = QLabel("Edita, une, firma y protege tus PDF")
        subtitulo.setObjectName("SubtituloInicio")
        subtitulo.setAlignment(Qt.AlignmentFlag.AlignCenter)

        boton = QPushButton("Abrir PDF")
        boton.setObjectName("BotonPrincipal")
        boton.setCursor(Qt.CursorShape.PointingHandCursor)
        boton.setMinimumWidth(180)
        boton.clicked.connect(self.abrir_solicitado.emit)

        boton_unir = QPushButton("Unir PDFs")
        boton_dividir = QPushButton("Dividir PDF")
        for b in (boton_unir, boton_dividir):
            b.setObjectName("BotonSecundario")
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setMinimumWidth(110)
        boton_unir.clicked.connect(self.unir_solicitado.emit)
        boton_dividir.clicked.connect(self.dividir_solicitado.emit)
        fila_secundaria = QHBoxLayout()
        fila_secundaria.setSpacing(10)
        fila_secundaria.addStretch(1)
        fila_secundaria.addWidget(boton_unir)
        fila_secundaria.addWidget(boton_dividir)
        fila_secundaria.addStretch(1)

        self.etiqueta_recientes = QLabel("Recientes")
        self.etiqueta_recientes.setObjectName("SubtituloInicio")
        self.lista = QListWidget()
        self.lista.setObjectName("ListaRecientes")
        self.lista.setFixedWidth(ANCHO_LISTA)
        self.lista.setMaximumHeight(ALTO_MAX_LISTA)
        self.lista.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.lista.setCursor(Qt.CursorShape.PointingHandCursor)
        self.lista.itemClicked.connect(lambda item: self.abrir_reciente.emit(item.data(RUTA)))

        centro = QVBoxLayout()
        centro.setSpacing(10)
        centro.addWidget(logo)
        centro.addWidget(titulo)
        centro.addWidget(subtitulo)
        centro.addSpacing(12)
        centro.addWidget(boton, alignment=Qt.AlignmentFlag.AlignCenter)
        centro.addLayout(fila_secundaria)
        centro.addSpacing(18)
        centro.addWidget(self.etiqueta_recientes, alignment=Qt.AlignmentFlag.AlignCenter)
        centro.addWidget(self.lista, alignment=Qt.AlignmentFlag.AlignCenter)

        layout = QVBoxLayout(self)
        layout.addStretch(1)
        layout.addLayout(centro)
        layout.addStretch(2)
        self.refrescar()

    def registrar(self, ruta):
        config.agregar_reciente(ruta)

    def refrescar(self):
        self.lista.clear()
        recientes = config.recientes()
        metricas = self.lista.fontMetrics()
        ancho_texto = ANCHO_LISTA - 60  # descuenta bordes, márgenes y la barra vertical
        for ruta in recientes:
            nombre = metricas.elidedText(os.path.basename(ruta), Qt.TextElideMode.ElideMiddle, ancho_texto)
            carpeta = metricas.elidedText(os.path.dirname(ruta), Qt.TextElideMode.ElideMiddle, ancho_texto)
            item = QListWidgetItem(f"{nombre}\n{carpeta}")
            item.setData(RUTA, ruta)
            item.setToolTip(ruta)
            self.lista.addItem(item)
        self.lista.setVisible(bool(recientes))
        self.etiqueta_recientes.setText("Recientes" if recientes else "Aún no has abierto documentos")
        self._ajustar_altura()
        
    def _ajustar_altura(self):
        """Altura según las filas reales (depende de la fuente, el escalado y el tema)."""
        if self.lista.count() == 0:
            return
        alto = self.lista.sizeHintForRow(0) * self.lista.count() + 2 * self.lista.frameWidth() + 20
        self.lista.setFixedHeight(min(ALTO_MAX_LISTA, alto))

    def showEvent(self, evento):
        super().showEvent(evento)
        self._ajustar_altura()  # ya con el estilo aplicado, que cambia el alto de las filas
