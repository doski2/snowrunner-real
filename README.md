# SnowRunner — mod realista (multi-camión)

Proyecto organizado por **carpeta de camión** + **módulos compartidos**.

## Estructura

```
snowrunner real/
├── README.md
├── apply_mod.py              ← mod .pak (todos o --vehicle)
├── grabar_ce.py              ← telemetría Havok sin CE
├── grabar_telemetria.bat     ← 120 s, auto camión+terreno+carga
├── importar_ce_csv.py / comparar_telemetria.py / telemetria.py
│
├── sim/core.py               ← física compartida
├── camiones/
│   ├── registry.py           ← VEHICLES, masas vacías CE
│   ├── ck1500/ mh9500/ fleetstar/ marshall/
│   │   ├── patches.py, simulador.py, FASES.md (mh/fs/km)
│
├── telemetria/sesiones/      ← JSON importados (CE/HUD)
│   └── _archivo/             ← sesiones obsoletas
├── docs/FASE-1.md … FASE-8.md
└── cheat_engine/             ← memoria_havok, offsets, calibración
```

## Comandos habituales

```powershell
# Mod
python apply_mod.py --refresh-backup
python verify_pak.py
python apply_mod.py --vehicle fleetstar

# Sim
python -m camiones.fleetstar.simulador
python -m camiones.marshall.simulador
python -m camiones.mh9500.simulador

# Tests
python -m unittest test_telemetria test_ce_import -v
python -m unittest discover -s camiones -p "test*.py" -v

# Telemetría (recomendado)
python grabar_ce.py --probe
grabar_telemetria.bat
python importar_ce_csv.py --auto --compare
python comparar_telemetria.py telemetria/sesiones/ce_*.json
```

## Telemetría Havok (Fase 6)

| Qué hace `--auto` | Detalle |
|-------------------|---------|
| Camión | `s_fleetstar_f2070a`, `s_gmc_9500`, `s_chevrolet_ck1500`, `s_khan_39_marshall` → registry |
| Terreno | `terrain_kind` + `contact_avg` → barro vs asfalto |
| Carga | `payload_kg` / `load_hint` → `fs_f3_carga`, `mh_f3_semi`, etc. |
| Comparación | Tramos mud/hard ≥12 s vs sim (`compare_session_by_terrain`) |

Documentación: **`docs/FASE-6.md`**, **`cheat_engine/README.md`**.

Sesión Fleetstar asfalto válida (post-fix terreno): `telemetria/sesiones/ce_fs_f1_asfalto_20260625_211942.json`.

## Añadir un camión nuevo

1. `camiones/<id>/patches.py` + registro en `registry.py` (`EMPTY_MASS_KG` para CE).
2. `camiones/<id>/simulador.py` si hace falta sim propio.
3. Protocolos `xx_*` en `telemetria.py` (`DEFAULT_MUD_PROTOCOL`, `DEFAULT_LOADED_MUD_PROTOCOL`).
4. `FASES.md` en la carpeta del camión.
