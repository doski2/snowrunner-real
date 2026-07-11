# Plan — Base de datos del juego (SnowRunner realismo)

**Objetivo:** acumular, estructurar y reutilizar **toda la información útil** del juego (XML, Havok, sesiones, terreno, carga, clima) como una **base de conocimiento viva** que alimente las Fases 1–8, el sim Python y los parches XML con **decisiones medidas**, no a ojo.

**Principio:** una captura → muchos usos. Cada sesión de juego o extracción del `.pak` aporta filas a la base; las fases **leen** la base, no reinventan datos.

---

## 1. Problema que resolvemos

| Hoy (jun-2026)                                             | Con la base (objetivo)                | Estado jun-2026 |
|------------------------------------------------------------|---------------------------------------|-----------------|
| Datos repartidos (JSON sueltos, CSV, memoria, docs FASE-*) | Índice único + historial              | **Parcial** — `datos/` + `manifest.json` + `consultar_base.py`; `calibracion.json` vacío; sin sesiones en `telemetria/sesiones/` |
| “¿Este parámetro XML hace algo?” → suposición              | Antes/después con CE + referencia XML | **Parcial** — refs XML al importar (§2.5); faltan baselines F1/F2 y tags `baseline_mod_v1` / `patch_*` |
| Calibrar `KM_MUD_*` sin baseline Marshall                  | Query: “barro TM II, vacío, Michigan” | **Parcial** — `indexar_sesion.py` hecho; falta volumen de sesiones/tramos en `calibracion.json` |
| Fase 7 clima sin datos propios                             | Sesiones día/noche etiquetadas        | **No** — campos `clima` / `hora_juego` en metadatos; cero sesiones `f7_*` |
| Varios GB del `.pak` sin inventario                        | Catálogo searchable de clases         | **Sí (stock)** — `auditar_pak_catalogo.py` (42 camiones, 125 motores, 76 cajas…); pendiente diff mod, `trailers.json` |

**Lectura rápida:** Capa B (catálogo XML stock) operativa; Capa C (evidencia CE indexada) casi vacía. El §1 sigue siendo la motivación del plan, no un checklist cerrado.

---

## 2. Fuentes de datos (qué entra en la base)

### 2.1 Estáticas (diseño — ~2–3 GB `initial.pak.bak`)

| Fuente                      | Tamaño orientativo | Qué aporta                                        | Herramienta actual               |
|-----------------------------|--------------------|---------------------------------------------------|----------------------------------|
| `initial.pak.bak` (Steam)   | ~29 MB ZIP + tail  | XML camiones, motores, ruedas, cajas, remolques   | `repack_pak.py`, `verify_pak.py` |
| Parches mod (`patches.py`)  | KB                 | Diff diseño vs stock                              | `camiones/*/patches.py`          |
| `remolques_inventario.json` | KB                 | Masas remolque, acople                            | `auditar_remolques.py`           |
| BinEditor Guides (Steam)    | PDF                | Terreno mapa, no camión                           | ruta en `telemetria.py`          |

**Pendiente:** inventario completo XML (ver §4.1).

### 2.2 Runtime (comportamiento — sesiones CE)

| Campo / concepto                                          | Origen            | Frecuencia         |
|-----------------------------------------------------------|-------------------|--------------------|
| `speed_kmh`, `t_s`                                        | Havok velocidad   | 0,5 s              |
| `vehicle_id`, `terrain_kind`, `wheel_grip`, `contact_avg` | Ruedas            | 0,5 s              |
| `load_hint`, `payload_kg`, `trailer_*`, `total_mass_kg`   | Masa / carga      | 0,5 s              |
| `packed_cargo_slots`, `cargo_types` (bastidor)            | attach+030 slots  | 0,5 s *(jun-2026)* |
| `pos_x/y/z`                                               | Posición (tramos) | 0,5 s              |
| `ang_yaw` → `yaw_rate_deg_s`, `turn_radius_m`             | Giro Havok + masa | 0,5 s              |
| Protocolo inferido                                        | `--auto`          | por sesión         |

**Herramientas:** `grabar_ce.py`, `importar_ce_csv.py`, `telemetria/sesiones/*.json`

### 2.3 Derivadas (sim + comparación)

| Artefacto                     | Uso                               |
|-------------------------------|-----------------------------------|
| `telemetria_comparacion.json` | MAE, v30 juego vs sim             |
| `simulacion_*.json`           | Matrices Fase 2–4                 |
| `camiones/*/simulador.py`     | Constantes calibradas (`*_MUD_*`) |

### 2.4 Contexto sesión (metadatos obligatorios)

Cada captura debe registrar:

- `build_juego` / fecha patch Steam  
- `vehicle_id` mod (`ck1500`, `mh9500`, …)  
- `mapa`, `ruta`, `clima` (Fase 7), `hora_juego` si aplica  
- Setup taller: motor, caja, neumáticos, suspensión, diff, remolque  
- **Referencias XML stock** (auto al importar CE, ver §2.5): `steer_speed_xml`, `responsiveness_xml`, `engine_responsiveness_xml`  
- `mod_version` (git commit o fecha `apply_mod`)  
- `protocol_id` o `--auto`  

