from collections import OrderedDict

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import QScrollArea

from .imagenes import pixmap_de_pagina
from .lienzo import LienzoPagina
ZOOM_MIN, ZOOM_MAX, PASO_ZOOM = 0.25, 5.0, 1.25
PRESUPUESTO_CACHE = 150 * 1024 * 1024  # bytes de píxeles que se guardan de páginas ya dibujadas


class VisorPagina(QScrollArea):
    """Muestra una página del documento con zoom."""

    zoom_cambiado = Signal(float)
    pagina_anterior = Signal()   # Re Pág estando arriba del todo
    pagina_siguiente = Signal()  # Av Pág estando abajo del todo

    def __init__(self, parent=None):
        super().__init__(parent)
        self._documento = None
        self._indice = -1
        self._zoom = 1.25
        self._al_final = False  # al llegar con Re Pág, la página nueva se muestra desde abajo
        self._cache = OrderedDict()  # páginas ya dibujadas
        self._bytes_cache = 0
        self._etiqueta = LienzoPagina()
        self._etiqueta.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setWidget(self._etiqueta)
        self.setWidgetResizable(True)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)

    @property
    def zoom(self):
        return self._zoom
    
    @property
    def lienzo(self):
        return self._etiqueta

    def mostrar(self, documento, indice):
        cambio = documento is not self._documento or indice != self._indice
        self._documento = documento
        self._indice = indice
        self._dibujar()
        if cambio:  # página distinta: vuelve arriba (o abajo si se llegó con Re Pág)
            barra = self.verticalScrollBar()
            if self._al_final:
                QTimer.singleShot(0, lambda: barra.setValue(barra.maximum()))
            else:
                barra.setValue(0)

    def refrescar(self):
        """Algo cambió en el documento: se descarta lo guardado y se vuelve a dibujar."""
        self._vaciar_cache()
        self._dibujar()

    def limpiar(self):
        self._documento = None
        self._indice = -1
        self._vaciar_cache()
        self._etiqueta.clear()

    def _dibujar(self):
        doc = self._documento
        if doc is None or not 0 <= self._indice < doc.num_paginas:
            self._etiqueta.clear()
            return
        self._etiqueta.zoom = self._zoom
        self._etiqueta.setPixmap(self._pixmap(doc, self._indice))

    def _pixmap(self, doc, indice):
        """Imagen de la página; si ya se dibujó con este zoom y esta versión del documento, se reutiliza."""
        dpr = self.devicePixelRatioF()
        clave = (id(doc), doc.version, indice, round(self._zoom, 4), dpr)
        pixmap = self._cache.get(clave)
        if pixmap is not None:
            self._cache.move_to_end(clave)
            return pixmap
        pixmap = pixmap_de_pagina(doc, indice, self._zoom, dpr)
        self._cache[clave] = pixmap
        self._bytes_cache += pixmap.width() * pixmap.height() * 4
        while self._bytes_cache > PRESUPUESTO_CACHE and len(self._cache) > 1:
            _clave, viejo = self._cache.popitem(last=False)
            self._bytes_cache -= viejo.width() * viejo.height() * 4
        return pixmap

    def _vaciar_cache(self):
        self._cache.clear()
        self._bytes_cache = 0

    def _fijar_zoom(self, zoom):
        zoom = max(ZOOM_MIN, min(ZOOM_MAX, zoom))
        if abs(zoom - self._zoom) < 1e-6:
            return
        vista, contenido = self.viewport(), self.widget()
        fx = (self.horizontalScrollBar().value() + vista.width() / 2) / max(1, contenido.width())
        fy = (self.verticalScrollBar().value() + vista.height() / 2) / max(1, contenido.height())
        self._zoom = zoom
        self._dibujar()
        self.zoom_cambiado.emit(zoom)
        QTimer.singleShot(0, lambda: self._restaurar_centro(fx, fy))

    def _restaurar_centro(self, fx, fy):
        """Tras el zoom, deja en el centro de la vista lo mismo que se veía antes."""
        vista, contenido = self.viewport(), self.widget()
        self.horizontalScrollBar().setValue(int(fx * contenido.width() - vista.width() / 2))
        self.verticalScrollBar().setValue(int(fy * contenido.height() - vista.height() / 2))

    def acercar(self):
        self._fijar_zoom(self._zoom * PASO_ZOOM)

    def alejar(self):
        self._fijar_zoom(self._zoom / PASO_ZOOM)

    def tamano_real(self):
        self._fijar_zoom(1.0)

    def ajustar_ancho(self):
        doc = self._documento
        if doc is None or not 0 <= self._indice < doc.num_paginas:
            return
        ancho = doc.ancho_pagina(self._indice)
        if ancho <= 0:
            return
        disponible = max(10, self.viewport().width() - 20)
        self._fijar_zoom(disponible / ancho)

    def wheelEvent(self, evento):
        if evento.modifiers() & Qt.KeyboardModifier.ControlModifier:
            delta_y = evento.angleDelta().y()
            if delta_y > 0:
                self.acercar()
                evento.accept()
            elif delta_y < 0:
                self.alejar()
                evento.accept()
        else:
            super().wheelEvent(evento)
    
    def keyPressEvent(self, evento):
        barra = self.verticalScrollBar()
        tecla = evento.key()
        if tecla == Qt.Key.Key_PageDown and barra.value() >= barra.maximum():
            self.pagina_siguiente.emit()
        elif tecla == Qt.Key.Key_PageUp and barra.value() <= barra.minimum():
            self._al_final = True
            self.pagina_anterior.emit()
            self._al_final = False
        else:
            super().keyPressEvent(evento)
