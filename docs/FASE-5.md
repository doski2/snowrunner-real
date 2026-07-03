# SnowRunner — Fase 5: Telemetría (validar Fases 1–4 en juego)

**Objetivo** (`personal.txt`): obtener datos del juego sobre cómo se comporta el CK1500; sin telemetría es difícil saber si lo fácil o difícil es real.

---

## Estado

| Tarea | Estado |
|-------|--------|
| Revisar `BinEditor\Guides` y docs Saber | Hecho |
| Investigar telemetría nativa / SimHub / consola | Hecho |
| Protocolo de pruebas (Fases 1–4) | Hecho |
| Grabador manual HUD + comparador vs sim | Hecho |
| **Cheat Engine Havok (Fase 6)** | **Operativo** — `grabar_ce.py` + `grabar_telemetria.bat` |
| Sesiones CK1500 (HUD o CE) | Archivadas — **re-grabar** con `--auto` |
| Sesiones MH9500 | Archivadas — pendiente re-grabar |
| Sesiones Fleetstar | **1 válida** asfalto (`ce_fs_f1_asfalto_*`); barro pendiente |
| Terreno + carga en CSV | **Hecho** — `terrain_kind`, `contact_avg`, `payload_kg` |
| Auto protocolo (terreno + carga) | **Hecho** — `importar_ce_csv.py --auto` |
| Comparación por tramos | **Hecho** — `compare_session_by_terrain` |

> **Fase 6** sustituye o complementa el HUD: `importar_ce_csv.py`, offsets en `FASE-6.md`. Criterio común: **MAE &lt; ~15 km/h** por escenario = sim útil.

---

## Hallazgo principal: no hay telemetría oficial

| Método | ¿Velocidad / física? | ¿Viable para el mod? |
|--------|----------------------|----------------------|
| API UDP / SimHub | **No existe** | — |
| `game.log` / `LegacyLog.txt` | Solo errores XML/mod | Útil post-prueba |
| Consola de desarrollo en juego | **No** (trainers ≠ consola real) | — |
| Menú **TOOLS** (Proving Grounds / mapas mod) | Tiempo, cámara, garage | No muestra km/h |
| **HUD del juego** | Velocidad km/h | **Sí** — método manual Fase 5 |
| **Cheat Engine (Fase 6)** | Havok: speed, vel_xyz, fuel, ID | **Sí** — automático cada 500 ms |
| Editor `SnowRunnerEditor.exe` | Logs del editor | No sirve en partida normal |

