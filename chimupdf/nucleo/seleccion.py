"""Selección de texto del PDF para copiarlo. Sin interfaz gráfica."""
import pymupdf

from .anotaciones import _palabras_entre, _punto


def _agrupar(pagina, palabras):
    """(rects por línea en coordenadas visuales, texto) de una lista de palabras de get_text('words')."""
    lineas = {}
    for w in palabras:
        clave = (w[5], w[6])
        r = pymupdf.Rect(w[:4])
        if clave in lineas:
            lineas[clave][0] = lineas[clave][0] | r
            lineas[clave][1].append(w[4])
        else:
            lineas[clave] = [r, [w[4]]]
    rects = [tuple(r * pagina.rotation_matrix) for r, _ in lineas.values()]
    texto = "\n".join(" ".join(ws) for _, ws in lineas.values())
    return rects, texto


def texto_entre(pagina, p1, p2, palabras=None):
    """Rects y texto de lo que hay entre dos puntos (coordenadas visuales)."""
    entre = _palabras_entre(pagina, _punto(pagina, p1), _punto(pagina, p2), palabras=palabras)
    return _agrupar(pagina, entre)


def palabra_en(pagina, p, palabras=None, tolerancia=2):
    """Rects y texto de la palabra bajo el punto p (coordenadas visuales)."""
    pt = _punto(pagina, p)
    if palabras is None:
        palabras = pagina.get_text("words")
    for w in palabras:
        r = pymupdf.Rect(w[:4])
        r = pymupdf.Rect(r.x0 - tolerancia, r.y0 - tolerancia, r.x1 + tolerancia, r.y1 + tolerancia)
        if r.contains(pt):
            return _agrupar(pagina, [w])
    return [], ""