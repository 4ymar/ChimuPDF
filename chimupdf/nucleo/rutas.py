"""Ubicación de los datos del usuario (configuración y firma)."""
import os


def carpeta_datos():
    return os.path.join(os.path.expanduser("~"), ".chimupdf")


def asegurar_carpeta():
    os.makedirs(carpeta_datos(), exist_ok=True)