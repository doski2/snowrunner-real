# SnowRunner — Fase 3: Peso, carga y remolque CK1500

> **Enfoque (jul 2026):** no `cargo_*.xml`. Masa chasis en Fase 1. Sim orienta; prueba en juego. CE
> archivado.

Continuación de Fase 1 y 2.

**Objetivo Fase 3** (de `personal.txt`): revisar peso del vehículo y de las cargas, entender el
comportamiento con carga y simular tendencias.

---

## Estado

| Tarea                                                        | Estado                                                    |
| ------------------------------------------------------------ | --------------------------------------------------------- |
| Inventario masa chasis / addons / remolque / cargo en `.pak` | Hecho                                                     |
| Referencia payload real K10 ~1971                            | Hecho                                                     |
| Extender `simulador_ck1500.py` con carga y remolque          | Hecho                                                     |
| `test_simulacion_carga.py` + `simular_carga.py`              | **Archivado** (eliminado jul 2026)                        |
| Parches XML de masas de carga                                | **No** (solo sim + doc)                                   |
| Prueba en juego CK1500 con remolque                          | Parcial                                                   |
| Escenarios semi MH9500 en sim                                | **Hecho** (`semi_vacio`, `semi_cargado`)                  |
| Prueba en juego MH9500 con semi                              | **En curso**                                              |
| Validación carga en juego                                    | Pendiente — F3 por vehículo en `camiones/*/FASES.md`      |

---

## Masa del CK1500 en el juego

### Chasis (ya parcheado Fase 1)

| Componente       | Fábrica     | Mod I6      | Archivo                |
| ---------------- | ----------- | ----------- | ---------------------- |
| Chasis delantero | 1150 kg     | **900 kg**  | `chevrolet_ck1500.xml` |
| Chasis trasero   | 1050 kg     | **850 kg**  | `chevrolet_ck1500.xml` |
| **Total seco**   | **2200 kg** | **1750 kg** | —                      |
| Combustible      | 80 L        | 76 L        | mismo XML              |
| CoG Y            | -0.15       | **-0.20**   | mismo XML              |

El CK1500 **no tiene slots de carga en la caja** en el XML base; transporta mercancía con **remolque
scout** o addons de utilidad (no carga de misión en el techo).

### Addons con masa (tuning)

| Addon                     | Masa XML   | Notas                                        |
| ------------------------- | ---------- | -------------------------------------------- |
| `rooftop_trunk`           | 200 kg     | Portaequipajes + combustible/repuestos extra |
| `rooftop_trunk_2`         | 100 kg     | Variante ligera                              |
| `trunk_stuff`             | 60 kg      | Decoración maletero                          |
| `trunk_stuff_2`           | 150 kg     | Decoración maletero                          |
| `snorkel_1` / `snorkel_2` | ~20 kg     | Snorkel                                      |

Escenario típico sim: **220 kg** (portaequipajes 200 + snorkel 20).

### Remolques scout compatibles

| Remolque                         | Masa chasis   | Uso                     |
| -------------------------------- | ------------- | ----------------------- |
| `scout_trailer_offroad_cargo`    | **800 kg**    | Caja offroad (misiones) |
| `scout_trailer_flatbed_1/2`      | 800 kg        | Plataforma              |
| `scout_trailer_offroad` / `tent` | 600 kg        | Sin carga               |
| `scout_trailer_oiltank`          | 2500 kg       | Cisterna (pesado)       |

La masa de la **mercancía** no está en el XML del remolque: cada unidad es un `TruckAddon` en
`[media]/classes/trucks/cargo/cargo_*.xml` con `<Body Mass="…">` y `CargoLength` (slots).

---

## Catálogo de carga Scout (extraído de `initial.pak.bak`)

| Carga              | Slots   | Masa    | kg/slot   |
| ------------------ | ------- | ------- | --------- |
| Tablones madera    | 1       | 500 kg  | 500       |
| Ladrillos          | 1       | 1000 kg | 1000      |
| Rollo metal        | 1       | 1000 kg | 1000      |
| Repuestos          | 1       | 1200 kg | 1200      |
| Bloques hormigón   | 1       | 3000 kg | 3000      |
| Vigas metal        | 2       | 2500 kg | 1250      |
| Tuberías medianas  | 2       | 2250 kg | 1125      |
| Contenedor pequeño | 2       | 1500 kg | 750       |
| Losas hormigón     | 2       | 3000 kg | 1500      |

Ejemplo misión habitual: remolque 800 kg + vigas metal 2500 kg → **5050 kg** remolque+carga, más
**1750 kg** camión = **~6800 kg** total (con addons ~7020 kg).

---

## Referencia real — Chevrolet K10 4×4 ~1971

| Aspecto                | Real                                                           | Juego (mod I6)                        |
| ---------------------- | -------------------------------------------------------------- | ------------------------------------- |
| Peso en vacío          | ~1750–1860 kg (3850–4100 lb)                                   | **1750 kg** ✓                         |
| Payload útil (caja)    | ~750–1000 kg (1650–2200 lb)                                    | 1 slot ≈ 1000–1200 kg en remolque     |
| Remolque ligero época  | 500–1500 kg + carga moderada                                   | Remolque 800 kg + hasta 2500 kg carga |
| Comportamiento cargado | Más lento, más hundimiento en barro, más inercia al soltar gas | Igual en sim (masa total en física)   |

