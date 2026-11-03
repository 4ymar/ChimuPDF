from PySide6.QtCore import QSize, Qt, QTimer, Signal
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import QAbstractItemView, QListView, QListWidget, QListWidgetItem

from .imagenes import pixmap_de_pagina

ZOOM_MINIATURA = 0.25
LISTO = Qt.ItemDataRole.UserRole  # dato del ítem: True si ya tiene su miniatura real
POR_LOTE = 2  # miniaturas que se dibujan por turno antes de devolver el control a la interfaz


class PanelMiniaturas(QListWidget):
    """Lista lateral de páginas; permite reordenar arrastrando."""

    # (posición original, posición final)
    pagina_movida = Signal(int, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setViewMode(QListView.ViewMode.ListMode)
        self.setIconSize(QSize(90, 120))
        self.setSpacing(4)
        self.setMinimumWidth(180)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.model().rowsMoved.connect(self._al_mover)

        self._documento = None
        vacio = QPixmap(90, 120)
        vacio.fill(Qt.GlobalColor.transparent)
        self._icono_vacio = QIcon(vacio)  # mantiene la altura de las filas mientras se dibujan
        self._temporizador = QTimer(self)
        self._temporizador.setSingleShot(True)
        self._temporizador.setInterval(0)
        self._temporizador.timeout.connect(self._dibujar_lote)

    def clear(self):
        self._temporizador.stop()
        self._documento = None
        super().clear()

    def cargar(self, documento):
        """Crea las filas al instante; las miniaturas se dibujan después, en lotes."""
        self.clear()
        self._documento = documento
        for i in range(documento.num_paginas):
            item = QListWidgetItem(f"Página {i + 1}")
            item.setIcon(self._icono_vacio)
            self.addItem(item)
        self._temporizador.start()

    def actualizar_miniatura(self, indice, documento):
        """Redibuja una miniatura ahora mismo."""
        item = self.item(indice)
        if item is not None and 0 <= indice < documento.num_paginas:
            item.setIcon(self._icono(documento, indice))
            item.setData(LISTO, True)

    def invalidar(self, documento, indices=None):
        """Marca miniaturas como desactualizadas (todas o las indicadas); se redibujan en lotes."""
        self._documento = documento
        for i in (range(self.count()) if indices is None else indices):
            item = self.item(i)
            if item is not None:
                item.setData(LISTO, False)
        self._temporizador.start()

    def _siguiente_pendiente(self):
        """Fila de la próxima miniatura por dibujar: primero las que se ven en el panel."""
        visible = self.viewport().rect()
        primera = None
        for i in range(self.count()):
            item = self.item(i)
            if item.data(LISTO):
                continue
            if visible.intersects(self.visualItemRect(item)):
                return i
            if primera is None:
                primera = i
        return primera

    def _dibujar_lote(self):
        doc = self._documento
        if doc is None:
            return
        for _ in range(POR_LOTE):
            i = self._siguiente_pendiente()
            if i is None:
                return
            if i >= doc.num_paginas:  # fila de más: no hay nada que dibujar
                self.item(i).setData(LISTO, True)
                continue
            try:
                self.actualizar_miniatura(i, doc)
            except Exception:  # el documento se cerró o cambió mientras tanto
                self._documento = None
                return
        self._temporizador.start()

    def quitar(self, indice):
        self.blockSignals(True)
        try:
            self.takeItem(indice)
            self._renumerar()
        finally:
            self.blockSignals(False)

    def mover_item(self, origen, destino):
        self.blockSignals(True)
        try:
            item = self.takeItem(origen)
            self.insertItem(destino, item)
            self._renumerar()
        finally:
            self.blockSignals(False)
        self.setCurrentRow(destino)

    def _icono(self, documento, indice):
        pm = pixmap_de_pagina(documento, indice, ZOOM_MINIATURA, self.devicePixelRatioF())
        icono = QIcon(pm)
        icono.addPixmap(pm, QIcon.Mode.Selected)  # sin el tinte de color al seleccionar
        icono.addPixmap(pm, QIcon.Mode.Active)
        return icono

    def _renumerar(self):
        for i in range(self.count()):
            self.item(i).setText(f"Página {i + 1}")

    def _al_mover(self, _padre, inicio, _fin, _padre_destino, fila):
        final = fila - 1 if fila > inicio else fila
        self._renumerar()
        self.pagina_movida.emit(inicio, final)
        self.setCurrentRow(final)
