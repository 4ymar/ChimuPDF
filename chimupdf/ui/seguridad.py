import os

from PySide6.QtCore import QObject
from PySide6.QtWidgets import QFileDialog, QInputDialog, QLineEdit, QMessageBox

from .comun import NOMBRE_APP, Boton, crear_accion
from .dialogo_proteger import DialogoProteger


class Seguridad(QObject):
    """Menú y lógica de contraseñas: abrir PDFs protegidos, proteger y quitar la protección."""

    def __init__(self, ventana):
        super().__init__(ventana)
        self.v = ventana
        self.a_proteger = crear_accion(self.v, "&Proteger con contraseña...", self.proteger)
        self.a_quitar = crear_accion(self.v, "&Quitar protección", self.quitar)
        self.a_copia = crear_accion(self.v, "Guardar copia &protegida...", self.guardar_copia)
        menu = self.v.menuBar().addMenu("&Seguridad")
        menu.addActions([self.a_proteger, self.a_quitar])
        menu.addSeparator()
        menu.addAction(self.a_copia)

    def actualizar_estado(self):
        doc = self.v.documento
        for accion in (self.a_proteger, self.a_quitar, self.a_copia):
            accion.setEnabled(doc is not None)

    # ---------- abrir PDFs protegidos ----------
    def pedir_contrasena(self, documento):
        """Pide la contraseña (3 intentos). Devuelve True si el documento quedó desbloqueado."""
        mensaje = f"'{documento.nombre}' está protegido.\nEscribe la contraseña:"
        for _ in range(3):
            clave, aceptado = QInputDialog.getText(
                self.v, "PDF protegido", mensaje, QLineEdit.EchoMode.Password
            )
            if not aceptado:
                return False
            if documento.autenticar(clave):
                return True
            mensaje = "Contraseña incorrecta. Inténtalo de nuevo:"
        QMessageBox.warning(self.v, NOMBRE_APP, "No se pudo abrir el archivo: contraseña incorrecta.")
        return False

    # ---------- proteger / quitar ----------
    def proteger(self):
        doc = self.v.documento
        if doc is None:
            return
        dialogo = DialogoProteger(self.v, doc.proteccion)
        if not dialogo.exec():
            return
        doc.proteccion = dialogo.proteccion
        doc.modificado = True
        self.v.actualizar_estado()
        QMessageBox.information(
            self.v, "Proteger con contraseña",
            "El documento se guardará con contraseña cuando uses Guardar o Guardar como.",
        )

    def quitar(self):
        doc = self.v.documento
        if doc is None:
            return
        if doc.proteccion is None:
            QMessageBox.information(self.v, "Quitar protección", "Este documento no tiene protección.")
            return
        r = QMessageBox.question(
            self.v, "Quitar protección",
            "El documento se guardará sin contraseña ni restricciones.\n¿Continuar?",
        )
        if r != Boton.Yes:
            return
        doc.proteccion = None
        doc.modificado = True
        self.v.actualizar_estado()
        QMessageBox.information(
            self.v, "Quitar protección",
            "Listo. Usa Guardar o Guardar como para guardar el archivo sin contraseña.",
        )

    def guardar_copia(self):
        doc = self.v.documento
        if doc is None:
            return
        dialogo = DialogoProteger(self.v, doc.proteccion, "Guardar copia protegida")
        if not dialogo.exec():
            return
        base, _ext = os.path.splitext(doc.ruta)
        ruta, _ = QFileDialog.getSaveFileName(
            self.v, "Guardar copia protegida como", base + "_protegido.pdf", "Archivos PDF (*.pdf)"
        )
        if not ruta:
            return
        if not ruta.lower().endswith(".pdf"):
            ruta += ".pdf"
        if os.path.normcase(os.path.abspath(ruta)) == os.path.normcase(os.path.abspath(doc.ruta)):
            QMessageBox.warning(
                self.v, NOMBRE_APP,
                "Elige otro nombre: la copia no puede reemplazar al archivo abierto.\n"
                "Para proteger el propio documento usa «Proteger con contraseña...».",
            )
            return
        try:
            doc.guardar_copia(ruta, dialogo.proteccion)
        except Exception as error:
            QMessageBox.critical(self.v, NOMBRE_APP, f"No se pudo guardar la copia:\n{error}")
            return
        QMessageBox.information(self.v, "Guardar copia protegida", f"Copia protegida guardada en:\n{ruta}")
