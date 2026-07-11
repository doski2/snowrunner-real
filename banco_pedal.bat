@echo off
setlocal
cd /d "%~dp0"

set PY=python
where python >nul 2>&1 || set PY=py -3

echo === Ventana pedal CE — buscar offset MANDO ===
echo   1. Objetivo %% = 25   2. Ref gas 0%%   3. Mando al 25%%   4. Delta vs ref
echo   Bases / Guia CE en la ventana. CLI: python cheat_engine/banco_drive.py --dump-bases
echo.

%PY% grabar_ce.py --probe
if errorlevel 1 (
    echo Abortado: SnowRunner en mapa conduciendo.
    pause
    exit /b 1
)

%PY% cheat_engine/banco_drive.py --gui %*
exit /b %ERRORLEVEL%
