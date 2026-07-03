# SnowRunner — grabar telemetria Havok (sin Cheat Engine)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path

$sr = Get-Process -Name SnowRunner -ErrorAction SilentlyContinue
if (-not $sr) {
    Write-Host "SnowRunner no esta corriendo. Abre el juego y entra al mapa." -ForegroundColor Yellow
    exit 1
}

$duration = 60
if ($args.Count -ge 1) { $duration = [int]$args[0] }

Write-Host "=== Grabacion memoria Havok ($duration s) ===" -ForegroundColor Cyan
Write-Host "Conduce en el mapa. Cambiar camion OK." -ForegroundColor Gray
Write-Host ""

Set-Location $root
python grabar_ce.py --duration $duration --import --compare --auto
