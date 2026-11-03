from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QMessageBox,
    QVBoxLayout,
)

from chimupdf.nucleo.proteccion import Proteccion


class DialogoProteger(QDialog):
    """Pide la contraseña para abrir y los permisos. Al aceptar deja listo 'proteccion'."""

    def __init__(self, parent=None, inicial=None, titulo="Proteger con contraseña"):
        super().__init__(parent)
        self.setWindowTitle(titulo)
        self.setMinimumWidth(420)
        self.proteccion = None

        self.e_clave = QLineEdit()
        self.e_repetir = QLineEdit()
        for campo in (self.e_clave, self.e_repetir):
            campo.setEchoMode(QLineEdit.EchoMode.Password)
        self.mostrar = QCheckBox("Mostrar contraseña")
        self.mostrar.toggled.connect(self._alternar_visibilidad)

        formulario = QFormLayout()
        formulario.addRow("Contraseña para abrir:", self.e_clave)
        formulario.addRow("Repetir contraseña:", self.e_repetir)

        ini = inicial or Proteccion("")
        if ini.clave:
            self.e_clave.setText(ini.clave)
            self.e_repetir.setText(ini.clave)
        self.c_imprimir = QCheckBox("Permitir imprimir")
        self.c_copiar = QCheckBox("Permitir copiar texto e imágenes")
        self.c_modificar = QCheckBox("Permitir modificar el documento")
        self.c_anotar = QCheckBox("Permitir agregar anotaciones")
        self.c_imprimir.setChecked(ini.permitir_imprimir)
        self.c_copiar.setChecked(ini.permitir_copiar)
        self.c_modificar.setChecked(ini.permitir_modificar)
        self.c_anotar.setChecked(ini.permitir_anotar)

        grupo = QGroupBox("Permisos de quien abra el archivo")
        caja = QVBoxLayout(grupo)
        for c in (self.c_imprimir, self.c_copiar, self.c_modificar, self.c_anotar):
            caja.addWidget(c)

        nota = QLabel(
            "Las restricciones las respetan la mayoría de los lectores de PDF, pero no son "
            "una barrera de seguridad: lo que protege el contenido es la contraseña para abrir."
        )
        nota.setWordWrap(True)

        botones = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        botones.button(QDialogButtonBox.StandardButton.Ok).setText("Aceptar")
        botones.button(QDialogButtonBox.StandardButton.Cancel).setText("Cancelar")
        botones.accepted.connect(self.accept)
        botones.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(formulario)
        layout.addWidget(self.mostrar)
        layout.addWidget(grupo)
        layout.addWidget(nota)
        layout.addWidget(botones)

    def _alternar_visibilidad(self, visible):
        modo = QLineEdit.EchoMode.Normal if visible else QLineEdit.EchoMode.Password
        self.e_clave.setEchoMode(modo)
        self.e_repetir.setEchoMode(modo)

    def accept(self):
        clave = self.e_clave.text()
        if not clave:
            QMessageBox.warning(self, "Proteger", "Escribe una contraseña.")
            return
        if clave != self.e_repetir.text():
            QMessageBox.warning(self, "Proteger", "Las contraseñas no coinciden.")
            return
        self.proteccion = Proteccion(
            clave,
            permitir_imprimir=self.c_imprimir.isChecked(),
            permitir_copiar=self.c_copiar.isChecked(),
            permitir_modificar=self.c_modificar.isChecked(),
            permitir_anotar=self.c_anotar.isChecked(),
        )
        super().accept()
