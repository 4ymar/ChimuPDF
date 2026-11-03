"""Tema claro/oscuro con los colores del logo, íconos en las barras y estilo general."""
from PySide6.QtCore import QObject, QSize, Qt
from PySide6.QtGui import QAction, QColor, QIcon, QPalette
from PySide6.QtWidgets import QApplication, QToolBar

from chimupdf.nucleo import config

from .iconos import crear_icono
from .recursos import ruta_recurso

# Paleta tomada del logo: negro, crema y terracota
CLARO = {
    "fondo": "#F4EEDF", "superficie": "#FBF7EC", "campo": "#FFFFFF", "texto": "#1E1D1A",
    "texto2": "#6B665A", "borde": "#D9CEB3", "hover": "#EADFC6", "acento": "#B86944",
    "sobre_acento": "#FFFFFF", "visor": "#DDD4BF", "desactivado": "#A8A292",
}
OSCURO = {
    "fondo": "#171918", "superficie": "#202322", "campo": "#2A2D2B", "texto": "#EDE3C9",
    "texto2": "#A39B86", "borde": "#363A38", "hover": "#2C302E", "acento": "#C9744B",
    "sobre_acento": "#FFFFFF", "visor": "#0F1110", "desactivado": "#6B6A62",
}


def _paleta(c):
    p = QPalette()
    for rol, clave in (
        (QPalette.ColorRole.Window, "fondo"), (QPalette.ColorRole.WindowText, "texto"),
        (QPalette.ColorRole.Base, "campo"), (QPalette.ColorRole.AlternateBase, "superficie"),
        (QPalette.ColorRole.Text, "texto"), (QPalette.ColorRole.Button, "superficie"),
        (QPalette.ColorRole.ButtonText, "texto"), (QPalette.ColorRole.Highlight, "acento"),
        (QPalette.ColorRole.HighlightedText, "sobre_acento"), (QPalette.ColorRole.ToolTipBase, "superficie"),
        (QPalette.ColorRole.ToolTipText, "texto"), (QPalette.ColorRole.PlaceholderText, "texto2"),
        (QPalette.ColorRole.Link, "acento"),
    ):
        p.setColor(rol, QColor(c[clave]))
    for rol in (QPalette.ColorRole.Text, QPalette.ColorRole.ButtonText, QPalette.ColorRole.WindowText):
        p.setColor(QPalette.ColorGroup.Disabled, rol, QColor(c["desactivado"]))
    return p


def _qss(c):
    return f"""
QMenuBar {{ background: {c['superficie']}; color: {c['texto']}; }}
QMenuBar::item {{ padding: 4px 10px; border-radius: 5px; background: transparent; }}
QMenuBar::item:selected {{ background: {c['hover']}; }}
QMenu {{ background: {c['superficie']}; color: {c['texto']}; border: 1px solid {c['borde']}; padding: 4px; }}
QMenu::item {{ padding: 5px 22px 5px 10px; border-radius: 4px; }}
QMenu::item:selected {{ background: {c['acento']}; color: {c['sobre_acento']}; }}
QMenu::item:disabled {{ color: {c['desactivado']}; }}
QMenu::separator {{ height: 1px; background: {c['borde']}; margin: 4px 6px; }}
QToolBar {{ background: {c['superficie']}; border: none; border-bottom: 1px solid {c['borde']}; padding: 1px 6px; spacing: 1px; }}
QToolBar::separator {{ background: {c['borde']}; width: 1px; margin: 5px 5px; }}
QToolButton {{ background: transparent; color: {c['texto']}; border: 1px solid transparent; border-radius: 6px; padding: 2px 7px 2px 5px; }}
QToolButton:hover {{ background: {c['hover']}; }}
QToolButton:checked {{ background: {c['acento']}; color: {c['sobre_acento']}; }}
QToolButton:disabled {{ color: {c['desactivado']}; }}
QToolButton:checked:disabled {{ background: transparent; }}
#BarraLateral {{ background: {c['superficie']}; border: none; border-right: 1px solid {c['borde']}; padding: 6px 4px; spacing: 3px; }}
#BarraLateral QToolButton {{ padding: 6px; }}
#BarraLateral::separator {{ background: {c['borde']}; height: 1px; margin: 6px 4px; }}
QStatusBar {{ background: {c['superficie']}; color: {c['texto2']}; border-top: 1px solid {c['borde']}; }}
QSplitter::handle {{ background: {c['borde']}; }}
QScrollArea > QWidget > QWidget {{ background: {c['visor']}; }}
QScrollArea {{ border: none; background: {c['visor']}; }}
QListWidget {{ background: {c['superficie']}; border: none; color: {c['texto']}; outline: 0; }}
QListWidget::item {{ border-radius: 6px; padding: 4px; margin: 1px 4px; }}
QListWidget::item:hover {{ background: {c['hover']}; }}
QListWidget::item:selected {{ background: {c['hover']}; border: 2px solid {c['acento']}; color: {c['texto']}; }}
QPushButton {{ background: {c['superficie']}; color: {c['texto']}; border: 1px solid {c['borde']}; border-radius: 6px; padding: 5px 14px; }}
QPushButton:hover {{ background: {c['hover']}; }}
QPushButton:default {{ border: 1px solid {c['acento']}; }}
QLineEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QComboBox {{ background: {c['campo']}; color: {c['texto']}; border: 1px solid {c['borde']}; border-radius: 5px; padding: 3px 6px; selection-background-color: {c['acento']}; selection-color: {c['sobre_acento']}; }}
QToolTip {{ background: {c['superficie']}; color: {c['texto']}; border: 1px solid {c['borde']}; padding: 3px; }}
#PantallaInicio {{ background: {c['fondo']}; }}
#TituloInicio {{ font-size: 30px; font-weight: 700; color: {c['texto']}; }}
#SubtituloInicio {{ font-size: 13px; color: {c['texto2']}; }}
#BotonPrincipal {{ background: {c['acento']}; color: {c['sobre_acento']}; border: none; border-radius: 8px; padding: 10px 26px; font-size: 15px; font-weight: 600; }}
#BotonPrincipal:hover {{ background: {c['acento']}; border: 2px solid {c['texto']}; padding: 8px 24px; }}
#ListaRecientes {{ background: {c['superficie']}; border: 1px solid {c['borde']}; border-radius: 10px; padding: 4px; }}
#BotonSecundario {{ padding: 7px 18px; }}
#BarraBusqueda {{ background: {c['superficie']}; border-top: 1px solid {c['borde']}; }}
"""


