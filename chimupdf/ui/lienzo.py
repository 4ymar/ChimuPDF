from PySide6.QtCore import QPoint, QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QLabel

AZUL = QColor(0, 120, 215)
MANIPULABLES = ("seleccionar", "seleccionar_imagen")  # herramientas con las que se arrastra lo seleccionado
CURSORES_ZONA = {
    "mover": Qt.CursorShape.SizeAllCursor,
    "esq_tl": Qt.CursorShape.SizeFDiagCursor,
    "esq_br": Qt.CursorShape.SizeFDiagCursor,
    "esq_tr": Qt.CursorShape.SizeBDiagCursor,
    "esq_bl": Qt.CursorShape.SizeBDiagCursor,
}
TAM_MIN = 12  # tamaño mínimo (en puntos PDF) al redimensionar


class LienzoPagina(QLabel):
    """Muestra la página y captura los gestos del mouse para anotar.

    Emite gesto(herramienta, puntos) al soltar el botón. Los puntos van en
    coordenadas visuales PDF (puntos medidos sobre la página mostrada).
    """

    gesto = Signal(str, list)
    arrastrando = Signal(str, list)  # durante el arrastre con la herramienta 'ver' (selección de texto en vivo)
    doble_clic = Signal(str, tuple)  # (herramienta, punto PDF)
    reubicado = Signal(str, tuple)  # (herramienta, nuevo rectángulo de lo seleccionado)
    puntero = Signal(tuple, QPoint)  # (punto PDF, posición global) con el mouse sin pulsar

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.zoom = 1.0
        self._herramienta = "seleccionar"
        self._trazo = []  # posiciones en píxeles del widget
        self._arrastrando = False
        self._seleccion = None  # (x0, y0, x1, y1) en puntos PDF visuales
        self._resultados = []  # coincidencias de la búsqueda, en puntos PDF visuales
        self._resultado_actual = -1
        self._modo_seleccion = None  # None, 'mover', 'ajustar' o 'proporcional': qué se puede hacer con lo seleccionado
        self._manip = None  # (zona, rect inicial, punto inicial) mientras se arrastra lo seleccionado
        self._movio = False
        self._texto_sel = []  # rects del texto seleccionado con el mouse
        self.setMouseTracking(True)

    def sizeHint(self):
        pm = self.pixmap()
        if pm and not pm.isNull():
            return pm.deviceIndependentSize().toSize()
        return super().sizeHint()

    # ---------- estado ----------
    def establecer_herramienta(self, nombre):
        self._herramienta = nombre
        self.setCursor(self._cursor_base())

    def _cursor_base(self):
        if self._herramienta == "ver":
            return Qt.CursorShape.IBeamCursor
        if self._herramienta in MANIPULABLES:
            return Qt.CursorShape.ArrowCursor
        return Qt.CursorShape.CrossCursor

    def establecer_seleccion(self, rect, modo=None):
        """modo: None (solo se ve), 'mover', 'ajustar' (tamaño libre) o 'proporcional'."""
        self._seleccion = rect
        self._modo_seleccion = modo if rect else None
        self.update()

    def establecer_texto_seleccionado(self, rects):
        self._texto_sel = list(rects)
        self.update()

    def establecer_resultados(self, rects, actual):
        """Resalta las coincidencias de la búsqueda; 'actual' es el índice de la seleccionada."""
        self._resultados = list(rects)
        self._resultado_actual = actual
        self.update()

    def a_widget(self, rect):
        """(x, y, ancho, alto) en píxeles del widget de un rect (x0, y0, x1, y1) en puntos PDF visuales."""
        origen = self._origen()
        if origen is None:
            return None
        ox, oy, _w, _h = origen
        x0, y0, x1, y1 = rect
        return ox + x0 * self.zoom, oy + y0 * self.zoom, (x1 - x0) * self.zoom, (y1 - y0) * self.zoom

    # ---------- geometría ----------
    def _origen(self):
        pm = self.pixmap()
        if pm is None or pm.isNull():
            return None
        tam = pm.deviceIndependentSize()
        return (self.width() - tam.width()) / 2.0, (self.height() - tam.height()) / 2.0, tam.width(), tam.height()

    def _a_pdf(self, pos):
        ox, oy, _w, _h = self._origen()
        return ((pos.x() - ox) / self.zoom, (pos.y() - oy) / self.zoom)

    # ---------- mouse ----------
    def mousePressEvent(self, evento):
        if evento.button() == Qt.MouseButton.RightButton and (self._arrastrando or self._manip):
            if self._manip:  # cancela el arrastre de lo seleccionado
                self._seleccion = self._manip[1]
            self._manip = None
            self._arrastrando = False
            self._trazo = []
            self.update()
            return
        origen = self._origen()
        if evento.button() != Qt.MouseButton.LeftButton or origen is None:
            return super().mousePressEvent(evento)
        zona = self._zona(evento.position())
        if zona:  # se agarró lo seleccionado: moverlo o cambiarle el tamaño
            self._manip = (zona, tuple(self._seleccion), evento.position())
            self._movio = False
            return
        ox, oy, w, h = origen
        if not QRectF(ox, oy, w, h).contains(evento.position()):
            return
        self._arrastrando = True
        self._trazo = [evento.position()]
        self.update()

    def mouseMoveEvent(self, evento):
        if self._manip is not None:
            self._arrastrar_seleccion(evento.position())
            return
        if not self._arrastrando:
            self._al_pasar(evento)
            return super().mouseMoveEvent(evento)
        if self._herramienta == "lapiz":
            self._trazo.append(evento.position())
        else:
            self._trazo = [self._trazo[0], evento.position()]
            if self._herramienta == "ver":  # selección de texto en vivo
                self.arrastrando.emit("ver", [self._a_pdf(p) for p in self._trazo])
        self.update()

    def mouseReleaseEvent(self, evento):
        if self._manip is not None:
            if evento.button() != Qt.MouseButton.LeftButton:
                return
            _zona, rect0, _punto = self._manip
            self._manip = None
            if self._movio:
                self.reubicado.emit(self._herramienta, tuple(self._seleccion))
            else:  # fue un clic sobre lo seleccionado: se trata como un clic normal
                self._seleccion = rect0
                self.gesto.emit(self._herramienta, [self._a_pdf(evento.position())])
            self.update()
            return
        if not self._arrastrando:
            return super().mouseReleaseEvent(evento)
        if evento.button() != Qt.MouseButton.LeftButton:
            return
        self._arrastrando = False
        trazo, self._trazo = self._trazo, []
        self.update()
        if self._herramienta != "lapiz":
            trazo = [trazo[0], evento.position()]
        self.gesto.emit(self._herramienta, [self._a_pdf(p) for p in trazo])

    def mouseDoubleClickEvent(self, evento):
        if evento.button() == Qt.MouseButton.LeftButton and self._origen() is not None:
            self.doble_clic.emit(self._herramienta, self._a_pdf(evento.position()))
            return
        super().mouseDoubleClickEvent(evento)

    # ---------- arrastrar lo seleccionado ----------
    def _zona(self, pos):
        """Parte de lo seleccionado bajo el cursor: una esquina, el interior ('mover') o None."""
        if not self._seleccion or not self._modo_seleccion or self._herramienta not in MANIPULABLES:
            return None
        caja = self.a_widget(self._seleccion)
        if caja is None:
            return None
        x, y, w, h = caja
        if self._modo_seleccion in ("ajustar", "proporcional"):
            esquinas = (("esq_tl", x, y), ("esq_tr", x + w, y), ("esq_bl", x, y + h), ("esq_br", x + w, y + h))
            for nombre, cx, cy in esquinas:
                if abs(pos.x() - cx) <= 7 and abs(pos.y() - cy) <= 7:
                    return nombre
        return "mover" if QRectF(x, y, w, h).contains(pos) else None

    def _al_pasar(self, evento):
        """Mouse sin pulsar: cursor según la zona y aviso para mostrar textos emergentes."""
        zona = self._zona(evento.position())
        self.setCursor(CURSORES_ZONA[zona] if zona else self._cursor_base())
        if self._origen() is not None:
            self.puntero.emit(self._a_pdf(evento.position()), evento.globalPosition().toPoint())

    def _arrastrar_seleccion(self, pos):
        zona, r0, p0 = self._manip
        if not self._movio and abs(pos.x() - p0.x()) + abs(pos.y() - p0.y()) < 4:
            return  # todavía puede ser un simple clic
        origen = self._origen()
        if origen is None:
            return
        self._movio = True
        dx = (pos.x() - p0.x()) / self.zoom
        dy = (pos.y() - p0.y()) / self.zoom
        x0, y0, x1, y1 = r0
        if zona == "mover":
            dx = min(max(dx, -x0), origen[2] / self.zoom - x1)  # sin salirse de la página
            dy = min(max(dy, -y0), origen[3] / self.zoom - y1)
            self._seleccion = (x0 + dx, y0 + dy, x1 + dx, y1 + dy)
        else:
            self._seleccion = self._redimensionar(zona, r0, dx, dy)
        self.update()

    def _redimensionar(self, zona, r0, dx, dy):
        x0, y0, x1, y1 = r0
        izquierda = zona in ("esq_tl", "esq_bl")
        arriba = zona in ("esq_tl", "esq_tr")
        if izquierda:
            x0 = min(x0 + dx, x1 - TAM_MIN)
        else:
            x1 = max(x1 + dx, x0 + TAM_MIN)
        if arriba:
            y0 = min(y0 + dy, y1 - TAM_MIN)
        else:
            y1 = max(y1 + dy, y0 + TAM_MIN)
        if self._modo_seleccion == "proporcional":
            proporcion = (r0[2] - r0[0]) / max(r0[3] - r0[1], 1e-6)
            alto = (x1 - x0) / proporcion
            if arriba:
                y0 = y1 - alto
            else:
                y1 = y0 + alto
        return (x0, y0, x1, y1)

    # ---------- dibujo ----------
    def paintEvent(self, evento):
        super().paintEvent(evento)
        origen = self._origen()
        if origen is None:
            return
        ox, oy, _w, _h = origen
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        for i, (x0, y0, x1, y1) in enumerate(self._resultados):
            r = QRectF(ox + x0 * self.zoom, oy + y0 * self.zoom, (x1 - x0) * self.zoom, (y1 - y0) * self.zoom)
            if i == self._resultado_actual:
                painter.fillRect(r, QColor(255, 140, 0, 110))
                painter.setPen(QPen(QColor(230, 110, 0), 1.5))
                painter.drawRect(r)
            else:
                painter.fillRect(r, QColor(255, 235, 0, 90))

        for x0, y0, x1, y1 in self._texto_sel:
            painter.fillRect(
                QRectF(ox + x0 * self.zoom, oy + y0 * self.zoom, (x1 - x0) * self.zoom, (y1 - y0) * self.zoom),
                QColor(0, 120, 215, 80),
            )

        if self._seleccion:
            x0, y0, x1, y1 = self._seleccion
            min_x, max_x = sorted((x0, x1))
            min_y, max_y = sorted((y0, y1))
            pen = QPen(AZUL, 1.5, Qt.PenStyle.DashLine)
            painter.setPen(pen)
            painter.drawRect(QRectF(
                ox + min_x * self.zoom - 2, oy + min_y * self.zoom - 2,
                (max_x - min_x) * self.zoom + 4, (max_y - min_y) * self.zoom + 4,
            ))
            if self._modo_seleccion in ("ajustar", "proporcional"):  # manijas en las esquinas
                painter.setPen(QPen(AZUL, 1.5))
                painter.setBrush(QColor(255, 255, 255))
                for cx, cy in ((min_x, min_y), (max_x, min_y), (min_x, max_y), (max_x, max_y)):
                    painter.drawRect(QRectF(ox + cx * self.zoom - 4, oy + cy * self.zoom - 4, 8, 8))
                painter.setBrush(Qt.BrushStyle.NoBrush)

        if self._arrastrando and len(self._trazo) >= 2 and self._herramienta != "ver":
            painter.setPen(QPen(AZUL, 1.5, Qt.PenStyle.DashLine))
            if self._herramienta == "lapiz":
                painter.setPen(QPen(AZUL, 2))
                for a, b in zip(self._trazo, self._trazo[1:]):
                    painter.drawLine(a, b)
            elif self._herramienta in (
                "rectangulo", "texto", "firma", "editar_texto", "agregar_texto",
                "borrar_zona", "insertar_imagen", "mover_imagen",
            ):
                painter.drawRect(QRectF(self._trazo[0], self._trazo[-1]).normalized())
            else:
                painter.drawLine(self._trazo[0], self._trazo[-1])
        painter.end()