Sin esto, la base acumula ruido.

### 2.5 Referencias XML en `session_context.setup` *(implementado)*

Al importar CSV (`importar_ce_csv.py`), se rellenan desde `datos/catalogo/` vía `datos/catalog_lookup.py`:

| Campo                                              | XML origen                                 | Notas                                                 |
|----------------------------------------------------|--------------------------------------------|-------------------------------------------------------|
| `steer_speed_xml`                                  | `TruckData` SteerSpeed                     | Constante diseño; giro real = `yaw_rate_deg_s` en CSV |
| `responsiveness_xml`                               | `TruckData` Responsiveness                 | Chasis; no varía con carga en runtime                 |
| `engine_responsiveness_xml`                        | motor default `EngineResponsiveness`       | Usado en sim Python como filtro acelerador            |
| `default_suspension_xml`                           | `SuspensionSocket` Default                 | Variante de taller stock                              |
| `suspension_socket_xml`                            | `SuspensionSocket` Type                    | Archivo en `suspensions.json`                         |
| `suspension_strength_front_xml`                    | `Suspension` Strength (1.ª variante front) | Rigidez delantera stock                               |
| `suspension_strength_rear_xml`                     | `Suspension` Strength (1.ª variante rear)  | Rigidez trasera stock                                 |
| `suspension_damping_front_xml`                     | `Suspension` Damping (1.ª variante front)  | Amortiguación delantera stock                         |
| `suspension_damping_rear_xml`                      | `Suspension` Damping (1.ª variante rear)   | Amortiguación trasera stock                           |
| `suspension_height_front_xml`                      | `Suspension` Height (1.ª variante front)   | Altura/neutral delantera stock                        |
| `suspension_height_rear_xml`                       | `Suspension` Height (1.ª variante rear)    | Altura/neutral trasera stock                          |
| `default_engine_xml`                               | `EngineSocket` Default                     | Enlace al motor indexado                              |
| `engine_socket_type_xml`                           | `EngineSocket` Type                        | Familias de motor compatibles (CSV)                   |
| `engine_name_xml`                                  | nombre variante en `engines.json`          | —                                                     |
| `default_gearbox_xml`                              | `GearboxSocket` Default                    | Caja stock default                                    |
| `gearbox_socket_type_xml`                          | `GearboxSocket` Type                       | Archivo de cajas compatible (ej. `gearboxes_scouts`)  |
| `gearbox_file_id_xml`                              | `gearboxes.json`                           | Resolución Default → archivo XML                      |
| `gearbox_lower_gear_xml` / `gearbox_high_gear_xml` | `IsLowerGearExists` / `IsHighGearExists`   | L− / H en taller                                      |
| `gearbox_first_gear_ang_vel_xml`                   | 1.ª `<Gear AngVel>`                        | Crawl / 1ª marcha                                     |
| `gearbox_high_gear_ang_vel_xml`                    | `<HighGear AngVel>`                        | Overdrive H                                           |
| `gearbox_fuel_consumption_xml`                     | `FuelConsumption` caja                     | —                                                     |
| `catalog_source`                                   | —                                          | Siempre `initial.pak.bak stock` hasta diff mod        |

**Live vs import (§2.5):**

| Origen               | Cuándo              | Qué suspensión / chasis                                            |
|----------------------|---------------------|--------------------------------------------------------------------|
| **`--live` / CSV**   | Cada 0,5 s en juego | `pos_y` (Havok), masa, giro — **no** Strength/Damping/Height XML   |
| **`catalog_lookup`** | Al importar CSV     | `suspension_*_xml`, motor, caja — diseño stock del `.pak`          |
| **Taller instalado** | —                   | No leído en CE; caja/suspensión mod manual en metadatos *(futuro)* |

**Terreno Havok (`terrain_kind`):** por rueda (grip +0x2FC, contact +0x2EC). Etiqueta = **mayoría** de ruedas; `mixed` solo si empate (p. ej. 2+2). En `--live`, `ruedas=mud|mud|soft|hard` si hay desacuerdo. Grip/contact en pantalla son **medias** — usar `grip_d=min-max` en notas CSV para ver ruedas distintas.

**Importante:** el catálogo actual es **stock Steam** (`initial.pak.bak`). Los parches mod (`patches.py`) pueden cambiar `Responsiveness` / `EngineResponsiveness`; comparar con `verify_pak` o catálogo mod *(futuro)*.

**Respuesta al acelerador en juego (futuro):** no hay offset CE para `Responsiveness`. Medir pendiente `Δspeed/Δt` en WOT a 5–10 km/h (vacío vs cargado), igual que desaceleración en crawl.

