# =============================================================================
# construir.ps1 – Empaquetado de ChimuPDF con PyInstaller
#
# Requisitos previos:
#   · Python 3.11 instalado y accesible como "py -3.11"
#   · Inno Setup 6 instalado (solo para generar el instalador al final)
#
# Lo que hace este script:
#   1. Crea/recrea el entorno virtual aislado .venv-build
#   2. Instala SOLO las dependencias de la app (requirements.txt)
#      + pyinstaller + pillow (para crear el icono). Nunca toca el Python global.
#   3. Copia spa.traineddata y eng.traineddata desde D:\Programas\tessdata
#      a chimupdf\recursos\tessdata\ (los unicos necesarios)
#   4. Genera chimupdf.ico si no existe
#   5. Ejecuta PyInstaller desde el venv limpio
#   6. (Opcional) Compila el instalador .exe con Inno Setup
# =============================================================================
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

# ---------------------------------------------------------------------------
# Parametros configurables
# ---------------------------------------------------------------------------
$PythonExe       = "py"                       # Python Launcher; cambia a "python" si prefieres
$PythonVer       = "-3.11"                    # Version concreta a usar
$VenvDir         = ".venv-build"              # Entorno virtual de compilacion (aislado)
$TessdataOrigen  = "D:\Programas\tessdata"
$TessdataDestino = "chimupdf\recursos\tessdata"
$InnoCompiler    = "D:\Programas\Inno Setup 7\ISCC.exe"

# ---------------------------------------------------------------------------
# 1. Crear entorno virtual limpio
# ---------------------------------------------------------------------------
Write-Host "== Creando entorno virtual de compilacion: $VenvDir ==" -ForegroundColor Cyan
if (Test-Path $VenvDir) {
    Write-Host "   Eliminando entorno anterior..."
    Remove-Item -Recurse -Force $VenvDir
}
& $PythonExe $PythonVer -m venv $VenvDir
if ($LASTEXITCODE -ne 0) { throw "No se pudo crear el entorno virtual con Python 3.11." }

$Pip    = "$VenvDir\Scripts\pip.exe"
$Python = "$VenvDir\Scripts\python.exe"

# ---------------------------------------------------------------------------
# 2. Instalar dependencias SOLO en el venv (nunca en el Python global)
# ---------------------------------------------------------------------------
Write-Host "== Instalando dependencias en el venv ==" -ForegroundColor Cyan
& $Python -m pip install --upgrade pip --quiet

# Solo PySide6 y PyMuPDF (segun requirements.txt)
& $Pip install -r requirements.txt --quiet
if ($LASTEXITCODE -ne 0) { throw "Fallo al instalar requirements.txt." }

# Herramientas de compilacion — NUNCA van en requirements.txt
& $Pip install "pyinstaller==6.13.0" "pillow>=10,<13" --quiet
if ($LASTEXITCODE -ne 0) { throw "Fallo al instalar PyInstaller/Pillow." }

Write-Host "   Paquetes instalados en el venv:" -ForegroundColor DarkGray
& $Pip list --format=columns | Select-String -Pattern "^(PySide6 |pymupdf |PyInstaller |Pillow |shiboken)" |
    ForEach-Object { Write-Host "   $_" -ForegroundColor DarkGray }

# ---------------------------------------------------------------------------
# 3. Copiar solo spa + eng desde la carpeta global de tessdata
# ---------------------------------------------------------------------------
Write-Host "== Copiando archivos tessdata ==" -ForegroundColor Cyan
if (-not (Test-Path $TessdataDestino)) {
    New-Item -ItemType Directory -Path $TessdataDestino | Out-Null
}
foreach ($codigo in @("spa", "eng")) {
    $origen  = Join-Path $TessdataOrigen "$codigo.traineddata"
    $destino = Join-Path $TessdataDestino "$codigo.traineddata"
    if (Test-Path $origen) {
        Copy-Item -Path $origen -Destination $destino -Force
        Write-Host "   Copiado: $codigo.traineddata" -ForegroundColor DarkGray
    } else {
        Write-Warning "No se encontro '$origen': el OCR en '$codigo' no funcionara."
    }
}

# ---------------------------------------------------------------------------
# 4. Generar icono si no existe
# ---------------------------------------------------------------------------
Write-Host "== Icono ==" -ForegroundColor Cyan
if (-not (Test-Path "chimupdf.ico")) {
    Write-Host "   Generando chimupdf.ico..."
    & $Python crear_icono.py
    if ($LASTEXITCODE -ne 0) { throw "Fallo al crear chimupdf.ico." }
} else {
    Write-Host "   chimupdf.ico ya existe, se reutiliza."
}

# ---------------------------------------------------------------------------
# 5. Compilar con PyInstaller (desde el venv limpio)
# ---------------------------------------------------------------------------
Write-Host "== Ejecutando PyInstaller ==" -ForegroundColor Cyan
& "$VenvDir\Scripts\pyinstaller.exe" --noconfirm --clean ChimuPDF.spec
if ($LASTEXITCODE -ne 0) { throw "PyInstaller termino con errores." }

Write-Host ""
Write-Host "== Compilacion terminada: dist\ChimuPDF\ChimuPDF.exe ==" -ForegroundColor Green

# ---------------------------------------------------------------------------
# 6. (Opcional) Generar instalador con Inno Setup
# ---------------------------------------------------------------------------
if (Test-Path $InnoCompiler) {
    Write-Host "== Generando instalador con Inno Setup ==" -ForegroundColor Cyan
    & $InnoCompiler instalador.iss
    if ($LASTEXITCODE -ne 0) { throw "Inno Setup termino con errores." }
    Write-Host "== Instalador generado en: instalador\ ==" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "Inno Setup no encontrado en '$InnoCompiler'." -ForegroundColor Yellow
    Write-Host "Para generar el instalador manualmente ejecuta:" -ForegroundColor Yellow
    Write-Host "   & '$InnoCompiler' instalador.iss" -ForegroundColor Yellow
}
