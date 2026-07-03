@echo off
cd /d "%~dp0"

if /i "%1"=="probe" goto PROBE
if /i "%1"=="snap" goto SNAP
if /i "%1"=="terr" goto SNAP
if /i "%1"=="diff" goto DIFF
if /i "%1"=="tire" goto TIRE
if /i "%1"=="cargo" goto CARGO
goto RECORD

:PROBE
echo === Preflight CE (vehiculo + terreno + carga) ===
python grabar_ce.py --probe
set ERR=%ERRORLEVEL%
if %ERR% neq 0 goto PAUSE_ERR
echo.
python cheat_engine/scan_wheel_substance.py
if errorlevel 1 set ERR=1
echo.
python cheat_engine/scan_cargo.py
if errorlevel 1 set ERR=1
goto PAUSE_ERR

:CARGO
shift
python cheat_engine/scan_cargo.py %*
set ERR=%ERRORLEVEL%
goto PAUSE_ERR

:SNAP
if "%2"=="" (
    echo Uso: grabar_telemetria.bat snap ^<nombre^>
    echo   ej. grabar_telemetria.bat snap barro_ligero
    echo Parada TERR: quieto ~30 s en el terreno, mismo camion.
    exit /b 1
)
echo === Snapshot TERR: %2 ===
python grabar_ce.py --probe
if errorlevel 1 goto PAUSE_ERR
python cheat_engine/scan_wheel_substance.py --save %2
set ERR=%ERRORLEVEL%
goto PAUSE_ERR

:DIFF
if "%3"=="" (
    echo Uso: grabar_telemetria.bat diff ^<A^> ^<B^>
    echo   ej. grabar_telemetria.bat diff tierra_seca barro_ligero
    exit /b 1
)
python cheat_engine/scan_wheel_substance.py --diff %2 %3
set ERR=%ERRORLEVEL%
goto PAUSE_ERR

:TIRE
shift
python cheat_engine/scan_wheel_addons.py %*
set ERR=%ERRORLEVEL%
goto PAUSE_ERR

:RECORD
echo SnowRunner - grabar telemetria (modo acumulacion)
echo.
echo 1. SnowRunner en MAPA conduciendo (un camion mod por grabacion)
echo 2. Juega normal: asfalto, barro, carga, remolque...
echo 3. Consola LIVE cada 2s: velocidad, terreno CE, mud_grade, grip, carga
echo 4. Ctrl+C para parar - importa, compara tramos e indexa calibracion.json
echo.
echo Diagnostico (sin grabar sesion):
echo   grabar_telemetria.bat probe
echo   grabar_telemetria.bat snap barro_ligero
echo   grabar_telemetria.bat diff tierra_seca barro_ligero
echo   grabar_telemetria.bat tire
echo   grabar_telemetria.bat cargo
echo   grabar_telemetria.bat cargo --save cargado
echo.

echo Preflight CE...
python grabar_ce.py --probe
if errorlevel 1 (
    echo.
    echo Abortado: entra al mapa conduciendo y reintenta.
    goto PAUSE_ERR
)
echo.
echo === Carga bastidor / remolque (quieto 30 s si F3) ===
python cheat_engine/scan_cargo.py
echo.
echo Si vas a grabar F3 con bastidor lleno y load_hint=vacio o payload ~0:
echo   - Para el camion quieto ~30 s y repite: grabar_telemetria.bat cargo
echo   - No sigas hasta ver cargado y payload_kg ^> 300
echo.

python grabar_ce.py --import --compare --auto --index --live --map Michigan --location "Black River partida libre" --baseline play_free_v1 %*
set ERR=%ERRORLEVEL%

echo.
if %ERR% neq 0 (
    echo Termino con error %ERR%.
    echo Si CSV vacio: grabar_telemetria.bat probe
) else (
    echo Listo.
    echo   telemetria/sesiones/     JSON importado
    echo   datos/indices/calibracion.json   tramos indexados
    echo   python consultar_base.py mae --entry-type segment
)
goto PAUSE_END

:PAUSE_ERR
echo.
if %ERR% neq 0 echo Termino con error %ERR%.
:PAUSE_END
pause
exit /b %ERR%
