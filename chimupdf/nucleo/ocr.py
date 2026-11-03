"""OCR con Tesseract a través de PyMuPDF. Sin interfaz gráfica.

PyMuPDF ya trae la lógica de OCR; lo que necesita de Tesseract son los datos de
idioma (archivos .traineddata) guardados en una carpeta llamada "tessdata".
"""
import glob
import os
import shutil
import sys

import pymupdf

from . import config

NOMBRES_IDIOMA = {
    "spa": "Español",
    "eng": "Inglés",
    "fra": "Francés",
    "por": "Portugués",
    "ita": "Italiano",
    "deu": "Alemán",
    "cat": "Catalán",
}
IGNORADOS = {"osd", "equ"}  # datos auxiliares de Tesseract, no son idiomas
MIN_CARACTERES_TEXTO = 10  # menos que esto se considera una página sin texto
DPI = 300
# Idiomas incluidos con la app: chimupdf/recursos/tessdata (spa.traineddata, eng.traineddata)
if getattr(sys, "frozen", False):  # programa empaquetado con PyInstaller
    _BASE = os.path.join(getattr(sys, "_MEIPASS", os.path.dirname(sys.executable)), "chimupdf")
else:
    _BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CARPETA_EMPAQUETADA = os.path.join(_BASE, "recursos", "tessdata")


class ErrorOCR(Exception):
    """Error de OCR con un mensaje listo para mostrar al usuario."""


# ---------- carpeta de idiomas ----------
def guardar_carpeta_tessdata(ruta):
    config.guardar("tessdata", ruta)


def idiomas_en(carpeta):
    """Códigos de idioma (spa, eng...) disponibles en una carpeta tessdata."""
    try:
        archivos = os.listdir(carpeta)
    except OSError:
        return []
    codigos = [os.path.splitext(a)[0] for a in archivos if a.endswith(".traineddata")]
    codigos = [c for c in codigos if c not in IGNORADOS]
    # español e inglés primero; el resto, por orden alfabético
    return sorted(codigos, key=lambda c: (c != "spa", c != "eng", c))


def buscar_tessdata():
    """Devuelve la carpeta tessdata con idiomas instalados, o None si no se encuentra."""
    candidatos = [
        config.leer().get("tessdata"),  # la que el usuario eligió a mano
        CARPETA_EMPAQUETADA,
        os.environ.get("TESSDATA_PREFIX"),
        r"C:\Program Files\Tesseract-OCR\tessdata",
        r"C:\Program Files (x86)\Tesseract-OCR\tessdata",
    ]
    ejecutable = shutil.which("tesseract")
    if ejecutable:
        candidatos.append(os.path.join(os.path.dirname(ejecutable), "tessdata"))
    candidatos += glob.glob("/usr/share/tesseract-ocr/*/tessdata") + ["/usr/share/tessdata"]
    for carpeta in candidatos:
        if not carpeta:
            continue
        for posible in (carpeta, os.path.join(carpeta, "tessdata")):
            if os.path.isdir(posible) and idiomas_en(posible):
                return posible
    return None


def nombre_idioma(codigo):
    return NOMBRES_IDIOMA.get(codigo, codigo)


# ---------- reconocimiento ----------
def tiene_texto(pagina):
    return len(pagina.get_text().strip()) >= MIN_CARACTERES_TEXTO


def _traducir_error(error, idioma, tessdata):
    if "esseract" in str(error):
        return ErrorOCR(
            f"No se pudo cargar el idioma «{idioma}».\n"
            f"Verifica que sus datos (.traineddata) estén en:\n{tessdata}"
        )
    return error


def pagina_a_pdf_ocr(pagina, idioma, tessdata, dpi=DPI):
    """PDF de una página (bytes): la imagen de la página con una capa de texto invisible."""
    try:
        return pagina.get_pixmap(dpi=dpi).pdfocr_tobytes(language=idioma, tessdata=tessdata)
    except Exception as error:
        raise _traducir_error(error, idioma, tessdata) from error


def texto_de_pagina(pagina, idioma, tessdata, dpi=DPI):
    """Texto de la página: lo lee directo si lo tiene; si no, usa OCR. Devuelve (texto, usó_ocr)."""
    if tiene_texto(pagina):
        return pagina.get_text().strip(), False
    try:
        tp = pagina.get_textpage_ocr(language=idioma, dpi=dpi, full=True, tessdata=tessdata)
        return pagina.get_text(textpage=tp).strip(), True
    except Exception as error:
        raise _traducir_error(error, idioma, tessdata) from error



# ---------- reconocimiento en procesos aparte ----------
# PyMuPDF no admite hilos (sí procesos): cada proceso abre su propia copia del documento.
_DOC = None
_AJUSTES = None


def iniciar_proceso(datos, idioma, tessdata, dpi, omitir):
    """Inicializador de cada proceso del pool: abre el documento una sola vez."""
    global _DOC, _AJUSTES
    # con varios procesos a la vez, cada Tesseract no debe usar todos los núcleos
    os.environ.setdefault("OMP_THREAD_LIMIT", "1")
    _DOC = pymupdf.open(stream=datos, filetype="pdf")
    _AJUSTES = (idioma, tessdata, dpi, omitir)


def reconocer_en_proceso(indice):
    """Tarea del pool. Devuelve (indice, estado, valor):
    'ok' (valor = PDF de la página con texto), 'omitida' o 'error' (valor = mensaje)."""
    idioma, tessdata, dpi, omitir = _AJUSTES
    try:
        pagina = _DOC[indice]
        if omitir and tiene_texto(pagina):
            return indice, "omitida", None
        return indice, "ok", pagina_a_pdf_ocr(pagina, idioma, tessdata, dpi)
    except Exception as error:
        return indice, "error", str(error)


def leer_texto_en_proceso(indice):
    """Tarea del pool. Devuelve (indice, 'ok', (texto, usó_ocr)) o (indice, 'error', mensaje)."""
    idioma, tessdata, dpi, _omitir = _AJUSTES
    try:
        return indice, "ok", texto_de_pagina(_DOC[indice], idioma, tessdata, dpi)
    except Exception as error:
        return indice, "error", str(error)