### 2.5.1 CE suspensión — estudio *(prioridad media; no bloquea grabación)*

**¿Conviene?** Sí **estudiar**; **implementar en CSV** solo tras validar offsets (mismo enfoque que terreno +0x2EC).

| Capa               | Qué tenemos                                        | Qué falta                                      |
|--------------------|----------------------------------------------------|------------------------------------------------|
| **XML §2.5**       | Strength/Damping/Height stock al importar          | Variante taller instalada; diff mod            |
| **CE runtime**     | `pos_y` chasis (Havok)                             | Compresión por rueda, travel, pitch bajo carga |
| **Carga bastidor** | `load_hint: cargado`, slots `BoneCargo_*` (§2.5.2) | Remolque enganchado; masa Havok inv=0 a veces  |
| **Sim**            | No modela suspensión XML                           | Calibrar con CE si hay señal estable           |

**Señales candidatas (por mapear):**

| Fuente                  | Hipótesis                                                       |
|-------------------------|-----------------------------------------------------------------|
| `rb + OFF_POS_Y`        | Hundimiento global (vacío vs cargado vs barro) — **ya grabado** |
| `TRUCK_WHEEL_MODEL`     | Floats de compresión/amortiguador por rueda — **sin offset**    |
| `addon + 0x1F8 / 0x210` | Pistones / elementos mecánicos — **sin offset**                 |
| Correlación             | Δpos_y vs `payload_kg`; mismo tramo vacío/cargado               |

**Calibración Fleetstar (jun-2026)** — snapshots en `cheat_engine/suspension_snaps/`:

| Snapshot       | Escenario                                                  | `load_hint`| `pos_y` | Notas                            |
|----------------|------------------------------------------------------------|------------|---------|----------------------------------|
| `vacio.json`   | Sideboard vacío, parado                                    | vacio      | ~68.567 | Masa ~6650 kg                    |
| `cargado.json` | Sideboard + **2×** piezas repuesto especiales empaquetadas | cargado    | ~68.566 | Masa ~9050 kg; `packed_slots: 2` |
| `bounce.json`  | Badén / frenada fuerte                                     | —          | —       | **Pendiente**                    |

**Resultado diff `vacio` → `cargado` (parado, mismo sitio):**

- Δ`pos_y` chasis ≈ **−0.001 m** — **sin señal útil** en reposo con carga.
- Cambios en floats rueda `+0D0/+0DC`, `+210–+224` y bloques `+3xx` (transform) — **ruido**, no validados como compresión.
- **Conclusión:** hace falta snapshot **`bounce`** o tramo en marcha; el criterio de implementación CSV **no se cumple** aún.

**Protocolo de estudio** (paralelo a juego libre §4.1):

```powershell
python grabar_ce.py --probe
python cheat_engine/scan_cargo.py          # packed_slots, cargo_types
python cheat_engine/scan_suspension.py --save vacio      # quieto, vacio
python cheat_engine/scan_suspension.py --save cargado    # misma zona, carga empaquetada
python cheat_engine/scan_suspension.py --save bounce     # baden o frenada
python cheat_engine/scan_suspension.py --diff vacio cargado
python cheat_engine/scan_suspension.py --diff vacio bounce
```

**Criterio para pasar a implementación:** float estable en ≥2 ruedas que correlacione con (a) carga o (b) parche `Strength` XML before/after. Entonces añadir columnas CSV `susp_compress_*` / derivar `pitch_deg` y enlazar en `session_context.setup` junto a `suspension_*_xml`.

**No intentar leer Strength/Damping XML en memoria** — son constantes de diseño; lo medible es **efecto** (pos_y, travel).

### 2.5.2 CE carga en bastidor — plataforma lateral *(implementado jun-2026)*

Carga empaquetada en **addon sideboard** (no remolque). Calibrado Fleetstar F2070A + `trucks_addons_frame_addon_sideboard_2`.

| Señal | Origen CE | Uso |
|-------|-----------|-----|
| `packed_cargo_slots` | `attach+078` → `+030` → slots `+090`, `+0E8`, … | Nº piezas empaquetadas |
| `packed_cargo_bones` | `BoneCargo_1_cdt`, `BoneCargo_2_cdt`, … | Slot 2 puede ser **puntero** (+0), no string inline |
| `cargo_types` | registro `veh+060` → … → `+0D0` | p. ej. `cargo_service_spare_parts_1` (UI: *piezas de repuesto especiales*) |
| `load_hint: cargado` | slots ≥1 o payload estimado | Sin `trailer_id` — normal en bastidor |
| `total_mass_kg` | XML vacío + slots×1200 kg si Havok inv mass=0 | `mass_estimated: true` frecuente parado |

**No detecta:** carga suelta en muelle del mapa; remolque no enganchado; piezas sin **pack** (`C`).

**Herramientas:** `memoria_havok.read_vehicle_load`, `scan_cargo.py --save vacio|cargado`, probe en `grabar_ce.py --probe`.

