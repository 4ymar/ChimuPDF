# -*- mode: python ; coding: utf-8 -*-
"""Receta de PyInstaller para ChimuPDF: carpeta (onedir), sin consola.

Ejecutar SIEMPRE desde construir.ps1, que usa el venv limpio .venv-build.
No lanzar directamente con el Python global.
"""
import os

from PyInstaller.utils.hooks import collect_all

RAIZ = os.path.abspath(SPECPATH)  # SPECPATH lo define PyInstaller

# --------------------------------------------------------------------------
# PyMuPDF: collect_all garantiza DLLs nativas, hooks y hidden imports.
# --------------------------------------------------------------------------
datos_mu, binarios_mu, ocultos_mu = collect_all("pymupdf")

# --------------------------------------------------------------------------
# Exclusiones: paquetes que PyInstaller a veces arrastra innecesariamente.
# Ampliar si el analisis --log-level WARN muestra otros grandes no usados.
# --------------------------------------------------------------------------
EXCLUIDOS = [
    "tkinter", "_tkinter",          # GUI alternativa, no usada
    "numpy", "pandas", "matplotlib", # ciencia de datos
    "tensorflow", "keras",           # ML
    "onnxruntime", "onnx",
    "pyarrow", "sqlalchemy",
    "IPython", "jupyter",
    "PIL",                           # Pillow: solo se usa en construir.ps1 para crear el .ico
    "streamlit",
    "scipy", "sklearn", "cv2",
    "wx",                            # otra GUI
    "PyQt5", "PyQt6",                # otras GUI Qt (no PySide6)
]

a = Analysis(
    [os.path.join(RAIZ, "main.py")],
    pathex=[RAIZ],
    binaries=binarios_mu,
    datas=[
        # Recursos de la app: icono PNG + tessdata (spa + eng)
        (os.path.join(RAIZ, "chimupdf", "recursos"), os.path.join("chimupdf", "recursos")),
    ] + datos_mu,
    hiddenimports=ocultos_mu,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=EXCLUIDOS,
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="ChimuPDF",
    debug=False,
    strip=False,
    upx=False,           # UPX puede causar falsos positivos en antivirus; desactivado
    console=False,       # Sin ventana de consola (los errores van a ~/.chimupdf/chimupdf.log)
    # Para depurar un arranque fallido, pon console=True temporalmente
    icon=os.path.join(RAIZ, "chimupdf.ico"),
    # Manifiesto para DPI alto en Windows
    uac_admin=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="ChimuPDF",
)
