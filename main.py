"""Punto de entrada de ChimuPDF."""
import multiprocessing
import os
import sys

# En el .exe sin consola, stdout y stderr valen None y cualquier aviso de una librería (también en los
# procesos del OCR) fallaría. Se redirigen a un archivo de registro.
if sys.stdout is None or sys.stderr is None:
    _carpeta = os.path.join(os.path.expanduser("~"), ".chimupdf")
    try:
        os.makedirs(_carpeta, exist_ok=True)
        _registro = open(os.path.join(_carpeta, "chimupdf.log"), "a", encoding="utf-8", errors="replace")
    except OSError:
        _registro = open(os.devnull, "w")
    sys.stdout = sys.stdout or _registro
    sys.stderr = sys.stderr or _registro


def main():
    # Se importan aquí para que los procesos del OCR no carguen toda la interfaz al arrancar
    from PySide6.QtWidgets import QApplication

    from chimupdf.ui.ventana_principal import VentanaPrincipal

    if sys.platform == "win32":  # para que Windows muestre el icono de ChimuPDF en la barra de tareas
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("GiraDevs.ChimuPDF")
    app = QApplication(sys.argv)
    app.setApplicationName("ChimuPDF")
    ventana = VentanaPrincipal()
    ventana.show()
    if len(sys.argv) > 1:
        ventana.abrir_ruta(sys.argv[1])
    sys.exit(app.exec())


if __name__ == "__main__":
    multiprocessing.freeze_support()  # imprescindible en Windows para que el OCR en procesos funcione en el .exe
    main()
