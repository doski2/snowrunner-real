# SnowRunner — Fase 4: Terreno (juego vs real K10)

> **Enfoque (jul 2026):** terreno del mapa no editable; solo neumático (Fase 2). CE archivado.

Continuación de Fases 1–3.

**Objetivo Fase 4** (de `personal.txt`): estudiar si el comportamiento por tipo de terreno es
adecuado y cómo debería ser.

---

## Estado

| Tarea                                                       | Estado                                                                                 |
| ----------------------------------------------------------- | -------------------------------------------------------------------------------------- |
| Documentar física terreno SnowRunner (Saber / blog oficial) | Hecho                                                                                  |
| Mapear superficies del sim → motor del juego                | Hecho                                                                                  |
| Bandas de referencia K10 ~1971 por terreno                  | Hecho                                                                                  |
| `run_terrain_audit()` + tests + informe                     | Hecho                                                                                  |
| Parches XML de terreno por vehículo                         | **No** (imposible desde mod de camión)                                                 |
| Prueba en juego CK1500 por mapa                             | Parcial                                                                                |
| Expectativas MH9500 documentadas                            | **Hecho** (`camiones/mh9500/simulador.py`)                                             |
| Prueba en juego MH9500 por mapa                             | **En curso**                                                                           |
| Validación por terreno en juego                             | Pendiente — F2/F3 en mapa por vehículo                                                 |
| Documentar qué es dato real vs calibración                  | **Hecho** (§ siguiente)                                                                |

---

## Tres capas de “terreno”: qué es real y qué no

En este proyecto conviven **tres fuentes** distintas. Mezclarlas es la causa habitual de confusión
al calibrar.

```text
```

### 1. Mundo real (expectativa, no medición nuestra)

No medimos un K10 de 1971 en pista. Usamos **bandas orientativas** en `sim/core.py` →
`REAL_K10_BANDS`:

| Terreno                | Stock (highway)    | Equipado (offroad / M&S)   |
| ---------------------- | ------------------ | -------------------------- |
| Barro ligero           | 5–15 km/h          | 15–40 km/h                 |
| Barro profundo         | 0–5 km/h           | 5–20 km/h                  |
| Asfalto / tierra firme | no limita en crawl | no limita en crawl         |
| Nieve suelta           | 10–30 km/h         | 25–50 km/h                 |

Son **rangos históricos documentales** para juzgar si el juego va “duro”, “blando” o “ok”. No
describen el barro concreto de un tramo de Michigan.

#### Comportamiento que el mod considera “adecuado”

| Familia                                     | Criterio                                                                                      |
| ------------------------------------------- | --------------------------------------------------------------------------------------------- |
| **Firme** (asfalto, tierra compacta, grava) | El terreno casi no limita en aceleración a fondo; mandan motor, masa y neumático en carretera |
| **Sustancias** (barro, nieve, agua)         | Cuello de botella = tracción + hundimiento; highway stock lento; offroad/M&S claramente mejor |
| **Barro profundo / agua sin snorkel**       | Atasco o avance muy lento — coherente con lo real en un Scout ligero                          |

### 2. SnowRunner — lo medible y lo editable

#### A) Terreno del mapa (real en el juego, **no editable** desde mod de camión)

Vive en el `.pak` del mapa, no en `initial.pak` del camión. **Todos los vehículos** en el mismo
tramo comparten:

- Viscosidad base, tint, máscara de humedad
- Datos de extrusión (barro bajo el suelo visible)
- Profundidad de nieve y de agua

El mod **no puede** hacer que el CK1500 “vea” un barro distinto al Fleetstar en el mismo sitio.

#### B) XML del camión — neumático ↔ terreno (**editable**, Fases 1–2)

| Atributo XML          | Terreno afectado    |
| --------------------- | ------------------- |
| `BodyFrictionAsphalt` | Asfalto / carretera |
| `BodyFriction`        | Tierra, grava       |
| `SubstanceFriction`   | Barro, nieve, agua  |
| `IsIgnoreIce`         | Cadenas en hielo    |

