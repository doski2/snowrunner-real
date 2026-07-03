# Pendientes — pruebas y comentarios (por vehículo)

Documento único para **no saltar de tema en tema**. Organizado **por camión**: abre solo la sección del vehículo en el que trabajas.

**Reglas**

1. **Un vehículo activo** a la vez. El resto en espera.
2. Dentro del vehículo, sigue el orden **F1 → F2 → F3 → extras**.
3. Al terminar: marca `[x]`, anota en **Comentarios** de ese vehículo y enlaza el JSON en **Sesiones CE**.
4. Detalle por fase: `docs/FASE-1.md` … `docs/FASE-8.md`. Detalle técnico: `camiones/<id>/FASES.md`.
5. **Carpetas:** `telemetria/sesiones/<vehicle_id>/` (nuevas sesiones van solas ahí). Reorganizar legacy: `python organizar_sesiones.py --apply`.

**Comandos habituales**

```powershell
python grabar_ce.py --probe
grabar_telemetria.bat                  # grabación + preflight
grabar_telemetria.bat snap barro_ligero  # snapshot TERR (sin sesión)
grabar_telemetria.bat diff tierra_seca barro_ligero
grabar_telemetria.bat tire             # neumático montado (CE)
grabar_telemetria.bat cargo            # carga bastidor / remolque (CE)
grabar_telemetria.bat drive            # traccion / diff / fuel rate (CE)
python importar_ce_csv.py --auto --compare --index
python verify_pak.py
python organizar_sesiones.py --apply   # solo si quedan JSON sueltos en sesiones/
```

**Carpetas de sesiones**

```
telemetria/sesiones/
  ck1500/
  fleetstar/
  kodiak/
  marshall/     ← ce_km_*.json
  mh9500/
  scout800/     ← ce_s8_*.json
  _archivo/     ← sesiones inválidas / histórico
```

---

## Índice rápido

| Vehículo | ID | Siguiente paso | Doc |
|----------|-----|----------------|-----|
| Chevrolet CK1500 | `ck1500` | F1 asfalto I6 | `camiones/ck1500/` |
| International Fleetstar F2070A | `fleetstar` | MOT-2100 (F1) o **F3 carga** (F2 hecho) | `camiones/fleetstar/FASES.md` |
| Chevrolet Kodiak C70 | `kodiak` | F1 asfalto | `camiones/kodiak/FASES.md` |
| KHAN 39 Marshall | `marshall` | F1 asfalto (F2 barro **hecho**) | `camiones/marshall/FASES.md` |
| GMC MH9500 | `mh9500` | Re-grabar `mh_f2_barro_offroad` | `camiones/mh9500/FASES.md` |
| International Scout 800 | `scout800` | F1 AAT-6V *(en espera)* | `camiones/scout800/FASES.md` |

**Vehículo activo recomendado:** `ck1500` (CK-F1 AAT-8V) → luego `scout800` o `fleetstar`.

**Motor compartido:** Fleetstar y Kodiak usan `e_us_truck_old.xml` (`us_truck_old_engine_0` / `_1`). Calibrar motor en un camión y **repetir F1** en el otro.

---

## Chevrolet CK1500 (`ck1500`)

Referencia Scout · CE: `s_chevrolet_ck1500` · Masa mod ~1750 kg

| ID | Fase | Estado | Protocolo | Qué probar | Cierre |
|----|------|--------|-----------|------------|--------|
| CK-F1 | 1 | [ ] | `f1_asfalto_aat8v` | **AAT-8V 5.2** solo motor; highway stock; sin diff/caja | `grabar_telemetria.bat motor`; MAE asfalto |
| CK-F1i6 | 1 | — | `f1_asfalto_i6` | Alias sim (mismo XML `us_scout_old_engine_ck1500` con mod) | Usar `f1_asfalto_aat8v` en CE |
| CK-F2h | 2 | [ ] | F2 highway | Highway en barro ~0 km/h | Comentario sensación |
| CK-F2o | 2 | [x] | `f2_barro_offroad` | Offroad + diff + L, barro Michigan | MAE mud **3.5** (sesión 2026-06-30) |
| CK-F3 | 3 | [ ] | `f3_carga_barro` | Remolque scout + vigas en barro | `load=cargado` estable; `scan_cargo` |

**Sesiones CE**