**Para suspensión (§2.5.1):** usar escenario **cargado** con `packed_slots ≥ 2` y mismo `pos_y`/rueda que vacío — ya reproducible.

### 2.6 Estado de implementación (jun-2026)

| Subsección | Cobertura | Estado jun-2026 |
|------------|-----------|-----------------|
| **2.1 Estáticas** | Diseño XML stock + remolques + parches | **~70 %** — `auditar_pak_catalogo.py` → 5 JSON (`trucks`, `engines`, `wheels`, `gearboxes`, `suspensions`); parches mod solo manual; `remolques_inventario.json` sin merge a `catalogo/trailers.json`; BinEditor no indexado |
| **2.2 Runtime CE** | Havok 0,5 s + protocolo `--auto` | **Pipeline OK** — `grabar_ce.py --live`, import/index; carga bastidor (§2.5.2); falta volumen en `telemetria/sesiones/` |
| **2.3 Derivadas** | Sim + MAE | **Parcial** — `simulacion_*.json` y `simulador.py` existen; `telemetria_comparacion.json` no persistido; MAE solo al vuelo con `--compare` |
| **2.4 Metadatos** | `session_context` obligatorio | **Infra hecha** — `datos/session_context.py` cableado en import/grabar; `gearbox`/`suspension`/`trailer` del taller no se leen del juego (vacíos en protocolo) |
| **2.5 Refs XML** | Auto en `setup` al importar | **Hecho** — `catalog_lookup.py` |
| **2.5.1 CE suspensión** | Estudio offsets | **Parcial** — snapshots Fleetstar vacio/cargado; sin CSV; falta `bounce` |
| **2.5.2 CE carga bastidor** | Sideboard + slots BoneCargo | **Hecho** — `memoria_havok.py`, `scan_cargo.py` |
| **2.8 CE gas/RPM** | Acelerador + régimen motor | **Parcial** — `throttle` veh+760, `engine_rpm` veh+114 (jul-2026, Bandit); diff/L u8 pendiente; T813 por revalidar |

**Lectura rápida:** entran bien las fuentes *estáticas* y el *formato* de sesión; Capa C crece con T813 y fleet (`telemetria/sesiones/`). Usar `.\grabar_telemetria.bat` en PowerShell.

**Siguiente paso:** (1) `scan_suspension.py --save bounce` + diff vacio/bounce; (2) partidas `play_free_v1` en **Black River** → `calibracion.json` vía `--index`.

### 2.7 Terreno — CE por rueda *(jun-2026, reemplaza blend mapa)*

**Fuente de verdad:** `terrain_kind`, `mud_grade`, grip, contact y deformación Havok (`memoria_havok.py`). Calibración con snapshots en `cheat_engine/wheel_snaps/` (`scan_wheel_substance.py --save` / `--diff`).

| Pieza | Archivo / origen |
|-------|------------------|
| Clasificación | `classify_terrain_from_wheels()` + `classify_mud_grade()` |
| Snapshots | `cheat_engine/wheel_snaps/tierra_seca.json`, … |
| Grabación | `grabar_ce.py` → CSV con `mud_grade_label` |
| Tramos / index | `terrain_kind` (CE) — ver `docs/PENDIENTES.md` TERR-1…4 |

**Obsoleto (eliminado):** blend `level_us_02_01.pak`, `datos/terrain_map.py`, `ver_mapa_michigan.py`. El mapa pintado no refleja contacto por rueda ni barro profundo.

### 2.8 Acelerador y RPM — CE drive_runtime *(jul-2026)*

**Objetivo:** saber si conduces a fondo, medio gas o patinando (correlación con hundimiento en barro).

| Campo | Offset | Calibración |
|-------|--------|-------------|
| `throttle` | `vehicle+0x760` f32 | `drive_snap` gas_off → 0, gas_full → 1.0 |
| `engine_rpm` | `vehicle+0x114` f32 | Sube ~80 rpm gas_off → gas_full (ralentí) |
| `fuel_rate_pct_min` | derivado `fuel_pct` | Sin offset; útil como proxy |

```powershell
.\grabar_telemetria.bat drive_snap gas_off
.\grabar_telemetria.bat drive_snap gas_full
.\grabar_telemetria.bat drive_diff gas_off gas_full
.\grabar_telemetria.bat drive --watch 30
```

Detalle: `cheat_engine/README.md`, `offsets_referencia.json` → `drive_runtime`. Snapshots: `cheat_engine/drive_snaps/`.

**Import sim con `mixed`:** `telemetria.py` usa superficie del protocolo si `terrain_kind` dominante es `mixed` (8×8); tramos `hard`/`mud` en `compare_session_by_terrain`.

**Pendiente:** `diff_lock_live` / `low_gear_live` (u8); revalidar gas en **Tatra T813**; análisis CE gas vs `mud_grade` / v30.

---

## 3. Arquitectura de la base

### 3.1 Capas

