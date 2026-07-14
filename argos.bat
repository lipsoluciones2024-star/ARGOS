@echo off
REM ==========================================================================
REM  ARGOS - Launcher de arranque en orden (Windows)
REM  Uso:  argos.bat [nobrowser]   |   argos.bat debug
REM    - Comprueba dependencias Python; si faltan, las instala.
REM    - Etapa 1: servidor API + dashboard (espera a que responda /health).
REM    - Etapa 2: agente recolector (espera a que confirme arranque).
REM    - Etapa 3: abre el dashboard en el navegador (salvo "nobrowser").
REM
REM  El servidor y el agente se ejecutan SIN ventana de consola (pythonw) y
REM  su salida se redirige a logs/. El propio launcher se ejecuta minimizado
REM  para no mostrar consolas. Usa "debug" para ver la consola de arranque.
REM ==========================================================================

setlocal EnableExtensions

REM --- Auto-minimiza el launcher para no mostrar consolas (salvo "debug") ----
if /i not "%~1"=="debug" (
    if not defined _ARGOS_MIN (
        set _ARGOS_MIN=1
        start /min "" "%~f0" %*
        goto :EOF
    )
)

set "REPO=%~dp0"
if "%REPO:~-1%"=="\" set "REPO=%REPO:~0,-1%"

REM --- Python: usa el venv del repo si existe, sino el del sistema ----------
if exist "%REPO%\.venv\Scripts\python.exe" (
    set "PY=%REPO%\.venv\Scripts\python.exe"
) else (
    set "PY=python"
)
REM pythonw = intérprete sin consola (evita ventanas del servidor/agente)
if exist "%REPO%\.venv\Scripts\pythonw.exe" (
    set "PYW=%REPO%\.venv\Scripts\pythonw.exe"
) else (
    set "PYW=%PY%"
)

REM --- Configuracion de arranque (heredada por los procesos hijos) ----------
set "ARGOS_SERVER_HOST=127.0.0.1"
set "ARGOS_SERVER_PORT=8000"
if not defined ARGOS_REQUIRE_AUTH set "ARGOS_REQUIRE_AUTH=false"
set "PYTHONPATH=%REPO%"

set "HOST=%ARGOS_SERVER_HOST%"
set "PORT=%ARGOS_SERVER_PORT%"
set "HEALTH=http://%HOST%:%PORT%/api/v1/health"
if not exist "%REPO%\logs" mkdir "%REPO%\logs"

echo =========================================================================
echo  ARGOS - arranque en orden
echo  Repo     : %REPO%
echo  Python   : %PY%
echo  Servidor : %HOST%:%PORT%
echo =========================================================================

REM ==========================================================================
REM  Etapa 0 - Comprobacion de dependencias
REM ==========================================================================
echo.
echo [Etapa 0/3] Comprobando dependencias de Python...
"%PY%" -c "import fastapi, uvicorn, pydantic, httpx, yaml, websockets" >nul 2>&1
if errorlevel 1 (
    echo   Faltan dependencias. Instalando con pip install -e .
    "%PY%" -m pip install -e .
    if errorlevel 1 (
        echo   ERROR: no se pudieron instalar las dependencias.
        pause
        goto :EOF
    )
    echo   Dependencias instaladas.
) else (
    echo   Dependencias OK.
)

REM ==========================================================================
REM  Etapa 1 - Servidor API + dashboard (espera a que este listo)
REM ==========================================================================
echo.
echo [Etapa 1/3] Iniciando servidor API + dashboard...
start "" "%PYW%" -m argos.server > "%REPO%\logs\server.log" 2>&1

set TRIES=0
:wait_server
"%PY%" -c "import sys,urllib.request; sys.exit(0 if urllib.request.urlopen('%HEALTH%',timeout=2).status==200 else 1)" >nul 2>&1
if not errorlevel 1 (
    echo   Servidor listo en %HEALTH%
    goto server_ok
)
set /a TRIES+=1
if %TRIES% geq 60 (
    echo   ERROR: el servidor no respondio tras 60s. Revisa %REPO%\logs\server.log
    pause
    goto :EOF
)
echo   esperando servidor... (%TRIES%s)
timeout /t 1 >nul
goto wait_server
:server_ok

REM ==========================================================================
REM  Etapa 2 - Agente recolector (espera a que confirme arranque)
REM ==========================================================================
echo.
echo [Etapa 2/3] Iniciando agente recolector...
start "" "%PYW%" -m argos.agent > "%REPO%\logs\agent.log" 2>&1

set ATRIES=0
:wait_agent
findstr /C:"ARGOS agent started" "%REPO%\logs\agent.log" >nul 2>&1
if not errorlevel 1 (
    echo   Agente conectado y enviando eventos al servidor.
    goto agent_ok
)
set /a ATRIES+=1
if %ATRIES% geq 30 (
    echo   AVISO: el agente no confirmo arranque en 30s. Revisa %REPO%\logs\agent.log. Continuando.
    goto agent_ok
)
timeout /t 1 >nul
goto wait_agent
:agent_ok

REM ==========================================================================
REM  Etapa 3 - Abrir dashboard
REM ==========================================================================
echo.
echo [Etapa 3/3] ARGOS en marcha.
if /i "%~1"=="nobrowser" (
    echo   Apertura de navegador omitida. Dashboard en: http://%HOST%:%PORT%/
) else (
    echo   Abriendo dashboard en http://%HOST%:%PORT%/
    start "" "http://%HOST%:%PORT%/"
)

if /i "%~1"=="debug" (
    echo.
    echo  Modo debug: esta consola queda abierta. Cierra para terminar el arranque.
    pause
) else (
    echo.
    echo  Listo. Servidor y agente corriendo en segundo plano (sin consolas).
    echo  Para detener: taskkill /FI "WINDOWTITLE eq ARGOS*"  (o cierra el proceso pythonw).
    timeout /t 2 >nul
)
endlocal
