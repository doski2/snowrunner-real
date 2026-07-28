# SnowRunner — Fase 8: Peso y distribución de remolques

> **Enfoque (jul 2026):** por defecto **no** parcheamos XML globales de remolque/carga. Fase 3 ya
> fijó masa de chasis en `patches.py`. Fase 8 = inventario + sim; CE archivado. Ver
> **`METODO-PAK.md`**, **`CE-ARCHIVADO.md`**.

Continuación de **Fase 3** (masa total camión + carga).

**Objetivo** (`personal.txt`): revisar el peso y la **distribución** de los remolques.

---

## Estado

| Tarea                                                | Estado                         |
| ---------------------------------------------------- | ------------------------------ |
| Inventario XML remolques scout + semi                | Hecho                          |
| Tipo acople Drawbar vs Saddle                        | Hecho                          |
| CoG / offset carga en `cargo_*.xml`                  | Hecho                          |
| Sim: remolque como masa + arrastre enganche          | Hecho (Fase 3)                 |
| Sim: distribución longitudinal (tongue / ejes)       | **No** — aproximación futura   |
| Parches XML remolques globales                       | **No recomendado** (ver abajo) |
| `auditar_remolques.py` + `remolques_inventario.json` | Hecho                          |
| Prueba en juego (misma carga, distinto remolque)     | Pendiente (tú)                 |
| Validación carga / semi en juego                     | Pendiente — F3 por vehículo    |

---

## Fase 3 vs Fase 8

|              | Fase 3                                      | Fase 8                                |
| ------------ | ------------------------------------------- | ------------------------------------- |
| Pregunta     | ¿Cuántos kg totales?                        | ¿Dónde están esos kg?                 |
| XML camión   | Masa chasis                                 | Enganche (`farkop` / saddle)          |
| XML remolque | Chasis ~800 kg scout                        | CoG, ejes, `AttachType`               |
| XML carga    | kg por slot                                 | `InstallSlot Offset` (adelante/atrás) |
| Sim          | `trailer_mass_kg` + `trailer_cargo_mass_kg` | Mismo + `TRAILER_HITCH_DRAG`          |

---

## Tipos de acople en SnowRunner

