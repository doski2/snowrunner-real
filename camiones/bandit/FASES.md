# SnowRunner — KRS 58 Bandit (mod realista)

Documento de referencia del vehículo activo. Metodología general: `docs/METODO-PAK.md`,
`docs/FASE-1.md` … `docs/FASE-4.md`.

| Campo          | Valor                          |
| -------------- | ------------------------------ |
| ID mod         | `bandit`                       |
| ID juego       | `krs_58_bandit`                |
| DLC            | `dlc_2_2`                      |
| Tipo           | OFFROAD 8×8                    |
| Masa vacía mod | **7600 kg**                    |
| Parches        | `camiones/bandit/patches.py`   |
| Simulador      | `camiones/bandit/simulador.py` |

---

## Setup en juego (referencia)

| Pieza      | En juego              | XML / socket                                    |
| ---------- | --------------------- | ----------------------------------------------- |
| Motor      | **LAZ 6 T60**         | `ru_truck_old_engine_0` en `e_ru_truck_old.xml` |
| Neumáticos | **51" UHD I**         | `highway_1` en `wheels_medium_double_front.xml` |
| Tracción   | 8×8 + diff **Always** | stock OFFROAD (`diff_lock_type: Always`)        |
| Caja       | stock                 | `g_truck_default`                               |
| Suspensión | stock                 | `krs_58_bandit_suspension_default`              |
| Carga F3   | Bastidor barro lleno  | escenario sim `frame_cargado` (+5050 kg)        |

**Motores alternativos** (mismo XML compartido, parcheados en bloque):

| Motor en taller   | XML `Name`              | Torque stock → mod (Ncm)   |
| ----------------- | ----------------------- | -------------------------- |
| LAZ 6 T60         | `ru_truck_old_engine_0` | 130000 → **88500**         |
| LAZ 6 T195        | `ru_truck_old_engine_1` | 140000 → **95300**         |
| IMZ-6 210         | `ru_truck_old_engine_2` | 160000 → **108900**        |
| LAZ 6 TA240       | `ru_truck_old_engine_3` | 185000 → **125900**        |

`e_ru_truck_old.xml` lo comparten Bandit, Actaeon, ZiKZ 566A y otros. Cualquier cambio de motor
afecta a todos.

---

## Referencia real

### Prototipo

