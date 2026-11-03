"""Seleccionar y copiar texto del PDF con el mouse."""
import math

from PySide6.QtCore import QObject
from PySide6.QtWidgets import QApplication

from chimupdf.nucleo import seleccion

from .comun import crear_accion


class SeleccionTexto(QObject):
    """Arrastrar sobre el texto lo selecciona (modo Ver); doble clic elige una palabra; Ctrl+C lo copia."""

    def __init__(self, ventana):
        super().__init__(ventana)
        self.v = ventana
        self.texto = ""
        self._clave_palabras = None
        self._palabras = []
        self.a_copiar = crear_accion(ventana, "&Copiar texto seleccionado", self.copiar, "Ctrl+C")
        self.a_copiar.setEnabled(False)
        for accion in ventana.menuBar().actions():
            if accion.text() == "&Ver":
                accion.menu().addAction(self.a_copiar)
        lienzo = ventana.visor.lienzo
        lienzo.arrastrando.connect(self._al_arrastrar)
        lienzo.gesto.connect(self._al_gesto)
        lienzo.doble_clic.connect(self._al_doble_clic)
        ventana.miniaturas.currentRowChanged.connect(lambda _fila: self.limpiar())

    def _pagina(self):
        doc, fila = self.v.documento, self.v.miniaturas.currentRow()
        if doc is None or fila < 0:
            return None, -1
        return doc.pagina(fila), fila

    def _palabras_de(self, pagina, fila):
        """Palabras de la página, guardadas para no extraerlas en cada movimiento del mouse."""
        doc = self.v.documento
        clave = (id(doc), doc.version, fila)
        if clave != self._clave_palabras:
            self._palabras = pagina.get_text("words")
            self._clave_palabras = clave
        return self._palabras

    def _mostrar(self, rects, texto):
        self.texto = texto
        self.v.visor.lienzo.establecer_texto_seleccionado(rects)
        self.a_copiar.setEnabled(bool(texto))

    def limpiar(self):
        self._mostrar([], "")

    def _al_arrastrar(self, herramienta, puntos):
        if herramienta != "ver":
            return
        pagina, fila = self._pagina()
        if pagina is None:
            return
        rects, texto = seleccion.texto_entre(pagina, puntos[0], puntos[-1], self._palabras_de(pagina, fila))
        self._mostrar(rects, texto)

    def _al_gesto(self, herramienta, puntos):
        if herramienta != "ver":
            return
        if math.dist(puntos[0], puntos[-1]) <= 4:  # un clic sin arrastrar quita la selección
            self.limpiar()
        else:
            self._al_arrastrar(herramienta, puntos)

    def _al_doble_clic(self, herramienta, punto):
        if herramienta != "ver":
            return
        pagina, fila = self._pagina()
        if pagina is None:
            return
        rects, texto = seleccion.palabra_en(pagina, punto, self._palabras_de(pagina, fila))
        self._mostrar(rects, texto)

    def copiar(self):
        if self.texto:
            QApplication.clipboard().setText(self.texto)
            self.v.statusBar().showMessage("Texto copiado", 4000)