Ejemplo aplicado: CK1500 `highway_1` `SubstanceFriction` **0.4 → 0.5**
(`camiones/ck1500/patches.py`). Eso no cambia el barro del mapa; cambia cómo **ese neumático**
interactúa con las sustancias.

#### C) Medición en juego (método vigente)

| Qué              | Cómo                                      |
| ---------------- | ----------------------------------------- |
| Velocidad        | km/h del HUD en ruta fija                 |
| Sensación        | Notas en `camiones/<id>/FASES.md`         |
| XML              | `verify_pak.py`                           |
| Orientación      | `simulador.py`                            |

Telemetría CE (Havok en memoria): **archivada** — ver `CE-ARCHIVADO.md`. Las sesiones
`telemetria/sesiones/ce_*.json` son histórico jun-2026, no gate de calibración.

#### D) Offsets rueda (investigación)

```text
```

Herramienta: `python cheat_engine/scan_wheel_substance.py --save asfalto` / `--save barro` /
`--diff`.

### 3. Simulador Python — modelo de calibración, no realidad

`sim/core.py` define `SurfaceConfig` (nombre, `kind`, `viscosity`, `water_depth`). Constantes como:

| Constante                                  | Rol                                                   |
| ------------------------------------------ | ----------------------------------------------------- |
| `MUD_RESIST_COEF`                          | Resistencia al avance en barro por tipo de neumático  |
| `mud_immersion` / `update_mud_immersion()` | Hundimiento acumulado                                 |
| `MH_MUD_*`, `FS_MUD_*`                     | Ajustes por camión pesado (`camiones/*/simulador.py`) |

**No salen del XML ni del mapa.** Se retocan en `simulador.py` hasta que la prueba en juego (km/h
HUD, sensación) coincida con la intención del mod.

El sim **no modela**: tint/humedad del mapa, clima (Fase 7), deformación Havok en tiempo real, ni
diferencias entre mapas. Por eso un protocolo `fs_f2_barro_uhd` usa `kind: "mud"` genérico aunque el
barro del juego sea único en ese tramo.

### Criterio de validación (Fases 2–4)

| Pregunta                      | Respuesta                                                      |
| ----------------------------- | -------------------------------------------------------------- |
| ¿Viene del mod XML?           | `SubstanceFriction`, masa, torque → **sí, editable**           |
| ¿Viene del mundo real?        | `REAL_K10_BANDS` → **referencia histórica**                    |
| ¿Viene del mapa?              | Viscosidad del barro → **sí en juego, no desde mod camión**    |
| ¿Calibra el sim?              | `MUD_RESIST_COEF`, `mud_immersion_rate` → orientación          |
| ¿Prueba final?                | **En juego** — misma ruta, anotar km/h HUD                     |

#### Flujo recomendado

1. Ruta fija: mismo camión, neumático, tracción, marcha reducida, **mismo tramo de mapa**.
2. `verify_pak.py` + simulador para tendencia.
3. Conducir en juego; anotar sensación y km/h.
4. Si no cuadra → ajustar XML en `patches.py` o `*_MUD_*` en sim.
5. Si diverge: primero XML neumático (`substance`); si el juego ya va bien pero el sim no, tocar

   `MUD_*` del sim.

---

## Cómo funciona el terreno en SnowRunner

Fuente principal: [Terrain Physics Blog — Focus
Forums](https://forums.focus-entmt.com/topic/43997/terrain-physics-blog) (Pavel Zagrebelnyy, creador
original).

### Dos familias de superficie

| Tipo              | Ejemplos                            | Comportamiento                           |
| ----------------- | ----------------------------------- | ---------------------------------------- |
| **No extrudable** | Asfalto, hormigón, roca             | No se deforma; el vehículo no se hunde   |
| **Extrudable**    | Hierba, tierra, arena, barro, nieve | Viscosidad base + hundimiento deformable |

### Capas que pinta el autor del mapa (no en `initial.pak` del camión)