| Archivo | Protocolo | MAE / notas |
|---------|-----------|-------------|
| `telemetria/sesiones/ck1500/ce_f2_barro_offroad_20260630_220307.json` | `f2_barro_offroad` | **MAE mud 3.5** (1260 muestras); crawl ~0–9 km/h (mediana 0.14); indexada |
| `telemetria/sesiones/ck1500/ce_f2_barro_offroad_20260702_215951.json` | `f2_barro_offroad` | Mezcla hard/mud; CE neumático **allterrain** (`wheels_scout2`, AT I) — **no offroad**; re-grabar con OS I si cierras F2o de libro |
| `telemetria/sesiones/ck1500/ce_f3_carga_barro_20260703_223237.json` | `f3_carga_barro` *(inválida)* | Scout **sin carga** en juego; meta `trailer_metal_planks` erróneo; 232× falsos `cargado` — **no indexar F3** |

**Comentarios**

```
2026-06-30 | CK-F2o | f2_barro_offroad
Archivo: telemetria/sesiones/ck1500/ce_f2_barro_offroad_20260630_220307.json
Setup: I6 mod, offroad, diff, L, Black River, vacío, 1750 kg
Resultado: MAE mud=3.5 | v30 juego 7.96 | v30 sim 39.9 | vmax barro ~9 km/h
Sensación: patina en barro profundo — grip ~0.02, contact ~0.36 → **mud_grade=3 (mud_deep)**
Sim vs juego: MAE bajo porque ambos pasan mucho tiempo en crawl; sim v30 alto = no replica el patinaje extremo del juego
Siguiente: CK-F1 asfalto dedicado; opcional CK-F2h highway en barro

2026-07-03 | CK-F3 | f3_carga_barro | ce_f3_carga_barro_20260703_223237 — **INVÁLIDA**
Setup: I6, offroad, L+diff, Black River — **scout sin carga** (confirmado en juego)
CE: load=vacio 835× (mass 1750 correcto) | cargado 232× = falsos positivos (2950/3162 fantasma)
Import: meta trailer_metal_planks por max_payload; indexación F3 retirada de calibracion.json
Siguiente: re-grabar F3 con remolque + 2 slots vigas; `grabar_telemetria.bat cargo` quieto 30 s antes
```

---

## International Scout 800 (`scout800`)

CE: `s_international_scout_800` · Masa mod objetivo **2350 kg** · Diff **Always**

| ID | Fase | Estado | Protocolo | Qué probar | Cierre |
|----|------|--------|-----------|------------|--------|
| S8-F1 | 1 | [ ] | `s8_f1_asfalto_aat6v` | AAT-6V 4.0 + 33\" HS I; asfalto WOT | `grabar_telemetria.bat motor_scout` |
| S8-F2 | 2 | [ ] | `s8_f2_barro_hs` | Mismo tramo barro; diff+L | MAE mud; `S8_MUD_*` |
| S8-F3 | 3 | [ ] | `s8_f3_carga_barro` | Remolque scout + vigas | `cargo` quieto 30 s |

**Setup actual (tu camioneta):** motor AAT-6V 4.0 · neumático 33\" HS I · sin más mejoras aún.

**Notas:** motor `us_scout_old_engine_0` compartido — no parchear `e_us_scout_old.xml` hasta cerrar S8-F1. Doc: `camiones/scout800/FASES.md`.

**Sesiones CE:** *(ninguna válida aún)* → `telemetria/sesiones/scout800/`

---

## International Fleetstar F2070A (`fleetstar`)

CE: `s_fleetstar_f2070a` · Masa mod **6650 kg** · 6×4 · 42" UHD · Si-6V

| ID | Fase | Estado | Protocolo | Qué probar | Cierre |
|----|------|--------|-----------|------------|--------|
| FS-MOT-1900 | motor | [x] | `fs_f1_asfalto` | Si-6V/1900, AWD+diff, asfalto WOT | Sesión válida |
| FS-MOT-2100 | motor | [ ] | `fs_f1_asfalto` | **2100T** en taller, mismo tramo | Δ 0→60 vs 1900; comentario |
| FS-F1 | 1 | [x] | `fs_f1_asfalto` | *(incluido en MOT-1900)* | `ce_fs_f1_asfalto_20260625_*` |
| FS-F2 | 2 | [x] | `fs_f2_barro_uhd` | Barro Michigan, L+diff, 42" UHD | MAE mud **4.6** / **2.0** (2026-07-02) |
| FS-F3 | 3 | [ ] | `fs_f3_carga` | Bastidor lleno estable | `load=cargado` estable; `scan_cargo` |
| FS-F2b | 2 | [ ] | `fs_f2_barro_offroad` | Mismo tramo, neumático offroad | Decisión XML |
| FS-SIM | sim | [ ] | — | `python -m camiones.fleetstar.simulador` vs FS-F1 | Tabla 0→60 / v30 |

