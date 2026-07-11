@echo off
setlocal
cd /d "%~dp0"

set PY=python
where python >nul 2>&1 || set PY=py -3

echo === AUTO-HUNT pedal — tu alternas gas 0%% y 100%% en el juego ===
echo   1. Ejecuta esto con SnowRunner abierto (mapa, motor ON)
echo   2. Cuenta atras 3s — Alt+Tab al juego
echo   3. Durante 5s alterna gas SUELTO y FONDO (sin tocar esta ventana)
echo   4. Lee el ranking aqui y en cheat_engine\drive_snaps\pedal_sweep_latest.json
echo.

%PY% grabar_ce.py --probe
if errorlevel 1 (
    echo Abortado: SnowRunner en mapa conduciendo.
    pause
    exit /b 1
)

%PY% cheat_engine/banco_drive.py --auto-hunt %*
set ERR=%ERRORLEVEL%
echo.
if %ERR% neq 0 echo Sin candidato claro — repite mas rapido 0%% ^<^> 100%% o: --sweep-duration 8
pause
exit /b %ERR%
