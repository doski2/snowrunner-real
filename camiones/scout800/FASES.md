# SnowRunner — International Scout 800 (mod realista)

Metodología: `docs/METODO-PAK.md`, `docs/FASE-1.md` … `docs/FASE-4.md`.

| Campo          | Valor                            |
| -------------- | -------------------------------- |
| ID mod         | `scout800`                       |
| ID juego       | `international_scout_800`        |
| Tipo           | Scout 4×4                        |
| Masa vacía mod | **2100 kg** *(objetivo)*         |
| Parches        | `camiones/scout800/patches.py`   |
| Simulador      | `camiones/scout800/simulador.py` |

---

## Setup en juego (referencia)

| Pieza      | En juego           | XML / socket                                   |
| ---------- | ------------------ | ---------------------------------------------- |
| Motor      | **AAT-6V 4.0**     | `us_scout_old_engine_0` (`e_us_scout_old.xml`) |
| Neumáticos | **33" HS I**       | `wheels_scout_highway` / JAT HS I              |
| Diff       | **Always**         | `DiffLockType="Always"` en truck               |
| Caja       | stock              | `g_scout_default`                              |

**No reutilizar sesiones CK1500:** otra masa, otro motor, diff distinto.

**Pendiente XML:** motor AAT-6V y neumático HS I en barro — calibrar tras F1/F2 en juego.

---

## Referencia real

### Prototipo

**International Scout 800** — SUV Scout **4×4** ~1965–1971 (IH segunda generación). Motor
**AAT-6V**,
neumático **33" HS I**, diff **Always** = taller juego.

### Truck Encyclopedia

Sin artículo al **Scout 800** (civil). Scout de referencia en TE:
[Willys CJ](https://truck-encyclopedia.com/coldwar/us/willys-cj.php) — rival Jeep del Scout IH.

| Scout 800 (histórico) | Valor típico               |
| --------------------- | -------------------------- |
| Producción            | **1965–1971** (800A/B)     |
| Motores               | 152 I4 → 232 I6 → 266 V8   |
| Masa                  | ~**1800–2200 kg**          |
| Tracción              | 4×4                        |

Mod objetivo **2100 kg** — bajar desde ~2812 kg catálogo hacia Scout real.

### Ficha comunidad (SR!NFO)

| Campo            | Valor            |
| ---------------- | ---------------- |
| Masa vacía       | **3143 kg**      |
| Torque stock/max | 35k / 50k Ncm    |
| Depósito         | 72 L             |
| Tracción         | 4×4, diff Always |

### XML stock vs mod (objetivo)

| Parámetro | Catálogo | Mod / objetivo                |
| --------- | -------- | ----------------------------- |
| Masa      | ~2812 kg | **2100 kg** objetivo registry |
| Chasis    | 1900+900 | **1600+750** (parcheado)      |

Motor AAT-6V en `e_us_scout_old.xml` (compartido scouts US; motor CK1500 dedicado en otro XML).

```powershell
```

---

## Qué hace el mod (stock → realista)

| Parámetro          | Stock | Mod (actual)     | Fase   |
| ------------------ | ----- | ---------------- | ------ |
| Masa chasis        | 1900  | **1600**         | 1 / 3  |
| Masa bastidor      | 900   | **600**          | 1 / 3  |
| AAT-6V `Torque`    | 35000 | **32000**        | 1      |
| `MaxDeltaAngVel`   | 0.01  | **0.012**        | 1      |

**Compartido:** `e_us_scout_old.xml` afecta otros scouts US (no el motor CK1500 dedicado). HS I en
`wheels_scout_highway.xml` pendiente.

---

## Fases de prueba (en juego)

### F1 — Asfalto

| Condición  | Valor                         |
| ---------- | ----------------------------- |
| Motor      | AAT-6V 4.0                    |
| Neumático  | 33" HS I                      |
| Carga      | Vacío                         |
| Conducción | WOT, marcha alta, ~60 s recto |

**Cierre:** aceleración realista vs stock.

### F2 — Barro HS I

| Condición  | Valor                    |
| ---------- | ------------------------ |
| Mapa       | Barro Michigan           |
| Diff       | ON (Always)              |
| Conducción | Marcha L, gas sostenido  |

**Cierre:** crawl coherente. Ajustar `S8_MUD_*` y/o `SubstanceFriction` en `patches.py`.

### F3 — Carga

| Condición | Valor                    |
| --------- | ------------------------ |
| Carga     | Remolque scout + vigas   |
| Resto     | Igual que F2             |

---

## Aplicar y validar

```powershell
```

---

## Pendiente

| ID    | Fase   | Estado   | Notas                              |
| ----- | ------ | -------- | ---------------------------------- |
| S8-F1 | 1      | [ ]      | Asfalto WOT                        |
| S8-F2 | 2      | [ ]      | Barro HS I — parche neumático      |
| S8-F3 | 3      | [ ]      | Remolque + vigas                   |

**Nota:** motor compartido aplicado; probar en juego con AAT-6V instalado.

---

## Comentarios

```text
```

---

*Última revisión: 2026-07-29 — Truck Encyclopedia + Referencia real.*
