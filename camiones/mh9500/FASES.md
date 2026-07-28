# SnowRunner — GMC MH9500 (mod realista)

Metodología: `docs/METODO-PAK.md`, `docs/FASE-1.md` … `docs/FASE-4.md`.

| Campo          | Valor                          |
| -------------- | ------------------------------ |
| ID mod         | `mh9500`                       |
| ID juego       | `gmc_9500`                     |
| Tipo           | Highway 6×4 Class 8            |
| Masa vacía mod | **8200 kg**                    |
| Parches        | `camiones/mh9500/patches.py`   |
| Simulador      | `camiones/mh9500/simulador.py` |

---

## Setup en juego (referencia)

| Pieza      | En juego                                    |
| ---------- | ------------------------------------------- |
| Motor      | stock diesel                                |
| Neumáticos | highway RWD stock / **offroad** en taller   |
| Tracción   | RWD stock; **AWD + diff** para barro (F2)   |
| Carga F3   | Semirremolque barro                         |

---

## Referencia real

### Prototipo

GMC **MH9500** — Class 8 **6×4** highway (familia GMC 9500 / Brigadier). RWD stock; offroad + AWD
en taller para barro.

### Truck Encyclopedia

Sin artículo al **MH9500**. Contexto en
[Cold War US trucks](https://truck-encyclopedia.com/coldwar/us/coldwar-us-trucks.php) — reemplazo
**M35** / GMC **CCKW**; serie GMC **9500** (**1967–1978**) predecesora del **Brigadier**.

| GMC 9500 / MH (histórico) | Valor                         |
| ------------------------- | ----------------------------- |
| Clase                     | Class **7–8**                 |
| MH9500                    | tandem, capó largo, **8V-71** |
| Depósito juego            | 240 L                         |

Mod **8200 kg** RWD: barro atascado sin offroad+AWD.

### Ficha comunidad (SR!NFO)

| Campo            | Valor              |
| ---------------- | ------------------ |
| Masa vacía       | **8438 kg**        |
| Torque stock/max | 140k / 145k Ncm    |
| Depósito         | 240 L              |
| Tracción         | 6×6, Switchable    |

### XML stock vs mod

| Parámetro | Catálogo                      | Mod         |
| --------- | ----------------------------- | ----------- |
| Masa      | ~7512 kg                      | **8200 kg** |
| CoG       | parcheado Y −0.2 en un cuerpo | más bajo    |

Comportamiento esperado: highway en barro **atascado**; offroad + AWD **crawl**; semi cargado casi
inmóvil.

```powershell
```

---

## Qué esperar del mod

| Situación                  | Comportamiento esperado   |
| -------------------------- | ------------------------- |
| Barro highway RWD          | Atasco o ~0 km/h          |
| Barro offroad + AWD + diff | Avance lento              |
| Semi ~12 t en barro        | Prácticamente inmóvil     |

Fases 1–4: XML + sim aplicados. Validación = **prueba en juego**.

---

## Fases de prueba (en juego)

### F1 — Asfalto

| Condición  | Valor              |
| ---------- | ------------------ |
| Carga      | Vacío              |
| Conducción | WOT, marcha alta   |

### F2 — Barro offroad

| Condición  | Valor                         |
| ---------- | ----------------------------- |
| Neumático  | offroad (no highway)          |
| AWD + diff | ON                            |
| Conducción | Marcha L                      |

**Cierre:** avance lento pero posible vs highway atascado.

### F3 — Semi cargado

| Condición | Valor              |
| --------- | ------------------ |
| Carga     | Semi barro         |
| Resto     | Igual que F2       |

---

## Aplicar y validar

```powershell
```

---

## Pendiente

| ID    | Fase   | Estado   | Notas                    |
| ----- | ------ | -------- | ------------------------ |
| MH-F1 | 1      | [ ]      | Asfalto vacío            |
| MH-F2 | 2      | [ ]      | Barro offroad + AWD      |
| MH-F3 | 3      | [ ]      | Semi cargado barro       |

---

## Comentarios

```text
```

---

*Última revisión: 2026-07-29 — Truck Encyclopedia + Referencia real.*
