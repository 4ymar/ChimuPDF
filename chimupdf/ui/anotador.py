import math
import os
import tempfile

from PySide6.QtCore import QObject
from PySide6.QtGui import QAction, QActionGroup, QColor, QImage, QTransform
from PySide6.QtWidgets import QColorDialog, QInputDialog, QMessageBox, QToolTip

from chimupdf.nucleo import anotaciones as anot
from chimupdf.nucleo.firma import hay_firma, ruta_firma

from .comun import NOMBRE_APP, Boton, crear_accion
from .dialogo_firma import DialogoFirma
from .dialogo_nota import DialogoNota

# (clave, texto de la acción)
HERRAMIENTAS = [
    ("seleccionar", "Seleccionar"),
    ("resaltar", "Resaltar texto"),
    ("subrayar", "Subrayar texto"),
    ("tachar", "Tachar texto"),
    ("nota", "Nota"),
    ("texto", "Texto libre"),
    ("rectangulo", "Rectángulo"),
    ("flecha", "Flecha"),
    ("lapiz", "Lápiz"),
    ("firma", "Firma"),
]


class Anotador(QObject):
    """Barra, menú y lógica para anotar y firmar el documento abierto."""

    def __init__(self, ventana):
        super().__init__(ventana)
        self.v = ventana
        self.color = None  # None = color predeterminado de cada herramienta
        self._xref = None  # anotación seleccionada en la página actual
        self._doc_visto = None
        self._crear_acciones()
        self._crear_menu_y_barra()
        self._xref_tip = None  # anotación sobre la que se mostró el texto emergente
        self.v.visor.lienzo.gesto.connect(self._al_gesto)
        self.v.visor.lienzo.reubicado.connect(self._al_reubicar)
        self.v.visor.lienzo.doble_clic.connect(self._al_doble_clic)
        self.v.visor.lienzo.puntero.connect(self._al_pasar)
        self.v.miniaturas.currentRowChanged.connect(lambda _fila: self.limpiar_seleccion())

    # ---------- interfaz ----------
    def _crear_acciones(self):
        self.grupo = QActionGroup(self.v)
        self.acciones_herramienta = {}
        for clave, texto in HERRAMIENTAS:
            accion = QAction(texto, self.v)
            accion.setCheckable(True)
            accion.setData(clave)
            self.grupo.addAction(accion)
            self.acciones_herramienta[clave] = accion
        self.acciones_herramienta["seleccionar"].setChecked(True)
        self.grupo.triggered.connect(self._cambiar_herramienta)

        self.a_color = crear_accion(self.v, "&Color...", self._elegir_color)
        self.a_color_auto = crear_accion(self.v, "Colores &predeterminados", self._color_automatico)
        self.a_firma = crear_accion(self.v, "&Mi firma...", self.crear_firma)
        self.a_borrar = crear_accion(self.v, "&Borrar anotación seleccionada", self.borrar_seleccion)
        self.a_incrustar = crear_accion(self.v, "&Incrustar anotaciones...", self._incrustar)

        self._acciones_documento = list(self.acciones_herramienta.values()) + [
            self.a_color, self.a_color_auto, self.a_borrar, self.a_incrustar,
        ]

    def _crear_menu_y_barra(self):
        menu = self.v.menuBar().addMenu("&Anotar")
        menu.addActions(list(self.acciones_herramienta.values()))
        menu.addSeparator()
        menu.addActions([self.a_color, self.a_color_auto, self.a_firma])
        menu.addSeparator()
        menu.addActions([self.a_borrar, self.a_incrustar])

    def actualizar_estado(self):
        doc = self.v.documento
        for accion in self._acciones_documento:
            accion.setEnabled(doc is not None)
        if doc is not self._doc_visto:
            self._doc_visto = doc
            self.limpiar_seleccion()
            self.acciones_herramienta["seleccionar"].setChecked(True)
            self.v.visor.lienzo.establecer_herramienta("seleccionar")

    def _cambiar_herramienta(self, accion):
        self.limpiar_seleccion()
        self.v.visor.lienzo.establecer_herramienta(accion.data())

    # ---------- color ----------
    def _elegir_color(self):
        inicial = QColor.fromRgbF(*self.color) if self.color else QColor(255, 0, 0)
        elegido = QColorDialog.getColor(inicial, self.v, "Color de las anotaciones")
        if elegido.isValid():
            self.color = (elegido.redF(), elegido.greenF(), elegido.blueF())

    def _color_automatico(self):
        self.color = None

    # ---------- selección ----------
    def limpiar_seleccion(self):
        self._xref = None
        self._xref_tip = None
        self.v.visor.lienzo.establecer_seleccion(None)

    def _seleccionar_xref(self, pagina, xref):
        """Selecciona la anotación y muestra su recuadro (con manijas si se puede mover o redimensionar)."""
        self._xref = xref
        self.v.visor.lienzo.establecer_seleccion(
            anot.rect_visual(pagina, xref), anot.capacidad(pagina, xref)
        )

    def _seleccionar(self, pagina, punto):
        xref = anot.anotacion_en(pagina, punto)
        if xref is None:
            self._xref = None
            self.v.visor.lienzo.establecer_seleccion(None)
            self.v.statusBar().clearMessage()
            return
        self._seleccionar_xref(pagina, xref)
        pistas = {
            "mover": "Arrástralo para moverlo. ",
            "ajustar": "Arrástralo para moverlo o tira de una esquina para cambiar su tamaño. ",
            "proporcional": "Arrástralo para moverlo o tira de una esquina para cambiar su tamaño. ",
        }
        pista = pistas.get(anot.capacidad(pagina, xref), "")
        if anot.contenido(pagina, xref) is not None:
            pista += "Doble clic para leerlo o editarlo. "
        self.v.statusBar().showMessage(
            f"{anot.nombre_tipo(pagina, xref)} seleccionado. {pista}Supr lo borra.", 8000
        )

    def _al_reubicar(self, herramienta, rect):
        """Se arrastró lo seleccionado para moverlo o cambiarle el tamaño."""
        doc, fila = self.v.documento, self.v.miniaturas.currentRow()
        if herramienta != "seleccionar" or self._xref is None or doc is None or fila < 0:
            return
        xref = self._xref
        try:
            if anot.reubicar(doc.pagina(fila), xref, rect):
                self.v.tras_cambio(fila)
        except Exception as error:
            QMessageBox.critical(self.v, NOMBRE_APP, f"No se pudo mover la anotación:\n{error}")
        self._seleccionar_xref(doc.pagina(fila), xref)  # recuadro final (o el anterior si no se pudo)

    def _al_doble_clic(self, herramienta, punto):
        """Doble clic sobre una nota o un texto libre: leerlo y editarlo."""
        doc, fila = self.v.documento, self.v.miniaturas.currentRow()
        if herramienta != "seleccionar" or doc is None or fila < 0:
            return
        pagina = doc.pagina(fila)
        xref = anot.anotacion_en(pagina, punto)
        if xref is None or anot.contenido(pagina, xref) is None:
            return
        self._seleccionar_xref(pagina, xref)
        self._editar_contenido(doc, fila, xref)

    def _editar_contenido(self, doc, fila, xref):
        pagina = doc.pagina(fila)
        actual = anot.contenido(pagina, xref) or ""
        dialogo = DialogoNota(self.v, anot.nombre_tipo(pagina, xref), actual)
        if not dialogo.exec():
            return
        nuevo = dialogo.texto.strip()
        try:
            if dialogo.eliminar:
                anot.borrar(pagina, xref)
                self.limpiar_seleccion()
            elif not nuevo:
                QMessageBox.information(self.v, NOMBRE_APP, "Escribe un texto o usa «Eliminar».")
                return
            elif nuevo == actual:
                return
            else:
                anot.cambiar_contenido(pagina, xref, nuevo)
        except Exception as error:
            QMessageBox.critical(self.v, NOMBRE_APP, f"No se pudo guardar el cambio:\n{error}")
            return
        self.v.tras_cambio(fila)
        if not dialogo.eliminar:
            self._seleccionar_xref(doc.pagina(fila), xref)

    def _al_pasar(self, punto, posicion):
        """Mouse sobre una nota o un texto libre: muestra su contenido (también en modo Ver)."""
        doc, fila = self.v.documento, self.v.miniaturas.currentRow()
        if doc is None or fila < 0:
            return
        pagina = doc.pagina(fila)
        xref = anot.anotacion_en(pagina, punto, 1)
        if xref == self._xref_tip:
            return
        self._xref_tip = xref
        texto = anot.contenido(pagina, xref) if xref else None
        if texto:
            QToolTip.showText(posicion, texto, self.v.visor.lienzo)
        else:
            QToolTip.hideText()

    def borrar_seleccion(self):
        """Borra la anotación seleccionada. Devuelve True si había una seleccionada."""
        doc, fila = self.v.documento, self.v.miniaturas.currentRow()
        if doc is None or fila < 0 or self._xref is None:
            return False
        r = QMessageBox.question(self.v, "Borrar anotación", "¿Borrar la anotación seleccionada?")
        if r == Boton.Yes:
            anot.borrar(doc.pagina(fila), self._xref)
            self.limpiar_seleccion()
            self.v.tras_cambio(fila)
        return True

    # ---------- firma ----------
    def crear_firma(self):
        return DialogoFirma(self.v).exec()

    # ---------- gestos ----------
    def _al_gesto(self, herramienta, puntos):
        doc, fila = self.v.documento, self.v.miniaturas.currentRow()
        if doc is None or fila < 0:
            return
        if herramienta not in self.acciones_herramienta:
            return  # herramientas de otros módulos (editor)
        pagina = doc.pagina(fila)
        p1, p2 = puntos[0], puntos[-1]
        arrastre = math.dist(p1, p2) > 4
        nuevo_xref = None
        try:
            if herramienta == "seleccionar":
                self._seleccionar(pagina, p1)
                return
            if herramienta in ("resaltar", "subrayar", "tachar", "rectangulo", "flecha") and not arrastre:
                self.v.statusBar().showMessage("Arrastra el mouse para usar esta herramienta.", 4000)
                return
            if herramienta in ("resaltar", "subrayar", "tachar"):
                anot.marcar_texto(pagina, herramienta, p1, p2, self.color)
            elif herramienta == "nota":
                texto, ok = QInputDialog.getMultiLineText(self.v, "Nota", "Escribe la nota:")
                if not ok or not texto.strip():
                    return
                anot.nota(pagina, p1, texto, self.color)
            elif herramienta == "texto":
                texto, ok = QInputDialog.getMultiLineText(self.v, "Texto libre", "Escribe el texto:")
                if not ok or not texto.strip():
                    return
                anot.texto_libre(pagina, p1, p2, texto, self.color)
            elif herramienta == "rectangulo":
                anot.rectangulo(pagina, p1, p2, self.color)
            elif herramienta == "flecha":
                anot.flecha(pagina, p1, p2, self.color)
            elif herramienta == "lapiz":
                anot.lapiz(pagina, puntos, self.color)
            elif herramienta == "firma":
                if not hay_firma():
                    if not self.crear_firma() or not hay_firma():
                        return
                nuevo_xref = self._colocar_firma(pagina, p1, p2)
        except ValueError as error:
            QMessageBox.information(self.v, NOMBRE_APP, str(error))
            return
        except Exception as error:
            QMessageBox.critical(self.v, NOMBRE_APP, f"No se pudo agregar la anotación:\n{error}")
            return
        self.v.tras_cambio(fila)
        if nuevo_xref:  # lo recién colocado queda seleccionado para ajustarlo de inmediato
            self.acciones_herramienta["seleccionar"].trigger()
            self._seleccionar_xref(doc.pagina(fila), nuevo_xref)

    def _colocar_firma(self, pagina, p1, p2):
        """En páginas rotadas gira la imagen para que la firma se vea derecha."""
        if pagina.rotation == 0:
            return anot.firma(pagina, ruta_firma(), p1, p2).xref
        imagen = QImage(ruta_firma()).transformed(QTransform().rotate(-pagina.rotation))
        fd, temporal = tempfile.mkstemp(suffix=".png")
        os.close(fd)
        try:
            imagen.save(temporal, "PNG")
            return anot.firma(pagina, ruta_firma(), p1, p2, ruta_estampa=temporal).xref
        finally:
            os.remove(temporal)

    # ---------- incrustar ----------
    def _incrustar(self):
        doc = self.v.documento
        if doc is None:
            return
        r = QMessageBox.question(
            self.v, "Incrustar anotaciones",
            "Las anotaciones pasarán a ser parte fija de las páginas y ya no se podrán "
            "editar ni borrar.\n\n¿Incrustarlas en todo el documento?",
        )
        if r != Boton.Yes:
            return
        try:
            doc.incrustar_anotaciones()
        except Exception as error:
            QMessageBox.critical(self.v, NOMBRE_APP, f"No se pudieron incrustar:\n{error}")
            return
        self.limpiar_seleccion()
        doc.registrar_estado()
        self.v.miniaturas.invalidar(doc)
        self.v.visor.refrescar()
        self.v.actualizar_estado()
