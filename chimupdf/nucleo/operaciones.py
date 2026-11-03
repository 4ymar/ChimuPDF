"""Operaciones de unir y dividir PDFs. No depende de la interfaz gráfica."""
import os

import pymupdf


def unir_archivos(rutas, salida):
    """Une los PDFs de 'rutas' (en ese orden) y guarda el resultado en 'salida'."""
    resultado = pymupdf.open()
    temporal = salida + ".tmp"
    try:
        for ruta in rutas:
            with pymupdf.open(ruta) as pdf:
                if pdf.needs_pass:
                    raise ValueError(f"'{os.path.basename(ruta)}' está protegido con contraseña.")
                resultado.insert_pdf(pdf)
        resultado.save(temporal, garbage=3, deflate=True)
        os.replace(temporal, salida)
    except Exception:
        if os.path.exists(temporal):
            try:
                os.remove(temporal)
            except OSError:
                pass
        raise
    finally:
        resultado.close()


def parsear_rangos(texto, total):
    """Convierte '1-3, 5, 7-9' en [(0, 2), (4, 4), (6, 8)] (base 0, inclusivo)."""
    grupos = []
    for parte in texto.replace(";", ",").split(","):
        parte = parte.strip()
        if not parte:
            continue
        try:
            if "-" in parte:
                a, b = parte.split("-", 1)
                inicio, fin = int(a), int(b)
            else:
                inicio = fin = int(parte)
        except ValueError:
            raise ValueError(f"Rango no válido: '{parte}'. Usa el formato 1-3, 5, 7-9.")
        if inicio < 1 or fin > total or inicio > fin:
            raise ValueError(f"Rango no válido: '{parte}' (el documento tiene {total} páginas).")
        grupos.append((inicio - 1, fin - 1))
    if not grupos:
        raise ValueError("Escribe al menos un rango, por ejemplo: 1-3, 4-10")
    return grupos


def grupos_por_pagina(total):
    return [(i, i) for i in range(total)]


def grupos_cada_n(total, n):
    if n <= 0:
        raise ValueError("El número de páginas por grupo debe ser al menos 1.")
    return [(i, min(i + n - 1, total - 1)) for i in range(0, total, n)]


def _ruta_libre(ruta):
    """Evita sobrescribir: agrega ' (1)', ' (2)'... si el archivo ya existe."""
    if not os.path.exists(ruta):
        return ruta
    base, ext = os.path.splitext(ruta)
    n = 1
    while os.path.exists(f"{base} ({n}){ext}"):
        n += 1
    return f"{base} ({n}){ext}"


def dividir(documento, grupos, carpeta, base):
    """Crea un PDF por cada (inicio, fin) de 'grupos'. Devuelve las rutas creadas."""
    creados = []
    for inicio, fin in grupos:
        if inicio == fin:
            nombre = f"{base}_pag{inicio + 1}.pdf"
        else:
            nombre = f"{base}_pags{inicio + 1}-{fin + 1}.pdf"
        ruta = _ruta_libre(os.path.join(carpeta, nombre))
        documento.exportar_rango(inicio, fin, ruta)
        creados.append(ruta)
    return creados