```text
┌─────────────────────────────────────────────────────────┐
│  CAPA D — Decisiones (parches, sim constants, docs)      │
│  patches.py, simulador.py, FASE-*.md                     │
├─────────────────────────────────────────────────────────┤
│  CAPA C — Evidencia (sesiones CE, comparaciones MAE)     │
│  telemetria/sesiones/, telemetria_comparacion.json       │
├─────────────────────────────────────────────────────────┤
│  CAPA B — Catálogo XML (stock + mod, searchable)         │
│  datos/catalogo/*.json                                   │
├─────────────────────────────────────────────────────────┤
│  CAPA A — Raw (pak, CSV crudos, logs)                    │
│  initial.pak.bak, telemetria_ce_log.csv, game.log        │
└─────────────────────────────────────────────────────────┘
```

Flujo: **A → B → C → D** (nunca parchear solo desde A sin pasar por C cuando sea comportamiento).

### 3.2 Layout de carpetas propuesto

```text
snowrunner real/
  datos/
    README.md                 # convenciones de la base
    catalogo/
      trucks.json             # índice camiones + rutas XML
      engines.json
      wheels.json
      gearboxes.json
      suspensions.json
      trailers.json           # merge auditar_remolques + futuras extracciones
      templates.json          # _templates/trucks.xml fricciones
    sesiones/                 # opcional: mirror organizado (symlink a telemetria/)
    indices/
      manifest.json           # builds, offsets, fechas probe OK
      calibracion.json        # MAE/v30 objetivo por protocolo × vehículo
    raw/
      ce_csv/                 # CSV Havok archivados por fecha
      game_logs/              # copias LegacyLog si hace falta
  telemetria/sesiones/        # (existente) JSON sesión importada
  docs/PLAN-BASE-DATOS-JUEGO.md  # este documento
```

**Base de datos “real”:** empezar con **JSON indexados** (sin SQLite) para no añadir dependencias; migrar a SQLite solo si superáis ~500 sesiones o queréis SQL.

---

## 4. Plan de implementación por oleadas

### Oleada 0 — Fundamentos (1–2 días)

| Tarea                                                             | Entregable                           | Prioridad |
|-------------------------------------------------------------------|--------------------------------------|-----------|
| Crear `datos/README.md` + estructura carpetas                     | Carpetas vacías + convención nombres | **Hecho** |
| `manifest.json`: build CE, offsets, masas vacías registry         | Un JSON versionado                   | **Hecho** |
| Documentar metadatos obligatorios en `grabar_ce.py` / sesión JSON | Campo `session_context` en meta      | **Hecho** |
| Archivar sesiones viejas sin `terrain_kind`                       | Ya en `_archivo/`                    | Hecho     |

### Oleada 1 — Catálogo XML (Capa B)

**Objetivo:** convertir el `.pak` en base consultable sin abrir 7-Zip cada vez.

| Script propuesto          | Función                                                    |
|---------------------------|------------------------------------------------------------|
| `auditar_pak_catalogo.py` | Recorre `initial.pak.bak`, extrae atributos clave por tipo |
| Salida                    | `datos/catalogo/trucks.json`, `engines.json`, …            |

**Atributos mínimos por tipo:**

| Tipo XML              | Atributos a indexar                                                                     |
|-----------------------|-----------------------------------------------------------------------------------------|
| Truck                 | Mass bodies, CoG, FuelCapacity, Responsiveness, SteerSpeed, DefaultEngine/Gearbox/Wheel |
| Engine                | Torque, MaxDeltaAngVel, EngineResponsiveness, FuelConsumption,                          |
| Wheel / WheelFriction | Radius, Mass, BodyFriction*, SubstanceFriction, template                                |
| Gearbox               | Gears AngVel, FuelModifier, awd_modifier, IsLower*Exists                                |
| Suspension            | Strength, Damping, Height, SuspensionMin                                                |
| Trailer               | Mass bodies, AttachType, wheel count                                                    |

**Criterio de éxito:** responder en &lt;10 s: “¿Qué motores comparte el Fleetstar?” “¿MaxDeltaAngVel stock MH9500?”

### Oleada 2 — Ingesta CE sistemática (Capa C)

**Objetivo:** cada sesión de juego enriquece la base automáticamente.

| Paso | Acción                                                                     |
|------|----------------------------------------------------------------------------|
| 1    | `grabar_telemetria.bat` (Ctrl+C, `--live`, `--auto`, `--compare`, `--index`) |
| 2    | JSON en `telemetria/sesiones/`                                             |
| 3    | `indexar_sesion.py` → append a `datos/indices/calibracion.json` | **Hecho** |
| 4    | Copiar CSV crudo a `datos/raw/ce_csv/YYYY-MM-DD_protocolo.csv` *(pendiente)* |

**Fila tipo en `calibracion.json`:**

