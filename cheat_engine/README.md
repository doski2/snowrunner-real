# Cheat Engine — Kit telemetría Havok (Fase 6)

Lectura de **velocidad**, combustible, terreno por rueda, carga y ID de vehículo → CSV → `importar_ce_csv.py` → comparación con sim.

> Offsets validados build Steam **2026-06-25**. Tras parche del juego: RTTI + `offsets_referencia.json`. Ver `docs/FASE-6.md`.

---

## Inicio rápido (sin Cheat Engine) — recomendado

1. SnowRunner en **mapa conduciendo** (no menú/garaje).
2. En la raíz del proyecto:

```powershell
python grabar_ce.py --probe
.\grabar_telemetria.bat
```

`.\grabar_telemetria.bat` = 120 s, ruta mixta, `--auto` (camión + terreno + carga), importa y compara por tramos. En **PowerShell** usar `.\` delante del `.bat`.

Subcomandos (sin grabar sesión):

```powershell
.\grabar_telemetria.bat probe              # preflight + resumen terreno
.\grabar_telemetria.bat snap barro_ligero  # snapshot TERR (calibracion mud_grade)
.\grabar_telemetria.bat diff tierra_seca barro_ligero
.\grabar_telemetria.bat tire               # neumatico montado (CE)
.\grabar_telemetria.bat cargo              # carga bastidor / remolque (CE)
.\grabar_telemetria.bat cargo --save cargado
.\grabar_telemetria.bat drive --watch 30   # throttle + rpm en vivo
```

Antes de **F3**: quieto ~30 s con bastidor lleno → `cargo` debe mostrar `load_hint=cargado` y `payload_kg` > 300.

Diagnóstico puntual:

```powershell
python grabar_ce.py --duration 60 --import --auto --compare
python cheat_engine/scan_cargo.py
python cheat_engine/scan_wheel_substance.py
python cheat_engine/scan_wheel_addons.py
python cheat_engine/scan_drive_state.py
python cheat_engine/scan_drive_state.py --watch 30
```

### Tracción, gas y RPM *(calibrado 2026-07-09)*

| Campo CSV / nota | Offset | Rango |
|----------------|--------|-------|
| `throttle` | `vehicle+0x760` (f32) | 0 = sin gas, 1 = a fondo |
| `engine_rpm` | `vehicle+0x114` (f32) | ~350 ralentí, sube con gas |
| `fuel_rate_pct_min` | derivado de `fuel_pct` | proxy de carga motor sin offset |

Calibración gas + RPM (recomendado por camión; quieto ~0 km/h, motor ON):

```powershell
.\grabar_telemetria.bat drive_cal      # escanea, aplica y verifica hasta OK
.\grabar_telemetria.bat drive_verify   # re-verificar gas off / gas fondo
```

**Banco de pruebas (independiente):** en la raíz del proyecto.

```powershell
.\banco_pedal.bat              # ventana: Ref 0% / Delta / Bases / Guia CE
python cheat_engine/banco_drive.py --dump-bases   # hijos TRUCK_CONTROL en consola
.\banco_pruebas.bat --scout
```

Escaneo profundo: singleton `TRUCK_CONTROL`, punteros hijos `tc+0xNN` (cada +8 hasta 0x200), `drive_logic`, `vehicle`. El pedal del mando suele estar en un hijo de TC, no en `vehicle+0x760`.

Flujo manual (snapshots):

```powershell
.\grabar_telemetria.bat drive_snap gas_off   # pie del freno
.\grabar_telemetria.bat drive_snap gas_full  # gas a fondo (freno o pared)
.\grabar_telemetria.bat drive_diff gas_off gas_full
python cheat_engine/calibrar_drive.py --from-snaps gas_off gas_full --apply --verify-live
```

Snapshots en `cheat_engine/drive_snaps/`. Offsets en `offsets_referencia.json` → `drive_runtime.candidates`. **Revalidar en T813** (Bandit usa `vehicle+0x760`; T813 puede necesitar otro offset).

`diff_lock_live` / `low_gear_live`: offsets u8 aún **null** — usar `--discover` togglando diff/L como en `scan_drive_state.py`.

---

## Inicio rápido (Cheat Engine + Lua)

1. CE → `SnowRunner.exe` → `TelemetryLogger.lua` → Execute.
2. Consola: `quickStart()` → conducir → `stopTelemetryLogger()`.
3. `python importar_ce_csv.py --auto --compare`

Mismo CSV que `grabar_ce.py` (mismos offsets en `memoria_havok.py`).

---

## Offsets actuales (2026-06-25)

| Constante           | Valor                                          |
|---------------------|------------------------------------------------|
| `TRUCK_CONTROL_OFF` | `0x2A8EDD8` (antes `0x2A876A8`)                |
| `DRIVE_LOGIC_OFF`   | `0x2A8EDC8`                                    |
| `OFF_VEH_TRUCK`     | `+0x8`                                         |
| `OFF_RB`            | `+0x5D0`                                       |
| `OFF_RB_MOTION_PTR` | `+0xB8` → `motion+0xA4` = 1/masa (kg)          |
| `OFF_ID`            | `+0xD10`                                       |
| `OFF_ADDON`         | `+0x48`                                        |
| Velocidad           | `rb+0x230`, `+0x238` (m/s)                     |
| Rueda grip          | `+0x2FC`                                       |
| Rueda sustancia     | `+0x2EC` (contact_avg); `+0x2B4` (deformación) |

**Lectura en vivo:** no hay caché en Python — cada muestra hace `ReadProcessMemory` fresco. Havok **suaviza** `+0x2EC` y `+0x2FC`: al cambiar de terreno el contacto puede tardar varios segundos en bajar (ej. 1.0 → 0.89 → 0.67). En tierra compacta Fleetstar puede quedarse en `contact=1.0` mucho rato (ver `wheel_snaps/tierra_seca.json`). La consola avisa drift de grip/contact aunque `terrain_kind` no cambie.

Detalle: `offsets_referencia.json` · código: `memoria_havok.py`.

---

## Archivos

| Archivo                   | Uso                                                          |
|---------------------------|--------------------------------------------------------------|
| `memoria_havok.py`        | Lectura Havok (compartida con `grabar_ce.py`)                |
| `grabar_ce.py`            | **Logger sin CE** (raíz del proyecto)                        |
| `TelemetryLogger.lua`     | Logger CE (`quickStart()`)                                   |
| `probe_memoria.py`        | Diagnóstico singleton                                        |
| `scan_singleton.py`       | Re-buscar TRUCK_CONTROL tras parche                          |
| `scan_veh_offsets.py`     | Buscar rb/id/fuel si cambian                                 |
| `scan_wheel_substance.py` | Calibrar terreno por rueda                                   |
| `scan_suspension.py`      | **Estudio** suspensión — pos_y, floats rueda, addon mecánico |
| `scan_cargo.py`           | Calibrar carga / remolque                                    |
| `scan_wheel_addons.py`    | **Neumatico montado** (game_id Havok, no protocolo)          |
| `wheel_snaps/`            | Referencias asfalto/barro (MH + Fleetstar)                   |
| `wheel_addon_snaps/`      | Snapshots neumatico (`scan_wheel_addons.py --save`)          |
| `suspension_snaps/`       | Snapshots vacío/cargado/bounce (`scan_suspension.py`)        |
| `load_snaps/`             | Snapshots vacío/cargado (`--save`, `--diff`)                 |
| `drive_snaps/`            | Snapshots diff/L/gas (`scan_drive_state.py`)                 |
| `grabar_telemetria.ps1`   | Alternativa PowerShell                                       |

---

## Terreno automático

Por rueda (`TRUCK_WHEEL_MODEL`), cada ~0,5 s:

| Campo CSV                       | Significado                                                     |
|---------------------------------|-----------------------------------------------------------------|
| `terrain_kind`                  | `hard`, `mud`, `soft`, `mixed`                                  |
| `mud_grade` / `mud_grade_label` | 0–4: seco → barro ligero → profundo → vado                      |
| `surface_deform_avg`            | Deformación `+0x2B4` (media ruedas; más negativo ≈ más hundido) |
| `contact_min` / `contact_max`   | Rango `+0x2EC` por rueda                                        |
| `contact_avg`                   | ~0.80 asfalto, ~0.55 barro, **~0.35 barro profundo**            |
| `wheel_grip`                    | ~1.0 asfalto MH; ~0.2 asfalto Fleetstar UHD                     |
| `surface_avg`                   | Sustancia efectiva usada al clasificar                          |
| `pos_x`, `pos_z`                | Coordenadas mundo                                               |

**Importación `mixed`:** si el terreno dominante CE es `mixed` (8×8, ruedas distintas), la comparación sim de sesión completa usa la superficie del **protocolo** (p. ej. asfalto en F1); los tramos `hard`/`mud` se comparan por separado (`compare_session_by_terrain`).

**Fleetstar:** en asfalto `+0x2B4` suele ser negativo; se usa `+0x2EC` para clasificar firme. Calibración: `wheel_snaps/asfalto_fs.json`.

```powershell
python cheat_engine/scan_wheel_substance.py --save asfalto_fs
python cheat_engine/scan_wheel_substance.py --diff asfalto_fs barro
# --diff muestra solo terrain_kind/mud_grade distintos y offsets +2FC/+2EC/+2B4
```

Al importar con `--auto`, los tramos `mud` y `hard` se comparan con protocolos distintos (`compare_session_by_terrain`).

---

## Carga automática

| Campo                           | Descripción                                             |
|---------------------------------|---------------------------------------------------------|
| `total_mass_kg`                 | Masa Havok chasis + piezas de carga (vector `+0x1E0`)   |
| `empty_mass_kg`                 | Masa vacía XML/sim (registry)                           |
| `payload_kg`                    | Carga útil ≈ `total − vacío − 400`                      |
| `cargo_mass_kg`                 | Máximo entre payload, slots BoneCargo y tipo `cargo_*`  |
| `load_hint`                     | `vacio`, `cargado`, `trailer_vacio`, `trailer_cargado`  |
| `packed_cargo_slots`            | Slots `BoneCargo_*` en bastidor (attach+030)            |
| `path_cargo_type`               | Tipo en registro runtime `veh+060`                      |
| `attached_cargo_mass_kg`        | Suma Havok de cuerpos de carga (vector addons `+0x1E0`) |
| `trailer_id`, `trailer_mass_kg` | Remolque enganchado                                     |

**Nota:** con bastidor lleno el chasis suele quedarse en ~6650 kg. La carga vive en **cuerpos Havok separados** (simulation island `rb+0x128`, vector addons `+0x1E0`). Si un frame falla, un **latch** mantiene `cargado` ~40 s.

**Antes de F3:** quieto 30 s con bastidor lleno → `python grabar_ce.py --probe` debe mostrar `cargado` y `cargo_kg` > 300.

Masas vacías mod: Fleetstar **6650**, MH9500 **7500**, CK1500 **1750**, T813 **14571** kg.

```powershell
python cheat_engine/scan_cargo.py --save vacio
python cheat_engine/scan_cargo.py --save cargado
python cheat_engine/scan_cargo.py --diff vacio cargado
```

`--auto` en importación elige `fs_f3_carga` / `mh_f3_semi` / `f3_carga_barro` si `payload_kg > 300` o `load_hint` cargado.

---

## Log CSV

- `%USERPROFILE%\Documents\My Games\SnowRunner\base\telemetria_ce_log.csv`
- Fallback: `cheat_engine\telemetria_ce_log.csv`
- Estado: `telemetria_ce_status.txt`

Cabecera completa (ver `memoria_havok.CSV_HEADER`):

`t_s`, `speed_kmh`, `vel_*`, `ang_yaw`, `pos_*`, `fuel_pct`, `vehicle_id`, `terrain_kind`, `contact_avg`, `throttle`, `engine_rpm`, `fuel_rate_pct_min`, `load_hint`, `payload_kg`, `total_mass_kg`, …

Sesiones JSON: `telemetria/sesiones/<vehiculo>/`. Histórico inválido: `telemetria/sesiones/_archivo/`.

---

## RTTI tras parche

[CE_RTTI_Reverse_Lookup](https://github.com/FindMuck/CE_RTTI_Reverse_Lookup): clase **`TRUCK_CONTROL@combine@@`** → actualizar `TRUCK_CONTROL_OFF` en `memoria_havok.py` y `TelemetryLogger.lua`.
