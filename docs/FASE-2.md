# SnowRunner — Fase 2: Neumáticos CK1500 (juego vs real)

Continuación de Fase 1 (motor + chasis I6). El flujo `repack_pak.py` → `verify_pak.py` se reutiliza para el siguiente vehículo o para parches de ruedas.

**Objetivo Fase 2** (de `personal.txt`): investigar si conviene modificar neumáticos, documentar comportamiento en juego y en la vida real, y usar el simulador para comparar tendencias antes de tocar el `.pak`.

---

## Estado

| Tarea | Estado |
|-------|--------|
| Localizar XML de neumáticos Scout en `initial.pak` | Hecho |
| Documentación Saber (`WheelFriction`) | Hecho |
| Referencia real K10 ~1971 (medidas, barro) | Hecho |
| Validar simulador para decisiones de rueda | Hecho (con límites) |
| Parches XML de neumáticos en `.pak` | **Hecho** (CK1500 + MH9500) |
| Prueba en juego CK1500 | Parcial |
| Prueba en juego MH9500 | **En curso** |
| Validación CE F2 offroad | **Hecho** (CK1500) |
| Validación CE F2 highway | Pendiente |

---

## Dónde viven los neumáticos en el juego

### Parámetros Saber (`WheelFriction`)

Fuente: [WheelFriction — Saber Modding Docs](https://expeditions-guides.saber.games/truck_modding/tags_and_attributes_of_trucks/truckwheels/trucktires/trucktire/wheelfriction/)

| Atributo XML | En SnowRunner controla | Rango |
|--------------|------------------------|-------|
| `BodyFriction` | Tierra limpia, grava, objetos de colisión | 0.1 – 10 |
| `BodyFrictionAsphalt` | **Carretera / asfalto** | 0.1 – 10 |
| `SubstanceFriction` | **Barro, nieve, agua** (sustancias) | 0 – 10 |
| `IsIgnoreIce` | Cadenas: ignora hielo resbaladizo | bool |

### Archivos relevantes para CK1500

| Archivo en `.pak` | Rol |
|-------------------|-----|
| `[media]/_templates/trucks.xml` | Plantillas `ScoutHighway`, `ScoutOffroad`, etc. — **afecta a todos los Scout** |
| `[media]/classes/wheels/wheels_scout1.xml` | Ruedas stock CK1500 (`highway_1`, `highway_2`, `highway_3`) |
| `[media]/classes/trucks/chevrolet_ck1500.xml` | `DefaultTire="highway_1"`, `DefaultWheelType="wheels_scout1"` |
| `[media]/_dlc/.../wheels_scout_offroad.xml` | Neumáticos offroad de taller |
| `[media]/_dlc/.../wheels_scout_mudtires.xml` | Mudtires |
| `[media]/_dlc/.../wheels_scout_allterrain.xml` | All-terrain |
| `[media]/_dlc/.../wheels_scout_allterrain_chain.xml` | Cadenas (`IsIgnoreIce`) |

> **No modificar** con `7z u` sobre el `.pak` completo. Usar `repack_pak.py` (mismo método que Fase 1).

---

## Valores de fábrica (extraídos de `initial.pak.bak`)

### Plantillas Scout — `_templates/trucks.xml`

| Plantilla | BodyFriction | BodyFrictionAsphalt | SubstanceFriction | IsIgnoreIce |
|-----------|--------------|---------------------|-------------------|-------------|
| **ScoutHighway** | 0.8 | 2.0 | **0.2** | — |
| ScoutOffroad | 2.0 | 1.0 | 1.2 | — |
| ScoutAllterrain | 1.0 | 1.0 | 1.0 | — |
| ScoutMudtires | 3.0 | 0.5 | 1.6 | — |
| ScoutChains | 2.0 | 0.9 | 1.1 | **true** |

### Neumático por defecto CK1500 — `wheels_scout1.xml` → `highway_1`

Hereda `ScoutHighway` pero **sobrescribe**:

```xml
<WheelFriction _template="ScoutHighway" SubstanceFriction="0.4"/>
```

| Neumático | Overrides respecto a plantilla |
|-----------|-------------------------------|
| `highway_1` (default) | `SubstanceFriction="0.4"` |
| `highway_2` | `BodyFriction="1.0"` |
| `highway_3` | `BodyFrictionAsphalt="2.5"` |

El CK1500 sale con `highway_1`: en barro usa **0.4** de sustancia, no 0.2 de la plantilla base.

---

## Comportamiento real K10 (~1971)

Fuentes: [GM Heritage 1971 Truck PDF](https://www.gm.com/content/dam/company/no_search/heritage-archive-docs/vehicle-information-kits/chevrolet-trucks/1971-Chevrolet-Truck.pdf), foros [67-72chevytrucks.com](https://www.67-72chevytrucks.com), neumáticos época [STA Super Traxion](https://cokertire.com/tires/sta-super-traxion-g78-15.html).

| Aspecto | Real K10 4×4 |
|---------|----------------|
| Neumático stock | **7.00-15** bias-ply, perfil alto (~30") |
| Alternativa off-road época | **7.50-16** (Traxion / mud & snow), más flotación |
| Asfalto | Buen agarre con highway; ruido y vibración con bias-ply |
| Barro medio | Con stock: **lento pero no inmóvil** (~5–15 km/h con esfuerzo); mucho mejor con M&S o off-road |
| Barro profundo | Atascado sin neumático ancho / bloqueo / momentum |
| Hielo/nieve | Cadenas o neumático M&S; stock resbala |
| Histórico | Muchos propietarios cambiaban a 7.50-16 o radiales 235/85-16 para uso mixto |

**Conclusión real:** el K10 de serie no es un “mud tire”, pero **no queda a 0 km/h** en barro ligero como el highway del juego. En barro serio necesitas otro neumático — igual que en SnowRunner, pero el juego exagera la diferencia stock vs offroad.

---

## Simulador: ¿sirve para Fase 2?

### Qué replica bien (`simulador_ck1500.py`)

| Uso | Validez |
|-----|---------|
| **Orden relativo** highway &lt; offroad &lt; mudtires en barro | Alta |
| Diff lock, snorkel, hielo/cadenas, daño motor | Alta (calibrado v3) |
| Asfalto / 0-97 con motor I6 | Alta |
| Comparar **antes / después** del mismo parche | Media-alta |

### Límites importantes

1. **`MUD_RESIST_COEF`** en el simulador (p. ej. highway = 11.0) **no existe en el XML** — es un ajuste de la aproximación Havok/barro. Por eso subir solo `SubstanceFriction` en el sim no desbloquea el highway en barro (sigue 0 km/h a 30 s).
2. El dict `TIRES` del simulador debe coincidir con el XML que parchees. Para CK1500 default conviene `substance: 0.4` (highway_1), no 0.2 de la plantilla.
3. Valores absolutos en barro (km/h) hay que **confirmar en juego**; el sim orienta tendencias.

### Matriz actual sim I6 (km/h a 30 s) — `simulacion_resultados.json`

| Neumático | Asfalto | Barro | Nieve | Hielo | Agua poco |
|-----------|---------|-------|-------|-------|-----------|
| highway | 150 | **0** | 107 | 2.3 | 0 |
| offroad | 150 | 16 | 112 | 2.3 | 22 |
| mudtires | 150 | 36 | 112 | 2.3 | 38 |
| chains | 150 | 15 | 112 | **24.5** | 21 |

### Objetivo real vs sim (barro)

| Métrica | Real K10 (stock) | Sim I6 highway | Sim I6 offroad |
|---------|------------------|----------------|----------------|
| Barro ligero | 5–15 km/h | 0 km/h | 16–40 km/h |

El sim **coincide** con el diseño del juego (highway inútil en barro) más que con el K10 real en barro suave. Si quieres realismo histórico en barro con neumático de serie, hay que **modificar XML** (o aceptar cambio de neumático en taller).

---

## Decisión aplicada (Fase 2)

### Auditoría neumáticos USA compatibles con CK1500

| Set / tipo | ¿Cambio? | Motivo |
|------------|----------|--------|
| **wheels_scout1 → highway_1** (stock) | **Sí** — substance 0.4 → **0.5** | Único hueco vs K10 real en barro ligero |
| highway_2 / highway_3 | No | No son default; valores plantilla OK |
| wheels_scout2 (allterrain) | No | Sim OK (~13 km/h barro) |
| wheels_scout_offroad | No | Sim 16–40 km/h barro — en rango real |
| wheels_scout_mudtires | No | Sim 36 km/h barro — coherente |
| wheels_scout_allterrain / chains | No | Compromiso / hielo OK |

### Alcance del parche `wheels_scout1.xml`

`highway_1` lo comparten varios Scout USA (CK1500, Don 71, International Scout 800, Tuz 166, Khan Lo4f, Jeep CJ7 Renegade, Khan 317 Sentinel). **Aceptado:** mismo neumático stock = misma física en todos.

Offroad / mudtires del taller usan XML **compartidos** (`wheels_scout_offroad`, etc.); no se tocan porque el sim ya calibra bien.

### Parche en `repack_pak.py` (4.ª entrada ZIP)

```xml
<!-- wheels_scout1.xml — solo highway_1 -->
SubstanceFriction="0.4" → SubstanceFriction="0.5"
```

---

## ¿Modificar neumáticos? (opciones consideradas)

### A — No tocar XML (recomendado como baseline)

- Dejar física de fábrica.
- En juego: instalar **offroad** o **mudtires** para barro (como haría un propietario real).
- Fase 1 ya cubre motor + masa; el cuello de botella en barro es el neumático, no el I6.

### B — Parche suave solo CK1500 default (`wheels_scout1.xml`)

Solo `highway_1`, sin cambiar todos los Scout:

| Parámetro | Actual | Propuesta | Motivo |
|-----------|--------|-----------|--------|
| `SubstanceFriction` | 0.4 | **0.45 – 0.55** | Acercar a 5–10 km/h en barro ligero (probar en juego) |

**Riesgo:** bajo alcance (un neumático de un camión). **Simulador:** no predice el km/h exacto solo con `SubstanceFriction`; usar juego como verdad.

### C — Plantilla global `ScoutHighway` (`_templates/trucks.xml`)

| Parámetro | Actual | Propuesta |
|-----------|--------|-----------|
| `SubstanceFriction` | 0.2 | 0.35 – 0.4 |

**Riesgo:** afecta **todos** los vehículos Scout del juego. No recomendado para mod “solo CK1500 realista”.

### D — Cambiar neumático por defecto (`chevrolet_ck1500.xml`)

```xml
DefaultTire="…"  → neumático offroad del set compatible
```

**Efecto:** el camión ya no sale con highway; es una decisión de diseño, no de física fina. Históricamente discutible (el K10 venía con highway).

### E — Buff global estilo comunidad (Steam guides)

Duplicar `SubstanceFriction` en `trucks.xml` para todos los tipos.

**No recomendado** para este proyecto: rompe el equilibrio Saber y contradice el objetivo “creíble, no fácil”.

---

## Recomendación Fase 2

1. **Sincronizar simulador** con XML real (`highway` → `substance 0.4` para tests CK1500).
2. **Primer paso en juego** con mod Fase 1: probar barro con highway vs offroad vs mudtires **sin** parche de ruedas.
3. Si el highway en barro ligero sigue absurdo vs K10 real → aplicar **opción B** (solo `highway_1`) con incremento pequeño de `SubstanceFriction` (+0.1, probar, +0.1 más).
4. Reutilizar pipeline Fase 1:
   - Añadir entradas a `PATCHES` en `repack_pak.py`
   - `apply_ck1500_mod.py` → `verify_pak.py`
   - Ampliar `test_simulacion.py` con ranking de neumáticos (ya existe).

---

## Próximos pasos técnicos

```powershell
# Estudio comparativo global vs solo CK1500 (200 celdas, ~1.6 s)
python "c:\Users\doski\snowrunner real\simular_neumaticos.py"
python -m unittest test_simulacion_neumaticos -v

# Simulación / tests Fase 1
python "c:\Users\doski\snowrunner real\simulador_ck1500.py"
python -m unittest test_simulacion -v
```

### Estudio de parches (`test_simulacion_neumaticos.py`)

| Plan | Qué simula | CK1500 afectado | Scout genérico afectado |
|------|-----------|-----------------|-------------------------|
| `factory` | Sin cambios | — | — |
| `ck1500_only` | `highway_1` substance 0.4→0.5 | **5 celdas** (solo highway) | **0 celdas** |
| `global_template` | `ScoutHighway` 0.2→0.35 en plantilla | 0 (override 0.4 se mantiene) | **5 celdas** (highway) |
| `global_buff` | +20% substance todos los tipos | **20 celdas** | **25 celdas** |

Salida: `simulacion_neumaticos.json`

> En barro, highway puede seguir a **0 km/h** en el sim por `MUD_RESIST_COEF`; usar **delta_mu** y prueba en juego para calibrar XML.

```powershell
# PATCHES["[media]/classes/wheels/wheels_scout1.xml"] = [
#     ('SubstanceFriction="0.4"', 'SubstanceFriction="0.5"'),
# ]
python "c:\Users\doski\snowrunner real\apply_ck1500_mod.py"
python "c:\Users\doski\snowrunner real\verify_pak.py"
```

### Checklist Fase 2

- [x] Inventario XML neumáticos Scout + CK1500 default
- [x] Tabla fricción fábrica vs documentación Saber
- [x] Referencia histórica K10 (medida, barro, bias-ply)
- [x] Tests comparativos global vs solo CK1500 (`test_simulacion_neumaticos.py`)
- [x] Opciones de parche con riesgos
- [ ] Prueba en juego baseline (sin parche ruedas)
- [ ] Decidir A vs B según sensación en barro ligero
- [x] Parche highway_1 en `wheels_scout1.xml` (0.4 → 0.5)
- [ ] Actualizar canvas / FASE-1 con resultados

---

## Validación con telemetría (Fases 5–6)

| | |
|--|--|
| **Protocolos** | `f2_barro_highway`, `f2_barro_offroad` (mismo tramo) |
| **Parámetros diseño (XML/sim)** | `SubstanceFriction`, `BodyFrictionAsphalt` — no requieren CE |
| **CE / HUD mide** | `speed_kmh`: highway ≈ 0 vs offroad > 0 en barro |
| **Estado CE** | Offroad grabado (`ce_f2_barro_offroad_*`); **highway pendiente** |
| **Futuro CE** | `vel_y` (hundimiento leve); importar `vel_x/z` al JSON |
| **Criterio** | Si highway avanza igual que offroad → neumático demasiado fácil |

```powershell
python importar_ce_csv.py --protocol f2_barro_highway --compare
python importar_ce_csv.py --protocol f2_barro_offroad --compare
```

Ver **`FASE-6.md`**.

---

## Reutilización para el siguiente vehículo

| De Fase 1 | Para Fase 2 / otro camión |
|-----------|---------------------------|
| `repack_pak.py` | Añadir rutas XML a `PATCHES` |
| `verify_pak.py` | Automático desde `PATCHES` |
| `simulador_ck1500.py` | Copiar `TIRES` + escenarios; cambiar masa/motor |
| `test_simulacion.py` | Mismos tests de ranking y calibración |
| `FASE-1.md` / este doc | Plantilla de análisis |

---

## MH9500 (segundo vehículo — Fase 2)

| Campo | Valor |
|-------|-------|
| XML ruedas | `[media]/classes/wheels/wheels_medium_double.xml` |
| Neumático stock | `highway_1` (plantilla `Highway`) |
| Parche | `SubstanceFriction` 0.4 → **0.5** (mismo criterio que CK1500) |
| Sim | `simulador_mh9500.py` — `TIRES["highway"]` |
| Doc completa | **`camiones/mh9500/FASES.md`** § Fase 2 |

**Importante:** `wheels_medium_double.xml` es **compartido** con otros camiones medium double del juego.

En juego: el MH9500 stock es **RWD**; en barro con highway espera atasco. Offroad + AWD + diff lock es upgrade — no stock.

---

*Documento Fase 2 — Neumáticos CK1500 · SnowRunner realismo histórico.*
