"""Edición de texto e imágenes dentro de las páginas del PDF. Sin interfaz gráfica.

Los puntos que reciben estas funciones están en coordenadas "visuales" (la página
tal como se ve en pantalla, ya rotada), igual que en anotaciones.py.
"""
import math
from dataclasses import dataclass

import pymupdf

from .anotaciones import _a_pagina, _punto, _rect_visual

BLANCO = (1.0, 1.0, 1.0)
NEGRO = (0.0, 0.0, 0.0)

# nombre que se muestra -> código interno de la familia
FAMILIAS = {
    "Helvetica (sin serifa)": "helv",
    "Times (con serifa)": "tiro",
    "Courier (monoespaciada)": "cour",
}
# familia -> (normal, negrita, cursiva, negrita+cursiva)
_TABLA = {
    "helv": ("helv", "hebo", "heit", "hebi"),
    "tiro": ("tiro", "tibo", "tiit", "tibi"),
    "cour": ("cour", "cobo", "coit", "cobi"),
}


@dataclass
class EstiloTexto:
    familia: str = "helv"
    tamano: float = 11.0
    negrita: bool = False
    cursiva: bool = False
    color: tuple = NEGRO

    @property
    def fontname(self):
        normal, negrita, cursiva, ambas = _TABLA[self.familia]
        if self.negrita and self.cursiva:
            return ambas
        return negrita if self.negrita else cursiva if self.cursiva else normal


@dataclass
class ZonaTexto:
    """Lo que hay en una zona de la página: texto, estilo detectado y orientación."""
    texto: str
    estilo: EstiloTexto
    rotacion: int  # 0/90/180/270: dirección en que corre el texto
    origen: tuple  # punto de la línea base del primer fragmento (o None)
    tiene_texto: bool


# ---------- detección de estilo ----------
def _rotacion_de_direccion(direccion):
    dx, dy = direccion
    if abs(dx) >= abs(dy):
        return 0 if dx > 0 else 180
    return 90 if dy < 0 else 270


def _familia(nombre, banderas):
    n = nombre.lower()
    if banderas & 8 or any(k in n for k in ("courier", "mono", "consol")):
        return "cour"
    if "sans" not in n and (banderas & 4 or any(k in n for k in ("times", "serif", "georgia", "garamond", "cambria", "palatino"))):
        return "tiro"
    return "helv"


def detectar_zona(pagina, rect, rotacion_defecto=0):
    """Analiza el texto dentro de 'rect' (coordenadas de página) y deduce su estilo."""
    texto = pagina.get_text("text", clip=rect).strip()
    for bloque in pagina.get_text("dict", clip=rect)["blocks"]:
        if bloque["type"] != 0:
            continue
        for linea in bloque["lines"]:
            for span in linea["spans"]:
                if not span["text"].strip():
                    continue
                n, b = span["font"].lower(), span["flags"]
                estilo = EstiloTexto(
                    familia=_familia(span["font"], b),
                    tamano=round(span["size"], 1),
                    negrita=bool(b & 16) or "bold" in n or "black" in n,
                    cursiva=bool(b & 2) or "italic" in n or "oblique" in n,
                    color=tuple(pymupdf.sRGB_to_pdf(span["color"])),
                )
                return ZonaTexto(texto, estilo, _rotacion_de_direccion(linea["dir"]), tuple(span["origin"]), True)
    return ZonaTexto(texto, EstiloTexto(), rotacion_defecto, None, bool(texto))


def zona_en(pagina, p1, p2):
    """Rect (en coordenadas de página) de lo arrastrado y análisis de su contenido."""
    rect = _a_pagina(pagina, _rect_visual(p1, p2))
    return rect, detectar_zona(pagina, rect, rotacion_defecto=pagina.rotation)


# ---------- escritura ----------
def _tamano_que_cabe(pagina, rect, texto, estilo, rotacion):
    """Tamaño de letra (<= el pedido) con el que el texto cabe en rect. Prueba en una hoja aparte."""
    ancho, alto = pagina.mediabox_size
    prueba = pymupdf.open()
    hoja = prueba.new_page(width=ancho, height=alto)
    try:
        tam = estilo.tamano
        min_tam = max(3.0, min(estilo.tamano, 5.0))
        while tam >= min_tam:
            rc = hoja.insert_textbox(
                rect, texto, fontname=estilo.fontname, fontsize=tam, rotate=rotacion, align=0
            )
            if rc >= 0:
                return tam
            tam -= 0.5
        raise ValueError("El texto nuevo no cabe en esa zona. Haz la zona más grande.")
    finally:
        prueba.close()


