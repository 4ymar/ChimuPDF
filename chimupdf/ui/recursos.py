import os
import sys


def carpeta_recursos():
    """Carpeta chimupdf/recursos, tanto en desarrollo como dentro del programa empaquetado."""
    if getattr(sys, "frozen", False):
        base = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
        return os.path.join(base, "chimupdf", "recursos")
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "recursos")


def ruta_recurso(nombre):
    """Ruta de un archivo de chimupdf/recursos."""
    return os.path.join(carpeta_recursos(), nombre)
