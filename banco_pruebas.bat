@echo off
setlocal
cd /d "%~dp0"

set PY=python
where python >nul 2>&1 || set PY=py -3

echo === Banco pruebas CE (independiente de grabar_telemetria) ===
echo Gas, RPM y aceleracion. Consola por defecto; ventana pedal: --gui
echo Si CAL queda en 1.0: .\\banco_pruebas.bat --scout
echo.

%PY% grabar_ce.py --probe
if errorlevel 1 (
    echo.
    echo Abortado: SnowRunner en mapa conduciendo.
    pause
    exit /b 1
)

%PY% cheat_engine/banco_drive.py %*
set ERR=%ERRORLEVEL%
echo.
if %ERR% neq 0 echo Termino con error %ERR%.
pause
exit /b %ERR%
