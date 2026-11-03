"""Preferencias del usuario (tema, archivos recientes) en ~/.chimupdf/config.json."""
import json
import os

from .rutas import asegurar_carpeta, carpeta_datos

MAX_RECIENTES = 8


def _ruta():
    return os.path.join(carpeta_datos(), "config.json")


def leer():
    try:
        with open(_ruta(), encoding="utf-8") as f:
            datos = json.load(f)
            return datos if isinstance(datos, dict) else {}
    except (OSError, ValueError):
        return {}


def guardar(clave, valor):
    datos = leer()
    datos[clave] = valor
    try:
        asegurar_carpeta()
        temporal = _ruta() + ".tmp"
        with open(temporal, "w", encoding="utf-8") as f:
            json.dump(datos, f, ensure_ascii=False, indent=2)
        os.replace(temporal, _ruta())  # reemplazo atómico: un corte a mitad no deja el JSON roto
    except OSError:
        pass  # una preferencia que no se guarda no debe romper la app


def recientes():
    """Archivos recientes que todavía existen (más nuevo primero)."""
    return [r for r in leer().get("recientes", []) if os.path.isfile(r)]


def agregar_reciente(ruta):
    ruta = os.path.abspath(ruta)
    lista = [r for r in leer().get("recientes", []) if r != ruta]
    guardar("recientes", ([ruta] + lista)[:MAX_RECIENTES])