```json
{
  "session_id": "ce_km_f2_barro_tm2_20260621_...",
  "vehicle_id": "marshall",
  "protocol_id": "km_f2_barro_tm2",
  "map": "Michigan",
  "setup": { "tire": "mudtires", "gearbox": "g_scout_offroad", "diff": true },
  "terrain_counts": { "mud": 180, "hard": 60 },
  "whole_mae_kmh": 12.4,
  "segments": [{ "kind": "mud", "mae": 11.2, "game_v30": 33, "sim_v30": 35 }],
  "mod_commit": "abc123",
  "build": "2026-06-25"
}
```

### Oleada 3 — Probes de referencia (baseline stock vs mod)

**Objetivo:** tabla before/after por parámetro XML.

**Modo laboratorio** (opcional): sesiones cortas, ruta repetible. Complementa, no sustituye, el **modo acumulación** (§4.1).

| Probe             | Duración          | Protocolo                           |
|-------------------|-------------------|-------------------------------------|
| Asfalto vacío WOT | 60 s              | `*_f1_asfalto`                      |
| Barro crawl       | 120 s             | `*_f2_*`                            |
| Cargado barro     | 120 s             | `*_f3_*`                            |
| Por vehículo mod  | 4 sesiones mínimo | ck1500, mh9500, fleetstar, marshall |

Guardar en base con tag `baseline_mod_v1`. Tras cada cambio XML: **misma ruta**, tag `patch_<nombre>_v1`, comparar delta MAE.

### 4.1 Modo acumulación (juego libre) *(recomendado para empezar)*

Cuando no se pueden reproducir rutas ni condiciones en poco tiempo: **jugar normal**, grabar todo, **clasificar después**.

| Aspecto | Modo laboratorio (Oleada 3) | Modo acumulación (§4.1) |
|---------|----------------------------|-------------------------|
| Duración | 60–120 s fijas | Hasta **Ctrl+C** (`--duration 0`, default) |
| Ruta | Misma GPS, anotada | Cualquiera; `location_note` aproximada |
| Terreno | Un tipo por sesión | Mixto (asfalto + barro + carga en una partida) |
| Protocolo meta | F1/F2/F3 explícito | `--auto` → terreno **dominante** al importar |
| MAE útil | Sesión entera | **Tramos** mud/hard (`compare_session_by_terrain`) |
| Baseline | `baseline_mod_v1` por probe | `play_free_v1` (pool de tramos indexados) |
| Cuándo | Validar un parche XML concreto | Llenar Capa C mientras jugáis |

**Flujo:**

```text
grabar_ce.py --import --auto --compare --map Michigan --location "partida libre" --baseline play_free_v1
  → CSV hasta Ctrl+C
  → import: terrain_counts + segmentos MAE por tramo
  → indexar_sesion.py: filas session + segment en calibracion.json
```

**Comandos:**

```powershell
# Grabar e importar al parar (recomendado)
python grabar_ce.py --import --auto --compare --map Michigan --location "partida libre" --baseline play_free_v1

# O grabar ahora, importar al cerrar el juego
python grabar_ce.py --auto --map Michigan --location "partida libre"
# Ctrl+C al terminar
python importar_ce_csv.py --auto --compare --map Michigan --location "partida libre" --baseline play_free_v1
```

**Reglas prácticas:**

1. **Un camión por grabación** — el import usa el `vehicle_id` más frecuente; si cambias de camión, Ctrl+C y nueva grabación.
2. **Empezar en mapa conduciendo** — evitar garaje/menú (>50 % `terrain_kind` vacío → descartar, §6).
3. **No hace falta misma ruta** — la clasificación usa `terrain_kind`, `load_hint`, duración de tramo y MAE por segmento.
4. **Oleada 3 sigue disponible** — cuando toque un parche (`patch_*`), repetir tramo corto en laboratorio si hace falta before/after limpio.

**Indexación (`indexar_sesion.py`):** una fila en `calibracion.json` por **segmento** homogéneo (mud/hard, vacío/cargado), más resumen por sesión. Usar `--index` al importar o `indexar_sesion.py --all`.

### Futuro — desaceleración en crawl *(nota; no implementado)*

En ~**90 %** del juego la velocidad **no supera 10 km/h** (barro, marcha L, remolque, subidas). Para el mod realista **no hace falta** protocolo de frenada a alta velocidad, parches de freno ni sim de pedal.

**Si más adelante interesa:** calcular **desaceleración** (`decel_ms2` ≈ \(-\Delta v / \Delta t\)) a partir de sesiones **F2 ya grabadas**, en tramos donde se suelta el acelerador (p. ej. ventana **10 → 3 km/h**). Sin sesión dedicada, sin `BrakeForce` XML (no existe en el `.pak`).

| Aspecto | Decisión |
|---------|----------|
| Prioridad | Baja — después de MAE barro F1/F2 |
| Fuente | `speed_kmh` + `t_s` del CSV CE actual |
| Indexación | Campo opcional en `calibracion.json` vía `indexar_sesion.py` |
| Sim Python | No prioritario; el sim ya desacelera por rodadura y resistencia de terreno |