def _escribir_caja(pagina, rect, texto, estilo, rotacion):
    tam = _tamano_que_cabe(pagina, rect, texto, estilo, rotacion)
    pagina.insert_textbox(
        rect, texto, fontname=estilo.fontname, fontsize=tam, color=estilo.color,
        rotate=rotacion, align=0,
    )


def _redactar(pagina, rect, relleno, imagenes):
    """Quita el contenido bajo 'rect'. relleno=None no pinta nada."""
    pagina.add_redact_annot(rect, fill=relleno if relleno else False)
    pagina.apply_redactions(
        images=imagenes, graphics=pymupdf.PDF_REDACT_LINE_ART_NONE, text=pymupdf.PDF_REDACT_TEXT_REMOVE
    )


def reemplazar_texto_zona(pagina, p1, p2, texto, estilo, rotacion, tapar_fondo):
    """Borra lo que hay en la zona y escribe 'texto' en su lugar."""
    rect_borrar = _a_pagina(pagina, _rect_visual(p1, p2))
    rect_escribir = _a_pagina(pagina, _rect_visual(p1, p2, min_alto=estilo.tamano * 1.4))
    _tamano_que_cabe(pagina, rect_escribir, texto, estilo, rotacion)  # falla antes de borrar nada
    if tapar_fondo:
        _redactar(pagina, rect_borrar, BLANCO, pymupdf.PDF_REDACT_IMAGE_PIXELS)
    else:
        _redactar(pagina, rect_borrar, None, pymupdf.PDF_REDACT_IMAGE_NONE)
    _escribir_caja(pagina, rect_escribir, texto, estilo, rotacion)


def agregar_texto(pagina, p1, p2, texto, estilo, ancho_clic=250):
    """Agrega texto nuevo sin borrar nada. Con un clic usa un ancho estándar; arrastrando, el área."""
    if abs(p2[0] - p1[0]) < 8 or abs(p2[1] - p1[1]) < 8:
        alto = max(pagina.rect.height - p1[1], estilo.tamano * 2)
        visual = pymupdf.Rect(p1[0], p1[1], p1[0] + ancho_clic, p1[1] + min(alto, 600))
    else:
        visual = _rect_visual(p1, p2)
    rect = _a_pagina(pagina, visual)
    _escribir_caja(pagina, rect, texto, estilo, pagina.rotation)


def borrar_zona(pagina, p1, p2, relleno=BLANCO):
    """Redacción permanente: elimina texto e imagen bajo la zona y la pinta del color indicado."""
    rect = _a_pagina(pagina, _rect_visual(p1, p2))
    _redactar(pagina, rect, relleno, pymupdf.PDF_REDACT_IMAGE_PIXELS)


# ---------- buscar y reemplazar ----------
def buscar_en_documento(documento, texto):
    """{índice de página: [rects]} con las coincidencias de 'texto'."""
    encontrados = {}
    for i in range(documento.num_paginas):
        rects = documento.pagina(i).search_for(texto)
        if rects:
            encontrados[i] = rects
    return encontrados


def _punto_linea_base(rect, rotacion, origen):
    if origen is None:
        origen = (rect.x0, rect.y1)
    if rotacion == 0:
        return pymupdf.Point(rect.x0, origen[1])
    if rotacion == 180:
        return pymupdf.Point(rect.x1, origen[1])
    if rotacion == 90:
        return pymupdf.Point(origen[0], rect.y1)
    return pymupdf.Point(origen[0], rect.y0)


