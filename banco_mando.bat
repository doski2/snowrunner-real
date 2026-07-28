@echo off
setlocal
cd /d "%~dp0"

set PY=python
where python >nul 2>&1 || set PY=py -3

echo === Monitor mando / gas (IN vs MOT) ===
echo   Pisa y suelta el acelerador; la fila con * es la que mas varia.
echo   IN = input jugador (TRUCK_CONTROL)   MOT = demanda motor (vehicle+760)
echo.

%PY% grabar_ce.py --probe
if errorlevel 1 (
    echo Abortado: SnowRunner en mapa conduciendo.
    pause
    exit /b 1
)

%PY% cheat_engine/banco_drive.py --mando %*
set ERR=%ERRORLEVEL%
echo.
if %ERR% neq 0 echo Termino con error %ERR%.
pause
exit /b %ERR%
