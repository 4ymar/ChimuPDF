"""Acceso a documentos PDF. No depende de la interfaz gráfica."""
import os

import pymupdf

from .proteccion import desde_documento, parametros_cifrado

MAX_PASOS = 20  # pasos de Deshacer
PRESUPUESTO_HISTORIAL = 200 * 1024 * 1024  # bytes; si se supera, se descartan los pasos más viejos


class DocumentoPDF:
    def __init__(self, ruta):
        self.ruta = ruta
        # Se lee a memoria para no mantener el archivo bloqueado en Windows
        # y poder sobrescribirlo al guardar.
        with open(ruta, "rb") as f:
            datos = f.read()
        self._doc = pymupdf.open(stream=datos, filetype="pdf")
        self.modificado = False
        self.proteccion = None  # contraseña y permisos con los que se guardará
        self.version = 0  # sube con cada cambio, deshacer o rehacer: invalida las cachés de dibujo
        self._estados = []  # instantáneas del documento; la actual es _estados[_pos]
        self._pos = -1
        self._pos_guardada = -1  # posición del historial que coincide con lo guardado en disco
        self._proteccion_guardada = None
        if not self._doc.needs_pass:
            self._iniciar_historial(datos)

    @property
    def nombre(self):
        return os.path.basename(self.ruta)

    @property
    def protegido(self):
        return self._doc.needs_pass

    def autenticar(self, clave):
        """Desbloquea un PDF protegido. Si la clave es correcta, la conserva al guardar."""
        if self._doc.authenticate(clave):
            self.proteccion = desde_documento(self._doc, clave)
            self._iniciar_historial(self._doc.tobytes(encryption=pymupdf.PDF_ENCRYPT_NONE))
            return True
        return False

    @property
    def num_paginas(self):
        return self._doc.page_count

    def ancho_pagina(self, indice):
        if not 0 <= indice < self.num_paginas:
            return 0.0
        return self._doc[indice].rect.width

    def renderizar(self, indice, zoom=1.0):
        """Devuelve (bytes RGB, ancho, alto, stride) de la página."""
        pagina = self._doc[indice]
        pix = pagina.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), alpha=False)
        return pix.samples, pix.width, pix.height, pix.stride

    def rotar(self, indice, grados):
        pagina = self._doc[indice]
        pagina.set_rotation((pagina.rotation + grados) % 360)
        self.modificado = True

    def eliminar(self, indice):
        if self.num_paginas <= 1:
            raise ValueError("No se puede eliminar la única página del documento.")
        self._doc.delete_page(indice)
        self.modificado = True

    def mover(self, origen, destino):
        """Mueve la página 'origen' para que quede en la posición 'destino'."""
        if origen == destino:
            return
        if destino > origen:
            antes_de = destino + 1
            if antes_de >= self.num_paginas:
                antes_de = -1  # al final
        else:
            antes_de = destino
        self._doc.move_page(origen, antes_de)
        self.modificado = True

    def guardar(self, ruta=None):
        """Guarda en 'ruta' (o sobrescribe el original si no se indica)."""
        ruta = ruta or self.ruta
        datos = self._escribir(ruta, self.proteccion)
        self._doc.close()
        self._doc = pymupdf.open(stream=datos, filetype="pdf")
        if self.proteccion:
            self._doc.authenticate(self.proteccion.clave)
        self.ruta = ruta
        self.modificado = False
        self._pos_guardada = self._pos
        self._proteccion_guardada = self.proteccion

    def guardar_copia(self, ruta, proteccion=None):
        """Guarda una copia (con o sin protección) sin cambiar el documento abierto."""
        self._escribir(ruta, proteccion)

    def _escribir(self, ruta, proteccion):
        datos = self._doc.tobytes(garbage=3, deflate=True, **parametros_cifrado(proteccion))
        temporal = ruta + ".tmp"
        try:
            with open(temporal, "wb") as f:
                f.write(datos)
            os.replace(temporal, ruta)
        except Exception:
            if os.path.exists(temporal):
                try:
                    os.remove(temporal)
                except OSError:
                    pass
            raise
        return datos

    def insertar_pdf(self, ruta, posicion):
        """Inserta las páginas de otro PDF antes de 'posicion'. Devuelve cuántas se insertaron."""
        with pymupdf.open(ruta) as otro:
            if otro.needs_pass:
                raise ValueError("El PDF a insertar está protegido con contraseña.")
            cantidad = otro.page_count
            inicio = -1 if posicion >= self.num_paginas else posicion
            self._doc.insert_pdf(otro, start_at=inicio)
        self.modificado = True
        return cantidad

    def exportar_rango(self, inicio, fin, ruta):
        """Guarda las páginas inicio..fin (base 0, inclusive) como un PDF nuevo."""
        nuevo = pymupdf.open()
        temporal = ruta + ".tmp"
        try:
            nuevo.insert_pdf(self._doc, from_page=inicio, to_page=fin)
            nuevo.save(temporal, garbage=3, deflate=True)
            os.replace(temporal, ruta)
        except Exception:
            if os.path.exists(temporal):
                try:
                    os.remove(temporal)
                except OSError:
                    pass
            raise
        finally:
            nuevo.close()
    
    def pagina(self, indice):
        """Página de PyMuPDF (para anotar)."""
        return self._doc[indice]

    def incrustar_anotaciones(self):
        """Convierte las anotaciones en contenido fijo de las páginas (no se puede deshacer)."""
        self._doc.bake(annots=True, widgets=False)
        self.modificado = True

    def reemplazar_pagina(self, indice, pdf_bytes):
        """Reemplaza una página por la primera página de otro PDF (en memoria)."""
        if not 0 <= indice < self.num_paginas:
            raise IndexError("Índice de página fuera de rango.")
        with pymupdf.open(stream=pdf_bytes, filetype="pdf") as nueva:
            self._doc.insert_pdf(nueva, from_page=0, to_page=0, start_at=indice)
        self._doc.delete_page(indice + 1)
        self.modificado = True

    # ---------- historial (Deshacer / Rehacer) ----------
    def _iniciar_historial(self, datos):
        self._estados = [datos]
        self._pos = 0
        self._pos_guardada = 0
        self._proteccion_guardada = self.proteccion

    @property
    def puede_deshacer(self):
        return self._pos > 0

    @property
    def puede_rehacer(self):
        return 0 <= self._pos < len(self._estados) - 1

    def registrar_estado(self):
        """Guarda una instantánea del documento tal como queda tras un cambio (para Deshacer)."""
        del self._estados[self._pos + 1:]  # lo que se había deshecho ya no se puede rehacer
        self._estados.append(self._doc.tobytes(encryption=pymupdf.PDF_ENCRYPT_NONE))
        self._pos += 1
        self.version += 1
        self.modificado = True
        total = sum(len(e) for e in self._estados)
        while len(self._estados) > 2 and (len(self._estados) > MAX_PASOS + 1 or total > PRESUPUESTO_HISTORIAL):
            total -= len(self._estados.pop(0))
            self._pos -= 1
            self._pos_guardada -= 1  # si queda < 0, el estado guardado ya no está en el historial

    def deshacer(self):
        return self._ir_a(self._pos - 1)

    def rehacer(self):
        return self._ir_a(self._pos + 1)

    def _ir_a(self, nueva):
        if not 0 <= nueva < len(self._estados):
            return False
        nuevo = pymupdf.open(stream=self._estados[nueva], filetype="pdf")
        self._doc.close()
        self._doc = nuevo
        self._pos = nueva
        self.version += 1
        self.modificado = (
            self._pos != self._pos_guardada or self.proteccion != self._proteccion_guardada
        )
        return True

    def exportar_bytes(self):
        """El documento tal como está ahora (sin cifrar), para entregárselo a otros procesos."""
        return self._doc.tobytes(encryption=pymupdf.PDF_ENCRYPT_NONE)

    def cerrar(self):
        self._estados = []
        self._doc.close()
