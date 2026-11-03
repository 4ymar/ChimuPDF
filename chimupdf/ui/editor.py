import math

from PySide6.QtCore import QObject
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QFileDialog, QMessageBox

from chimupdf.nucleo import edicion

from .comun import NOMBRE_APP, Boton, crear_accion
from .dialogo_texto import DialogoBuscarReemplazar, DialogoRelleno, DialogoTexto

FILTRO_IMAGENES = "Imágenes (*.png *.jpg *.jpeg *.bmp *.gif *.tif *.tiff)"

HERRAMIENTAS = [
    ("editar_texto", "Editar texto"),
    ("agregar_texto", "Agregar texto"),
    ("borrar_zona", "Borrar/tapar"),
    ("insertar_imagen", "Insertar imagen"),
    ("seleccionar_imagen", "Seleccionar y mover imagen"),
]


class Editor(QObject):
    """Edición de texto e imágenes dentro de las páginas. Los cambios son definitivos en el documento."""

    def __init__(self, ventana):
        super().__init__(ventana)
        self.v = ventana
        self._img = None  # (xref, bbox, rotación) de la imagen seleccionada
        self._ultimo_estilo = None
        self._crear_acciones()
        self._crear_menu_y_barra()
        self.v.visor.lienzo.gesto.connect(self._al_gesto)
        self.v.visor.lienzo.reubicado.connect(self._al_reubicar)
        self.v.anotador.grupo.triggered.connect(self._al_cambiar_herramienta)
        self.v.miniaturas.currentRowChanged.connect(lambda _fila: self.limpiar_imagen())

    # ---------- interfaz ----------
    def _crear_acciones(self):
        self.herramientas = {}
        for clave, texto in HERRAMIENTAS:
            accion = QAction(texto, self.v)
            accion.setCheckable(True)
            accion.setData(clave)
            self.v.anotador.grupo.addAction(accion)  # comparte el grupo exclusivo de herramientas
            self.herramientas[clave] = accion
        self.a_buscar = crear_accion(self.v, "&Buscar y reemplazar...", self.buscar_reemplazar, "Ctrl+H")
        self.a_reemplazar_img = crear_accion(self.v, "&Reemplazar imagen seleccionada...", self.reemplazar_imagen)
        self.a_eliminar_img = crear_accion(self.v, "&Eliminar imagen seleccionada", self.eliminar_imagen)
        self._acciones = list(self.herramientas.values()) + [
            self.a_buscar, self.a_reemplazar_img, self.a_eliminar_img,
        ]

    def _crear_menu_y_barra(self):
        menu = self.v.menuBar().addMenu("&Editar")
        menu.addActions([self.v.a_deshacer, self.v.a_rehacer])
        menu.addSeparator()
        menu.addActions([self.herramientas[c] for c in ("editar_texto", "agregar_texto", "borrar_zona")])
        menu.addAction(self.a_buscar)
        menu.addSeparator()
        menu.addActions([self.herramientas[c] for c in ("insertar_imagen", "seleccionar_imagen")])
        menu.addActions([self.a_reemplazar_img, self.a_eliminar_img])

    def actualizar_estado(self):
        for accion in self._acciones:
            accion.setEnabled(self.v.documento is not None)

    # ---------- imagen seleccionada ----------
    def limpiar_imagen(self):
        self._img = None
        self.v.visor.lienzo.establecer_seleccion(None)

    def _al_cambiar_herramienta(self, accion):
        clave = accion.data()
        if clave == "seleccionar_imagen" and self._img:
            doc, fila = self.v.documento, self.v.miniaturas.currentRow()
            rect = edicion.rect_visual_de(doc.pagina(fila), self._img[1])
            self.v.visor.lienzo.establecer_seleccion(rect, "proporcional")
        else:
            self.limpiar_imagen()

    def _pedir_imagen_seleccionada(self):
        if self._img is None:
            QMessageBox.information(
                self.v, NOMBRE_APP,
                "Primero selecciona una imagen: elige «Seleccionar imagen» y haz clic sobre ella.",
            )
        return self._img

    def borrar_seleccion(self):
        """Borra la imagen seleccionada si hay una. Devuelve True si había una seleccionada."""
        if self._img is None:
            return False
        self.eliminar_imagen()
        return True

    # ---------- gestos ----------
    def _al_gesto(self, herramienta, puntos):
        if herramienta not in self.herramientas:
            return
        doc, fila = self.v.documento, self.v.miniaturas.currentRow()
        if doc is None or fila < 0:
            return
        pagina = doc.pagina(fila)
        p1, p2 = puntos[0], puntos[-1]
        arrastre = math.dist(p1, p2) > 4
        pasar_a_seleccion = False
        try:
            if herramienta in ("editar_texto", "borrar_zona") and not arrastre:
                self.v.statusBar().showMessage("Arrastra el mouse para elegir la zona.", 4000)
                return
            if herramienta == "editar_texto":
                _rect, zona = edicion.zona_en(pagina, p1, p2)
                dialogo = DialogoTexto(self.v, "Editar texto", "reemplazar", zona)
                if not dialogo.exec():
                    return
                edicion.reemplazar_texto_zona(
                    pagina, p1, p2, dialogo.texto, dialogo.estilo, zona.rotacion, dialogo.tapar_fondo
                )
                self._ultimo_estilo = dialogo.estilo
            elif herramienta == "agregar_texto":
                dialogo = DialogoTexto(self.v, "Agregar texto", "agregar", None, self._ultimo_estilo)
                if not dialogo.exec():
                    return
                edicion.agregar_texto(pagina, p1, p2, dialogo.texto, dialogo.estilo)
                self._ultimo_estilo = dialogo.estilo
            elif herramienta == "borrar_zona":
                dialogo = DialogoRelleno(self.v)
                if not dialogo.exec():
                    return
                edicion.borrar_zona(pagina, p1, p2, dialogo.color)
            elif herramienta == "insertar_imagen":
                ruta, _ = QFileDialog.getOpenFileName(self.v, "Insertar imagen", "", FILTRO_IMAGENES)
                if not ruta:
                    return
                self._img = edicion.insertar_imagen(pagina, ruta, p1, p2)
                pasar_a_seleccion = self._img is not None
            elif herramienta == "seleccionar_imagen":
                self._img = edicion.imagen_en(pagina, p1)
                if self._img is None:
                    self.v.visor.lienzo.establecer_seleccion(None)
                    self.v.statusBar().showMessage("No hay ninguna imagen en ese punto.", 4000)
                else:
                    self.v.visor.lienzo.establecer_seleccion(
                        edicion.rect_visual_de(pagina, self._img[1]), "proporcional"
                    )
                    self.v.statusBar().showMessage(
                        "Imagen seleccionada. Arrástrala para moverla o tira de una esquina para cambiar su tamaño.",
                        8000,
                    )
                return
        except ValueError as error:
            QMessageBox.information(self.v, NOMBRE_APP, str(error))
            return
        except Exception as error:
            self._tras_cambio(fila)  # pudo quedar a medias (p. ej. borró pero no reinsertó): se refresca
            QMessageBox.critical(self.v, NOMBRE_APP, f"No se pudo aplicar el cambio:\n{error}")
            return
        self._tras_cambio(fila)
        if pasar_a_seleccion:  # la imagen recién insertada queda seleccionada para ajustarla de inmediato
            self.herramientas["seleccionar_imagen"].trigger()

    def _tras_cambio(self, fila):
        self.v.anotador.limpiar_seleccion()
        self.v.tras_cambio(fila)
        if self._img:
            doc = self.v.documento
            self.v.visor.lienzo.establecer_seleccion(
                edicion.rect_visual_de(doc.pagina(fila), self._img[1]), "proporcional"
            )

    def _al_reubicar(self, herramienta, rect):
        """Se arrastró la imagen seleccionada (para moverla o cambiarle el tamaño)."""
        doc, fila = self.v.documento, self.v.miniaturas.currentRow()
        if herramienta != "seleccionar_imagen" or self._img is None or doc is None or fila < 0:
            return
        pagina = doc.pagina(fila)
        xref, bbox, rotacion = self._img
        x0, y0, x1, y1 = rect
        try:
            self._img = edicion.mover_imagen(pagina, xref, bbox, rotacion, (x0, y0), (x1, y1))
        except ValueError as error:  # p. ej. la imagen se repite en el documento
            QMessageBox.information(self.v, NOMBRE_APP, str(error))
            self.v.visor.lienzo.establecer_seleccion(edicion.rect_visual_de(pagina, bbox), "proporcional")
            return
        except Exception as error:
            self._tras_cambio(fila)  # pudo quedar a medias
            QMessageBox.critical(self.v, NOMBRE_APP, f"No se pudo mover la imagen:\n{error}")
            return
        self._tras_cambio(fila)
        
    def _refrescar_todo(self):
        """Vuelve a dibujar miniaturas y visor (tras un cambio que pudo tocar varias páginas)."""
        doc = self.v.documento
        doc.registrar_estado()
        self.v.miniaturas.invalidar(doc)
        self.v.visor.refrescar()
        self.v.actualizar_estado()    

    # ---------- acciones del menú ----------
    def reemplazar_imagen(self):
        doc, fila = self.v.documento, self.v.miniaturas.currentRow()
        if doc is None or fila < 0 or not self._pedir_imagen_seleccionada():
            return
        ruta, _ = QFileDialog.getOpenFileName(self.v, "Imagen de reemplazo", "", FILTRO_IMAGENES)
        if not ruta:
            return
        try:
            edicion.reemplazar_imagen(doc.pagina(fila), self._img[0], self._img[1], ruta)
        except ValueError as error:
            QMessageBox.information(self.v, NOMBRE_APP, str(error))
            return
        except Exception as error:
            QMessageBox.critical(self.v, NOMBRE_APP, f"No se pudo reemplazar la imagen:\n{error}")
            return
        
            edicion.reemplazar_imagen(doc.pagina(fila), self._img[1], ruta)
        except Exception as error:
            self._tras_cambio(fila)
            QMessageBox.critical(self.v, NOMBRE_APP, f"No se pudo reemplazar la imagen:\n{error}")
            return
        self.limpiar_imagen()
        self._tras_cambio(fila)

    def eliminar_imagen(self):
        doc, fila = self.v.documento, self.v.miniaturas.currentRow()
        if doc is None or fila < 0 or not self._pedir_imagen_seleccionada():
            return
        if QMessageBox.question(self.v, "Eliminar imagen", "¿Eliminar la imagen seleccionada?") != Boton.Yes:
            return
        try:
            edicion.eliminar_imagen(doc.pagina(fila), self._img[0], self._img[1])
        except ValueError as error:
            QMessageBox.information(self.v, NOMBRE_APP, str(error))
            return
        except Exception as error:
            QMessageBox.critical(self.v, NOMBRE_APP, f"No se pudo eliminar la imagen:\n{error}")
            return
            edicion.eliminar_imagen(doc.pagina(fila), self._img[1])
        except Exception as error:
            self._tras_cambio(fila)
            QMessageBox.critical(self.v, NOMBRE_APP, f"No se pudo eliminar la imagen:\n{error}")
            return
        self.limpiar_imagen()
        self._tras_cambio(fila)

    def buscar_reemplazar(self):
        doc = self.v.documento
        if doc is None:
            return
        dialogo = DialogoBuscarReemplazar(self.v)
        if not dialogo.exec():
            return
        encontrados = edicion.buscar_en_documento(doc, dialogo.buscar)
        total = sum(len(r) for r in encontrados.values())
        if total == 0:
            QMessageBox.information(
                self.v, "Buscar y reemplazar",
                "No se encontraron coincidencias.\nSi el documento es un escaneo, haz antes el OCR.",
            )
            return
        r = QMessageBox.question(
            self.v, "Buscar y reemplazar",
            f"Se encontraron {total} coincidencias en {len(encontrados)} páginas.\n"
            f"¿Reemplazarlas por «{dialogo.nuevo}»?",
        )
        if r != Boton.Yes:
            return
        try:
            hechos, paginas = edicion.reemplazar_todo(
                doc, dialogo.buscar, dialogo.nuevo, dialogo.estilo, dialogo.ajustar
            )
        except Exception as error:
            # Pudo quedar a medias: algunas páginas ya cambiaron, así que se refresca todo
            doc.modificado = True
            self._refrescar_todo()
            QMessageBox.critical(
                self.v, NOMBRE_APP,
                f"No se pudo completar el reemplazo:\n{error}\n\n"
                "Algunas páginas pueden haber cambiado. Si no quieres conservar esos cambios, "
                "cierra el documento sin guardar.",
            )
            return
        self._refrescar_todo()
        QMessageBox.information(self.v, "Buscar y reemplazar", f"Se reemplazaron {hechos} coincidencias.")
