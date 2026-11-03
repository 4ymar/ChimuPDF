"""Protección de PDFs con contraseña (AES-256) y permisos. Sin interfaz gráfica."""
import secrets
from dataclasses import dataclass

import pymupdf


@dataclass
class Proteccion:
    clave: str  # contraseña para abrir el documento
    permitir_imprimir: bool = True
    permitir_copiar: bool = True
    permitir_modificar: bool = True
    permitir_anotar: bool = True

    @property
    def tiene_restricciones(self):
        return not (
            self.permitir_imprimir and self.permitir_copiar
            and self.permitir_modificar and self.permitir_anotar
        )

    def permisos(self):
        permisos = pymupdf.PDF_PERM_ACCESSIBILITY
        if self.permitir_imprimir:
            permisos |= pymupdf.PDF_PERM_PRINT | pymupdf.PDF_PERM_PRINT_HQ
        if self.permitir_copiar:
            permisos |= pymupdf.PDF_PERM_COPY
        if self.permitir_modificar:
            permisos |= pymupdf.PDF_PERM_MODIFY | pymupdf.PDF_PERM_ASSEMBLE
        if self.permitir_anotar:
            permisos |= pymupdf.PDF_PERM_ANNOTATE | pymupdf.PDF_PERM_FORM
        return permisos


def parametros_cifrado(proteccion):
    """Argumentos de cifrado para tobytes()/save(). Sin protección, se guarda sin cifrar."""
    if proteccion is None:
        return {"encryption": pymupdf.PDF_ENCRYPT_NONE}
    # Si hay restricciones, la contraseña de propietario debe ser distinta de la de apertura;
    # de lo contrario quien abre el archivo tendría todos los permisos.
    propietario = secrets.token_urlsafe(16) if proteccion.tiene_restricciones else proteccion.clave
    return {
        "encryption": pymupdf.PDF_ENCRYPT_AES_256,
        "user_pw": proteccion.clave,
        "owner_pw": propietario,
        "permissions": proteccion.permisos(),
    }


def desde_documento(doc, clave):
    """Reconstruye la protección de un PDF abierto con 'clave' para conservarla al guardar."""
    p = doc.permissions
    return Proteccion(
        clave,
        permitir_imprimir=bool(p & pymupdf.PDF_PERM_PRINT),
        permitir_copiar=bool(p & pymupdf.PDF_PERM_COPY),
        permitir_modificar=bool(p & pymupdf.PDF_PERM_MODIFY),
        permitir_anotar=bool(p & pymupdf.PDF_PERM_ANNOTATE),
    )
