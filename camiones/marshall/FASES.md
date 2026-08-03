# SnowRunner — KHAN 39 Marshall (mod realista)

Metodología: `docs/METODO-PAK.md`, `docs/FASE-1.md` … `docs/FASE-4.md`.

| Campo          | Valor                            |
| -------------- | -------------------------------- |
| ID mod         | `marshall`                       |
| ID juego       | `khan_39_marshall`               |
| Tipo           | Scout UAZ/TREKOL                 |
| Masa vacía mod | **2030 kg**                      |
| Parches        | `camiones/marshall/patches.py`   |
| Simulador      | `camiones/marshall/simulador.py` |

---

## Setup en juego (referencia)

| Pieza       | En juego              | XML / socket                                   |
| ----------- | --------------------- | ---------------------------------------------- |
| Motor       | **Kr 135-T**          | `ru_scout_old_engine_1`                        |
| Suspensión  | **Reptadora**         | `khan_39_marshall_suspension_crawler` (taller) |
| Neumáticos  | **45" TM II**         | `mudtires_2` / `wheels_scout_yar_871`          |
| Tracción    | AWD + diff            | stock                                          |
| Caja        | SnowRunner *(taller)* | `g_scout_offroad` — no parcheada               |

**Compartido:** `wheels_scout_yar_871.xml` (Yar 87, Chevy Apache).

---

## Referencia real

### Prototipo

**KHAN 39 Marshall** — scout pesado del juego (UAZ / TREKOL). Motor **Kr** y neumático **TM II** =
taller; suspensión **reptadora** = upgrade juego.

### Ficha histórica ([Truck Encyclopedia — UAZ-469](https://truck-encyclopedia.com/coldwar/ussr/UAZ-469.php))

Análogo scout ruso documentado: **UAZ-469** (sustituye GAZ-69, **1972–2007**, ~1 000 000 u.).

| Campo       | UAZ-469 (TE)              |
| ----------- | ------------------------- |
| Dimensiones | 4025 × 1785 × 2050 mm     |
| Masa        | **2380 kg**               |
| Motor       | 2,4 L, **70 hp**          |
| Vel. máx.   | **70 km/h**               |
| Autonomía   | ~**600 km** (2×39 L)      |
| Carga       | 6 pax / **600 kg** útil   |
| GC          | **220–300 mm**            |

Mod **2030 kg** cerca de masa UAZ; motor Kr 104 / Kr 135-T en `e_ru_scout_old.xml` (compartido
scouts RU).

### Ficha comunidad (SR!NFO)

| Campo            | Valor                            |
| ---------------- | -------------------------------- |
| Masa vacía       | **2029 kg**                      |
| Torque stock/max | 30k / 90k Ncm                    |
| Depósito         | 70 L                             |
| Tracción         | 4×4, AWD Always, diff Switchable |

### XML stock vs mod

| Parámetro        | Catálogo                       | Mod                            |
| ---------------- | ------------------------------ | ------------------------------ |
| Masa             | ~1792 kg                       | **2030 kg**                    |
| `Responsiveness` | 0.6 (volante; **no parchear**) |                                |

Mod sube masa hacia SR!NFO; motor Kr 104 **30000→28000** Ncm, Kr 135-T **40000→37333** Ncm.

```powershell
```

---

## Qué hace el mod (stock → realista)

| Parámetro                 | Stock | Mod       | Fase   |
| ------------------------- | ----- | --------- | ------ |
| Masa total                | 1500  | **2030**  | 1 / 3  |
| TM II `SubstanceFriction` | 2.4   | **1.7**   | 2 / 4  |
| TM I `BodyFriction`       | 2.4   | **2.0**   | 2      |
| Kr 104 `Torque`           | 30000 | **28000** | 1      |
| Kr 135-T `Torque`         | 40000 | **37333** | 1      |

**No se toca:** suspensión reptadora (taller). `e_ru_scout_old.xml` es **compartido** (otros scouts
RU).

---

## Fases de prueba (en juego)

### F1 — Asfalto

| Condición  | Valor                              |
| ---------- | ---------------------------------- |
| Motor      | Kr 135-T                           |
| Neumático  | 45" TM II                          |
| Diff       | ON                                 |
| Conducción | WOT, marcha alta, ~60 s recto      |

**Cierre:** vmax contenido; caja SnowRunner en barro, H en asfalto si aplica.

### F2 — Barro TM II

| Condición  | Valor                    |
| ---------- | ------------------------ |
| Mapa       | Barro Michigan           |
| Conducción | Marcha L o L+, diff ON   |

**Cierre:** crawl lento pero avanza. Ajustar `KM_MUD_*` y/o `SubstanceFriction`.

### F3 — Carga

| Condición | Valor                    |
| --------- | ------------------------ |
| Carga     | Remolque scout + carga   |
| Resto     | Igual que F2             |

---

## Aplicar y validar

```powershell
```

---

## Pendiente

| ID    | Fase   | Estado   | Notas                 |
| ----- | ------ | -------- | --------------------- |
| KM-F1 | 1      | [ ]      | Asfalto Kr 135-T      |
| KM-F2 | 2      | [ ]      | Barro TM II           |
| KM-F3 | 3      | [ ]      | Remolque + carga      |

---

## Comentarios

```text
```

---

*Última revisión: 2026-07-29 — Truck Encyclopedia + Referencia real.*
