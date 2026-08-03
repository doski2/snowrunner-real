# SnowRunner — Chevrolet Kodiak C70 (mod realista)

Metodología: `docs/METODO-PAK.md`, `docs/FASE-1.md` … `docs/FASE-4.md`.
Referencia cercana: `camiones/fleetstar/FASES.md`.

| Campo          | Valor                          |
| -------------- | ------------------------------ |
| ID mod         | `kodiak`                       |
| ID juego       | `chevrolet_kodiakc70`          |
| Tipo           | HEAVY_DUTY 4×4                 |
| Masa vacía mod | **8150 kg**                    |
| Parches        | `camiones/kodiak/patches.py`   |
| Simulador      | `camiones/kodiak/simulador.py` |

---

## Setup en juego (referencia)

| Pieza      | En juego                              |
| ---------- | ------------------------------------- |
| Motor      | **Si-6V/1900** (opcional 2100T)       |
| Neumáticos | **39" UHD I** (`highway_1`)           |
| Tracción   | **AWD** + diff (instalar en taller)   |
| Ruedas     | **4** (no 6×4 como Fleetstar)         |

**No confundir con Fleetstar:** F2070A lleva **42"** UHD; Kodiak **39"** (y 43" en taller).

Parches compartidos: `e_us_truck_old.xml`, `wheels_medium_double.xml`.

---

## Referencia real

### Prototipo

**Chevrolet Kodiak C70** — Class 7 **4×4** (serie Kodiak **1981–1989**). Mismo **Si-6V** que
Fleetstar; neumático **39"** UHD (Fleetstar **42"**).

### Truck Encyclopedia

Sin artículo al **Kodiak C70**. Antecedente GM en TE:
[Chevrolet G506](https://truck-encyclopedia.com/ww2/us/Chevrolet-G506-7101-1.5-ton-4x4-truck.php).
C70 entre C/K y Brigadier; motor Caterpillar **3208** típico en gen. 1.

| Kodiak C70 (histórico) | Valor                |
| ---------------------- | -------------------- |
| Clase                  | Class **7** (C7000)  |
| Producción             | **1980–1989**        |
| BBC cabina             | **92″** (elevada)    |
| Tracción               | 4×4 / 6×6 opcional   |

Calibrar Si-6V en Fleetstar y repetir F1 (`KD-MOT`).

### Ficha comunidad (SR!NFO)

| Campo            | Valor              |
| ---------------- | ------------------ |
| Masa vacía       | **8201 kg**        |
| Torque stock/max | 135k / 145k Ncm    |
| Depósito         | 200 L              |
| Tracción         | 4×4, Switchable    |

### XML stock vs mod

| Parámetro  | Catálogo | Mod         |
| ---------- | -------- | ----------- |
| Masa       | ~7513 kg | **8150 kg** |
| Si-6V/1900 | 135k Ncm | **92k Ncm** |

Calibrar motor en Fleetstar y **repetir F1** aquí (`KD-MOT` en pendientes).

```powershell
```

---

## Qué hace el mod (stock → realista)

| Parámetro             | Stock    | Mod         | Fase   |
| --------------------- | -------- | ----------- | ------ |
| Masa total            | ~7513 kg | **8150 kg** | 1 / 3  |
| Combustible           | 200 L    | **175 L**   | 1      |
| Si-6V/1900 torque     | 135000   | **92000**   | 1      |
| `highway_1` Substance | 0.4      | **0.5**     | 2 / 4  |

---

## Fases de prueba (en juego)

### F1 — Asfalto

| Condición  | Valor                    |
| ---------- | ------------------------ |
| Neumático  | 39" UHD I                |
| AWD + diff | ON                       |
| Conducción | WOT, marcha alta         |

**Cierre:** comparar sensación con Fleetstar FS-F1 (mismo motor, +masa, 4 ruedas).

### F2 — Barro UHD

| Condición  | Valor             |
| ---------- | ----------------- |
| Conducción | Marcha L, diff ON |

**Cierre:** afinar `KD_MUD_*` en sim y/o neumático en `patches.py`.

### F3 — Carga

| Condición | Valor              |
| --------- | ------------------ |
| Carga     | Bastidor en barro  |

---

## Aplicar y validar

```powershell
```

---

## Pendiente

| ID     | Fase   | Estado   | Notas                              |
| ------ | ------ | -------- | ---------------------------------- |
| KD-F1  | 1      | [ ]      | Asfalto WOT                        |
| KD-F2  | 2      | [ ]      | Barro UHD                          |
| KD-F3  | 3      | [ ]      | Bastidor cargado                   |
| KD-MOT | motor  | [ ]      | Repetir F1 tras cerrar FS-MOT-2100 |

---

## Comentarios

```text
```

---

*Última revisión: 2026-07-29 — Truck Encyclopedia + Referencia real.*