**Sesiones CE**

| Archivo | Protocolo | MAE / notas |
|---------|-----------|-------------|
| `telemetria/sesiones/fleetstar/ce_fs_f2_barro_uhd_20260702_223218.json` | `fs_f2_barro_uhd` | **MAE mud 4.6** (133–443 s) y **2.0** (488–584 s); 401× mud; mezcla hard — indexada |
| `telemetria/sesiones/fleetstar/ce_fs_f3_carga_20260630_223710.json` | `fs_f3_carga` | **MAE mud 6.3** (349–866 s); carga CE casi siempre `vacio` (7/1495) — barro OK, **re-grabar F3** |
| `telemetria/sesiones/fleetstar/ce_fs_f3_carga_20260703_220658.json` | `fs_f3_carga` *(inválida)* | Camión **vacío** en juego; meta `frame_cargado` erróneo; 489× falsos `cargado` (fantasmas Havok) — **no indexar F3** |
| `telemetria/sesiones/fleetstar/ce_fs_f1_asfalto_20260630_225129.json` | `fs_f1_asfalto` | Mezcla 50/50 mud/hard; MAE whole 16.7; tramos hard 25–42 — **borrador**, no cerrar F1 |
| `ce_fs_f1_asfalto_20260625_*` | `fs_f1_asfalto` | MOT-1900 (histórico) |

**Comentarios**

```
2026-07-02 | FS-F2 | fs_f2_barro_uhd | ce_fs_f2_barro_uhd_20260702_223218
Setup: fs_real, highway (UHD sim), L+diff, Black River partida libre, vacío, 6650 kg
Resultado: MAE mud=4.6 (288 muestras, t 133–443 s) | MAE mud=2.0 (94 muestras, t 488–584 s)
Telemetría mud: mud_deep 360× (grip ~0.05, contact ~0.44) | mud_light 30× (grip ~0.10, contact ~0.65) | water_ford 13×
Sensación: ruta mixta (144× hard) — usar solo tramos mud para F2; hard compara como fs_f1 (MAE alto, ignorar)
Siguiente: MOT-2100 o re-grabar F3 con carga estable

2026-06-30 | FS-F3 | fs_f3_carga | ce_fs_f3_carga_20260630_223710
Setup: fs_real, highway, L+diff, Black River, meta frame_cargado
MAE mud=6.3 | contact suavizado Havok (1.0→0.34 al entrar barro)
Carga: load=vacio 1488 muestras, cargado 7 — masa 6650–10250 kg inestable
Siguiente: re-grabar F3 quieto 30 s con bastidor lleno

2026-07-03 | FS-F3 | fs_f3_carga | ce_fs_f3_carga_20260703_220658 — **INVÁLIDA**
Setup: fs_real, highway, L+diff, Black River — **camión vacío** (confirmado en juego)
CE: load=vacio 1735× (mass 6650 correcto) | cargado 489× = falsos positivos (cargo_kg 1200–2400 fantasma)
Import: meta frame_cargado por max_payload>300; indexación F3 retirada de calibracion.json
Siguiente: re-grabar F3 con bastidor lleno; `grabar_telemetria.bat cargo` quieto 30 s antes de F3

2026-06-30 | FS-F1 borrador | fs_f1_asfalto | ce_fs_f1_asfalto_20260630_225129
Arranque mud_deep; mitad sesión barro — no usar para MOT-2100 ni cerrar F1
Siguiente: F1 asfalto WOT tramo fijo, vacío, sin barro en ruta
```

---

## Chevrolet Kodiak C70 (`kodiak`)

CE: `s_chevrolet_kodiakc70` · Masa mod **7900 kg** · 4×4 · **39"** UHD · Mismo motor Si-6V que Fleetstar

| ID | Fase | Estado | Protocolo | Qué probar | Cierre |
|----|------|--------|-----------|------------|--------|
| KD-F1 | 1 | [ ] | `kd_f1_asfalto` | 39" UHD, AWD+diff, asfalto | Comparar con Fleetstar FS-F1 |
| KD-F2 | 2 | [ ] | `kd_f2_barro_uhd` | Barro, L; calibrar `KD_MUD_*` | MAE barro |
| KD-F3 | 3 | [ ] | `kd_f3_carga` | Bastidor en barro | payload estable |
| KD-SUSP | extra | [ ] | — | Suspensión **alta** taller — ¿parcheada? | Decisión sí/no |
| KD-MOT | motor | [ ] | `kd_f1_asfalto` | Tras cerrar FS-MOT-2100, repetir F1 aquí | Misma motorización, +masa |

