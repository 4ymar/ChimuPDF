"""Barra lateral izquierda única: selector de modo (Ver / Anotar / Editar) y herramientas del modo."""
from PySide6.QtCore import QObject, Qt
from PySide6.QtGui import QAction, QActionGroup
from PySide6.QtWidgets import QToolBar

MODOS = [
    ("ver", "Modo Ver"),
    ("anotar", "Modo Anotar"),
    ("editar", "Modo Editar"),
]


class BarraModos(QObject):
    """Muestra los botones de modo y, debajo, solo las herramientas del modo activo.

    Las acciones siguen perteneciendo a Anotador y Editor (y a sus menús); esta clase solo
    decide cuáles se muestran en la barra y reinicia la herramienta al cambiar de modo.
    """

    def __init__(self, ventana):
        super().__init__(ventana)
        self.v = ventana
        self.modo = "ver"
        self._doc_visto = None

        self.grupo_modos = QActionGroup(ventana)
        self.acciones = {}
        for clave, texto in MODOS:
            accion = QAction(texto, ventana)
            accion.setCheckable(True)
            accion.setData(clave)
            self.grupo_modos.addAction(accion)
            self.acciones[clave] = accion
        self.acciones["ver"].setChecked(True)
        self.grupo_modos.triggered.connect(
            lambda accion: self._aplicar_modo(accion.data(), reiniciar=True)
        )

        self._sep_modos = self._separador()
        self._sep_extra = self._separador()
        a, e = ventana.anotador, ventana.editor
        self._contenido = {
            "ver": [],
            "anotar": list(a.acciones_herramienta.values()) + [self._sep_extra, a.a_color, a.a_firma],
            "editar": list(e.herramientas.values()) + [self._sep_extra, e.a_buscar],
        }

        self.barra = QToolBar("Herramientas")
        self.barra.setObjectName("BarraLateral")
        self.barra.setMovable(False)
        self.barra.setFloatable(False)
        self.barra.setAllowedAreas(Qt.ToolBarArea.LeftToolBarArea)
        ventana.addToolBar(Qt.ToolBarArea.LeftToolBarArea, self.barra)
        self._reconstruir()

        # Si una herramienta se elige desde un menú, la barra pasa al modo al que pertenece
        a.grupo.triggered.connect(self._al_elegir_herramienta)

    def _separador(self):
        sep = QAction(self.v)
        sep.setSeparator(True)
        return sep

    def _reconstruir(self):
        self.barra.clear()
        self.barra.addActions(list(self.acciones.values()))
        contenido = self._contenido[self.modo]
        if contenido:
            self.barra.addAction(self._sep_modos)
            self.barra.addActions(contenido)

    def _aplicar_modo(self, modo, reiniciar=False):
        self.modo = modo
        self.acciones[modo].setChecked(True)
        if reiniciar:
            self._reiniciar_herramienta()
            if modo == "editar":
                self.v.statusBar().showMessage(
                    "Modo Editar: elige una herramienta de la barra lateral.", 5000
                )
        self._reconstruir()

    def _reiniciar_herramienta(self):
        """Al cambiar de modo: Anotar arranca en Seleccionar; Ver y Editar, sin herramienta activa."""
        v = self.v
        v.anotador.limpiar_seleccion()
        v.editor.limpiar_imagen()
        v.seleccion_texto.limpiar()
        for accion in v.anotador.grupo.actions():  # el grupo incluye también las del editor
            accion.setChecked(False)
        if self.modo == "anotar":
            v.anotador.acciones_herramienta["seleccionar"].setChecked(True)
            v.visor.lienzo.establecer_herramienta("seleccionar")
        else:
            v.visor.lienzo.establecer_herramienta("ver")

    def _al_elegir_herramienta(self, accion):
        clave = accion.data()
        if clave in self.v.anotador.acciones_herramienta:
            modo = "anotar"
        elif clave in self.v.editor.herramientas:
            modo = "editar"
        else:
            return
        if modo != self.modo:
            self._aplicar_modo(modo)  # sin reiniciar: la herramienta ya quedó elegida

    def actualizar_estado(self):
        doc = self.v.documento
        for accion in self.acciones.values():
            accion.setEnabled(doc is not None)
        self.barra.setVisible(doc is not None)
        if doc is not self._doc_visto:  # documento nuevo: siempre se empieza en modo Ver
            self._doc_visto = doc
            if doc is not None:
                self._aplicar_modo("ver", reiniciar=True)