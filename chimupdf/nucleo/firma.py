"""Ubicación de la firma guardada del usuario."""
import os

# Estas dos funciones ahora viven en rutas.py; se reexportan porque otros módulos aún las importan de aquí
from .rutas import asegurar_carpeta, carpeta_datos  # noqa: F401


def ruta_firma():
    return os.path.join(carpeta_datos(), "firma.png")


def hay_firma():
    return os.path.isfile(ruta_firma())