### Giro vs carga — captura CE *(implementado en pipeline)*

`SteerSpeed` en XML (`datos/catalogo/trucks.json`) es **constante de diseño** del volante; **no** varía con la carga en runtime. Para estudiar “gira más lento cargado” se usa:

| Campo CSV / JSON | Origen | Uso |
|------------------|--------|-----|
| `ang_yaw` | Havok `+0x244` (rad/s) | Velocidad angular en plano |
| `yaw_rate_deg_s` | derivado | Grados/s — legible en análisis |
| `turn_radius_m` | \(v / \|\omega\|\) si giro claro | Radio en curva a 5–10 km/h |
| `total_mass_kg`, `payload_kg` | masa Havok | Vacío vs cargado en la misma maniobra |

**Maniobra recomendada (futuro análisis):** misma curva, marcha L, ~5–10 km/h, vacío y con carga/remolque; comparar `yaw_rate_deg_s` y `turn_radius_m` por fila.

Metadatos XML al importar: `steer_speed_xml`, `responsiveness_xml`, `engine_responsiveness_xml` (§2.5).

**Herramientas:** `grabar_ce.py` (`--live`, CSV), `importar_ce_csv.py` + `catalog_lookup.py`, `indexar_sesion.py`.

### Oleada 4 — Alimentar Fases 1–8

| Fase               | Qué lee de la base                   | Decisión que habilita               |
|--------------------|--------------------------------------|-------------------------------------|
| **1 Motor/chasis** | `engines.json` + CE v30 asfalto      | Torque, MaxDeltaAngVel              |
| **2 Neumáticos**   | `wheels.json` + CE grip/contact      | SubstanceFriction por tipo          |
| **3 Carga**        | `trailers.json` + CE payload         | Escenarios LOAD_SCENARIOS           |
| **4 Terreno**      | CE terrain_kind por mapa + BinEditor | Qué no parchear en camión           |
| **5 Telemetría**   | `calibracion.json`                   | Protocolos válidos / MAE umbral     |
| **6 Havok**        | `manifest.json` offsets              | Re-probe tras update Steam          |
| **7 Clima**        | Sesiones `f7_*` mismo tramo          | Lluvia/noche vs seco                |
| **8 Remolques**    | `trailers.json` + CE trailer_mass    | No parchear vs ajustar camión       |

### Oleada 5 — Cierre de sesión de estudio

Tras una tarde de juego (~2–4 h):

1. Importar todos los CSV del día: `python importar_ce_csv.py --auto --compare --index`  
2. `python indexar_sesion.py --all` (sesiones sin indexar)  
3. `python comparar_telemetria.py --export`  
4. Revisar `calibracion.json`: ¿algún MAE &lt; 15 barro? ¿regresión?  
5. Nota en `personal.txt` o issue: “Marshall barro OK; Fleetstar asfalto MAE 93 → revisar setup”  
6. **Solo entonces** tocar `patches.py` o `*_MUD_*`

---

## 5. Protocolo de captura “sesión larga” (varios GB de *información*, no de video)

No hace falta grabar vídeo. Sí acumular:

| Bloque         | Tiempo             | Contenido                                          |
|----------------|--------------------|----------------------------------------------------|
| A — Probe      | 2 min              | `grabar_ce.py --probe` × cada camión               |
| B — Catálogo   | 1 h (offline)      | `auditar_pak_catalogo.py` + `auditar_remolques.py` |
| C — Ruta mixta | 120 s × N camiones **o juego libre (§4.1)** | `grabar_ce.py --auto` hasta Ctrl+C |
| D — Barro puro | 120 s              | mismo tramo barro, marcha L                        |
| E — Carga      | 120 s              | semi / remolque scout                              |
| F — Clima (F7) | 2 × 120 s          | mismo tramo día vs noche o lluvia                  |

**Tamaño disk orientativo:**  

- CSV 120 s @ 0,5 s ≈ 240 filas × ~500 B ≈ **120 KB/sesión**  
- 100 sesiones ≈ **12 MB** (JSON + CSV)  
- Catálogo XML completo ≈ **50–200 MB** JSON  
- El `.pak` ya lo tenéis (**~29 MB**); no duplicar salvo backup

Los “varios gigas” del juego instalado **no** se copian enteros: se **indexan** las partes físicas relevantes.

**Monitor en vivo:** `grabar_ce.py --live` (cada 2 s por defecto) muestra velocidad, `terrain_kind`, grip, carga y masa en consola; cambios de terreno/carga al instante. `grabar_telemetria.bat` lo activa por defecto.

**Archivos por partida:** 1 CSV + 1 JSON; los **tramos** mud/hard se calculan al importar/indexar (no son ficheros separados). Ver §4.1.

---

## 6. Reglas de calidad de datos

