#define AppNombre    "ChimuPDF"
#define AppVersion   "1.0.0"
#define AppEditor    "GiraDevs"
#define AppExe       "ChimuPDF.exe"
#define AppId        "8F4B2C6E-1A3D-4F7B-9C5E-6D2A0B8E7F31"

; ---------------------------------------------------------------------------
; [Setup]
; ---------------------------------------------------------------------------
[Setup]
AppId={{{#AppId}}
AppName={#AppNombre}
AppVersion={#AppVersion}
AppPublisher={#AppEditor}
AppPublisherURL=https://giradevs.com

; Sin requerir reinicio tras instalar/desinstalar
RestartIfNeededByRun=no

; Instalacion por usuario (sin UAC). El usuario puede elevar si lo desea.
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

; Solo 64 bits
ArchitecturesInstallIn64BitMode=x64compatible
ArchitecturesAllowed=x64compatible

; Rutas de salida
OutputDir=instalador
OutputBaseFilename=ChimuPDF-Setup-{#AppVersion}

; Directorio de instalacion predeterminado
; autopf -> %ProgramFiles% si es admin, %LocalAppData%\Programs si es usuario
DefaultDirName={autopf}\{#AppNombre}
DefaultGroupName={#AppNombre}

; Icono e imagen del asistente
SetupIconFile=chimupdf.ico
; WizardImageFile=   ; opcional: imagen lateral 164x314 px
; WizardSmallImageFile= ; opcional: imagen esquina 55x58 px

; Desinstalador
UninstallDisplayName={#AppNombre}
UninstallDisplayIcon={app}\{#AppExe}
CreateUninstallRegKey=yes

; Compresion
Compression=lzma2/ultra64
SolidCompression=yes

; Estilo moderno
WizardStyle=modern

; Indicar al sistema que las asociaciones de archivo cambian
ChangesAssociations=yes

; Mostrar version en Agregar o quitar programas
VersionInfoVersion={#AppVersion}
VersionInfoCompany={#AppEditor}
VersionInfoDescription={#AppNombre} - Editor de PDF

; ---------------------------------------------------------------------------
; [Languages]
; ---------------------------------------------------------------------------
[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

; ---------------------------------------------------------------------------
; [Tasks]
; ---------------------------------------------------------------------------
[Tasks]
Name: "desktopicon"; Description: "Crear un acceso directo en el Escritorio"; GroupDescription: "Accesos directos:"; Flags: unchecked

; ---------------------------------------------------------------------------
; [Files]
; ---------------------------------------------------------------------------
[Files]
; Toda la carpeta dist\ChimuPDF\ generada por PyInstaller
Source: "dist\ChimuPDF\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

; ---------------------------------------------------------------------------
; [Icons]
; ---------------------------------------------------------------------------
[Icons]
; Acceso directo en el menu de inicio
Name: "{group}\{#AppNombre}";         Filename: "{app}\{#AppExe}"
Name: "{group}\Desinstalar {#AppNombre}"; Filename: "{uninstallexe}"
; Acceso directo en el escritorio (solo si el usuario marco la tarea)
Name: "{autodesktop}\{#AppNombre}";   Filename: "{app}\{#AppExe}"; Tasks: desktopicon

; ---------------------------------------------------------------------------
; [Registry]  – Registro en "Abrir con" para .pdf SIN cambiar el predeterminado
; ---------------------------------------------------------------------------
[Registry]
; Descripcion de la aplicacion (aparece en el dialogo "Abrir con")
Root: HKA; Subkey: "Software\Classes\Applications\{#AppExe}";                                   ValueType: string; ValueName: "FriendlyAppName"; ValueData: "{#AppNombre}";          Flags: uninsdeletekey
; Tipo de archivo admitido
Root: HKA; Subkey: "Software\Classes\Applications\{#AppExe}\SupportedTypes";                    ValueType: string; ValueName: ".pdf";             ValueData: "";
; Comando de apertura con parametro de archivo
Root: HKA; Subkey: "Software\Classes\Applications\{#AppExe}\shell\open\command";                ValueType: string; ValueName: "";                 ValueData: """{app}\{#AppExe}"" ""%1""";
; Enlace en la lista "OpenWithList" del .pdf
Root: HKA; Subkey: "Software\Classes\.pdf\OpenWithList\{#AppExe}";                              ValueType: none;                                                                      Flags: uninsdeletekey
; Icono para el explorador de archivos
Root: HKA; Subkey: "Software\Classes\Applications\{#AppExe}\DefaultIcon";                       ValueType: string; ValueName: "";                 ValueData: """{app}\{#AppExe}"",0"; Flags: uninsdeletekey

; ---------------------------------------------------------------------------
; [Run]  – Ofrecer arrancar la app al finalizar la instalacion
; ---------------------------------------------------------------------------
[Run]
Filename: "{app}\{#AppExe}"; Description: "Abrir {#AppNombre} ahora"; Flags: nowait postinstall skipifsilent

; ---------------------------------------------------------------------------
; [UninstallDelete]  – Limpiar carpeta si queda vacia tras desinstalar
; ---------------------------------------------------------------------------
[UninstallDelete]
Type: dirifempty; Name: "{app}"