| Capa                     | Efecto                                                     |
| ------------------------ | ---------------------------------------------------------- |
| **Viscosidad base**      | Arena > tierra > hierba (nuevo en SnowRunner vs MudRunner) |
| **Tint**                 | Más oscuro = más viscoso = más atasco                      |
| **Wetness mask**         | Humedad extra en zonas mojadas                             |
| **Extrusion data**       | Barrizales / rutas difíciles ocultos bajo el suelo         |
| **Profundidad de nieve** | Hundimiento hasta el suelo firme debajo                    |
| **Profundidad de agua**  | Vado, flotación, daño al motor sin snorkel                 |

### Qué controla el XML del camión (Fases 1–2)

| Atributo neumático    | Terreno afectado                 |
| --------------------- | -------------------------------- |
| `BodyFrictionAsphalt` | Asfalto / carretera              |
| `BodyFriction`        | Tierra limpia, grava, colisiones |
| `SubstanceFriction`   | Barro, nieve, agua (sustancias)  |
| `IsIgnoreIce`         | Cadenas en hielo                 |

**El mod CK1500 solo puede tocar la columna derecha** (neumáticos, motor, masa). No puede cambiar la
viscosidad del barro de Michigan.

---

## Simulador: mapeo `SurfaceConfig` → juego

| Superficie sim       | `kind`     | Capas juego aproximadas            | `MUD_RESIST_COEF` sim    |
| -------------------- | ---------- | ---------------------------------- | ------------------------ |
| Asfalto              | `asphalt`  | Rígido + `BodyFrictionAsphalt`     | —                        |
| Tierra               | `dirt`     | Extrudable, viscosidad media       | —                        |
| Grava                | `gravel`   | `BodyFriction` × 0.85              | —                        |
| Barro                | `mud`      | Substance + deformación + tint     | por neumático            |
| Barro profundo       | `deep_mud` | Substance + extrusion + agua       | ×1.6 profundidad         |
| Nieve                | `snow`     | Substance + profundidad nieve      | —                        |
| Hielo                | `ice`      | Fricción muy baja; cadenas ignoran | —                        |
| Agua poco / profunda | `water`    | Profundidad + snorkel + substance  | por neumático            |

`MUD_RESIST_COEF` es **calibración del sim**, no un valor XML del juego.

---

## K10 real vs sim I6 (v30 km/h a 30 s, vacío 1750 kg)

### Superficies firmes (tierra / grava / asfalto)

En aceleración a fondo el sim no limita por “crucero real” — el terreno no es cuello de botella si
`v30 > 40 km/h`. Coherente con un K10 en camino seco.

### Barro y sustancias

| Terreno         | K10 stock (highway)   | K10 equipado (offroad/M&S)   | Sim highway   | Sim offroad+diff   |
| --------------- | --------------------- | ---------------------------- | ------------- | ------------------ |
| Barro ligero    | 5–15 km/h             | 15–40 km/h                   | **0**         | **~40**            |
| Barro profundo  | 0–5                   | 5–20                         | **0**         | **0**              |
| Nieve suelta    | 10–30                 | 25–50                        | **~112**      | **~150**           |
| Hielo           | 5–15 (peligroso)      | cadenas 20–40                | **~2**        | **~2**             |
| Hielo + cadenas | —                     | 20–40                        | —             | **~24**            |
| Agua poco prof. | 5–20 (vado)           | 10–25                        | **0**         | **~22**            |
| Agua profunda   | 0–5                   | 0–10                         | **0**         | **0**              |

### Veredictos principales

| Terreno                  | ¿Adecuado para mod realista?   | Notas                                                                                      |
| ------------------------ | ------------------------------ | ------------------------------------------------------------------------------------------ |
| Asfalto / tierra / grava | **Sí**                         | Terreno no limita; velocidad la marca motor (Fase 1)                                       |
| Barro + highway stock    | **Juego más duro que K10**     | Highway a 0 km/h; K10 real iría a 5–15 km/h. Parche Fase 2 (+0.1 substance) mitiga un poco |
| Barro + offroad          | **Sí**                         | ~40 km/h en rango real equipado                                                            |
| Barro profundo           | **Sí (duro)**                  | Atasco con cualquier setup ligero — realista en espíritu                                   |
| Nieve + highway          | **Juego más blando**           | Sim muy rápido vs K10; diseño arcade de SnowRunner                                         |
| Hielo + cadenas          | **Aceptable**                  | Cadenas desbloquean (~24 km/h sim)                                                         |
| Agua                     | **Coherente**                  | Sin snorkel / profundo = parado; vado corto con offroad OK                                 |

