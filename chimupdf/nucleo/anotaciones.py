"""Creación y manejo de anotaciones PDF estándar (editables). Sin interfaz gráfica.

Todos los puntos que reciben estas funciones están en coordenadas "visuales":
puntos PDF medidos sobre la página tal como se ve en pantalla (ya rotada).
"""
import re

import pymupdf

COLORES = {
    "resaltar": (1.0, 0.92, 0.0),
    "subrayar": (0.0, 0.35, 0.9),
    "tachar": (1.0, 0.0, 0.0),
    "forma": (1.0, 0.0, 0.0),
    "lapiz": (1.0, 0.0, 0.0),
    "texto": (0.0, 0.0, 0.0),
}

NOMBRES_TIPO = {
    "Highlight": "Resaltado",
    "Underline": "Subrayado",
    "StrikeOut": "Tachado",
    "Text": "Nota",
    "FreeText": "Texto libre",
    "Square": "Rectángulo",
    "Line": "Flecha",
    "Ink": "Dibujo a mano alzada",
    "Stamp": "Firma / sello",
}


def _punto(pagina, p):
    return pymupdf.Point(p) * pagina.derotation_matrix


def _rect_visual(p1, p2, min_ancho=0, min_alto=0):
    x0, x1 = sorted((p1[0], p2[0]))
    y0, y1 = sorted((p1[1], p2[1]))
    return pymupdf.Rect(x0, y0, x0 + max(x1 - x0, min_ancho), y0 + max(y1 - y0, min_alto))


def _a_pagina(pagina, rect_visual):
    return rect_visual * pagina.derotation_matrix


def _colorear(anot, color, defecto, ancho=None):
    anot.set_colors(stroke=color or defecto)
    if ancho is not None:
        anot.set_border(width=ancho)
    anot.update()


# ---------- crear ----------
def _distancia(rect, pt):
    dx = max(rect.x0 - pt.x, 0, pt.x - rect.x1)
    dy = max(rect.y0 - pt.y, 0, pt.y - rect.y1)
    return (dx * dx + dy * dy) ** 0.5


def _palabras_entre(pagina, a, b, margen=20, palabras=None):
    """Palabras (tuplas de get_text('words')) entre los puntos a y b, en coordenadas de página."""
    if palabras is None:
        palabras = pagina.get_text("words")  # (x0, y0, x1, y1, texto, bloque, línea, nº)
    if not palabras:
        return []
    rects = [pymupdf.Rect(w[:4]) for w in palabras]

    def mas_cercana(pt):
        distancias = [_distancia(r, pt) for r in rects]
        i = min(range(len(rects)), key=distancias.__getitem__)
        return i, distancias[i]

    ia, da = mas_cercana(a)
    ib, db = mas_cercana(b)
    if da <= margen and db <= margen:
        elegidas = range(min(ia, ib), max(ia, ib) + 1)
    else:  # extremos sobre espacio en blanco: usa las palabras dentro del área arrastrada
        area = pymupdf.Rect(a, b)
        area.normalize()
        elegidas = [i for i, r in enumerate(rects) if r.intersects(area)]
    return [palabras[i] for i in elegidas]


def _quads_seleccion(pagina, a, b, margen=20):
    """Quads (uno por línea) de las palabras entre los puntos a y b, en coordenadas de página."""
    lineas = {}  # une las palabras de una misma línea en un solo rectángulo
    for w in _palabras_entre(pagina, a, b, margen):
        r = pymupdf.Rect(w[:4])
        clave = (w[5], w[6])
        lineas[clave] = lineas[clave] | r if clave in lineas else r
    return [r.quad for r in lineas.values()]