Fuente: [Saber — Truck
AttachType](https://expeditions-guides.saber.games/truck_modding/tags_and_attributes_of_trucks/truck/)

| Tipo                      | Uso típico                                  | Vehículos proyecto  |
| ------------------------- | ------------------------------------------- | ------------------- |
| **Drawbar** (barra)       | Remolque scout enganchado al gancho trasero | **CK1500**          |
| **Saddle** (quinta rueda) | Semirremolque sobre el chasis               | **MH9500**          |

El tipo afecta **respawn** tras portales y cinemática del enganche en Havok, no solo la masa.

---

## Inventario remolques (base game, `initial.pak.bak`)

Ejecutar: `python auditar_remolques.py` → `remolques_inventario.json`

### Scout (CK1500)

| Remolque                      | Masa cuerpo principal  | Suma todos los `Body`    | Acople   | Ruedas   |
| ----------------------------- | ---------------------- | ------------------------ | -------- | -------- |
| `scout_trailer_offroad_cargo` | **800 kg**             | ~1315 kg                 | Drawbar  | 4        |
| `scout_trailer_offroad`       | **600 kg**             | ~850 kg                  | Drawbar  | 4        |
| `scout_trailer_oiltank`       | **2500 kg** (tanque)   | ~3555 kg                 | Drawbar  | 3        |

En Fase 3 usamos **800 kg** del cuerpo principal del offroad cargo — correcto para misiones
estándar.

### Semirremolque (MH9500)

| Remolque                  | Masa principal (aprox.)   | Suma `Body`   | Acople   | Ejes     |
| ------------------------- | ------------------------- | ------------- | -------- | -------- |
| `semitrailer_sideboard_5` | 1000 kg × 4 bloques       | **~4385 kg**  | Saddle   | 4 ruedas |
| `semitrailer_flatbed_5`   | similar                   | **~4585 kg**  | Saddle   | 4        |
| `semitrailer_oiltank`     | tanque 3700–4000 kg       | **~8085 kg**  | Saddle   | 6        |

**Nota sim:** el escenario `semi_vacio` usa **2500 kg** como atajo (~12 t carga útil de diseño). El
chasis real del sideboard vacío ronda **4,3–4,6 t** — el sim **subestima** masa del semi vacío. Para
tendencias «cargado vs vacío» vale; para cifras absolutas del MH9500, usar escenario
`semi_sideboard_vacio` (ver sim).

---

## Distribución de la carga (mercancía)

La mercancía no reparte masa en el XML del remolque: es un **`TruckAddon`** en
`[media]/classes/trucks/cargo/cargo_*.xml`.

Ejemplo `cargo_metal_planks_2.xml` (vigas, 2 slots, 2500 kg):

```xml
```

| Campo                         | Efecto                                                                      |
| ----------------------------- | --------------------------------------------------------------------------- |
| `Mass`                        | Peso del bulto                                                              |
| `CargoLength`                 | Slots ocupados en el remolque                                               |
| `Offset`                      | Posición del bulto respecto al slot (**X** = adelante/atrás en el remolque) |
| `CenterOfMassOffset` en carga | Poco usado en cargas estándar; Havok calcula desde malla                    |

**En juego:** carga larga (2 slots) suele ir más **centrada o adelantada** en el eje del remolque →
más peso en la **barra de tracción** (drawbar) o en el **kingpin** (saddle). SnowRunner no muestra %
de tongue weight; se nota en:

- Patinaje delantero / levantamiento del enganche en cuestas
- Oscilación en asfalto (fishtail) con semi vacío o carga alta

---

## Centro de masa en remolques

Casi todos los remolques stock tienen `CenterOfMassOffset="(0; 0; 0)"` en el cuerpo principal —
Havok deriva el CoG de la **malla de colisión**. No hay ajuste fino por remolque en el XML salvo
casos custom.

Implicación: **no puedes «repartir» peso** solo con el mod del camión; haría falta parchear cada
`trailers/*.xml` o el `cargo_*.xml` de la mercancía.

---

## Qué modela el simulador hoy

En `simulador_ck1500.py` (`step()`):

```text
```

| Efecto real                         | ¿En sim?                        |
| ----------------------------------- | ------------------------------- |
| Más masa → menos aceleración        | Sí                              |
| Más masa en barro → más hundimiento | Sí (aprox.)                     |
| Peso en la barra / quinta rueda     | **No**                          |
| Carga adelantada vs atrás           | **No**                          |
| Ruedas del remolque con tracción    | **No** (remolque pasivo)        |
| Semi 4,3 t vacío vs sim 2,5 t       | **Subestimado** en `semi_vacio` |

Escenario añadido para MH9500 más realista:

| ID sim                   | Remolque                      | Carga         |
| ------------------------ | ----------------------------- | ------------- |
| `semi_sideboard_vacio`   | **4300 kg** (sideboard vacío) | 0             |
| `semi_sideboard_cargado` | 4300 kg                       | 12000 kg útil |

---

## ¿Parchear remolques en el mod?

| Opción                                                                | Veredicto                                                         |
| --------------------------------------------------------------------- | ----------------------------------------------------------------- |
| Bajar masa `scout_trailer_*.xml`                                      | **No** — afecta todas las misiones Scout del juego                |
| Subir masa semi para «más real»                                       | **No** — global; rompe contratos equilibrados para otros camiones |
| Bajar masa `cargo_*.xml`                                              | **No** — cientos de archivos, impacto global                      |
| Ajustar **solo camión** (Fases 1–2) si con remolque va demasiado bien | **Sí** — ya es la estrategia del proyecto                         |
| Documentar + sim + telemetría                                         | **Sí** — Fase 8                                                   |

El realismo del **par remolque+camión** se valida en juego; el mod toca el **tractocamión/scout**,
no la logística de contratos.

---

## Referencia real (orden de magnitud)

### Scout + remolque barra (K10)

| Concepto                  | Real ~1971                        | Juego + mod                        |
| ------------------------- | --------------------------------- | ---------------------------------- |
| Tongue weight recomendado | 10–15 % del peso del remolque     | No calculado                       |
| Remolque + carga misión   | A menudo **> payload** K10        | 5 t+ en remolque vs 1750 kg camión |
| Distribución              | Carga centrada sobre eje remolque | Offset por tipo de cargo           |

### Semi + quinta rueda (Class 8)

| Concepto              | Real                                | Juego                    |
| --------------------- | ----------------------------------- | ------------------------ |
| Kingpin / eje trailer | ~20–25 % peso en tractor (variable) | Havok + saddle           |
| Semi vacío            | ~4–6 t                              | ~4,3 t XML sideboard     |
| GVWR combinado        | Muy superior a 7500 kg tractor      | Misiones 20–30 t totales |

Con **MH9500 mod 7500 kg**, semi cargado es coherente que sea **lento o inmóvil** en barro (Fase 3)
— no es fallo del remolque, es masa combinada.

---

## Qué mirar en juego

1. **CK1500 + scout offroad cargo vacío vs + vigas (2 slots)** — ¿levanta morro o patina delantero

   en cuesta?

2. **Mismo camión, remolque tent (600 kg) vs oiltank (2500 kg)** — diferencia en barro y

   comportamiento general.

3. **MH9500 + semi sideboard vacío vs + 12 t** — ¿solo arrastre o también oscilación en asfalto?
4. **Carga 1 slot vs 2 slots** en el mismo remolque — ¿cambia equilibrio? (offset distinto en XML)

### Telemetría sugerida

Usa Fase 5 con notas en `location_note`:

- `scout_800_vigas` — protocolo `f3_carga_barro` o `trailer_metal_planks`
- `semi_vacio` / `semi_cargado` — `mh_f3_semi`

Compara **v30** y sensación de patinaje; el sim no distingue distribución longitudinal.

---

## Comandos

```powershell
```

---

## Archivos

| Archivo                     | Rol                              |
| --------------------------- | -------------------------------- |
| `FASE-8.md`                 | Este documento                   |
| `FASE-3.md`                 | Masa total y escenarios de carga |
| `auditar_remolques.py`      | Extrae masas/acople del `.pak`   |
| `remolques_inventario.json` | Salida auditoría                 |
| `simulador_ck1500.py`       | `semi_sideboard_*` escenarios    |

---

## Siguiente paso

1. Ejecutar `auditar_remolques.py` tras cada actualización del juego (por si cambian masas).
2. En juego: CK1500 con **vigas** en cuesta 12 % — ¿diff lock + marcha baja bastan?
3. MH9500: semi **vacío real** (~4,3 t) en asfalto antes de `semi_cargado`.
4. Si el scout con remolque lleno sigue **demasiado capaz**, afina motor/ruedas (Fases 1–2), no el

   XML del remolque.

---

## Validación en juego (Fase 8)

| Qué comprobar | Cómo                                                         |
| ------------- | ------------------------------------------------------------ |
| Enganche      | Comportamiento con remolque en mapa (F3)                     |
| Masa          | Chasis en Fase 1; no `cargo_*.xml` globales sin cuidado      |
| Sim           | `LOAD_SCENARIOS`, escenarios semi en `simulador.py`          |

Fases 5–6 (telemetría CE): **archivadas** — ver `CE-ARCHIVADO.md`.

Ver **`docs/FASE-3.md`** y **`camiones/mh9500/FASES.md`**.

---

*Documento Fase 8 — Remolques y distribución de peso · SnowRunner realismo histórico.*