1. **Un cambio XML por experimento** — si no, la base no sabe qué funcionó.  
2. **Misma ruta GPS** (anotar `location_note`) para comparar sesiones.  
3. **Descartar** sesiones con `terrain_kind` vacío en &gt;50 % muestras (menú/garaje).  
4. **MAE barro útil** si tramo mud ≥ 12 s y ≥ 8 muestras (ya en `telemetria.py`).  
5. Tras **update Steam**: re-ejecutar `--probe`, actualizar `manifest.json`, invalidar offsets viejos.  
6. XML compartido (`wheels_scout_yar_871`, `e_us_truck_old.xml`): tag `shared_asset` en catálogo.

---

## 7. Herramientas: existentes vs a construir

| Herramienta                         | Estado        | Oleada |
|-------------------------------------|---------------|--------|
| `auditar_remolques.py`              | Hecho         | 1      |
| `grabar_ce.py` / `.bat`             | Hecho         | 2      |
| `importar_ce_csv.py`                | Hecho         | 2      |
| `comparar_telemetria.py`            | Hecho         | 2      |
| `verify_pak.py`                     | Hecho         | 1      |
| `scan_wheel_substance.py`           | Hecho         | 3      |
| `scan_suspension.py`                  | Estudio (snapshots Fleetstar) | 6      |
| `scan_cargo.py`                     | Hecho (sideboard + slots) | 3      |
| **`auditar_pak_catalogo.py`**       | **Hecho**     | 1      |
| **`indexar_sesion.py`**             | **Hecho**     | 2      |
| **`consultar_base.py`** (CLI query) | **Hecho**     | 4      |
| **`datos/catalog_lookup.py`**       | **Hecho**     | 2      |
| **`datos/README.md`**               | **Hecho**     | 0      |

---

## 8. Consultas que la base debe responder (ejemplos)

- “¿MAE barro Marshall últimas 5 sesiones?”  
- “¿Qué `SubstanceFriction` tiene highway_1 stock vs mod?”  
- “¿Fleetstar asfalto: game v30 vs sim cuando MAE &gt; 50?”  
- “¿Motores que usan `MaxDeltaAngVel` &lt; 0.02?”  
- “¿Remolque scout vacío masa Havok vs XML 800 kg?”  
- “¿Offsets CE válidos para build X?”  

---

## 9. Métricas de éxito del plan

| Métrica                                      | Objetivo 3 meses                      |
|----------------------------------------------|---------------------------------------|
| Vehículos mod con baseline CE completo       | 4/4                                   |
| MAE barro por protocolo                      | &lt; 15 km/h o documentado por qué no |
| Catálogo XML indexado                        | trucks + engines + wheels principales |
| Sesiones indexadas en `calibracion.json`     | ≥ 40                                  |
| Regresiones detectadas antes de merge parche | 100 % (compare obligatorio)           |

---

## 10. Orden de trabajo recomendado (próximas 2 semanas)

| Semana | Foco                                                                                     |
|--------|------------------------------------------------------------------------------------|
| **S1** | Oleada 0 + 1: carpetas `datos/`, `auditar_pak_catalogo.py`, manifest               |
| **S2** | Oleada 2 + §4.1: juego libre + `indexar_sesion.py`; probes Oleada 3 opcionales |
| **S3** | Oleada 3: baseline + primer experimento XML nuevo (caja Marshall u otro parámetro motor) |
| **S4** | Oleada 4–5: Fase 7 sesiones clima; cerrar `calibracion.json` v1                    |

---

## 11. Enlaces internos

| Documento                              | Rol                                     |
|----------------------------------------|-----------------------------------------|
| [FASE-1.md](FASE-1.md)                 | Motor/chasis — consume catálogo engines |
| [FASE-2.md](FASE-2.md)                 | Neumáticos — consume wheels + CE grip   |
| [FASE-3.md](FASE-3.md)                 | Carga — trailers + LOAD_SCENARIOS       |
| [FASE-4.md](FASE-4.md)                 | Terreno mapa vs sim                     |
| [FASE-5.md](FASE-5.md)                 | Protocolos telemetría                   |
| [FASE-6.md](FASE-6.md)                 | Pipeline Havok                          |
| [FASE-7.md](FASE-7.md)                 | Clima — sesiones etiquetadas            |
| [FASE-8.md](FASE-8.md)                 | Remolques — inventario + CE             |
| `camiones/registry.py`                 | Masas vacías, IDs CE                    |
| `cheat_engine/offsets_referencia.json` | Build → offsets                         |

---

## 12. Decisión explícita: qué NO entra en la base

- Texturas, modelos 3D, audio (no aportan física).  
- Copia completa de mapas `.pak` por zona (solo notas BinEditor + CE en tramos).  
- Opiniones sin número (“iba bien”) — solo filas con `speed_kmh` o MAE.  
- Parches globales no revertibles sin fila `baseline` previa.

---

*Documento vivo. Actualizar al completar cada oleada y al cambiar build Steam.*
