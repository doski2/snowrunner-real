# SnowRunner — Fase 6: Telemetría Havok (memoria + comparación)

**Objetivo:** muestreo automático desde memoria Havok (sin depender del HUD) y comparación juego vs simulador Python.

**Estado:** pipeline operativo (junio 2026). Recomendado: `grabar_ce.py` / `grabar_telemetria.bat` (no hace falta Cheat Engine).

---

## Estado actual (2026-06-25)

| Componente | Estado |
|------------|--------|
| `memoria_havok.py` — lectura sin CE | **Hecho** |
| `grabar_ce.py` + `grabar_telemetria.bat` | **Hecho** — 120 s, `--auto`, comparación por tramos |
| Terreno runtime (`terrain_kind`, `contact_avg`) | **Hecho** — fix Fleetstar asfalto (`+0x2EC`) |
| Carga runtime (`payload_kg`, masa Havok) | **Hecho** — experimental; calibrar con `scan_cargo.py` |
| Auto protocolo (camión + terreno + carga) | **Hecho** — `resolve_protocol_from_ce_rows` |
| Comparación por tramos mud/hard | **Hecho** — `compare_session_by_terrain` |
| Fleetstar asfalto CE | **1 sesión válida** — `ce_fs_f1_asfalto_20260625_211942.json` |
| Sesiones antiguas (sin `contact_avg` / terreno erróneo) | Archivadas en `telemetria/sesiones/_archivo/` |
| MH9500 / CK1500 CE recientes | **Pendiente** re-grabar con pipeline actual |
| Calibrar sim barro (MAE &lt; 15 km/h) | En curso |

---

## Inicio rápido (recomendado)

```powershell
# 1. SnowRunner en MAPA conduciendo (camión mod)
python grabar_ce.py --probe

# 2. Grabar 120 s ruta mixta + importar + comparar
grabar_telemetria.bat

# 3. Solo importar CSV existente
python importar_ce_csv.py --auto --compare
```

`--auto` elige:
- **Camión** desde `vehicle_id` del CSV
- **Terreno** dominante (`mud` → barro, `hard` → asfalto)
- **Carga** desde `load_hint` / `payload_kg` → `fs_f3_carga`, `mh_f3_semi`, `f3_carga_barro`, etc.

---

## Cadena de punteros (build Steam 2026-06-25)

```
SnowRunner.exe+2A8EDD8  →  TRUCK_CONTROL@combine@@
  → +0x8   →  vehículo activo
  → +0x5D0 →  hkpRigidBody chasis
  → +0xB8  →  hkpMotion*
  → motion+0xA4 →  1/masa (kg)
  → rb+0x230, +0x238 → velocidad m/s
  → veh+0xD10 → ID (p. ej. s_fleetstar_f2070a)
  → veh+0x48 → addon → +0x568 combustible
```

| Constante | Valor actual | Legacy (obsoleto) |
|-----------|--------------|---------------------|
| `TRUCK_CONTROL_OFF` | `0x2A8EDD8` | `0x2A876A8` |
| `DRIVE_LOGIC_OFF` | `0x2A8EDC8` | `0x2E5DA08` |
| `OFF_RB` | `+0x5D0` | `+0x5C8` |
| `OFF_ID` | `+0xD10` | `+0xCE8` |

Detalle: `cheat_engine/offsets_referencia.json` · código: `cheat_engine/memoria_havok.py`.

---

## Terreno automático (runtime)

**No leemos el mapa .pak** (viscosidad, capas del autor). Leemos contacto Havok por rueda (`TRUCK_WHEEL_MODEL`):

| Offset | Campo CSV | Uso |
|--------|-----------|-----|
| `+0x2FC` | `wheel_grip` | Grip; en Fleetstar UHD asfalto ~0.2 |
| `+0x2B4` | `surface_avg` | Deformación; en FS suele ser negativo en asfalto |
| `+0x2EC` | `contact_avg` | **Sustancia** — ~0.80 asfalto, ~0.55 barro (ambos camiones) |

Clasificación `terrain_kind`: `hard` | `mud` | `soft` | `mixed`.  
Si `+0x2B4` es muy negativo (Fleetstar), se usa `+0x2EC` para discriminar asfalto/barro.

Calibración: `cheat_engine/wheel_snaps/` (`asfalto.json`, `barro.json`, `asfalto_fs.json`).

---

## Carga automática (runtime)

| Campo CSV | Origen |
|-----------|--------|
| `total_mass_kg` | Masa Havok chasis (`motion+0xA4`) |
| `empty_mass_kg` | XML/sim del mod (6650 Fleetstar, 7500 MH9500, 1750 CK1500) |
| `payload_kg` | `total − vacío − 400 kg` (tara combustible/aditivos) |
| `load_hint` | `vacio` \| `cargado` \| `trailer_vacio` \| `trailer_cargado` |
| `trailer_id`, `trailer_mass_kg` | Remolque enganchado (grafo Havok, ≤22 m) |