def marcar_texto(pagina, tipo, p1, p2, color=None):
    """Resalta, subraya o tacha el texto entre dos puntos (como al seleccionar con el mouse)."""
    metodos = {
        "resaltar": pagina.add_highlight_annot,
        "subrayar": pagina.add_underline_annot,
        "tachar": pagina.add_strikeout_annot,
    }
    quads = _quads_seleccion(pagina, _punto(pagina, p1), _punto(pagina, p2))
    if not quads:
        raise ValueError(
            "No se encontró texto en esa zona.\n"
            "Si el PDF es una imagen escaneada, primero necesitará OCR."
        )
    anot = metodos[tipo](quads=quads)
    _colorear(anot, color, COLORES[tipo])
    return anot


def nota(pagina, p, texto, color=None):
    anot = pagina.add_text_annot(_punto(pagina, p), texto, icon="Note")
    if color:
        anot.set_colors(stroke=color)
        anot.update()
    return anot


def texto_libre(pagina, p1, p2, texto, color=None, tamano=12):
    rect = _a_pagina(pagina, _rect_visual(p1, p2, min_ancho=140, min_alto=28))
    anot = pagina.add_freetext_annot(
        rect, texto, fontsize=tamano, text_color=color or COLORES["texto"],
        rotate=pagina.rotation,
    )
    return anot


def rectangulo(pagina, p1, p2, color=None):
    anot = pagina.add_rect_annot(_a_pagina(pagina, _rect_visual(p1, p2)))
    _colorear(anot, color, COLORES["forma"], ancho=1.5)
    return anot


def flecha(pagina, p1, p2, color=None):
    anot = pagina.add_line_annot(_punto(pagina, p1), _punto(pagina, p2))
    anot.set_line_ends(pymupdf.PDF_ANNOT_LE_NONE, pymupdf.PDF_ANNOT_LE_OPEN_ARROW)
    _colorear(anot, color, COLORES["forma"], ancho=1.5)
    return anot


def lapiz(pagina, puntos, color=None):
    if len(puntos) < 2:
        raise ValueError("Dibuja un trazo arrastrando el mouse.")
    if len(puntos) > 600:  # simplifica trazos muy largos
        paso = len(puntos) // 600 + 1
        puntos = puntos[::paso] + [puntos[-1]]
    trazo = [tuple(_punto(pagina, p)) for p in puntos]
    anot = pagina.add_ink_annot([trazo])
    _colorear(anot, color, COLORES["lapiz"], ancho=2)
    return anot


def firma(pagina, ruta_png, p1, p2, ruta_estampa=None, ancho_clic=150):
    """Coloca la imagen de la firma. Con un clic usa un tamaño estándar; arrastrando, ajusta al área.

    ruta_estampa: imagen ya girada para páginas rotadas (si no, se usa ruta_png).
    """
    pix = pymupdf.Pixmap(ruta_png)
    proporcion = pix.width / pix.height if pix.height > 0 else 1.0
    ancho_arrastre = abs(p2[0] - p1[0])
    alto_arrastre = abs(p2[1] - p1[1])
    if ancho_arrastre < 8 or alto_arrastre < 8:  # clic: centrar en el punto
        w, h = ancho_clic, ancho_clic / proporcion
        cx, cy = p1
    else:
        area = _rect_visual(p1, p2)
        if area.width / area.height > proporcion:
            h = area.height
            w = h * proporcion
        else:
            w = area.width
            h = w / proporcion
        cx, cy = (area.x0 + area.x1) / 2, (area.y0 + area.y1) / 2
    visual = pymupdf.Rect(cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)
    return pagina.add_stamp_annot(_a_pagina(pagina, visual), stamp=ruta_estampa or ruta_png)


# ---------- seleccionar / borrar ----------
def anotacion_en(pagina, p, tolerancia=3):
    """Devuelve el xref de la anotación bajo el punto (la más pequeña si hay varias) o None."""
    pt = _punto(pagina, p)
    mejor, area_mejor = None, None
    for anot in pagina.annots():
        r = pymupdf.Rect(anot.rect)
        r.x0 -= tolerancia
        r.y0 -= tolerancia
        r.x1 += tolerancia
        r.y1 += tolerancia
        if r.contains(pt):
            area = r.width * r.height
            if mejor is None or area < area_mejor:
                mejor, area_mejor = anot.xref, area
    return mejor


