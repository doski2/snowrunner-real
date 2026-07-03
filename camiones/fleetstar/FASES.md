# SnowRunner — Fleetstar F2070A (mod realista)

Metodología general: `docs/FASE-1.md` … `docs/FASE-8.md` · MH9500: `camiones/mh9500/FASES.md`.

---

## Tu setup actual (junio 2026)

| Pieza | En juego |
|-------|----------|
| Motor | **Si-6V/1900** |
| Neumáticos | **42" UHD I** (highway) |
| Tracción | **AWD** + **bloqueo diferencial** |
| Suspensión | Stock |

---

## Qué hace el mod

| Parámetro | Stock | Mod |
|-----------|-------|-----|
| Masa total | 6300 kg | **6650 kg** |
| Combustible | 240 L | **210 L** |
| Si-6V/1900 torque | 135000 | **92000** |
| Si-6V/2100T torque | 145000 | **99000** |
| Si-6V/2100T consumo | 6.0 | **3.9** |
| `highway_1` Substance | 0.4 | **0.5** |

Los motores comparten `e_us_truck_old.xml` (`EngineResponsiveness` 0,024). El **2100T** usa el mismo ratio de nerfeo que el 1900 (92÷135 ≈ **68 %** del torque stock → 99k). Pendiente validar con CE `fs_f1_asfalto` cuando lo instales.

El parche afecta otros camiones con socket `e_us_truck_old` (p. ej. White Western 4964). Solo Fleetstar (chasis, ruedas, suspensión): `python apply_mod.py --vehicle fleetstar`.

---

## Motores Si-6V (taller)

| Nombre in-game | XML | Torque mod | Cuándo |
|----------------|-----|------------|--------|
| Si-6V/1900 | `us_truck_old_engine_0` | 92000 | Setup actual / telemetría histórica |
| Si-6V/2100T | `us_truck_old_engine_1` | 99000 | Upgrade ~+7 % vs 1900 mod (ratio stock 145k/135k) |

**Probar más adelante** (mismo tramo, UHD + AWD + diff):

```powershell
python apply_mod.py --vehicle fleetstar
python verify_pak.py
# Instalar 2100T en taller, luego:
python grabar_ce.py --probe
grabar_telemetria.bat
python importar_ce_csv.py --auto --compare --index
```

La comparación sim usa `engine_name_xml` del import si es `us_truck_old_engine_1`, o `engine_id` `fs_real_2100`. Sim: `python -m camiones.fleetstar.simulador` (muestra 1900 y 2100T en asfalto).

---

## Aplicar

```powershell
python apply_mod.py --vehicle fleetstar
python verify_pak.py
python -m camiones.fleetstar.simulador
python -m unittest camiones.fleetstar.test -v
```

Copiar `initial.pak` → `...\SnowRunner\preload\paks\client\`

---

## Fases — orden y telemetría

| Fase | Qué hacer | Protocolo / grabación |
|------|-----------|------------------------|
| **1** | Asfalto vacío, AWD, acelerar | `fs_f1_asfalto` |
| **2** | Barro UHD + AWD + diff, marcha baja | `fs_f2_barro_uhd` |
| **2b** | (Futuro) Offroad mismo tramo | `fs_f2_barro_offroad` |
| **3** | Bastidor cargado en barro | `fs_f3_carga` |
| **5–6** | CE / comparación sim | `grabar_telemetria.bat` |

```powershell
python grabar_ce.py --probe
grabar_telemetria.bat
python importar_ce_csv.py --auto --compare
```

`--auto` detecta Fleetstar, terreno y carga; no hace falta `--protocol fs_f3_carga` manual si `payload_kg` &gt; 300.

---

## Sim de referencia

```powershell
python -m camiones.fleetstar.simulador
```

| Situación | Esperado (sim) |
|-----------|----------------|
| Asfalto AWD | ~0–97 en ~38 s |
| Barro UHD + AWD + diff | crawl ~2–3 km/h |
| Cargado 6 t barro | más lento que vacío |

---

## CE / memoria

| Campo | Valor |
|-------|--------|
| ID juego (CE) | `s_fleetstar_f2070a` |
| Masa vacía mod | **6650 kg** (`registry.EMPTY_MASS_KG`) |
| Offsets | Igual que CK1500/MH — `cheat_engine/README.md` |
| Terreno asfalto | Usar `contact_avg` ~0.80 (`+0x2EC`); ver `wheel_snaps/asfalto_fs.json` |

### Sesiones CE (jun 2026)

| Sesión | Estado |
|--------|--------|
| `ce_fs_f1_asfalto_20260625_211942.json` | **Válida** — asfalto, `contact=0.804`, `kind=hard` |
| `ce_fs_f2_barro_uhd_*` (varias) | Archivadas en `telemetria/sesiones/_archivo/` — re-grabar barro real |

---

## Archivos

| Archivo | Función |
|---------|---------|
| `camiones/fleetstar/patches.py` | Parches XML |
| `camiones/fleetstar/apply_mod.py` | Solo Fleetstar |
| `camiones/fleetstar/simulador.py` | Sim 6 ruedas |
| `camiones/fleetstar/test.py` | Tests |
| `grabar_telemetria.bat` | Grabación 120 s (todos los camiones) |

---

## Pendiente

- [ ] Re-grabar `fs_f2_barro_uhd` en barro Michigan (tramo fijo)
- [ ] Calibrar `FS_MUD_*` con telemetría real
- [ ] Validar `fs_f3_carga` con bastidor lleno (`scan_cargo.py`)
- [ ] Validar **Si-6V/2100T** (`us_truck_old_engine_1`) con `fs_f1_asfalto` tras instalar en taller
