from PySide6.QtWidgets import QDialog, QHBoxLayout, QPlainTextEdit, QPushButton, QVBoxLayout


class DialogoNota(QDialog):
    """Lee y edita el texto de una nota o de un texto libre; permite guardarlo o eliminar la anotación."""

    def __init__(self, parent, titulo, texto):
        super().__init__(parent)
        self.setWindowTitle(titulo)
        self.resize(420, 260)
        self.eliminar = False
        self.campo = QPlainTextEdit(texto)

        b_guardar = QPushButton("Guardar")
        b_guardar.setDefault(True)
        b_eliminar = QPushButton("Eliminar")
        b_cancelar = QPushButton("Cancelar")
        b_guardar.clicked.connect(self.accept)
        b_eliminar.clicked.connect(self._eliminar)
        b_cancelar.clicked.connect(self.reject)

        pie = QHBoxLayout()
        pie.addWidget(b_eliminar)
        pie.addStretch()
        pie.addWidget(b_guardar)
        pie.addWidget(b_cancelar)
        layout = QVBoxLayout(self)
        layout.addWidget(self.campo)
        layout.addLayout(pie)

    @property
    def texto(self):
        return self.campo.toPlainText()

    def _eliminar(self):
        self.eliminar = True
        self.accept()