# (objeto, atributo o clave) -> (ícono, texto corto de la barra)
def _acciones_con_icono(v):
    a, e, m = v.anotador, v.editor, v.modos
    return [
        (v.a_abrir, "abrir", "Abrir"), (v.a_guardar, "guardar", "Guardar"),
        (v.a_deshacer, "deshacer", "Deshacer"), (v.a_rehacer, "rehacer", "Rehacer"),
        (v.a_rot_izq, "rotar_izq", "Girar izq."), (v.a_rot_der, "rotar_der", "Girar der."),
        (v.a_subir, "subir", "Subir"), (v.a_bajar, "bajar", "Bajar"),
        (v.a_eliminar, "eliminar", "Eliminar"),
        (v.a_alejar, "alejar", "Alejar"), (v.a_acercar, "acercar", "Acercar"),
        (v.a_ancho, "ajustar", "Ajustar"),
        (a.acciones_herramienta["seleccionar"], "seleccionar", "Seleccionar"),
        (a.acciones_herramienta["resaltar"], "resaltar", "Resaltar"),
        (a.acciones_herramienta["subrayar"], "subrayar", "Subrayar"),
        (a.acciones_herramienta["tachar"], "tachar", "Tachar"),
        (a.acciones_herramienta["nota"], "nota", "Nota"),
        (a.acciones_herramienta["texto"], "texto", "Texto"),
        (a.acciones_herramienta["rectangulo"], "rectangulo", "Rectángulo"),
        (a.acciones_herramienta["flecha"], "flecha", "Flecha"),
        (a.acciones_herramienta["lapiz"], "lapiz", "Lápiz"),
        (a.acciones_herramienta["firma"], "firma", "Firma"),
        (a.a_color, "color", "Color"), (a.a_firma, "usuario", "Mi firma"),
        (e.herramientas["editar_texto"], "editar_texto", "Editar"),
        (e.herramientas["agregar_texto"], "agregar_texto", "Agregar"),
        (e.herramientas["borrar_zona"], "borrar", "Borrar"),
        (e.herramientas["insertar_imagen"], "imagen", "Imagen"),
        (e.herramientas["seleccionar_imagen"], "elegir_imagen", "Elegir img."),
        (e.a_buscar, "buscar", "Reemplazar"),
        (m.acciones["ver"], "modo_ver", "Ver"),
        (m.acciones["anotar"], "modo_anotar", "Anotar"),
        (m.acciones["editar"], "modo_editar", "Editar"),
    ]


class Estetica(QObject):
    """Aplica el tema, el icono de la app, los íconos de las barras y el interruptor claro/oscuro."""

    def __init__(self, ventana):
        super().__init__(ventana)
        self.v = ventana
        self.oscuro = config.leer().get("tema") == "oscuro"
        self.v.setWindowIcon(QIcon(ruta_recurso("chimupdf.png")))
        QApplication.instance().setStyle("Fusion")

        self._acciones = _acciones_con_icono(ventana)
        for accion, _clave, corto in self._acciones:
            nombre = accion.text().replace("&", "").rstrip(".")
            accion.setIconText(corto)
            accion.setToolTip(nombre)
        for barra in ventana.findChildren(QToolBar):
            if barra.objectName() == "BarraLateral":  # solo íconos; el nombre sale en el tooltip
                barra.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
                barra.setIconSize(QSize(20, 20))
            else:
                barra.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
                barra.setIconSize(QSize(18, 18))

        self.a_tema = QAction("Tema &oscuro", ventana)
        self.a_tema.setCheckable(True)
        self.a_tema.setChecked(self.oscuro)
        self.a_tema.toggled.connect(self._cambiar_tema)
        for accion in ventana.menuBar().actions():
            if accion.text() == "&Ver":
                accion.menu().addSeparator()
                accion.menu().addAction(self.a_tema)
        self.aplicar()

    def _cambiar_tema(self, oscuro):
        self.oscuro = oscuro
        config.guardar("tema", "oscuro" if oscuro else "claro")
        self.aplicar()

    def aplicar(self):
        c = OSCURO if self.oscuro else CLARO
        app = QApplication.instance()
        app.setPalette(_paleta(c))
        app.setStyleSheet(_qss(c))
        for accion, clave, _corto in self._acciones:
            accion.setIcon(crear_icono(clave, c["texto"], c["desactivado"], c["sobre_acento"]))
