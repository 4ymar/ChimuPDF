import os

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QInputDialog,
    QMainWindow,
    QMessageBox,
    QSplitter,
    QStackedWidget,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from chimupdf.nucleo.documento import DocumentoPDF
from chimupdf.nucleo.operaciones import dividir
from .anotador import Anotador
from .barra_busqueda import BarraBusqueda
from .barra_modos import BarraModos
from .comun import NOMBRE_APP, Boton, crear_accion
from .controlador_ocr import ControladorOCR
from .dialogo_dividir import DialogoDividir      
from .dialogo_unir import DialogoUnir
from .editor import Editor
from .miniaturas import PanelMiniaturas
from .pantalla_inicio import PantallaInicio
from .seguridad import Seguridad
from .seleccion_texto import SeleccionTexto
from .tema import Estetica
from .visor import VisorPagina

class VentanaPrincipal(QMainWindow):
    def __init__(self):
        super().__init__()
        self.documento = None
        self.resize(1100, 750)

        self.miniaturas = PanelMiniaturas()
        self.visor = VisorPagina()
        self.busqueda = BarraBusqueda(self)
        panel_visor = QWidget()
        disposicion = QVBoxLayout(panel_visor)
        disposicion.setContentsMargins(0, 0, 0, 0)
        disposicion.setSpacing(0)
        disposicion.addWidget(self.visor, 1)
        disposicion.addWidget(self.busqueda)
        divisor = QSplitter(Qt.Orientation.Horizontal)
        divisor.addWidget(self.miniaturas)
        divisor.addWidget(panel_visor)
        divisor.setStretchFactor(1, 1)
        divisor.setSizes([200, 900])
        self.inicio = PantallaInicio()
        self.pila = QStackedWidget()
        self.pila.addWidget(self.inicio)
        self.pila.addWidget(divisor)
        self.setCentralWidget(self.pila)
        self.inicio.abrir_solicitado.connect(self._abrir)
        self.inicio.abrir_reciente.connect(self.abrir_ruta)
        self.inicio.unir_solicitado.connect(self._unir)
        self.inicio.dividir_solicitado.connect(self._dividir_desde_inicio)
        self.visor.pagina_anterior.connect(lambda: self._pagina_relativa(-1))
        self.visor.pagina_siguiente.connect(lambda: self._pagina_relativa(1))
        self.setAcceptDrops(True)

        self._crear_acciones()
        self._crear_menus()
        self._crear_barra_herramientas()
        self.anotador = Anotador(self)
        self.seguridad = Seguridad(self)
        self.ocr = ControladorOCR(self)
        self.editor = Editor(self)
        self.modos = BarraModos(self)
        self.seleccion_texto = SeleccionTexto(self)
        self.estetica = Estetica(self)
        self.miniaturas.currentRowChanged.connect(self._al_cambiar_pagina)
        self.miniaturas.pagina_movida.connect(self._al_mover_pagina)
        self.visor.zoom_cambiado.connect(lambda _z: self.actualizar_estado())
        self.actualizar_estado()

    # ---------- construcción de la interfaz ----------
    def _crear_acciones(self):
        S = QKeySequence.StandardKey
        self.a_abrir = crear_accion(self, "&Abrir...", self._abrir, S.Open)
        self.a_guardar = crear_accion(self, "&Guardar", self._guardar, S.Save)
        self.a_guardar_como = crear_accion(self, "Guardar &como...", self._guardar_como, S.SaveAs)
        self.a_cerrar = crear_accion(self, "&Cerrar documento", self._cerrar, "Ctrl+W")
        self.a_salir = crear_accion(self, "&Salir", self.close, S.Quit)

        self.a_rot_der = crear_accion(self, "Rotar a la &derecha", lambda: self._rotar(90), "Ctrl+R")
        self.a_rot_izq = crear_accion(self, "Rotar a la &izquierda", lambda: self._rotar(-90), "Ctrl+L")
        self.a_eliminar = crear_accion(self, "&Eliminar página", self._eliminar, "Del")
        self.a_subir = crear_accion(self, "Mover &arriba", lambda: self._mover(-1), "Alt+Up")
        self.a_bajar = crear_accion(self, "Mover a&bajo", lambda: self._mover(1), "Alt+Down")

        self.a_acercar = crear_accion(self, "&Acercar", self.visor.acercar, S.ZoomIn)
        self.a_alejar = crear_accion(self, "A&lejar", self.visor.alejar, S.ZoomOut)
        self.a_real = crear_accion(self, "&Tamaño real", self.visor.tamano_real, "Ctrl+0")
        self.a_ancho = crear_accion(self, "Ajustar al a&ncho", self.visor.ajustar_ancho, "Ctrl+9")
        self.a_pag_ant = crear_accion(self, "Página ant&erior", lambda: self._pagina_relativa(-1), "Ctrl+PgUp")
        self.a_pag_sig = crear_accion(self, "Página &siguiente", lambda: self._pagina_relativa(1), "Ctrl+PgDown")
        self.a_ir_a = crear_accion(self, "&Ir a la página...", self._ir_a_pagina, "Ctrl+G")
        self.a_buscar_texto = crear_accion(self, "&Buscar texto...", self.busqueda.abrir, "Ctrl+F")
        self.a_deshacer = crear_accion(self, "&Deshacer", self._deshacer, S.Undo)
        self.a_rehacer = crear_accion(self, "&Rehacer", self._rehacer, S.Redo)

        self.a_insertar = crear_accion(self, "&Insertar PDF en el documento...", self._insertar_pdf)
        self.a_unir = crear_accion(self, "&Unir varios PDFs...", self._unir)
        self.a_dividir = crear_accion(self, "&Dividir PDF...", self._dividir)

        self._acciones_documento = [
            self.a_insertar, self.a_dividir,
            self.a_guardar, self.a_guardar_como, self.a_cerrar,
            self.a_rot_der, self.a_rot_izq,
            self.a_eliminar, self.a_subir, self.a_bajar,
            self.a_acercar, self.a_alejar, self.a_real, self.a_ancho,
            self.a_pag_ant, self.a_pag_sig, self.a_ir_a, self.a_buscar_texto,
        ]

    def _crear_menus(self):
        barra = self.menuBar()
        m = barra.addMenu("&Archivo")
        m.addActions([self.a_abrir, self.a_guardar, self.a_guardar_como, self.a_cerrar])
        m.addSeparator()
        m.addAction(self.a_salir)

        m = barra.addMenu("&Páginas")
        m.addActions([self.a_rot_der, self.a_rot_izq])
        m.addSeparator()
        m.addActions([self.a_subir, self.a_bajar])
        m.addSeparator()
        m.addAction(self.a_eliminar)
        m = barra.addMenu("&Herramientas")
        m.addActions([self.a_insertar, self.a_unir, self.a_dividir])

        m = barra.addMenu("&Ver")
        m.addActions([self.a_acercar, self.a_alejar, self.a_real, self.a_ancho])
        m.addSeparator()
        m.addActions([self.a_pag_ant, self.a_pag_sig, self.a_ir_a])
        m.addSeparator()
        m.addAction(self.a_buscar_texto)

    def _crear_barra_herramientas(self):
        barra = QToolBar("Principal")
        barra.setMovable(False)
        self.addToolBar(barra)
        barra.addActions([self.a_abrir, self.a_guardar, self.a_deshacer, self.a_rehacer])
        barra.addSeparator()
        barra.addActions([self.a_rot_izq, self.a_rot_der, self.a_subir, self.a_bajar, self.a_eliminar])
        barra.addSeparator()
        barra.addActions([self.a_alejar, self.a_acercar, self.a_ancho])

    # ---------- abrir ----------
    def _abrir(self):
        if not self._confirmar_cambios():
            return
        ruta, _ = QFileDialog.getOpenFileName(self, "Abrir PDF", "", "Archivos PDF (*.pdf)")
        if ruta:
            self.abrir_ruta(ruta)

    def abrir_ruta(self, ruta):
        if not self._confirmar_cambios():
            return
        try:
            nuevo = DocumentoPDF(ruta)
        except Exception as error:
            QMessageBox.critical(self, NOMBRE_APP, f"No se pudo abrir el archivo:\n{error}")
            return
        if nuevo.protegido and not self.seguridad.pedir_contrasena(nuevo):
            nuevo.cerrar()
            return
        if nuevo.num_paginas == 0:
            nuevo.cerrar()
            QMessageBox.warning(self, NOMBRE_APP, "El PDF no contiene páginas.")
            return

        self.visor.limpiar()
        if self.documento:
            self.documento.cerrar()
        self.documento = nuevo
        self.inicio.registrar(ruta)
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            self.miniaturas.cargar(nuevo)
        finally:
            QApplication.restoreOverrideCursor()
        self.miniaturas.setCurrentRow(0)
        self.actualizar_estado()

    # ---------- guardar ----------
    def _guardar(self, confirmar=True):
        if not self.documento:
            return False
        if confirmar:
            r = QMessageBox.question(
                self, "Guardar",
                f"Se sobrescribirá el archivo original:\n{self.documento.ruta}\n\n¿Continuar?",
            )
            if r != Boton.Yes:
                return False
        return self._escribir(None)

    def _guardar_como(self):
        if not self.documento:
            return False
        ruta, _ = QFileDialog.getSaveFileName(
            self, "Guardar PDF como", self.documento.ruta, "Archivos PDF (*.pdf)"
        )
        if not ruta:
            return False
        if not ruta.lower().endswith(".pdf"):
            ruta += ".pdf"
        return self._escribir(ruta)

    def _escribir(self, ruta):
        try:
            self.documento.guardar(ruta)
        except Exception as error:
            QMessageBox.critical(self, NOMBRE_APP, f"No se pudo guardar el archivo:\n{error}")
            return False
        self.inicio.registrar(self.documento.ruta)
        self.actualizar_estado()
        return True

    def _cerrar(self):
        if not self._confirmar_cambios():
            return
        if self.documento:
            self.documento.cerrar()
            self.documento = None
        self.anotador.limpiar_seleccion()
        self.editor.limpiar_imagen()
        self.visor.limpiar()
        self.miniaturas.clear()
        self.inicio.refrescar()
        self.actualizar_estado()

    def _confirmar_cambios(self):
        if not self.documento or not self.documento.modificado:
            return True
        r = QMessageBox.question(
            self, "Cambios sin guardar",
            "El documento tiene cambios sin guardar.\n¿Deseas guardarlos?",
            Boton.Save | Boton.Discard | Boton.Cancel,
        )
        if r == Boton.Save:
            return self._guardar(confirmar=False)
        return r == Boton.Discard

    def keyPressEvent(self, evento):
        if evento.key() == Qt.Key.Key_Escape:
            self.anotador.limpiar_seleccion()
            self.editor.limpiar_imagen()
            self.seleccion_texto.limpiar()
            evento.accept()
            return
        super().keyPressEvent(evento)

    def closeEvent(self, evento):
        if self._confirmar_cambios():
            evento.accept()
        else:
            evento.ignore()

    # ---------- operaciones de página ----------
    def _fila(self):
        return self.miniaturas.currentRow()

    def tras_cambio(self, fila):
        """Llamar después de modificar la página 'fila': marca el documento y refresca la interfaz."""
        doc = self.documento
        doc.registrar_estado()  # instantánea para Deshacer (también marca el documento como modificado)
        self.busqueda.invalidar()
        self.seleccion_texto.limpiar()
        self.miniaturas.actualizar_miniatura(fila, doc)
        self.visor.refrescar()
        self.actualizar_estado()

    def _deshacer(self):
        self._viajar_historial(deshacer=True)

    def _rehacer(self):
        self._viajar_historial(deshacer=False)

    def _viajar_historial(self, deshacer):
        doc = self.documento
        if doc is None:
            return
        fila = max(self._fila(), 0)
        try:
            hecho = doc.deshacer() if deshacer else doc.rehacer()
        except Exception as error:
            accion = "deshacer" if deshacer else "rehacer"
            QMessageBox.critical(self, NOMBRE_APP, f"No se pudo {accion}:\n{error}")
            return
        if not hecho:
            return
        self.anotador.limpiar_seleccion()
        self.editor.limpiar_imagen()
        self.busqueda.invalidar()
        self.seleccion_texto.limpiar()
        if doc.num_paginas == self.miniaturas.count():
            self.miniaturas.invalidar(doc)
            self.visor.refrescar()
        else:  # cambió el número de páginas
            self.miniaturas.cargar(doc)
            self.miniaturas.setCurrentRow(min(fila, doc.num_paginas - 1))
        self.actualizar_estado()
        self.ocr.actualizar_aviso()

    def _rotar(self, grados):
        fila = self._fila()
        if self.documento is None or fila < 0:
            return
        self.anotador.limpiar_seleccion()
        self.editor.limpiar_imagen()
        self.documento.rotar(fila, grados)
        self.tras_cambio(fila)

    def _eliminar(self):
        if self.anotador.borrar_seleccion():
            return
        if self.editor.borrar_seleccion():
            return
        fila = self._fila()
        if self.documento is None or fila < 0:
            return
        if self.documento.num_paginas <= 1:
            QMessageBox.warning(self, NOMBRE_APP, "No se puede eliminar la única página del documento.")
            return
        r = QMessageBox.question(self, "Eliminar página", f"¿Eliminar la página {fila + 1}?")
        if r != Boton.Yes:
            return
        self.anotador.limpiar_seleccion()
        self.editor.limpiar_imagen()
        self.documento.eliminar(fila)
        self.documento.registrar_estado()
        self.miniaturas.quitar(fila)
        nueva_fila = min(fila, self.miniaturas.count() - 1)
        self.miniaturas.setCurrentRow(nueva_fila)
        self.visor.mostrar(self.documento, nueva_fila)
        self.actualizar_estado()

    def _mover(self, delta):
        fila = self._fila()
        nueva = fila + delta
        if self.documento is None or fila < 0 or not 0 <= nueva < self.documento.num_paginas:
            return
        self.documento.mover(fila, nueva)
        self.documento.registrar_estado()
        self.miniaturas.mover_item(fila, nueva)
        self.actualizar_estado()

    def _al_mover_pagina(self, origen, destino):
        """Llamado cuando el usuario reordena arrastrando una miniatura."""
        if self.documento is None:
            return
        self.documento.mover(origen, destino)
        self.documento.registrar_estado()
        self.visor.mostrar(self.documento, destino)
        self.actualizar_estado()

    def _al_cambiar_pagina(self, fila):
        if self.documento is not None and fila >= 0:
            self.visor.mostrar(self.documento, fila)
        self.actualizar_estado()

    # ---------- navegación y arrastrar ----------
    def _pagina_relativa(self, delta):
        nueva = self._fila() + delta
        if self.documento is not None and 0 <= nueva < self.documento.num_paginas:
            self.miniaturas.setCurrentRow(nueva)

    def _ir_a_pagina(self):
        if self.documento is None:
            return
        total = self.documento.num_paginas
        numero, aceptado = QInputDialog.getInt(
            self, "Ir a la página", f"Página (1 a {total}):", max(self._fila(), 0) + 1, 1, total
        )
        if aceptado:
            self.miniaturas.setCurrentRow(numero - 1)

    def _dividir_desde_inicio(self):
        self._abrir()  # dividir necesita un documento abierto: primero se elige el archivo
        if self.documento is not None:
            self._dividir()

    def dragEnterEvent(self, evento):
        if any(url.toLocalFile().lower().endswith(".pdf") for url in evento.mimeData().urls()):
            evento.acceptProposedAction()

    def dropEvent(self, evento):
        for url in evento.mimeData().urls():
            ruta = url.toLocalFile()
            if ruta.lower().endswith(".pdf"):
                self.abrir_ruta(ruta)
                break
    
    # ---------- unir y dividir ----------
    def _insertar_pdf(self):
        if self.documento is None:
            return
        ruta, _ = QFileDialog.getOpenFileName(self, "Insertar PDF", "", "Archivos PDF (*.pdf)")
        if not ruta:
            return
        opciones = ["Al final del documento", "Antes de la página actual", "Después de la página actual"]
        eleccion, aceptado = QInputDialog.getItem(
            self, "Insertar PDF", "¿Dónde insertar las páginas?", opciones, 0, False
        )
        if not aceptado:
            return
        fila = max(self._fila(), 0)
        if eleccion == opciones[0]:
            posicion = self.documento.num_paginas
        elif eleccion == opciones[1]:
            posicion = fila
        else:
            posicion = fila + 1
        try:
            cantidad = self.documento.insertar_pdf(ruta, posicion)
        except Exception as error:
            QMessageBox.critical(self, NOMBRE_APP, f"No se pudo insertar el PDF:\n{error}")
            return
        self.documento.registrar_estado()
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            self.miniaturas.cargar(self.documento)
        finally:
            QApplication.restoreOverrideCursor()
        self.miniaturas.setCurrentRow(posicion)
        self.actualizar_estado()
        self.statusBar().showMessage(f"Se insertaron {cantidad} páginas", 5000)

    def _unir(self):
        dialogo = DialogoUnir(self)
        if dialogo.exec() and dialogo.resultado:
            r = QMessageBox.question(
                self, "Unir PDFs",
                f"PDF unido guardado en:\n{dialogo.resultado}\n\n¿Abrirlo ahora?",
            )
            if r == Boton.Yes:
                self.abrir_ruta(dialogo.resultado)

    def _dividir(self):
        if self.documento is None:
            return
        carpeta_base = os.path.dirname(os.path.abspath(self.documento.ruta))
        dialogo = DialogoDividir(
            self.documento.num_paginas, carpeta_base, self
        )
        if not dialogo.exec():
            return
        base = os.path.splitext(self.documento.nombre)[0]
        try:
            archivos = dividir(self.documento, dialogo.grupos, dialogo.carpeta, base)
        except Exception as error:
            QMessageBox.critical(self, NOMBRE_APP, f"No se pudo dividir el PDF:\n{error}")
            return
        QMessageBox.information(
            self, "Dividir PDF", f"Se crearon {len(archivos)} archivos en:\n{dialogo.carpeta}"
        )
    
    # ---------- estado ----------
    def actualizar_estado(self):
        self.pila.setCurrentIndex(0 if self.documento is None else 1)
        self.anotador.actualizar_estado()
        self.seguridad.actualizar_estado()
        self.ocr.actualizar_estado()
        self.editor.actualizar_estado()
        self.modos.actualizar_estado()
        self.busqueda.actualizar_estado()
        doc = self.documento
        for accion in self._acciones_documento:
            accion.setEnabled(doc is not None)
        self.a_deshacer.setEnabled(doc is not None and doc.puede_deshacer)
        self.a_rehacer.setEnabled(doc is not None and doc.puede_rehacer)
        if doc is None:
            self.setWindowTitle(NOMBRE_APP)
            self.statusBar().showMessage("Abre un PDF para comenzar (Ctrl+O)")
            return
        marca = "*" if doc.modificado else ""
        self.setWindowTitle(f"{marca}{doc.nombre} — {NOMBRE_APP}")
        fila = max(self._fila(), 0)
        protegido = "   |   Protegido con contraseña" if doc.proteccion else ""
        self.statusBar().showMessage(
            f"Página {fila + 1} de {doc.num_paginas}   |   Zoom {round(self.visor.zoom * 100)}%{protegido}"
        )
