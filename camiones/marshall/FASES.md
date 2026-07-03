# SnowRunner — KHAN 39 Marshall (mod realista)

Metodología general: `docs/FASE-1.md` … `docs/FASE-8.md`.

---

## Tu setup actual

| Pieza | En juego | XML |
|-------|----------|-----|
| Motor | **Kr 104** | `ru_scout_old_engine_0` |
| Suspensión | **Reptadora** (Rock Crawler) | `khan_39_marshall_suspension_crawler` |
| Neumáticos | **45" TM II** | `mudtires_2` / `wheels_scout_yar_871` |
| Caja (prevista) | **SnowRunner** | `g_scout_offroad` en `gearboxes_scouts.xml` |
| Tracción | AWD siempre + diff lock | stock |

---

## Qué hace el mod

| Parámetro | Stock | Mod |
|-----------|-------|-----|
| Masa total | 1500 kg | **1780 kg** |
| `Responsiveness` | 0.6 | **0.04** |
| TM II `SubstanceFriction` | 2.4 | **1.7** |
| TM I `BodyFriction` | 2.4 | **2.0** |
| Kr 104 | sin cambio | MaxDelta 0.01 ya OK |

**No se toca:** suspensión reptadora (taller), motor compartido `e_ru_scout_old.xml` (afecta Lo4F / Gor BY-4).

**Compartido:** `wheels_scout_yar_871.xml` también lo usan **Yar 87** y **Chevy Apache**.

**Caja SnowRunner:** el mod **no parchea** `gearboxes_scouts.xml`. Instálala en taller; no hace falta repack.

| Caja | XML | Uso recomendado |
|------|-----|-----------------|
| Stock (default) | `g_scout_default` | 5 marchas auto; solo L |
| **SnowRunner** | `g_scout_offroad` | Barro/charcos: **L, L+, L−, H**; menos vmax |
| Freeway | `g_scout_highway` | Carretera; no para tu setup |
| Fine-tune | `g_scout_finetune` | L manual fino; más consumo AWD |

En barro profundo: **L o L+**, diff ON, no pares. En asfalto: auto o **H** (máx ~16 angVel vs 20 stock).

---

## Aplicar

```powershell
python apply_mod.py --vehicle marshall
python verify_pak.py
python -m camiones.marshall.simulador
python -m unittest camiones.marshall.test -v
```

Copiar `initial.pak` → `...\SnowRunner\preload\paks\client\`

---

## Telemetría

| Fase | Protocolo | Notas |
|------|-----------|-------|
| F1 | `km_f1_asfalto` | Kr 104 + TM II + diff |
| F2 | `km_f2_barro_tm2` | Mismo tramo barro, marcha baja |
| F2b | `km_f2_barro_profundo` | Barro tint oscuro / extrusion |
| F3 | `km_f3_carga` | Remolque scout + carga |

```powershell
python grabar_ce.py --probe
grabar_telemetria.bat
python importar_ce_csv.py --auto --compare
```

CE ID: `s_khan_39_marshall` · Masa vacía mod: **1780 kg**

---

## Pendiente

- [ ] Grabar baseline `km_f2_barro_tm2` con reptadora
- [ ] Calibrar `KM_MUD_*` en sim si MAE &gt; 15 km/h
- [ ] Validar carga Havok (`scan_cargo.py`)