**Sesiones CE**

| Archivo | Protocolo | MAE / notas |
|---------|-----------|-------------|
| *(ninguna indexada aún)* | | Parche Steam OK (`verify_pak.py`) |

**Comentarios**

```
(fecha) KD-F1 — 
```

---

## KHAN 39 Marshall (`marshall`)

CE: `s_khan_39_marshall` · Masa mod **1780 kg** · Kr 104 · 45" TM II

| ID | Fase | Estado | Protocolo | Qué probar | Cierre |
|----|------|--------|-----------|------------|--------|
| KM-F2 | 2 | [x] | `km_f2_barro_tm2` | Barro, TM II, L+diff | MAE mud **5.3** (sesión 2026-06-30) |
| KM-F1 | 1 | [ ] | `km_f1_asfalto` | Asfalto TM II | vmax; caja usada |
| KM-F3 | 3 | [ ] | `km_f3_carga` | Remolque scout + carga | `scan_cargo` |
| KM-CAJA | extra | [ ] | — | Caja **SnowRunner** (`g_scout_offroad`) en taller | L vs H barro/asfalto |

**Sesiones CE**

| Archivo | Protocolo | MAE / notas |
|---------|-----------|-------------|
| `telemetria/sesiones/marshall/ce_km_f2_barro_tm2_20260630_213602.json` | `km_f2_barro_tm2` | **MAE mud 5.3** (1384 muestras); Black River |
| `telemetria/sesiones/marshall/ce_km_f2_barro_tm2_20260629_222234.json` | `km_f2_barro_tm2` | Archivo antiguo (MAE ~10–12); usar la de 202606-30 |

**Comentarios**

```
2026-06-30 | KM-F2 | km_f2_barro_tm2
Setup: Kr 104, TM II, diff, L, Michigan Black River, vacío
MAE mud=5.3 — mejor que sesión 20260629
Revisar: session_context dice suspensión default, no reptadora — ¿setup en juego?
Siguiente: KM-F1 asfalto
```

---

## GMC MH9500 (`mh9500`)

CE: `s_gmc_9500` · Masa mod **7500 kg** · Pipeline CE listo; **re-grabar** con `contact_avg`

| ID | Fase | Estado | Protocolo | Qué probar | Cierre |
|----|------|--------|-----------|------------|--------|
| MH-F1 | 1 | [ ] | `mh_f1_asfalto` | Baseline asfalto vacío | Sesión indexada |
| MH-F2 | 2 | [ ] | `mh_f2_barro_offroad` | AWD+diff, offroad, barro | vs highway RWD atascado |
| MH-F3 | 3 | [ ] | `mh_f3_semi` | Semi cargado barro | ¿Inmóvil como sim? |

**Sesiones CE**

| Archivo | Protocolo | MAE / notas |
|---------|-----------|-------------|
| Antiguas sin `contact_avg` | | No usar — re-grabar |

**Comentarios**

```
(fecha) MH-F2 — 
```

---

## Simulador (todos los vehículos)

Solo tocar código cuando CE marque hueco. Disparador → vehículo afectado.

| ID | Estado | Mejora | Vehículos | Disparador |
|----|--------|--------|-----------|------------|
| SIM-1 | [ ] | Caja `g_truck_default` en `sim/core` | fleetstar, kodiak, mh9500 | F1 sim ≠ CE 0→60 |
| SIM-2 | [ ] | `torque_shape` diesel | Si-6V compartido | vmax alto, arranque OK |
| SIM-3 | [ ] | Par × carga | fleetstar, kodiak | F3 crawl mal |
| SIM-4 | [ ] | Informe 0→30/60, consumo | todos | Cualquier F1 |

---

## Calibración terreno — 4 paradas (mud_grade)

**Objetivo:** afinar `classify_mud_grade()` en `memoria_havok.py` con snapshots reales.

| ID | Estado | Parada | `scan_wheel_substance --save` | Esperado `mud_grade_label` |
|----|--------|--------|-------------------------------|----------------------------|
| TERR-1 | [x] | Tierra seca / trail compacto | `tierra_seca` | `dry_hard` (grip 1.0, contact 1.0) |
| TERR-2 | [ ] | Barro donde avanzas 3–5 km/h | `barro_ligero` | `mud_light` |
| TERR-3 | [ ] | Barro patinaje / casi parado | `barro_profundo` | `mud_deep` |
| TERR-4 | [ ] | Charco / vado con agua | `agua_vado` | `water_ford` |