---

## ¿Se puede parchear el terreno para el CK1500?

| Opción                                    | ¿Factible?                                              |
| ----------------------------------------- | ------------------------------------------------------- |
| Editar viscosidad de un mapa concreto     | Solo en mod de mapa (.pak de zona), no en mod de camión |
| Cambiar `SubstanceFriction` del neumático | **Sí** — Fase 2 (`highway_1` 0.4 → 0.5)                 |
| Cambiar `MUD_RESIST_COEF` del sim         | Solo para calibrar el simulador Python                  |
| Parche global de terreno en `initial.pak` | **No hay** archivos de sustancia editables por vehículo |

**Decisión Fase 4:** no añadir entradas de terreno en `patches.py`. El CK1500 hereda el mismo
barro/nieve del mapa que todos los vehículos.

---

## Comandos

```powershell
```

Salida informe sim: `simulacion_terreno.json`

---

## Archivos

| Archivo                                      | Rol                                                                      |
| -------------------------------------------- | ------------------------------------------------------------------------ |
| `sim/core.py`                                | `TERRAIN_GAME`, `REAL_K10_BANDS`, `run_terrain_audit()`, `SurfaceConfig` |
| `camiones/ck1500/test_simulacion_terreno.py` | Tests unittest Fase 4                                                    |
| `simular_terreno.py`                         | Informe consola                                                          |
| `cheat_engine/memoria_havok.py`              | Lectura CE: grip, `surface_wheel`, `terrain_hint`                        |
| `telemetria.py`                              | Protocolos `*_f2_barro_*`; meta `surface_kind`                           |
| `docs/FASE-4.md`                             | Este documento                                                           |

---

## Prueba en juego recomendada

Misma ruta, mismo CK1500 mod I6, comparar sensación (no solo km/h del HUD):

1. **Carretera asfaltada** — ¿aceleración creíble con I6?
2. **Barro ligero Michigan** — highway vs offroad (¿0 vs avance lento?)
3. **Nieve Alaska** — ¿demasiado fácil con highway stock?
4. **Vado con remolque vacío** — ¿coherente con Fase 3 (más masa = más hundimiento)?

---

## MH9500 — terreno (expectativas)

| Terreno              | Stock mod (RWD highway)        | Con upgrades (offroad + AWD + diff)            |
| -------------------- | ------------------------------ | ---------------------------------------------- |
| Asfalto              | Aceleración más lenta, jugable | Igual tracción en seco                         |
| Barro ligero         | Atasco o avance mínimo         | Avance lento; riesgo de hundirse si insistes   |
| Barro + semi cargado | Prácticamente inmóvil          | Igual — no es vehículo de campo con 12 t       |
| Nieve / agua         | Muy penalizado con highway     | Mejora con offroad; sigue siendo camión pesado |

Matriz sim: `python -m camiones.mh9500.simulador` · Doc: **`camiones/mh9500/FASES.md`** § Fase 4.

**Fase 7:** la lluvia dinámica no endurece el barro; la noche no lo seca. Ver **`FASE-7.md`**.

Anotar si el gap barro-highway sigue siendo el único punto débil tras el parche Fase 2; el resto del
terreno es **diseño de mapa + neumático**, no del chasis.

---

## Validación en juego (Fase 4)

| Qué comprobar | Cómo                                                         |
| ------------- | ------------------------------------------------------------ |
| Barro         | F2 en mapa; km/h HUD vs sensación                            |
| Sim           | `SurfaceConfig`, `*_MUD_*` orientan tendencia                |
| Ajuste        | Neumático XML y/o constantes sim si crawl no cuadra          |

Ejemplo CK1500: si barro demasiado rápido en juego → subir `SubstanceFriction` o `MUD_RESIST_*`.

Fases 5–6 (telemetría CE): **archivadas** — ver `CE-ARCHIVADO.md`.

---

*Documento Fase 4 — Terreno · SnowRunner realismo histórico.*
