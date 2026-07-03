# SnowRunner — Cheat Engine + telemetria (Fase 6)

$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$root = Split-Path -Parent $here

Write-Host "=== Opcion A: SIN Cheat Engine (recomendado) ===" -ForegroundColor Green
Write-Host @"
  1. SnowRunner en MAPA conduciendo
  2. Desde la carpeta del proyecto:

     python grabar_ce.py --probe              # comprobar lectura
     python grabar_ce.py --duration 60        # grabar 60 s
     python grabar_ce.py --duration 60 --import --protocol f2_barro_offroad --compare

  O doble clic / ejecutar:
     cheat_engine\grabar_telemetria.ps1
"@ -ForegroundColor Gray
Write-Host ""

Write-Host "=== Opcion B: Cheat Engine ===" -ForegroundColor Cyan
Write-Host @"
  1. CE -> Open Process -> SnowRunner.exe
  2. Table -> Lua Script -> TelemetryLogger.lua -> Execute
  3. Consola CE: quickStart()
  4. Conduce -> stopTelemetryLogger()
  5. python importar_ce_csv.py --protocol f2_barro_offroad --compare
"@ -ForegroundColor Gray
Write-Host ""

Write-Host "=== Diagnostico rapido ===" -ForegroundColor Cyan
Set-Location $root
python grabar_ce.py --probe
