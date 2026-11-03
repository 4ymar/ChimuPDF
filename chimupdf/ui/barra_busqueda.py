"""Barra de búsqueda de texto (Ctrl+F) bajo el visor."""
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QApplication, QHBoxLayout, QLabel, QLineEdit, QPushButton, QWidget

from chimupdf.nucleo import edicion


class BarraBusqueda(QWidget):
    """Busca texto página por página, resalta las coincidencias y salta de una a otra."""

    def __init__(self, ventana):
        super().__init__()
        self.v = ventana
        self._doc = None
        self._texto = ""
        self._pagina = -1
        self._rects = []  # coincidencias de la página actual, en coordenadas de página
        self._i = -1

        self.setObjectName("BarraBusqueda")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self.campo = QLineEdit()
        self.campo.setPlaceholderText("Buscar en el documento...")
        self.campo.setClearButtonEnabled(True)
        self.estado = QLabel("")
        b_anterior = QPushButton("↑")
        b_siguiente = QPushButton("↓")
        b_cerrar = QPushButton("✕")
        for boton, ayuda in (
            (b_anterior, "Anterior (Mayús+Enter)"),
            (b_siguiente, "Siguiente (Enter)"),
            (b_cerrar, "Cerrar (Esc)"),
        ):
            boton.setFixedWidth(36)
            boton.setToolTip(ayuda)

        self.campo.returnPressed.connect(self._al_pulsar_enter)
        self.campo.textChanged.connect(self._al_cambiar_texto)
        b_anterior.clicked.connect(lambda: self._ir(-1))
        b_siguiente.clicked.connect(lambda: self._ir(1))
        b_cerrar.clicked.connect(self.cerrar)
        ventana.miniaturas.currentRowChanged.connect(self._al_cambiar_pagina)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.addWidget(self.campo, 1)
        layout.addWidget(b_anterior)
        layout.addWidget(b_siguiente)
        layout.addWidget(self.estado)
        layout.addWidget(b_cerrar)
        self.setVisible(False)

    # ---------- abrir y cerrar ----------
    def abrir(self):
        if self.v.documento is None:
            return
        self.setVisible(True)
        self.campo.setFocus()
        self.campo.selectAll()

    def cerrar(self):
        self._limpiar_resultados()
        self.estado.setText("")
        self.setVisible(False)
        self.v.visor.setFocus()

    def invalidar(self):
        """El documento cambió: las coincidencias resaltadas ya no valen."""
        self._limpiar_resultados()
        self.estado.setText("")

    def actualizar_estado(self):
        if self.v.documento is None and self.isVisible():
            self.cerrar()

    def keyPressEvent(self, evento):
        if evento.key() == Qt.Key.Key_Escape:
            self.cerrar()
            evento.accept()
            return
        super().keyPressEvent(evento)

    # ---------- eventos ----------
    def _al_pulsar_enter(self):
        retroceder = bool(QApplication.keyboardModifiers() & Qt.KeyboardModifier.ShiftModifier)
        self._ir(-1 if retroceder else 1)

    def _al_cambiar_texto(self, _texto):
        self._limpiar_resultados()
        self.estado.setText("")

    def _al_cambiar_pagina(self, fila):
        if fila != self._pagina:  # otra página: las coincidencias resaltadas ya no corresponden
            self.v.visor.lienzo.establecer_resultados([], -1)

    # ---------- búsqueda ----------
    def _limpiar_resultados(self):
        self._rects, self._i, self._pagina, self._texto = [], -1, -1, ""
        self.v.visor.lienzo.establecer_resultados([], -1)

    def _ir(self, direccion):
        """direccion = +1 (siguiente) o -1 (anterior). Sigue por las demás páginas y da la vuelta."""
        texto = self.campo.text().strip()
        doc = self.v.documento
        if not texto or doc is None:
            return
        n = doc.num_paginas
        fila = max(self.v.miniaturas.currentRow(), 0)
        mismo = bool(self._rects) and texto == self._texto and fila == self._pagina and doc is self._doc
        if mismo:
            i = self._i + direccion
            if 0 <= i < len(self._rects):
                self._mostrar(doc, fila, self._rects, i, texto)
                return
        pasos = range(1, n + 1) if mismo else range(n)
        for paso in pasos:
            p = (fila + direccion * paso) % n
            rects = doc.pagina(p).search_for(texto)
            if rects:
                self._mostrar(doc, p, rects, 0 if direccion > 0 else len(rects) - 1, texto)
                return
        self._limpiar_resultados()
        self.estado.setText("Sin resultados")

    def _mostrar(self, doc, pagina, rects, i, texto):
        self._doc, self._pagina, self._rects, self._i, self._texto = doc, pagina, rects, i, texto
        if self.v.miniaturas.currentRow() != pagina:
            self.v.miniaturas.setCurrentRow(pagina)
        pagina_pdf = doc.pagina(pagina)
        visuales = [edicion.rect_visual_de(pagina_pdf, r) for r in rects]
        self.v.visor.lienzo.establecer_resultados(visuales, i)
        self.estado.setText(f"Pág. {pagina + 1} · {i + 1} de {len(rects)}")
        QTimer.singleShot(0, lambda: self._llevar_a_la_vista(visuales[i]))

    def _llevar_a_la_vista(self, rect):
        posicion = self.v.visor.lienzo.a_widget(rect)
        if posicion is None:
            return
        x, y, w, h = posicion
        self.v.visor.ensureVisible(int(x + w / 2), int(y + h / 2), 80, 120)