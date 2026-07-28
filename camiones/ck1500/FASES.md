# SnowRunner — Chevrolet CK1500 (mod realista)

Metodología: `docs/METODO-PAK.md`, `docs/FASE-1.md` … `docs/FASE-4.md`.

| Campo          | Valor                        |
| -------------- | ---------------------------- |
| ID mod         | `ck1500`                     |
| ID juego       | `chevrolet_ck1500`           |
| Tipo           | Scout 4×4 K10 ~1971          |
| Masa vacía mod | **~1750 kg**                 |
| Parches        | `camiones/ck1500/patches.py` |
| Simulador      | `sim/core.py`                |

---

## Setup en juego (referencia)

| Pieza      | En juego               | XML / socket                              |
| ---------- | ---------------------- | ----------------------------------------- |
| Motor      | **AAT-8V 5.2**         | `us_scout_old_engine_ck1500`              |
| Neumáticos | highway stock          | `wheels_scout1` / `highway_1`             |
| Tracción   | 4×4 stock              | sin diff always                           |
| Carga F3   | Remolque scout + vigas | —                                         |

---

## Referencia real

Detalle completo con fuentes (GM Heritage, Wikipedia): **`docs/FASE-1.md`** § comparativa K10.

### Mundo real — Chevrolet K10 ~1971

| Parámetro   | Referencia histórica         |
| ----------- | ---------------------------- |
| Masa vacía  | **1750–1860 kg**             |
| Depósito    | ~76 L                        |
| Motor serie | 250 I6 ~185 lb-ft            |
| 0–97 km/h   | ~13–18 s (orden de magnitud) |

### Truck Encyclopedia ([Chevrolet G506](https://truck-encyclopedia.com/ww2/us/Chevrolet-G506-7101-1.5-ton-4x4-truck.php))

No hay artículo al **K10 / CK1500 ~1971** (pickup civil). Antecedente GM 4×4 ligero en TE:

| Campo       | G506 1,5 t 4×4 (WW2)   |
| ----------- | ---------------------- |
| Masa vacía  | **2100 kg**            |
| Dimensiones | 4380 × 1990 × 1930 mm  |
| Motor       | 83 hp I6, 184 lb-ft    |
| Vel. máx.   | **80 km/h**            |
| Autonomía   | **430 km**             |
| Carga       | **800 kg**             |

Detalle K10: **`docs/FASE-1.md`**. Mod **1750 kg** alineado con K10, no G506 ni SR!NFO.

### Ficha comunidad (SR!NFO)

| Campo            | Valor                |
| ---------------- | -------------------- |
| Masa (hoja)      | 2532 kg              |
| Torque stock/max | 35k / 62k Ncm        |
| Depósito         | 80 L                 |
| Tracción         | 4×4, diff Switchable |

La hoja SR!NFO mezcla Scout/K10; el mod usa **1750 kg** alineado con K10 real, no 2532 kg.

### XML stock vs mod

| Parámetro        | Catálogo `.pak`   | Mod objetivo    |
| ---------------- | ----------------- | --------------- |
| Masa chasis      | 1752 kg           | **1750 kg**     |
| Motor CK1500     | 62k / MaxDelta 10 | **40k / 0.015** |

```powershell
```

---

## Qué hace el mod (stock → realista)

| Parámetro                     | Stock  | Mod (aprox.) | Fase   |
| ----------------------------- | ------ | ------------ | ------ |
| Masa chasis (900+850)         | 2200   | **1750**     | 1 / 3  |
| AAT-8V torque                 | 62000  | **40000**    | 1      |
| `MaxDeltaAngVel`              | 10     | **0.015**    | 1      |
| `highway_1` SubstanceFriction | 0.4    | **0.5**      | 2      |
| Suspensión delantera Strength | 0.035  | **0.045**    | 1      |

---

## Fases de prueba (en juego)

### F1 — Asfalto AAT-8V

| Condición  | Valor                         |
| ---------- | ----------------------------- |
| Motor      | AAT-8V 5.2 solo               |
| Conducción | WOT, marcha alta, ~60 s recto |

**Cierre:** no “cohete”; aceleración contenida vs stock.

### F2 — Barro offroad

| Condición  | Valor                              |
| ---------- | ---------------------------------- |
| Neumático  | offroad + diff + marcha L          |
| Mapa       | Barro Michigan                     |

**Cierre:** crawl lento pero avanza (highway en barro ≈ 0 km/h es diseño).

### F3 — Carga

| Condición | Valor                    |
| --------- | ------------------------ |
| Carga     | Remolque scout + vigas   |

---

## Aplicar y validar

```powershell
```

---

## Pendiente

| ID    | Fase   | Estado   | Notas                 |
| ----- | ------ | -------- | --------------------- |
| CK-F1 | 1      | [ ]      | Asfalto AAT-8V WOT    |
| CK-F2 | 2      | [ ]      | Barro offroad + diff  |
| CK-F3 | 3      | [ ]      | Remolque + vigas      |

---

## Comentarios

```text
```

---

*Última revisión: 2026-07-29 — Truck Encyclopedia + Referencia real.*
