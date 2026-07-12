@echo off
setlocal EnableDelayedExpansion
title ARGOS Launcher
cd /d "%~dp0"

set "VENV=.venv"
set "PY=%VENV%\Scripts\python.exe"

echo ============================================================
echo   ARGOS - Verificador y arranque en modo DEBUG
echo ============================================================

REM 1) Verificar que Python esta instalado
where python >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python no esta instalado o no esta en el PATH.
    echo         Instalalo desde https://www.python.org/ e intenta de nuevo.
    pause
    exit /b 1
)
for /f "tokens=*" %%i in ('python --version 2^>^&1') do echo [OK] %%i detectado

REM 2) Verificar / crear el entorno virtual
if not exist "%PY%" (
    echo [..] No existe %VENV%. Creando entorno virtual...
    python -m venv "%VENV%"
    if errorlevel 1 (
        echo [ERROR] No se pudo crear el entorno virtual.
        pause
        exit /b 1
    )
) else (
    echo [OK] Entorno virtual %VENV% presente
)

REM 3) Verificar / instalar dependencias SOLO si no estan presentes
"%PY%" -c "import argos" >nul 2>&1
if errorlevel 1 (
    echo [..] Dependencias no encontradas. Instalando, esto puede tardar...
    "%PY%" -m pip install --upgrade pip
    "%PY%" -m pip install -e ".[dev]"
    if errorlevel 1 (
        echo [ERROR] Fallo la instalacion de dependencias. Revisa la conexion o los logs.
        pause
        exit /b 1
    )
    echo [OK] Dependencias instaladas
) else (
    echo [OK] Dependencias ya instaladas, se omite el install para arrancar rapido
)

REM 4) Activar nivel DEBUG para ver todo mientras usas el programa
set "ARGOS_LOG_LEVEL=DEBUG"

REM 5) Arrancar servidor (API + dashboard) y agente (recoleccion) en consolas de debug
echo.
echo [OK] Todo listo. Arrancando ARGOS en modo DEBUG...
echo      Servidor : http://localhost:8000
echo      Dashboard: http://localhost:8000
echo.

start "ARGOS-SERVER (debug)" "%PY%" -m argos.server
start "ARGOS-AGENT (debug)"  "%PY%" -m argos.agent

REM Esperar a que el servidor levante y abrir el dashboard
timeout /t 5 >nul
start "" "http://localhost:8000"

echo ============================================================
echo  Consolas de DEBUG abiertas:
echo    - ARGOS-SERVER (debug) : logs del API/dashboard
echo    - ARGOS-AGENT  (debug) : logs de la recoleccion
echo  Cierra esas ventanas para detener ARGOS.
echo ============================================================
pause
endlocal
