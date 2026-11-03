"""Utilidades compartidas por los módulos de la interfaz."""
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMessageBox

NOMBRE_APP = "ChimuPDF"
Boton = QMessageBox.StandardButton


def crear_accion(padre, texto, funcion, atajo=None):
    """QAction que llama a funcion() sin argumentos (ignora el valor 'marcado' que envía triggered)."""
    accion = QAction(texto, padre)
    accion.triggered.connect(lambda _marcado=False: funcion())
    if atajo is not None:
        accion.setShortcut(atajo)
    return accion