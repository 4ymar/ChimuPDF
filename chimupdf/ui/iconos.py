"""Íconos de línea (SVG de 24x24) que cambian de color según el tema."""
from PySide6.QtCore import QByteArray, Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

# clave -> contenido del SVG (trazos con currentColor)
ICONOS = {
    "abrir": '<path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>',
    "guardar": '<path d="M5 3h11l4 4v12a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2z"/><path d="M7 3v5h8V3"/><path d="M7 21v-7h10v7"/>',
    "rotar_izq": '<path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/>',
    "rotar_der": '<path d="M21 12a9 9 0 1 1-9-9 9.75 9.75 0 0 1 6.74 2.74L21 8"/><path d="M21 3v5h-5"/>',
    "subir": '<path d="M12 19V5"/><path d="m5 12 7-7 7 7"/>',
    "bajar": '<path d="M12 5v14"/><path d="m19 12-7 7-7-7"/>',
    "eliminar": '<path d="M3 6h18"/><path d="M8 6V4a1 1 0 0 1 1-1h6a1 1 0 0 1 1 1v2"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/><path d="M10 11v6M14 11v6"/>',
    "alejar": '<circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/><path d="M8 11h6"/>',
    "acercar": '<circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/><path d="M8 11h6M11 8v6"/>',
    "ajustar": '<path d="M3 5v14M21 5v14"/><path d="M7 12h10"/><path d="m10 9-3 3 3 3M14 9l3 3-3 3"/>',
    "seleccionar": '<path d="M5 3l14 8-6 2-2 6z"/>',
    "resaltar": '<path d="m9 11-6 6v3h9l3-3"/><path d="m22 12-4.6 4.6a2 2 0 0 1-2.8 0l-5.2-5.2a2 2 0 0 1 0-2.8L14 4"/>',
    "subrayar": '<path d="M6 4v6a6 6 0 0 0 12 0V4"/><path d="M4 21h16"/>',
    "tachar": '<path d="M16 4H9a3 3 0 0 0-2.83 4"/><path d="M14 12a4 4 0 0 1 0 8H6"/><path d="M4 12h16"/>',
    "nota": '<path d="M4 4h16v10l-6 6H4z"/><path d="M14 20v-6h6"/>',
    "texto": '<path d="M4 7V5h16v2"/><path d="M12 5v14"/><path d="M9 19h6"/>',
    "rectangulo": '<rect x="4" y="6" width="16" height="12" rx="1.5"/>',
    "flecha": '<path d="M7 17 17 7"/><path d="M8 7h9v9"/>',
    "lapiz": '<path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4z"/>',
    "firma": '<path d="M3 14c2-5 4-5 5-1s2 3 4-2 3-1 4 1"/><path d="M3 20h18"/>',
    "color": '<path d="M12 3s6 6.5 6 11a6 6 0 0 1-12 0c0-4.5 6-11 6-11z"/>',
    "usuario": '<circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/>',
    "editar_texto": '<path d="M9 4h6"/><path d="M12 4v16"/><path d="M9 20h6"/>',
    "agregar_texto": '<path d="M4 6V4h12v2"/><path d="M10 4v12"/><path d="M7.5 16h5"/><path d="M18 14v6M15 17h6"/>',
    "borrar": '<path d="m7 21-4.3-4.3c-1-1-1-2.5 0-3.4l9.6-9.6c1-1 2.5-1 3.4 0l5.6 5.6c1 1 1 2.5 0 3.4L13 21"/><path d="M22 21H7"/><path d="m5 11 9 9"/>',
    "imagen": '<rect x="3" y="4" width="18" height="16" rx="2"/><circle cx="9" cy="10" r="1.5"/><path d="m21 16-5-5-8 8"/>',
    "elegir_imagen": '<path d="M4 8V5a1 1 0 0 1 1-1h3M16 4h3a1 1 0 0 1 1 1v3M20 16v3a1 1 0 0 1-1 1h-3M8 20H5a1 1 0 0 1-1-1v-3"/><circle cx="12" cy="12" r="1.5"/>',
    "mover": '<path d="M5 9l-3 3 3 3M9 5l3-3 3 3M15 19l-3 3-3-3M19 9l3 3-3 3"/><path d="M2 12h20M12 2v20"/>',
    "buscar": '<circle cx="10" cy="10" r="6"/><path d="m21 21-6-6"/><path d="M8 10h4"/>',
    "modo_ver": '<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/>',
    "modo_anotar": '<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/><path d="M8 8h8"/><path d="M8 12h5"/>',
    "modo_editar": '<path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>',
    "deshacer": '<path d="m9 14-5-5 5-5"/><path d="M20 20v-7a4 4 0 0 0-4-4H4"/>',
    "rehacer": '<path d="m15 14 5-5-5-5"/><path d="M4 20v-7a4 4 0 0 1 4-4h12"/>',
}

ESCALA = 2  # se dibuja al doble para que se vea nítido


def _pixmap(clave, color, lado):
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
        f'stroke="{color}" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round">'
        f"{ICONOS[clave]}</svg>"
    )
    pm = QPixmap(lado * ESCALA, lado * ESCALA)
    pm.fill(Qt.GlobalColor.transparent)
    pintor = QPainter(pm)
    QSvgRenderer(QByteArray(svg.encode("utf-8"))).render(pintor)
    pintor.end()
    pm.setDevicePixelRatio(ESCALA)
    return pm


def crear_icono(clave, color, color_desactivado, color_marcado, lado=18):
    """QIcon con tres estados: normal, desactivado y marcado (herramienta activa)."""
    icono = QIcon()
    icono.addPixmap(_pixmap(clave, color, lado), QIcon.Mode.Normal, QIcon.State.Off)
    icono.addPixmap(_pixmap(clave, color_desactivado, lado), QIcon.Mode.Disabled, QIcon.State.Off)
    icono.addPixmap(_pixmap(clave, color_marcado, lado), QIcon.Mode.Normal, QIcon.State.On)
    icono.addPixmap(_pixmap(clave, color_marcado, lado), QIcon.Mode.Active, QIcon.State.On)
    return icono