def reemplazar_todo(documento, buscar, nuevo, estilo=None, ajustar=True):
    """Reemplaza todas las coincidencias. estilo=None iguala la fuente de cada coincidencia.

    Devuelve (total de reemplazos, lista de páginas modificadas).
    """
    total, paginas = 0, []
    for i, rects in buscar_en_documento(documento, buscar).items():
        pagina = documento.pagina(i)
        trabajos = []
        for r in rects:
            zona = detectar_zona(pagina, r, rotacion_defecto=0)
            trabajos.append((pymupdf.Rect(r), zona))
        for r, _zona in trabajos:
            pagina.add_redact_annot(r, fill=False)
        pagina.apply_redactions(
            images=pymupdf.PDF_REDACT_IMAGE_NONE,
            graphics=pymupdf.PDF_REDACT_LINE_ART_NONE,
            text=pymupdf.PDF_REDACT_TEXT_REMOVE,
        )
        for r, zona in trabajos:
            est = estilo or zona.estilo
            tam = est.tamano  # inicializar para que el bloque ajustar lo pueda modificar
            if ajustar and nuevo:
                largo_original = r.width if zona.rotacion in (0, 180) else r.height
                largo_nuevo = pymupdf.get_text_length(nuevo, fontname=est.fontname, fontsize=tam)
                if largo_nuevo > largo_original > 0:
                    tam = max(min(tam, 4.0), tam * largo_original / largo_nuevo)
            if nuevo:
                pagina.insert_text(
                    _punto_linea_base(r, zona.rotacion, zona.origen), nuevo,
                    fontname=est.fontname, fontsize=tam, color=est.color, rotate=zona.rotacion,
                )
            total += 1
        paginas.append(i)
        documento.modificado = True
    return total, paginas


# ---------- imágenes ----------
def _rotacion_de_transformacion(t):
    a, b = t[0], t[1]
    if abs(a) >= abs(b):
        return 0 if a > 0 else 180
    return 90 if b < 0 else 270


def imagen_en(pagina, p):
    """(xref, bbox, rotación) de la imagen más pequeña bajo el punto, o None."""
    pt = _punto(pagina, p)
    mejor = None
    for info in pagina.get_image_info(xrefs=True):
        if info.get("xref", 0) <= 0:
            continue
        r = pymupdf.Rect(info["bbox"])
        if r.contains(pt) and (mejor is None or r.width * r.height < mejor[0]):
            mejor = (r.width * r.height, info["xref"], tuple(r), _rotacion_de_transformacion(info["transform"]))
    return None if mejor is None else mejor[1:]


def rect_visual_de(pagina, bbox):
    r = pymupdf.Rect(bbox) * pagina.rotation_matrix
    return (r.x0, r.y0, r.x1, r.y1)


def _ajustar(proporcion, p1, p2, ancho_clic):
    """Rect visual con la proporción dada: centrado en el clic o ajustado al área arrastrada."""
    if proporcion <= 0:
        proporcion = 1.0
    if abs(p2[0] - p1[0]) < 8 or abs(p2[1] - p1[1]) < 8:
        w, h = ancho_clic, ancho_clic / proporcion
        cx, cy = p1
    else:
        area = _rect_visual(p1, p2)
        if area.height <= 0:
            return area
        if area.width / area.height > proporcion:
            h = area.height
            w = h * proporcion
        else:
            w = area.width
            h = w / proporcion
        cx, cy = (area.x0 + area.x1) / 2, (area.y0 + area.y1) / 2
    return pymupdf.Rect(cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)

def _encajar_en_rect(proporcion, rect):
    """Ajusta proporcionalmente dentro de un rectángulo dado."""
    if proporcion <= 0:
        proporcion = 1.0
    w_disp, h_disp = rect.width, rect.height
    if h_disp <= 0:
        return rect
    if w_disp / h_disp > proporcion:
        h = h_disp
        w = h * proporcion
    else:
        w = w_disp
        h = w / proporcion
    cx, cy = (rect.x0 + rect.x1) / 2.0, (rect.y0 + rect.y1) / 2.0
    return pymupdf.Rect(cx - w / 2.0, cy - h / 2.0, cx + w / 2.0, cy + h / 2.0)

def insertar_imagen(pagina, ruta, p1, p2, ancho_clic=200):
    pix = pymupdf.Pixmap(ruta)
    proporcion = pix.width / pix.height if pix.height > 0 else 1.0
    visual = _ajustar(proporcion, p1, p2, ancho_clic)
    pagina.insert_image(
        _a_pagina(pagina, visual), filename=ruta, rotate=pagina.rotation, keep_proportion=False
    )
    centro = ((visual.x0 + visual.x1) / 2, (visual.y0 + visual.y1) / 2)
    return imagen_en(pagina, centro)  # (xref, bbox, rotación) de la imagen recién puesta