def _buscar(pagina, xref):
    for anot in pagina.annots():
        if anot.xref == xref:
            return anot
    return None


def rect_visual(pagina, xref):
    """Rectángulo (x0, y0, x1, y1) de la anotación en coordenadas visuales, o None."""
    anot = _buscar(pagina, xref)
    if anot is None:
        return None
    r = pymupdf.Rect(anot.rect) * pagina.rotation_matrix
    return (r.x0, r.y0, r.x1, r.y1)


def nombre_tipo(pagina, xref):
    anot = _buscar(pagina, xref)
    if anot is None:
        return ""
    return NOMBRES_TIPO.get(anot.type[1], anot.type[1])


def borrar(pagina, xref):
    anot = _buscar(pagina, xref)
    if anot is None:
        return False
    pagina.delete_annot(anot)
    return True



# ---------- mover, redimensionar y leer ----------
CAPACIDAD = {  # qué se puede hacer con el mouse en cada tipo (set_rect solo vale para algunos)
    "Text": "mover",  # la nota es un ícono de tamaño fijo
    "FreeText": "ajustar",
    "Square": "ajustar",
    "Stamp": "proporcional",
}


def capacidad(pagina, xref):
    """'mover', 'ajustar' (tamaño libre), 'proporcional' o None según el tipo de anotación."""
    anot = _buscar(pagina, xref)
    return CAPACIDAD.get(anot.type[1]) if anot is not None else None


def reubicar(pagina, xref, rect_visual):
    """Mueve o redimensiona la anotación al rectángulo dado (coordenadas visuales)."""
    anot = _buscar(pagina, xref)
    if anot is None:
        return False
    tipo = anot.type[1]
    nuevo = _a_pagina(pagina, pymupdf.Rect(rect_visual))
    if CAPACIDAD.get(tipo) == "mover":  # conserva el tamaño del ícono; solo cambia la posición
        viejo = anot.rect
        cx, cy = (nuevo.x0 + nuevo.x1) / 2, (nuevo.y0 + nuevo.y1) / 2
        nuevo = pymupdf.Rect(
            cx - viejo.width / 2, cy - viejo.height / 2, cx + viejo.width / 2, cy + viejo.height / 2
        )
    if anot.set_rect(nuevo) is False:
        return False
    if tipo == "FreeText":  # el texto se vuelve a acomodar en el nuevo tamaño
        tamano, color = _estilo_freetext(pagina, xref)
        anot.update(fontsize=tamano, text_color=color)
    elif tipo == "Square":
        anot.update()
    return True


def contenido(pagina, xref):
    """Texto de una nota o de un texto libre; None si no es de ese tipo o está vacío."""
    anot = _buscar(pagina, xref)
    if anot is None or anot.type[1] not in ("Text", "FreeText"):
        return None
    return anot.info.get("content", "").strip() or None


def _estilo_freetext(pagina, xref):
    """(tamaño, color) del texto de un texto libre, leídos de su /DA; si no se pueden leer, los de por defecto."""
    tamano, color = 12.0, COLORES["texto"]
    try:
        da = pagina.parent.xref_get_key(xref, "DA")[1]
        m = re.search(r"([\d.]+)\s+Tf", da)
        if m:
            tamano = float(m.group(1))
        m = re.search(r"([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+rg", da)
        if m:
            color = tuple(float(g) for g in m.groups())
        else:
            m = re.search(r"([\d.]+)\s+g\b", da)
            if m:
                color = (float(m.group(1)),) * 3
    except Exception:
        pass
    return tamano, color


def cambiar_contenido(pagina, xref, texto):
    anot = _buscar(pagina, xref)
    if anot is None or anot.type[1] not in ("Text", "FreeText"):
        return False
    anot.set_info(content=texto)
    if anot.type[1] == "FreeText":
        tamano, color = _estilo_freetext(pagina, xref)
        anot.update(fontsize=tamano, text_color=color)
    else:
        anot.update()
    return True
