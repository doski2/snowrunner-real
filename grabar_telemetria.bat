@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"
set ERR=0

set PY=python
where python >nul 2>&1 || set PY=py -3
where python >nul 2>&1 || where py >nul 2>&1 || (
    echo Python no encontrado en PATH. Instala Python o usa "py -3".
    set ERR=1
    goto PAUSE_END
)

if /i "%1"=="probe" goto PROBE
if /i "%1"=="snap" goto SNAP
if /i "%1"=="terr" goto SNAP
if /i "%1"=="diff" goto DIFF
if /i "%1"=="tire" goto TIRE
if /i "%1"=="cargo" goto CARGO
if /i "%1"=="drive" goto DRIVE
if /i "%1"=="drive_snap" goto DRIVE_SNAP
if /i "%1"=="drive_diff" goto DRIVE_DIFF
if /i "%1"=="motor" goto MOTOR
if /i "%1"=="motor_scout" goto MOTOR_SCOUT
goto RECORD

:PROBE
echo === Preflight CE (vehiculo + terreno + carga) ===
%PY% grabar_ce.py --probe
set ERR=!ERRORLEVEL!
if !ERR! neq 0 goto PAUSE_ERR
echo.
%PY% cheat_engine/scan_wheel_substance.py
if errorlevel 1 set ERR=1
echo.
%PY% cheat_engine/scan_cargo.py
if errorlevel 1 set ERR=1
goto PAUSE_ERR

:CARGO
%PY% cheat_engine/scan_cargo.py %2 %3 %4 %5 %6 %7 %8 %9
set ERR=!ERRORLEVEL!
goto PAUSE_ERR

:DRIVE
%PY% cheat_engine/scan_drive_state.py %2 %3 %4 %5 %6 %7 %8 %9
set ERR=!ERRORLEVEL!
goto PAUSE_ERR

:DRIVE_SNAP
if "%2"=="" (
    echo Uso: grabar_telemetria.bat drive_snap ^<nombre^>
    echo.
    echo Calibracion diff/L — mismo camion, mapa, 0 km/h, motor ON:
    echo   1. diff OFF, marcha H:  grabar_telemetria.bat drive_snap diff_off
    echo   2. diff ON,  marcha H:  grabar_telemetria.bat drive_snap diff_on
    echo   3. marcha L:            grabar_telemetria.bat drive_snap low_on
    echo   4. comparar:             grabar_telemetria.bat drive_diff diff_off diff_on
    echo   5. comparar L:           grabar_telemetria.bat drive_diff diff_on low_on
    echo.
    echo Verifica vehicle_id igual en los 3 antes de comparar.
    exit /b 1
)
echo === Snapshot DRIVE discover: %2 ===
echo Motor ON, 0 km/h, togglear diff/L segun el nombre del snap.
echo.
%PY% grabar_ce.py --probe
if errorlevel 1 (
    set ERR=1
    goto PAUSE_ERR
)
%PY% cheat_engine/scan_drive_state.py --discover --save %2
set ERR=!ERRORLEVEL!
goto PAUSE_ERR

:DRIVE_DIFF
if "%3"=="" (
    echo Uso: grabar_telemetria.bat drive_diff ^<A^> ^<B^>
    echo   ej. grabar_telemetria.bat drive_diff diff_off diff_on
    echo   ej. grabar_telemetria.bat drive_diff diff_on low_on
    exit /b 1
)
%PY% cheat_engine/scan_drive_state.py --diff %2 %3
set ERR=!ERRORLEVEL!
goto PAUSE_ERR

:MOTOR
echo === F1 CK1500 — AAT-8V 5.2 (solo motor, resto stock) ===
echo.
echo Setup en taller ANTES de diff/offroad/caja/remolque:
echo   - Motor: AAT-8V 5,2 Custom (us_scout_old_engine_ck1500)
echo   - Neumatico: Highway 31 stock
echo   - Caja / diff / AWD: de serie (sin mejoras)
echo   - Mapa: asfalto recto, vacio, WOT ~60 s (mapa auto-detectado)
echo.
echo Ctrl+C para parar - importa con protocolo f1_asfalto_aat8v
echo.
%PY% grabar_ce.py --probe
if errorlevel 1 (
    set ERR=1
    goto PAUSE_ERR
)
%PY% grabar_ce.py --import --compare --index --live --protocol f1_asfalto_aat8v --baseline ck_aat8v_f1 %2 %3 %4 %5 %6 %7 %8 %9
set ERR=!ERRORLEVEL!
goto PAUSE_ERR

:MOTOR_SCOUT
echo === F1 Scout 800 — AAT-6V 4.0 + 33 HS I ===
echo.
echo Setup: solo motor AAT-6V y neumatico HS I; diff siempre; caja stock; vacio.
echo   Asfalto recto WOT ~60 s — Ctrl+C para parar
echo.
%PY% grabar_ce.py --probe
if errorlevel 1 (
    set ERR=1
    goto PAUSE_ERR
)
%PY% grabar_ce.py --import --compare --index --live --protocol s8_f1_asfalto_aat6v --baseline s8_aat6v_f1 %2 %3 %4 %5 %6 %7 %8 %9
set ERR=!ERRORLEVEL!
goto PAUSE_ERR

:SNAP
if "%2"=="" (
    echo Uso: grabar_telemetria.bat snap ^<nombre^>
    echo   ej. grabar_telemetria.bat snap barro_ligero
    echo Parada TERR: quieto ~30 s en el terreno, mismo camion.
    exit /b 1
)
echo === Snapshot TERR: %2 ===
%PY% grabar_ce.py --probe
if errorlevel 1 (
    set ERR=1
    goto PAUSE_ERR
)
%PY% cheat_engine/scan_wheel_substance.py --save %2
set ERR=!ERRORLEVEL!
goto PAUSE_ERR

:DIFF
if "%3"=="" (
    echo Uso: grabar_telemetria.bat diff ^<A^> ^<B^>
    echo   ej. grabar_telemetria.bat diff tierra_seca barro_ligero
    exit /b 1
)
%PY% cheat_engine/scan_wheel_substance.py --diff %2 %3
set ERR=!ERRORLEVEL!
goto PAUSE_ERR

:TIRE
%PY% cheat_engine/scan_wheel_addons.py %2 %3 %4 %5 %6 %7 %8 %9
set ERR=!ERRORLEVEL!
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
echo   grabar_telemetria.bat drive
echo   grabar_telemetria.bat drive --watch 30
echo   grabar_telemetria.bat drive_snap diff_off
echo   grabar_telemetria.bat drive_diff diff_off diff_on
echo   grabar_telemetria.bat motor
echo   grabar_telemetria.bat motor_scout
echo.

echo Preflight CE...
%PY% grabar_ce.py --probe
if errorlevel 1 (
    echo.
    echo Abortado: entra al mapa conduciendo y reintenta.
    set ERR=1
    goto PAUSE_ERR
)
echo.
echo === Carga bastidor / remolque (quieto 30 s si F3) ===
%PY% cheat_engine/scan_cargo.py
echo.
echo Si vas a grabar F3 con bastidor lleno y load_hint=vacio o payload ~0:
echo   - Para el camion quieto ~30 s y repite: grabar_telemetria.bat cargo
echo   - No sigas hasta ver cargado y payload_kg ^> 300
echo.

%PY% grabar_ce.py --import --compare --auto --index --live --baseline play_free_v1 %*
set ERR=!ERRORLEVEL!

echo.
if !ERR! neq 0 (
    echo Termino con error !ERR!.
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
if !ERR! neq 0 echo Termino con error !ERR!.
:PAUSE_END
pause
exit /b !ERR!