```powershell
python cheat_engine/scan_cargo.py --save vacio
# cargar bastidor o enganchar remolque
python cheat_engine/scan_cargo.py --save cargado
python cheat_engine/scan_cargo.py --diff vacio cargado
```

> Si `payload_kg` sigue en 0 con carga visual, la masa puede no reflejarse en el rigid body del chasis — ver `cheat_engine/README.md`.

### Auto protocolo según carga

| Camión | Vacío + barro | Cargado + barro |
|--------|---------------|-----------------|
| Fleetstar | `fs_f2_barro_uhd` | `fs_f3_carga` |
| MH9500 | `mh_f2_barro_offroad` | `mh_f3_semi` |
| CK1500 | `f2_barro_offroad` | `f3_carga_barro` |

En asfalto cargado: protocolo firme + `load_scenario_id` del escenario cargado en el sim.

---

## Columnas CSV completas

`telemetria_ce_log.csv` en `Documents\My Games\SnowRunner\base\` (fallback: `cheat_engine\`).

| Grupo | Columnas |
|-------|----------|
| Movimiento | `t_s`, `speed_kmh`, `vel_x/y/z`, `ang_yaw`, `pos_x/y/z` |
| Vehículo | `vehicle_id`, `fuel_pct`, `chain`, `event` |
| Terreno | `terrain_kind`, `surface_wheel`, `wheel_grip`, `surface_avg`, `contact_avg`, `grip_min/max`, `terrain_hint` |
| Carga | `load_hint`, `trailer_id`, `cargo_mass_kg`, `payload_kg`, `total_mass_kg`, `empty_mass_kg`, `trailer_mass_kg`, `truck_mass_kg`, `attached_cargo_mass_kg` |

Sesiones importadas: `telemetria/sesiones/ce_*.json`.  
Sesiones obsoletas: `telemetria/sesiones/_archivo/` (formato antiguo o terreno mal clasificado).

---

## Flujo alternativo (Cheat Engine + Lua)

1. CE → `SnowRunner.exe` → `TelemetryLogger.lua` → `quickStart()`
2. Conducir → `stopTelemetryLogger()`
3. `python importar_ce_csv.py --auto --compare`

Mismo CSV y mismos scripts que `grabar_ce.py`. Ver `cheat_engine/README.md`.

---

## Re-buscar offsets tras parche del juego

1. [CE_RTTI_Reverse_Lookup](https://github.com/FindMuck/CE_RTTI_Reverse_Lookup) → clase **`TRUCK_CONTROL@combine@@`**
2. Actualizar `TRUCK_CONTROL_OFF` en `memoria_havok.py`, `TelemetryLogger.lua`, `offsets_referencia.json`
3. `python grabar_ce.py --probe` en mapa conduciendo
4. Si falla: `python cheat_engine/scan_singleton.py`, `scan_veh_offsets.py`

---

## Archivos del kit

| Archivo | Rol |
|---------|-----|
| `grabar_ce.py` | Logger principal (sin CE) |
| `grabar_telemetria.bat` | 120 s + `--auto` + `--compare` |
| `importar_ce_csv.py` | CSV → JSON + comparación |
| `comparar_telemetria.py` | Comparar sesiones guardadas |
| `telemetria.py` | Protocolos, auto, segmentos, sim |
| `cheat_engine/memoria_havok.py` | Lectura Havok compartida |
| `cheat_engine/scan_wheel_substance.py` | Calibrar terreno |
| `cheat_engine/scan_cargo.py` | Calibrar carga |
| `test_telemetria.py`, `test_ce_import.py` | Tests |

---

## Comandos

```powershell
python grabar_ce.py --probe
python grabar_ce.py --duration 60 --import --auto --compare
python importar_ce_csv.py --auto --compare
python comparar_telemetria.py telemetria/sesiones/ce_*.json --export
python -m unittest test_telemetria test_ce_import -v
```

---

## Pendiente

1. Re-grabar MH9500 y CK1500 con columnas actuales (terreno + carga).
2. Fleetstar barro `fs_f2_barro_uhd` en tramo barro real (sesiones previas archivadas).
3. Validar detección de carga en juego (`scan_cargo.py`).
4. Afinar sim hasta MAE &lt; 15 km/h por tramo.
5. Importar `vel_y` al JSON de sesión (ya está en CSV).

Ver también: **`FASE-5.md`**, `cheat_engine/README.md`, `camiones/fleetstar/FASES.md`, `camiones/mh9500/FASES.md`.