**Conclusión:** el chasis vacío del mod es realista. Las **misiones con remolque lleno** exceden con
creces el payload histórico del K10 — es diseño de juego (Scout como furgoneta de contratos), no
error del mod.

---

## Simulador Fase 3

### `VehicleConfig` (solo vacío)

| Campo     | Descripción              |
| --------- | ------------------------ |
| `mass_kg` | Masa chasis mod (vacío)  |

`total_mass_kg()` devuelve `mass_kg`. La función `step()` usa esa masa en:

- Fuerza normal → límite de tracción
- Resistencia a la rodadura y pendiente
- Hundimiento en barro (`sink`, `MUD_RESIST_COEF`)
- Aceleración `F = ma`

Carga, bastidor lleno y remolques **no** se modelan en Python (jul 2026). Validar F3 en juego.

### Sim por vehículo (activo)

Cada `camiones/<id>/simulador.py` cubre **F1 asfalto** y **F2 barro vacío**. No hay matriz global
ni `simulacion_carga.json`.

### Matriz global (`LOAD_SCENARIOS`) — archivado

La matriz CK1500 (`simular_carga.py`, `LOAD_SCENARIOS`, `run_cargo_matrix`) se eliminó jul 2026.
Referencia histórica de IDs:

| ID                     | Descripción                | Masa total aprox.   |
| ---------------------- | -------------------------- | ------------------- |
| `vacio`                | Solo chasis mod            | 1750 kg             |
| `trailer_metal_planks` | + remolque + vigas 2 slots | 5050 kg remolque    |
| `frame_cargado`        | Bastidor + 6 t util        | —                   |
| `semi_cargado`         | Semi + 12 t util           | —                   |

### Comandos (histórico)

```powershell
```

---

## Decisión Fase 3

### No parchear masas de carga en `.pak`

| Opción                            | Veredicto                                                     |
| --------------------------------- | ------------------------------------------------------------- |
| Bajar `Mass` en `cargo_*.xml`     | **No** — afecta todos los contratos del juego, no solo CK1500 |
| Subir masa remolque / bajar carga | **No** — cambio global de balance de misiones                 |
| Mantener chasis 1750 kg (Fase 1)  | **Sí** — ya alineado con K10 real                             |
| Matriz `simular_carga`            | **Archivado** — validar carga en juego (F3 en `FASES.md`)     |

Si en juego el CK1500 con remolque lleno resulta **demasiado capaz** en barro, el ajuste fino iría
en motor (Fase 1) o neumáticos (Fase 2), no en multiplicar cientos de XML de carga.

**Fase 8** amplía esto: distribución longitudinal, tipo de acople (drawbar vs saddle) y masas reales
de semi — ver **`FASE-8.md`** (archivado; validar F3 en juego).

---

## Qué mirar en juego

1. **Vacío vs remolque + 2 slots** en barro medio (misma ruta Fase 2).
2. **Cuesta 12–15 %** con `mision_pesada` — ¿requiere marcha baja + diff lock?
3. **Aceleración en asfalto** cargado — ¿sensible pero jugable?
4. Comparar con **stock 2200 kg** desactivando mod (opcional) para sentir solo el efecto de carga.

---

## Archivos del proyecto

| Archivo                   | Rol                                                         |
| ------------------------- | ----------------------------------------------------------- |
| `sim/core.py`             | `total_mass_kg()` = `mass_kg`; `step()` sin remolque/carga  |
| `camiones/*/simulador.py` | F1 asfalto + F2 barro vacío                                 |
| `FASE-3.md`               | Este documento                                              |

Eliminados (jul 2026): `simular_carga.py`, `simulacion_carga.json`,
`camiones/ck1500/test_simulacion_carga.py`.

---

## Validación en juego (Fases 1–4)

| Qué comprobar | Cómo                                                           |
| ------------- | -------------------------------------------------------------- |
| Masa chasis   | Ya en Fase 1 (`patches.py`); no `cargo_*.xml`                  |
| Carga F3      | Mismo tramo barro vacío vs cargado; km/h HUD y sensación       |
| Sim           | `camiones/*/simulador.py` (vacío vs cargado); no matriz global |

Fases 5–6 (telemetría CE): **archivadas** — ver `CE-ARCHIVADO.md`.

---

## Siguiente paso sugerido

**CK1500:** mod I6, offroad + diff lock, remolque `scout_trailer_offroad_cargo` con **vigas metal (2
slots)** en barro de Michigan / Alaska.

**MH9500:** semirremolque highway. Ver **`camiones/mh9500/FASES.md`** § Fase 3.

---

## MH9500 — carga (semirremolque)

| Escenario sim   | Masa remolque   | Carga útil   | Uso                    |
| --------------- | --------------- | ------------ | ---------------------- |
| `semi_vacio`    | 2500 kg         | 0            | Baseline               |
| `semi_cargado`  | 2500 kg         | **12000 kg** | Contrato pesado típico |

El MH9500 **no es un scout**: con ~19 t totales en barro el sim predice **inmovilidad** incluso con
offroad + AWD — coherente con un camión de carretera sobrecargado.

```powershell
```
