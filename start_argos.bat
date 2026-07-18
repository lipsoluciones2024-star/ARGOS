@echo off
REM ===========================================================================
REM ARGOS Enterprise - Launcher para Windows
REM 1. Verifica Python y el entorno virtual (.venv)
REM 2. Instala dependencias solo si faltan
REM 3. Arranca servidor + agente (sin consolas sueltas) y abre el dashboard
REM ===========================================================================
setlocal EnableDelayedExpansion
cd /d "%~dp0"

set "VENV=.\.venv"
set "PY=%VENV%\Scripts\python.exe"
set "PYW=%VENV%\Scripts\pythonw.exe"

echo [ARGOS] Verificando entorno...

REM --- Python ---
where python >nul 2>&1
if errorlevel 1 (
    echo [ARGOS] ERROR: Python no esta en PATH. Instale Python 3.10+ y marque "Add to PATH".
    pause
    exit /b 1
)

REM --- Entorno virtual ---
if not exist "%PY%" (
    echo [ARGOS] Creando entorno virtual (.venv)...
    python -m venv %VENV%
    if errorlevel 1 (
        echo [ARGOS] ERROR: no se pudo crear el entorno virtual.
        pause
        exit /b 1
    )
)

REM --- Dependencias: instalar solo si falta algun paquete clave ---
set "NEED_INSTALL=0"
%PY% -c "import fastapi, uvicorn, pydantic, httpx, yaml, websockets" >nul 2>&1
if errorlevel 1 (
    set "NEED_INSTALL=1"
)

if "%NEED_INSTALL%"=="1" (
    echo [ARGOS] Instalando dependencias (puede tardar unos minutos)...
    %PY% -m pip install --upgrade pip >nul 2>&1
    %PY% -m pip install -e ".[dev]"
    if errorlevel 1 (
        echo [ARGOS] ERROR: fallo la instalacion de dependencias.
        pause
        exit /b 1
    )
    echo [ARGOS] Dependencias instaladas.
) else (
    echo [ARGOS] Dependencias ya presentes. Nada que instalar.
)

REM --- .env de arranque local (si no existe) ---
if not exist ".env" (
    echo [ARGOS] Generando .env de arranque local (auth desactivada para 127.0.0.1)...
    (
        echo # Generado por start_argos.bat - entorno local de prueba.
        echo ARGOS_SERVER_HOST=127.0.0.1
        echo ARGOS_SERVER_PORT=8000
        echo ARGOS_REQUIRE_AUTH=false
        echo ARGOS_DEFAULT_SWITCH=OBSERVE
        echo ARGOS_LLM_MODE=hybrid
    ) > ".env"
)

echo [ARGOS] Todo listo. Iniciando ARGOS...
echo.

REM --- Arranque: launcher oculto (sin consolas sueltas) + nuestra consola de control ---
if not exist "%PYW%" set "PYW=%PY%"
start "ARGOS" /min "%PYW%" "%~dp0tools\launch.py"

echo [ARGOS] ARGOS se esta iniciando en segundo plano.
echo [ARGOS] El dashboard se abrira en el navegador automaticamente.
echo [ARGOS] Para detener: cierre la ventana "ARGOS" que aparece minimizada (logs/ para detalles).
echo.
pause
endlocal