def eliminar_imagen(pagina, xref, bbox):
    """True si, además de la imagen indicada, otra imagen se superpone a su zona."""
    zona = pymupdf.Rect(bbox)
    for info in pagina.get_image_info(xrefs=True):
        if info.get("xref", 0) == xref:
            continue
        if pymupdf.Rect(info["bbox"]).intersects(zona):
            return True
    return False


def _usos_de_imagen(pagina, xref):
    """Cuántas veces se muestra esta imagen en todo el documento."""
    doc = pagina.parent
    total = 0
    for i in range(doc.page_count):
        if any(item[0] == xref for item in doc.get_page_images(i, full=True)):
            total += len(doc[i].get_image_rects(xref))
    return total


def _quitar_imagen(pagina, xref, bbox):
    """Quita una imagen de la página sin llevarse otras por error.

    1) Sin otras imágenes encima: redacción de la zona (afecta solo a esta página).
    2) Con otras encima y la imagen usada solo aquí: delete_image (no toca las otras).
    3) Con otras encima y la imagen repetida en el documento: no hace nada y avisa.
    """
    if not _otras_imagenes_superpuestas(pagina, xref, bbox):
        pagina.add_redact_annot(pymupdf.Rect(bbox), fill=False)
        pagina.apply_redactions(
            images=pymupdf.PDF_REDACT_IMAGE_REMOVE,
            graphics=pymupdf.PDF_REDACT_LINE_ART_NONE,
            text=pymupdf.PDF_REDACT_TEXT_NONE,
        )
    elif _usos_de_imagen(pagina, xref) <= 1:
        pagina.delete_image(xref)
    else:
        raise ValueError(
            "Esta imagen se repite en otras partes del documento y hay otra imagen "
            "superpuesta.\nQuitarla desde aquí afectaría a las demás o borraría la otra imagen."
        )


def eliminar_imagen(pagina, xref, bbox):
    _quitar_imagen(pagina, xref, bbox)



def reemplazar_imagen(pagina, xref, bbox, ruta):
    """Quita la imagen y coloca otra del mismo tamaño aproximado (conserva su proporción)."""
    pix = pymupdf.Pixmap(ruta)
    proporcion = pix.width / pix.height if pix.height > 0 else 1.0
    visual_vieja = pymupdf.Rect(bbox) * pagina.rotation_matrix
    visual = _encajar_en_rect(proporcion, visual_vieja)
    eliminar_imagen(pagina, xref, bbox)
    pagina.insert_image(
        _a_pagina(pagina, visual), filename=ruta, rotate=pagina.rotation, keep_proportion=False
    )



def _pixmap_de_xref(pagina, xref):
    doc = pagina.parent
    pix = pymupdf.Pixmap(doc, xref)
    if pix.colorspace is not None and pix.colorspace.n > 3:
        pix = pymupdf.Pixmap(pymupdf.csRGB, pix)
    for datos in pagina.get_images(full=True):
        if datos[0] == xref and datos[1] > 0 and not pix.alpha:  # tiene máscara de transparencia
            try:
                mask = pymupdf.Pixmap(doc, datos[1])
                if mask.colorspace is not None and mask.colorspace.n != 1:
                    mask = pymupdf.Pixmap(pymupdf.csGRAY, mask)
                pix = pymupdf.Pixmap(pix, mask)
            except Exception:
                pass
            break
    return pix


def mover_imagen(pagina, xref, bbox, rotacion, p1, p2):
    """Mueve y/o cambia el tamaño de una imagen: se coloca en el área arrastrada (o centrada en el clic)."""
    pix = _pixmap_de_xref(pagina, xref)
    visual_vieja = pymupdf.Rect(bbox) * pagina.rotation_matrix
    proporcion = visual_vieja.width / visual_vieja.height if visual_vieja.height > 0 else 1.0
    visual = _ajustar(proporcion, p1, p2, visual_vieja.width)
    eliminar_imagen(pagina, xref, bbox)
    rect_pag = _a_pagina(pagina, visual)
    xref_nuevo = pagina.insert_image(rect_pag, pixmap=pix, rotate=rotacion, keep_proportion=False)
    return (xref_nuevo, tuple(rect_pag), rotacion)
