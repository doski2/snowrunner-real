# SnowRunner — International Fleetstar F2070A (mod realista)

Metodología: `docs/METODO-PAK.md`, `docs/FASE-1.md` … `docs/FASE-4.md`.

| Campo          | Valor                             |
| -------------- | --------------------------------- |
| ID mod         | `fleetstar`                       |
| ID juego       | `international_fleetstar_f2070a`  |
| Tipo           | HEAVY 6×4                         |
| Masa vacía mod | **7400 kg**                       |
| Parches        | `camiones/fleetstar/patches.py`   |
| Simulador      | `camiones/fleetstar/simulador.py` |

---

## Setup en juego (referencia)

| Pieza      | En juego              |
| ---------- | --------------------- |
| Motor      | **Si-6V/1900**        |
| Neumáticos | **42" UHD I**         |
| Tracción   | **AWD** + diff lock   |
| Suspensión | stock                 |

**Motores alternativos** (mismo XML `e_us_truck_old.xml`):

| Motor       | XML                     | Torque stock → mod (Ncm) |
| ----------- | ----------------------- | ------------------------ |
| Si-6V/1900  | `us_truck_old_engine_0` | 135000 → **92000**       |
| Si-6V/2100T | `us_truck_old_engine_1` | 145000 → **99000**       |

Parche compartido afecta otros camiones con socket `e_us_truck_old` (p. ej. White Western 4964).
Solo chasis Fleetstar: `python apply_mod.py --vehicle fleetstar`.

---

## Referencia real

### Prototipo

**International Fleetstar F2070A** — camión **6×4** civil IH/Navistar (1960s–1970s), entre Loadstar
y Paystar. Motor juego **Si-6V** = `e_us_truck_old.xml`.

### Truck Encyclopedia

Sin artículo al **Fleetstar**. Fabricante en
[US trucks WW2](https://truck-encyclopedia.com/ww2/us/us-trucks.php) (**International Harvester**)
y [Cold War US](https://truck-encyclopedia.com/coldwar/us/coldwar-us-trucks.php).

| Campo (F2070 civil) | Referencia histórica        |
| ------------------- | --------------------------- |
| Masa vacía          | ~**8200 kg** (18 000 lb)    |
| GVWR máx.           | hasta ~**27 630 kg**        |
| Motor típico        | Cummins **NTC-335**, 13 spd |
| Configuración       | 6×4 tandem, cabina D        |

Mod **7400 kg** vacío: por debajo del vacío civil (juego arcade).

### Ficha comunidad (SR!NFO)

| Campo            | Valor                    |
| ---------------- | ------------------------ |
| Masa vacía       | **7674 kg**              |
| Torque stock/max | 135k / 155k Ncm          |
| Depósito         | 240 L                    |
| Tracción         | 6×6, AWD/diff Switchable |

### XML stock vs mod

| Parámetro        | Catálogo                       | Mod                 |
| ---------------- | ------------------------------ | ------------------- |
| Masa             | ~6658 kg                       | **7400 kg**         |
| Si-6V/1900       | 135k Ncm                       | **92k Ncm**         |
| `Responsiveness` | 0.1 (volante; **no parchear**) |                     |

Torque mod ≈ **68 %** del stock (misma ratio que otros Si-6V del proyecto).

```powershell
```

---

## Qué hace el mod (stock → realista)

| Parámetro             | Stock   | Mod         | Fase   |
| --------------------- | ------- | ----------- | ------ |
| Masa total            | 6300 kg | **7400 kg** | 1 / 3  |
| Combustible           | 240 L   | **210 L**   | 1      |
| Si-6V/1900 torque     | 135000  | **92000**   | 1      |
| `highway_1` Substance | 0.4     | **0.5**     | 2 / 4  |

---

## Fases de prueba (en juego)

### F1 — Asfalto

| Condición  | Valor                         |
| ---------- | ----------------------------- |
| Motor      | Si-6V/1900 (o 2100T a probar) |
| Neumático  | 42" UHD I                     |
| AWD + diff | ON                            |
| Conducción | WOT, marcha alta, ~60 s       |

**Cierre:** aceleración diesel contenida; comparar 1900 vs 2100T en mismo tramo.

### F2 — Barro UHD

| Condición  | Valor                    |
| ---------- | ------------------------ |
| Mapa       | Barro Michigan           |
| Conducción | Marcha L, diff ON        |

**Cierre:** crawl ~2–3 km/h. Ajustar `FS_MUD_*` y/o `SubstanceFriction`.

### F3 — Bastidor cargado

| Condición | Valor              |
| --------- | ------------------ |
| Carga     | Bastidor lleno     |
| Resto     | Igual que F2       |

---

## Referencia simulador

```powershell
```

| Escenario        | Esperado (sim)      |
| ---------------- | ------------------- |
| Asfalto AWD      | ~0–97 en ~38 s      |
| Barro UHD + diff | crawl ~2–3 km/h     |
| Cargado 6 t      | más lento que vacío |

---

## Aplicar y validar

```powershell
```

---

## Pendiente

| ID          | Fase   | Estado   | Notas                          |
| ----------- | ------ | -------- | ------------------------------ |
| FS-F1       | 1      | [ ]      | Asfalto WOT Si-6V/1900         |
| FS-MOT-2100 | motor  | [ ]      | 2100T mismo tramo              |
| FS-F2       | 2      | [ ]      | Barro UHD marcha L             |
| FS-F3       | 3      | [ ]      | Bastidor lleno barro           |

---

## Comentarios

```text
```

---

*Última revisión: 2026-07-29 — Truck Encyclopedia + Referencia real.*
