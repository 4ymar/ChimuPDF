import multiprocessing
import os

from PySide6.QtCore import QEventLoop, QObject, Qt, QTimer
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox, QProgressDialog, QPushButton

from chimupdf.nucleo import ocr

from .comun import NOMBRE_APP, Boton, crear_accion
from .dialogo_ocr import DialogoOCR

AYUDA_INSTALACION = (
    "No se encontraron los datos de idioma del OCR.\n\n"
    "Deberían venir incluidos con ChimuPDF, en la carpeta «recursos\\tessdata». "
    "Si falta, reinstala la aplicación.\n\n"
    "También puedes indicar tú mismo una carpeta «tessdata» con archivos .traineddata "
    "(por ejemplo, la de una instalación de Tesseract).\n\n¿Elegir la carpeta ahora?"
)


class ControladorOCR(QObject):
    """Menú y lógica de OCR: hacer buscable, exportar texto y copiar texto."""

    def __init__(self, ventana):
        super().__init__(ventana)
        self.v = ventana
        self._doc_visto = None
        self.a_rapido = crear_accion(self.v, "&Reconocer texto (OCR)", self.reconocer_rapido)
        self.a_buscable = crear_accion(self.v, "Reconocer con &opciones...", self.hacer_buscable)
        self.a_exportar = crear_accion(self.v, "&Exportar texto a .txt...", self.exportar_texto)
        self.a_copiar = crear_accion(self.v, "&Copiar texto de la página", self.copiar_texto)
        self.a_carpeta = crear_accion(self.v, "Carpeta de &idiomas...", self.elegir_carpeta)
        menu = self.v.menuBar().addMenu("&OCR")
        menu.addActions([self.a_rapido, self.a_buscable])
        menu.addSeparator()
        menu.addActions([self.a_exportar, self.a_copiar])
        menu.addSeparator()
        menu.addAction(self.a_carpeta)

        self.boton_aviso = QPushButton("Parece un escaneo: reconocer texto (OCR)")
        self.boton_aviso.setCursor(Qt.CursorShape.PointingHandCursor)
        self.boton_aviso.clicked.connect(self.reconocer_rapido)
        self.boton_aviso.setVisible(False)
        self.v.statusBar().addPermanentWidget(self.boton_aviso)

    def actualizar_estado(self):
        doc = self.v.documento
        for accion in (self.a_rapido, self.a_buscable, self.a_exportar, self.a_copiar):
            accion.setEnabled(doc is not None)
        if doc is not self._doc_visto:  # documento nuevo: ¿parece un escaneo?
            self._doc_visto = doc
            self.actualizar_aviso()

    def actualizar_aviso(self):
        """Muestra en la barra de estado el botón de OCR si las primeras páginas no tienen texto."""
        doc = self.v.documento
        escaneo = False
        if doc is not None and doc.num_paginas > 0:
            primeras = range(min(3, doc.num_paginas))
            escaneo = not any(ocr.tiene_texto(doc.pagina(i)) for i in primeras)
        self.boton_aviso.setVisible(escaneo)

    # ---------- carpeta de idiomas ----------
    def elegir_carpeta(self):
        carpeta = QFileDialog.getExistingDirectory(
            self.v, "Elige la carpeta «tessdata» (con los archivos .traineddata)"
        )
        if not carpeta:
            return None
        if not ocr.idiomas_en(carpeta):
            QMessageBox.warning(self.v, NOMBRE_APP, "Esa carpeta no contiene archivos .traineddata.")
            return None
        ocr.guardar_carpeta_tessdata(carpeta)
        return carpeta

    def _tessdata(self):
        """Carpeta de idiomas; si no se encuentra, explica cómo instalar y permite elegirla."""
        carpeta = ocr.buscar_tessdata()
        if carpeta:
            return carpeta
        if QMessageBox.question(self.v, "OCR no disponible", AYUDA_INSTALACION) == Boton.Yes:
            return self.elegir_carpeta()
        return None

    # ---------- utilidades ----------
    def _ejecutar_en_procesos(self, doc, indices, tarea, idioma, tessdata, omitir, al_resultado):
        """Reparte las páginas entre procesos (PyMuPDF no admite hilos) y llama a
        al_resultado(indice, estado, valor) aquí, a medida que cada página termina.

        Devuelve 'terminado', 'cancelado' o, si algo falló, el mensaje de error.
        """
        datos = doc.exportar_bytes()
        procesos = max(1, min(4, len(indices), (os.cpu_count() or 2) - 1))
        progreso = QProgressDialog("Preparando el OCR...", "Cancelar", 0, len(indices), self.v)
        progreso.setWindowTitle("OCR")
        progreso.setWindowModality(Qt.WindowModality.WindowModal)
        progreso.setMinimumDuration(0)
        progreso.setAutoClose(False)
        progreso.setAutoReset(False)
        progreso.setValue(0)

        bucle = QEventLoop(self)
        progreso.canceled.connect(bucle.quit)
        temporizador = QTimer(self)
        temporizador.setInterval(80)
        final = {"resultado": "terminado"}
        pendientes = []
        pool = None

        def revisar():
            nonlocal pendientes
            faltan = []
            for i, trabajo in pendientes:
                if not trabajo.ready():
                    faltan.append((i, trabajo))
                    continue
                try:
                    _indice, estado, valor = trabajo.get()
                    if estado == "error":
                        raise RuntimeError(valor)
                    al_resultado(i, estado, valor)
                except Exception as error:
                    final["resultado"] = str(error) or "Error desconocido"
                    bucle.quit()
                    return
            pendientes = faltan
            hechas = len(indices) - len(faltan)
            progreso.setValue(hechas)
            progreso.setLabelText(f"Reconociendo texto...  {hechas} de {len(indices)} páginas")
            if not faltan:
                bucle.quit()

        temporizador.timeout.connect(revisar)
        try:
            pool = multiprocessing.Pool(
                processes=procesos,
                initializer=ocr.iniciar_proceso,
                initargs=(datos, idioma, tessdata, ocr.DPI, omitir),
            )
            pendientes = [(i, pool.apply_async(tarea, (i,))) for i in indices]
            temporizador.start()
            bucle.exec()
            cancelado = progreso.wasCanceled()  # antes de close(), que también emite canceled
        finally:
            temporizador.stop()
            progreso.close()
            if pool is not None:
                pool.terminate()
                pool.join()
        if final["resultado"] != "terminado":
            return final["resultado"]
        return "cancelado" if cancelado else "terminado"

    def _dialogo(self, titulo, modo, tessdata):
        doc = self.v.documento
        dialogo = DialogoOCR(
            self.v, ocr.idiomas_en(tessdata), doc.num_paginas,
            max(self.v.miniaturas.currentRow(), 0), titulo, modo,
        )
        return dialogo if dialogo.exec() else None

    # ---------- hacer buscable ----------
    def reconocer_rapido(self):
        """OCR en un paso: todas las páginas sin texto, en español (o el primer idioma disponible)."""
        doc = self.v.documento
        if doc is None:
            return
        tessdata = self._tessdata()
        if tessdata is None:
            return
        idiomas = ocr.idiomas_en(tessdata)
        idioma = "spa" if "spa" in idiomas else idiomas[0]
        self._reconocer(doc, tessdata, idioma, list(range(doc.num_paginas)), True)

    def hacer_buscable(self):
        doc = self.v.documento
        if doc is None:
            return
        tessdata = self._tessdata()
        if tessdata is None:
            return
        dialogo = self._dialogo("Reconocer texto (OCR)", "buscable", tessdata)
        if dialogo is None:
            return
        self._reconocer(doc, tessdata, dialogo.idioma, dialogo.indices, dialogo.omitir)

    def _reconocer(self, doc, tessdata, idioma, indices, omitir):
        cambiadas, omitidas = [], 0

        def al_resultado(i, estado, valor):
            nonlocal omitidas
            if estado == "omitida":
                omitidas += 1
                return
            doc.reemplazar_pagina(i, valor)
            cambiadas.append(i)

        try:
            resultado = self._ejecutar_en_procesos(
                doc, indices, ocr.reconocer_en_proceso, idioma, tessdata, omitir, al_resultado,
            )
        except Exception as error:  # p. ej. no se pudieron iniciar los procesos
            QMessageBox.critical(self.v, NOMBRE_APP, f"No se pudo iniciar el OCR:\n{error}")
            return

        if cambiadas:
            self.v.anotador.limpiar_seleccion()
            doc.registrar_estado()
            self.v.miniaturas.invalidar(doc, cambiadas)
            self.v.visor.refrescar()
            self.v.actualizar_estado()
            self.actualizar_aviso()
        if resultado not in ("terminado", "cancelado"):  # llegó un mensaje de error
            QMessageBox.critical(self.v, NOMBRE_APP, f"No se pudo completar el OCR:\n{resultado}")
            return
        if not cambiadas and resultado == "terminado" and omitidas:
            QMessageBox.information(
                self.v, "Reconocer texto (OCR)",
                "Todas las páginas ya tienen texto: no hizo falta el OCR.",
            )
            return
        estado = "OCR terminado" if resultado == "terminado" else "OCR cancelado"
        mensaje = f"{estado}: {len(cambiadas)} páginas reconocidas, {omitidas} omitidas por tener texto.\n"
        if cambiadas:
            mensaje += (
                "Ya puedes seleccionar el texto arrastrando en modo Ver (Ctrl+C para copiarlo) "
                "y buscarlo con Ctrl+F.\n"
            )
        mensaje += "Usa Guardar o Guardar como para conservar los cambios."
        QMessageBox.information(self.v, "Reconocer texto (OCR)", mensaje)

    # ---------- exportar texto ----------
    def exportar_texto(self):
        doc = self.v.documento
        if doc is None:
            return
        tessdata = self._tessdata()
        if tessdata is None:
            return
        dialogo = self._dialogo("Exportar texto", "exportar", tessdata)
        if dialogo is None:
            return
        base, _ext = os.path.splitext(doc.ruta)
        ruta, _ = QFileDialog.getSaveFileName(
            self.v, "Guardar texto como", base + ".txt", "Texto (*.txt)"
        )
        if not ruta:
            return
        if not ruta.lower().endswith(".txt"):
            ruta += ".txt"
        partes, con_ocr = {}, 0

        def al_resultado(i, _estado, valor):
            nonlocal con_ocr
            texto, uso_ocr = valor
            con_ocr += uso_ocr
            partes[i] = f"--- Página {i + 1} ---\n{texto}\n"

        try:
            resultado = self._ejecutar_en_procesos(
                doc, dialogo.indices, ocr.leer_texto_en_proceso,
                dialogo.idioma, tessdata, False, al_resultado,
            )
            if resultado == "cancelado":
                return
            if resultado != "terminado":
                raise RuntimeError(resultado)
            with open(ruta, "w", encoding="utf-8") as f:
                f.write("\n".join(partes[i] for i in sorted(partes)))
        except Exception as error:
            QMessageBox.critical(self.v, NOMBRE_APP, f"No se pudo exportar el texto:\n{error}")
            return
        QMessageBox.information(
            self.v, "Exportar texto",
            f"Texto guardado en:\n{ruta}\n\n{len(partes)} páginas ({con_ocr} con OCR).",
        )

    # ---------- copiar texto ----------
    def copiar_texto(self):
        doc, fila = self.v.documento, self.v.miniaturas.currentRow()
        if doc is None or fila < 0:
            return
        pagina = doc.pagina(fila)
        usó_ocr = False
        if ocr.tiene_texto(pagina):
            texto = pagina.get_text().strip()
        else:
            tessdata = self._tessdata()
            if tessdata is None:
                return
            dialogo = self._dialogo("Copiar texto (OCR)", "copiar", tessdata)
            if dialogo is None:
                return
            try:
                QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
                try:
                    texto, usó_ocr = ocr.texto_de_pagina(pagina, dialogo.idioma, tessdata)
                finally:
                    QApplication.restoreOverrideCursor()
            except Exception as error:
                QMessageBox.critical(self.v, NOMBRE_APP, f"No se pudo reconocer el texto:\n{error}")
                return
        if not texto:
            QMessageBox.information(self.v, "Copiar texto", "No se encontró texto en esta página.")
            return
        QApplication.clipboard().setText(texto)
        origen = " (reconocido con OCR)" if usó_ocr else ""
        self.v.statusBar().showMessage(f"Texto de la página {fila + 1} copiado{origen}", 6000)