```powershell
# En cada parada: quieto 30 s, mismo camión (CK1500 u otro scout)
grabar_telemetria.bat probe
grabar_telemetria.bat cargo              # bastidor/remolque en vivo
grabar_telemetria.bat cargo --save cargado
grabar_telemetria.bat snap tierra_seca
# Repetir TERR-2…4, luego (solo cambios):
grabar_telemetria.bat diff tierra_seca barro_ligero
grabar_telemetria.bat diff barro_ligero barro_profundo
# Neumatico montado (CE vs protocolo):
grabar_telemetria.bat tire
# --full si quieres todos los floats, no solo +2FC/+2EC/+2B4
```

Anotar: `grip`, `contact`, `surface_deform_avg`, `mud_grade`, `pos_x/z`.

**Terreno por mapa (blend) eliminado** — `terrain_kind` + `mud_grade` desde CE bajo rueda; el blend del `.pak` no coincidía con la física real (ej. sesión CK1500: CE `mud` vs mapa `off_map`).

**Referencias telemetría (umbrales `classify_mud_grade`)**

| Fuente | mud_light | mud_deep |
|--------|-----------|----------|
| CK1500 F2 (`20260630`) | — | grip ~0.02, contact ~0.36 |
| Fleetstar F2 UHD (`20260702`) | grip ~0.10, contact ~0.65 (30×) | grip ~0.05, contact ~0.44 (360×) |

Snapshots dedicados TERR-2…4 (`barro_ligero`, `barro_profundo`, `agua_vado`) siguen pendientes; la sesión Fleetstar F2 ayuda pero no sustituye paradas quietas con `--snap`.

---

## En espera (no mezclar con CE actual)

| Tema | Doc | Retomar cuando |
|------|-----|----------------|
| Clima / día-noche | `docs/FASE-7.md` | Barro estable en 2+ camiones |
| Remolques / hitch | `docs/FASE-8.md` | `mh_f3_semi` + `km_f3_carga` |
| Curva RPM / potencia | `personal.txt` | F1 Si-6V cerrado en fleetstar+kodiak |
| `bounce.json` | `docs/PLAN-BASE-DATOS-JUEGO.md` | Suspensión avanzada |
| Neumáticos estudio F2 | `docs/FASE-2.md` | F2 no cuadra tras calibrar barro |
| `trailers.json` / catálogo | Plan §4 | Mantenimiento |

---

## Sesiones inválidas (no calibrar)

| Tema | Problema | Vehículo | Acción |
|------|----------|----------|--------|
| `ce_fs_f3_carga_20260630` | carga CE inestable (`vacio` 99 %) | fleetstar | Barro indexado (MAE 6.3); re-grabar F3 con carga |
| `ce_fs_f3_carga_20260703` | camión vacío; meta `frame_cargado` falso; 489× `cargado` fantasma | fleetstar | Retirada de calibracion; no usar para F3 ni barro cargado |
| `ce_f3_carga_barro_20260703` | scout sin carga; meta `trailer_metal_planks` falso; 232× `cargado` fantasma | ck1500 | Retirada de calibracion; no usar para F3 |
| CE sin `contact_avg` | pipeline viejo | varios | Re-grabar |
| `ce_km_f2_*_20260629` | MAE ~12 vs 5.3 nueva | marshall | Usar solo 20260630 |

---

## Plantilla comentario

```text
YYYY-MM-DD | ID (ej. KM-F2) | vehículo | protocolo
Archivo: telemetria/sesiones/<vehiculo>/ce_....json
Setup: motor / neumático / tracción / mapa / suspensión
Resultado: vmax= | t_0_30= | t_0_60= | MAE= | crawl=
Sensación: 
Siguiente: 
```

---

## Orden sugerido entre vehículos

```
Fleetstar: MOT-2100 y/o F3 carga (F2 barro cerrado 2026-07-02)
    ↓
Kodiak: F1 → F2 (mismo motor)
    ↓
Marshall: F1 asfalto (F2 hecho)
    ↓
MH9500: re-grabar F2/F3
    ↓
CK1500: cerrar referencias F1/F2
```

---

## Índice documentos

| Qué | Dónde |
|-----|--------|
| Plan base de datos | `docs/PLAN-BASE-DATOS-JUEGO.md` |
| Notas personales | `personal.txt` |
| CE / offsets | `cheat_engine/README.md`, `docs/FASE-6.md` |

*Última revisión: 2026-07-03 — CK-F3 y FS-F3 `20260703` invalidadas (vacío real); retiradas de calibracion.json.*
