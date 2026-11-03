from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtGui import QColor, QImage, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from chimupdf.nucleo.firma import asegurar_carpeta, hay_firma, ruta_firma


def quitar_fondo_blanco(imagen):
    """Hace transparente el fondo claro de una imagen (útil para fotos de firmas)."""
    if imagen.width() > 800:
        imagen = imagen.scaledToWidth(800, Qt.TransformationMode.SmoothTransformation)
    imagen = imagen.convertToFormat(QImage.Format.Format_ARGB32)
    ancho, alto, paso = imagen.width(), imagen.height(), imagen.bytesPerLine()
    datos = bytearray(imagen.constBits())
    for y in range(alto):
        fila = y * paso
        for x in range(ancho):
            i = fila + x * 4  # orden en memoria: B, G, R, A
            minimo = min(datos[i], datos[i + 1], datos[i + 2])
            if minimo >= 230:
                datos[i + 3] = 0
            elif minimo > 180:
                datos[i + 3] = (230 - minimo) * 255 // 50
    return QImage(bytes(datos), ancho, alto, paso, QImage.Format.Format_ARGB32).copy()


class LienzoFirma(QWidget):
    """Área para dibujar la firma con el mouse."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(560, 220)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self._imagen = QImage(self.size(), QImage.Format.Format_ARGB32)
        self._imagen.fill(Qt.GlobalColor.transparent)
        self._ultimo = None
        self._caja = None

    def limpiar(self):
        self._imagen.fill(Qt.GlobalColor.transparent)
        self._caja = None
        self.update()

    def hay_trazos(self):
        return self._caja is not None

    def imagen_recortada(self):
        caja = self._caja.adjusted(-8, -8, 8, 8).intersected(self._imagen.rect())
        return self._imagen.copy(caja)

    def _extender_caja(self, pos):
        punto = QRect(pos.x() - 3, pos.y() - 3, 7, 7)
        self._caja = punto if self._caja is None else self._caja.united(punto)

    def _dibujar(self, a, b):
        painter = QPainter(self._imagen)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor(0, 0, 0), 3, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        painter.drawLine(a, b)
        painter.end()

    def mousePressEvent(self, evento):
        if evento.button() == Qt.MouseButton.LeftButton:
            self._ultimo = evento.position().toPoint()
            self._dibujar(self._ultimo, self._ultimo)
            self._extender_caja(self._ultimo)
            self.update()

    def mouseMoveEvent(self, evento):
        if self._ultimo is not None:
            actual = evento.position().toPoint()
            self._dibujar(self._ultimo, actual)
            self._extender_caja(actual)
            self._ultimo = actual
            self.update()

    def mouseReleaseEvent(self, evento):
        self._ultimo = None

    def paintEvent(self, evento):
        painter = QPainter(self)
        painter.fillRect(self.rect(), Qt.GlobalColor.white)
        painter.setPen(QPen(QColor(200, 200, 200), 1, Qt.PenStyle.DashLine))
        painter.drawLine(20, self.height() - 50, self.width() - 20, self.height() - 50)
        painter.drawImage(0, 0, self._imagen)
        painter.setPen(QColor(120, 120, 120))
        painter.drawRect(self.rect().adjusted(0, 0, -1, -1))
        painter.end()


class DialogoFirma(QDialog):
    """Crea la firma (dibujada o desde una imagen) y la guarda para reutilizarla."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Mi firma")
        self._imagen_cargada = None

        # Pestaña: dibujar
        self.lienzo = LienzoFirma()
        b_limpiar = QPushButton("Limpiar")
        b_limpiar.clicked.connect(self.lienzo.limpiar)
        pestana_dibujar = QWidget()
        lay = QVBoxLayout(pestana_dibujar)
        lay.addWidget(QLabel("Dibuja tu firma con el mouse:"))
        lay.addWidget(self.lienzo)
        lay.addWidget(b_limpiar, alignment=Qt.AlignmentFlag.AlignLeft)

        # Pestaña: cargar imagen
        b_elegir = QPushButton("Elegir imagen...")
        b_elegir.clicked.connect(self._elegir_imagen)
        self.vista = QLabel("Aún no has elegido una imagen")
        self.vista.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.vista.setMinimumHeight(220)
        self.vista.setStyleSheet("background: white; border: 1px solid #888;")
        self.quitar_fondo = QCheckBox("Quitar el fondo blanco")
        self.quitar_fondo.setChecked(True)
        self.quitar_fondo.toggled.connect(self._actualizar_vista)
        pestana_imagen = QWidget()
        lay = QVBoxLayout(pestana_imagen)
        lay.addWidget(b_elegir, alignment=Qt.AlignmentFlag.AlignLeft)
        lay.addWidget(self.vista)
        lay.addWidget(self.quitar_fondo)

        self.pestanas = QTabWidget()
        self.pestanas.addTab(pestana_dibujar, "Dibujar")
        self.pestanas.addTab(pestana_imagen, "Cargar imagen")

        botones = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        botones.button(QDialogButtonBox.StandardButton.Ok).setText("Guardar firma")
        botones.button(QDialogButtonBox.StandardButton.Cancel).setText("Cancelar")
        botones.accepted.connect(self.accept)
        botones.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        if hay_firma():
            layout.addWidget(QLabel("Ya tienes una firma guardada; al guardar se reemplazará."))
        layout.addWidget(self.pestanas)
        layout.addWidget(botones)

    def _elegir_imagen(self):
        ruta, _ = QFileDialog.getOpenFileName(
            self, "Elegir imagen de la firma", "", "Imágenes (*.png *.jpg *.jpeg *.bmp)"
        )
        if not ruta:
            return
        imagen = QImage(ruta)
        if imagen.isNull():
            QMessageBox.warning(self, "Mi firma", "No se pudo leer esa imagen.")
            return
        self._imagen_cargada = imagen
        self._actualizar_vista()

    def _imagen_final_cargada(self):
        imagen = self._imagen_cargada
        if self.quitar_fondo.isChecked():
            return quitar_fondo_blanco(imagen)
        return imagen

    def _actualizar_vista(self):
        if self._imagen_cargada is None:
            return
        imagen = self._imagen_final_cargada()
        self.vista.setPixmap(QPixmap.fromImage(imagen).scaled(
            self.vista.width() - 10, self.vista.height() - 10,
            Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation,
        ))

    def accept(self):
        if self.pestanas.currentIndex() == 0:
            if not self.lienzo.hay_trazos():
                QMessageBox.warning(self, "Mi firma", "Dibuja tu firma primero.")
                return
            imagen = self.lienzo.imagen_recortada()
        else:
            if self._imagen_cargada is None:
                QMessageBox.warning(self, "Mi firma", "Elige una imagen primero.")
                return
            imagen = self._imagen_final_cargada()
        try:
            asegurar_carpeta()
            if not imagen.save(ruta_firma(), "PNG"):
                raise OSError("No se pudo escribir el archivo de la firma.")
        except OSError as error:
            QMessageBox.critical(self, "Mi firma", f"No se pudo guardar la firma:\n{error}")
            return
        super().accept()