KRS-58 **Bandit** en el juego: grúa/recovery **8×8** de Yukon (DLC). **No existe** el Bandit real;
inspiración soviética (KrAZ, grúas KRS). En [Truck Encyclopedia](https://truck-encyclopedia.com/) la
referencia cercana es la familia **KrAZ** off-road pesada.

Motores **LAZ** en taller = nombres de juego, no fábrica.

### Ficha histórica ([Truck Encyclopedia — KrAZ-6322](https://truck-encyclopedia.com/modern/ukraine/KrAZ-6322.php))

Documentado en TE: antecesor **KrAZ-260** / **KrAZ-255B** (serie desde **1981**), diseño basado en
Berliet GBC 8KT; inflado central, bloqueos de diff. El **6322** sustituye al 260 desde **1994**.

| Campo            | Valor KrAZ-6322 (TE)         |
| ---------------- | ---------------------------- |
| Masa vacía       | **11,3–12,7 t**              |
| Dimensiones      | 8980 × 2500 × 3030 mm        |
| Motor            | YaMZ V8 ~**330 hp**          |
| Torque           | ~**1233 Nm** (1200–1400 rpm) |
| Vel. máx.        | **75 km/h**                  |
| Depósito         | **550 L** (~800 km)          |
| Carga / tropas   | hasta **20 t** / 20–28 pax   |

Bandit juego es **8×8** y más ligero (~7 t vacío mod); la KrAZ TE es 6×6 logística — misma
filosofía off-road, distinta configuración.

### Ficha comunidad ([SR!NFO — Trucks](https://docs.google.com/spreadsheets/d/1TPla-u2zxpzFMhpxzymhwzxDU_x85Y_1SxylgRPonH0/edit))

| Campo            | Valor SR!NFO                 |
| ---------------- | ---------------------------- |
| Masa vacía       | **7861 kg**                  |
| Torque stock/max | 130 000 / 185 000 Ncm        |
| Depósito         | 150 L                        |
| Tracción         | 8×8, AWD Always, diff Always |

Local: `datos/comunidad/srinfo_trucks.json` → `krs_58_bandit`.

### XML stock (`datos/catalogo/trucks.json`)

| Campo            | Valor catálogo          |
| ---------------- | ----------------------- |
| Masa cuerpos     | **7014 kg**             |
| `Responsiveness` | 0.55                    |
| Motor default    | `ru_truck_old_engine_0` |

### Objetivo del mod vs referencia

| Parámetro        | Stock juego | Mod               | Criterio                                  |
| ---------------- | ----------- | ----------------- | ----------------------------------------- |
| Masa             | ~7014 kg    | **7600 kg**       | Cerca de SR!NFO pero sin inflar al arcade |
| LAZ 6 T60 torque | 130 000     | **88500** (~68 %) | Nerfeo diesel, no cohete                  |
| UHD barro        | 0.4         | **0.5**           | Crawl en barro sin highway imposible      |

No hay PDF de fábrica del Bandit en el repo; validación = coherencia SR!NFO + sim + prueba F1–F3.

```powershell
```

---

## Qué hace el mod (stock → realista)

| Parámetro                       | Stock      | Mod                | Fase   |
| ------------------------------- | ---------- | ------------------ | ------ |
| Masa chasis (cuerpos 4000+3000) | 7014 kg    | **7600 kg** (+206) | 1 / 3  |
| Depósito                        | 150 L      | **135 L**          | 1      |
| LAZ 6 T60 `Torque`              | 130000 Ncm | **88500 Ncm**      | 1      |
| LAZ 6 T60 `FuelConsumption`     | 4.5        | **3.1**            | 1      |
| UHD I `SubstanceFriction`       | 0.4        | **0.5**            | 2 / 4  |

**No se toca:** `Responsiveness` / `SteerSpeed` (volante, Saber §8), suspensión, caja, diff lock,
geometría de ruedas, remolques globales.

**Compartido con otros camiones:** `e_ru_truck_old.xml` (motores), `wheels_medium_double_front.xml`
(51" UHD en varios 8×8).

---

## Archivos XML parcheados

| Archivo en `initial.pak`                                | Cambios                                                                                          |
| ------------------------------------------------------- | ------------------------------------------------------------------------------------------------ |
| `[media]/_dlc/dlc_2_2/classes/trucks/krs_58_bandit.xml` | Masa, `FuelCapacity`                                                                             |
| `[media]/classes/engines/e_ru_truck_old.xml`            | Plantilla `RUTruckOldEngine` → `EngineResponsiveness="0.028"`; torque y consumo de los 4 motores |
| `[media]/classes/wheels/wheels_medium_double_front.xml` | `highway_1` → `SubstanceFriction="0.5"`                                                          |

---

## Fases de prueba (en juego)

Misma ruta en cada fase; anotar sensación y km/h del HUD. El sim orienta tendencias; la prueba final
es en mapa.

### F1 — Asfalto (`bandit_f1_asfalto`)

| Condición   | Valor                                      |
| ----------- | ------------------------------------------ |
| Mapa        | Carretera recta (Michigan, Black River, …) |
| Motor       | LAZ 6 T60                                  |
| Neumático   | 51" UHD I                                  |
| Diff        | ON (Always)                                |
| Carga       | Vacío (7600 kg)                            |
| Conducción  | WOT, marcha alta, ~60 s recto              |

**Cierre:** aceleración contenida vs stock; no “cohete” en recta.

### F2 — Barro UHD (`bandit_f2_barro_uhd`) ← **siguiente paso**

| Condición   | Valor                                            |
| ----------- | ------------------------------------------------ |
| Mapa        | Barro Michigan o North Port                      |
| Neumático   | 51" UHD I (highway en barro = diseño deliberado) |
| Diff        | ON                                               |
| Carga       | Vacío                                            |
| Conducción  | Marcha **L**, gas sostenido 30–60 s              |

**Cierre:** crawl lento pero avanza; no queda clavado al primer metro. Si demasiado lento o
demasiado rápido → ajustar `BANDIT_MUD_*` en sim y/o `SubstanceFriction` en `patches.py`.

### F3 — Bastidor cargado (`bandit_f3_carga`)

| Condición   | Valor                                              |
| ----------- | -------------------------------------------------- |
| Carga       | Bastidor del Bandit lleno en barro                 |
| Sim         | No modelado — validar solo en juego (~12 t total)  |
| Resto       | Igual que F2                                       |

**Cierre:** casi inmóvil o avance muy lento; coherente con peso total ~12 t.

---

## Referencia simulador

Salida de `python -m camiones.bandit.simulador` (LAZ 6 T60 mod, UHD I, diff AWD 8×8):

| Escenario      | Métrica    | Valor sim        |
| -------------- | ---------- | ---------------- |
| F1 asfalto WOT | 0–97 km/h  | ~42 s            |
| F1 asfalto WOT | v a 60 s   | ~128 km/h        |
| F2 barro L     | v30 / vmax | ~1.7 / ~2.0 km/h |

F3 (bastidor cargado): solo prueba en juego.

Constantes barro en sim: `BANDIT_MUD_IMMERSION_RATE = 0.52`, `BANDIT_MUD_RESIST_MULT = 1.12`.

---

## Aplicar y validar

```powershell
```

| Paso            | Qué comprueba                                 |
| --------------- | --------------------------------------------- |
| `verify_pak.py` | Valores XML dentro del `.pak`                 |
| `simulador`     | Tendencias F1/F2 (vacío)                      |
| Prueba en juego | Sensación + km/h HUD (F3 carga solo en juego) |

---

## Pendiente

| ID    | Fase   | Estado   | Notas                          |
| ----- | ------ | -------- | ------------------------------ |
| BD-F1 | 1      | [ ]      | Asfalto WOT — validar en juego |
| BD-F2 | 2      | [ ]      | Barro marcha baja — **activo** |
| BD-F3 | 3      | [ ]      | Bastidor cargado barro         |

---

## Comentarios

```text
```

---

*Última revisión: 2026-07-29 — Truck Encyclopedia + Referencia real.*