Fuentes: [SimHub — sin telemetría SnowRunner](https://www.simhubdash.com/community-2/simhub/snowrunner/), [Saber — error log](https://expeditions-guides.saber.games/truck_modding/getting_started/sample_mod_by_the_game/viewing_error_log/), [TOOLS menu](https://expeditions-guides.saber.games/map_modding/creating_a_map/other_map_settings/tools_menu/), proyecto comunitario [FindMuck/SnowRunner_Noclip](https://github.com/FindMuck/SnowRunner_Noclip) (memoria Havok).

---

## Guías en `BinEditor\Guides`

Ruta: `C:\Program Files (x86)\Steam\steamapps\common\SnowRunner\Sources\BinEditor\Guides`

| Archivo | Contenido |
|---------|-----------|
| `SnowRunner_Editor_Guide.pdf` | Editor de mapas; panel Output = logs |
| `Integration_of_Trucks_and_Addons.pdf` | Integración camiones; **revisa game.log al probar** |
| `Console_Requirements_for_Mods.pdf` | Requisitos consola (Xbox/PS) para mods |
| `Quick_Guide_-_Adding_Trucks.pdf` | Añadir camiones |
| `Creating_Custom_Cargo.pdf` | Carga custom |
| `Addons_List.xlsx` | Listado addons |

Ninguna guía expone telemetría de vehículo en tiempo real. Sirven para **modding y logs de error**, no para RPM/velocidad.

---

## Solución del proyecto: telemetría + comparador

### Método A — HUD manual (Fase 5)

```
1. python apply_mod.py
2. Entrar en SnowRunner — misma ruta cada vez
3. python grabar_telemetria.py
4. Leer velocidad del HUD cada 5 s
5. python comparar_telemetria.py
6. Ajustar mod (Fase 1–2) si MAE o tendencias no cuadran
```

### Método B — Havok automático (Fase 6, recomendado)

```
1. SnowRunner en mapa conduciendo
2. grabar_telemetria.bat   (o grabar_ce.py --duration 120 --import --auto --compare)
3. Revisar comparación por tramos mud/hard en consola
4. JSON en telemetria/sesiones/
```

Alternativa CE clásica: `TelemetryLogger.lua` → mismo CSV → `importar_ce_csv.py --auto --compare`.

Ambos métodos producen JSON en `telemetria/sesiones/` comparables con `comparar_telemetria.py`.

### Qué va en el sim vs qué mide CE

| Dato | Sim / XML | CE runtime |
|------|-----------|------------|
| Masa, motor, ruedas | Sí | Masa Havok + payload vs vacío XML |
| Velocidad, combustible | Predicción | Sí |
| Terreno barro/firme | `SurfaceConfig` | `terrain_kind`, `contact_avg` por rueda |
| Carga / remolque | `LOAD_SCENARIOS` | `payload_kg`, `load_hint`, `trailer_id` |

### Protocolos incluidos (`TEST_PROTOCOLS`)

| ID | Fase | Qué valida |
|----|------|------------|
| `f1_asfalto_i6` | 1 | Aceleración motor I6 en asfalto |
| `f2_barro_highway` | 2 | Highway en barro (¿0 km/h?) |
| `f2_barro_offroad` | 2 | Offroad + diff en **mismo** tramo |
| `f3_carga_barro` | 3 | Remolque + vigas en barro |
| `f4_nieve_highway` | 4 | Nieve con highway stock |
| `f4_hielo_cadenas` | 4 | Hielo con cadenas |

### Comandos

```powershell
python grabar_telemetria.py --list
grabar_telemetria.bat
python importar_ce_csv.py --auto --compare
python comparar_telemetria.py telemetria/sesiones/ce_*.json --export
python -m unittest test_telemetria test_ce_import -v
```

Salidas:
- `telemetria/sesiones/*.json` — sesiones grabadas
- `telemetria/sesiones/_archivo/` — sesiones obsoletas (formato antiguo)
- `telemetria_comparacion.json` — informe exportado (`--export`)

### Cómo leer la comparación

| Situación | Interpretación |
|-----------|----------------|
| MAE &lt; 15 km/h en barro/nieve | Sim calibrado; mod coherente |
| Juego 0, sim &gt; 0 en barro highway | Juego más duro; Fase 2 (+0.1 substance) puede ayudar |
| Juego &gt; 0, sim = 0 en barro highway | Parche Fase 2 funcionando |
| Juego ≫ sim en asfalto | Normal: sim no modela vmax de crucero |
| Muchos errores en `game.log` | Revisar `verify_pak.py` / XML roto |

---

## game.log

Ubicación: `Documents\My Games\SnowRunner\base\logs\`

- `LegacyLog.txt` — errores al cargar mods, packing
- **No** registra velocidad, slip ni hundimiento

Tras cada sesión de prueba, ejecuta `comparar_telemetria.py` para ver errores recientes del mod.

---

## Opciones avanzadas (opcional)

### Cheat Engine + memoria Havok

**Operativo** — ver **`FASE-6.md`**. Singleton `TRUCK_CONTROL` `+2A8EDD8` (build 2026-06-25).

```powershell
grabar_telemetria.bat
python importar_ce_csv.py --auto --compare
```

### Mapa de prueba con menú TOOLS

En mapas mod locales o Proving Grounds: menú superior derecho (cambiar hora, cámara libre). Activa `isEnableDevMenu` en `zone_settings.json` del mapa. Facilita repetir pruebas; **no** sustituye leer velocidad.

### Grabación de vídeo

Pantalla + cronómetro externo si prefieres revisar después; más lento que `grabar_telemetria.py`.

---

## Archivos Fase 5

| Archivo | Rol |
|---------|-----|
| `telemetria.py` | Protocolos, grabación, comparación, logs |
| `grabar_telemetria.py` | CLI interactiva en juego |
| `comparar_telemetria.py` | Juego vs sim + export JSON |
| `test_telemetria.py` | Tests unittest |
| `telemetria/sesiones/` | JSON de sesiones (HUD y CE) |
| `grabar_ce.py` / `grabar_telemetria.bat` | Logger Havok sin CE |
| `importar_ce_csv.py` | CSV → sesión; `--auto` camión+terreno+carga |
| `FASE-5.md` | Este documento |
| `FASE-6.md` | Offsets, flujo CE, calibración |

---

## Checklist primera sesión

1. [ ] Mod aplicado (`python apply_mod.py`, `verify_pak.py`)
2. [ ] CK1500 con motor I6, neumático según protocolo
3. [ ] Marcar punto de inicio en el mapa (misma ruta siempre)
4. [ ] `grabar_telemetria.py` — protocolo `f2_barro_highway` luego `f2_barro_offroad`
5. [ ] `comparar_telemetria.py` — anotar MAE y v30 juego vs sim
6. [ ] Si barro highway sigue a 0: confirmar si Fase 2 (+0.1) mejora en **segunda** sesión

Con 2–3 sesiones por fase tendrás evidencia real para decidir si el mod está bien o hace falta ajuste fino.

### MH9500 — protocolos

| ID | Fase | Qué grabar |
|----|------|------------|
| `mh_f1_asfalto` | 1 | Aceleración RWD vacío en asfalto |
| `mh_f2_barro_highway` | 2 | Barro sin AWD — confirmar atasco |
| `mh_f2_barro_offroad` | 2 | Offroad + diff (AWD instalado) |
| `mh_f3_semi` | 3 | Semi cargado en barro |

```powershell
python grabar_telemetria.py --protocol mh_f1_asfalto --map Michigan
python comparar_telemetria.py telemetria/sesiones/<sesion>.json
```

Detalle MH9500: **`camiones/mh9500/FASES.md`** § Fase 5. Fleetstar: **`camiones/fleetstar/FASES.md`**.

### Fase 7 — día vs noche (misma ruta)

| ID | Uso |
|----|-----|
| `f7_barro_dia` / `f7_barro_noche` | CK1500 — validar que hora no cambia física |
| `mh_f7_barro_dia` / `mh_f7_barro_noche` | MH9500 — igual |

Ver **`FASE-7.md`** — la lluvia visual no debería cambiar v30; si empeora al repetir, son surcos.

---

## Validación con telemetría (Fases 5–6)

| | |
|--|--|
| **Protocolos** | Todos en `TEST_PROTOCOLS` (`f1_*` … `f4_*`, `f7_*`, `mh_*`) |
| **Parámetros diseño** | Ninguno en telemetría — vienen de Fases 1–4 (XML/sim) |
| **CE / HUD mide** | `speed_kmh`, `fuel_pct`, `terrain_kind`, `contact_avg`, `payload_kg` |
| **Estado CE** | Fleetstar asfalto OK; resto re-grabar con pipeline actual |
| **Criterio** | **MAE &lt; ~15 km/h** por tramo = sim útil |

```powershell
grabar_telemetria.bat
python importar_ce_csv.py --auto --compare
```

Ver **`FASE-6.md`** (offsets, sesión referencia, pendientes).

---
