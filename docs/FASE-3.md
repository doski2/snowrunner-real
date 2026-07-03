# SnowRunner — Fase 3: Peso, carga y remolque CK1500

Continuación de Fase 1 (motor + chasis I6) y Fase 2 (neumáticos highway). El simulador ahora modela **masa adicional** (addons, carga, remolque) para comparar vacío vs cargado antes de tocar más XML.

**Objetivo Fase 3** (de `personal.txt`): revisar peso del vehículo y de las cargas, entender el comportamiento con carga y simular tendencias.

---

## Estado

| Tarea | Estado |
|-------|--------|
| Inventario masa chasis / addons / remolque / cargo en `.pak` | Hecho |
| Referencia payload real K10 ~1971 | Hecho |
| Extender `simulador_ck1500.py` con carga y remolque | Hecho |
| `test_simulacion_carga.py` + `simular_carga.py` | Hecho |
| Parches XML de masas de carga | **No** (solo sim + doc) |
| Prueba en juego CK1500 con remolque | Parcial |
| Escenarios semi MH9500 en sim | **Hecho** (`semi_vacio`, `semi_cargado`) |
| Prueba en juego MH9500 con semi | **En curso** |
| Validación CE carga | Pipeline listo — `payload_kg`, `--auto` protocolo cargado |

---

## Masa del CK1500 en el juego

### Chasis (ya parcheado Fase 1)

| Componente | Fábrica | Mod I6 | Archivo |
|------------|---------|--------|---------|
| Chasis delantero | 1150 kg | **900 kg** | `chevrolet_ck1500.xml` |
| Chasis trasero | 1050 kg | **850 kg** | `chevrolet_ck1500.xml` |
| **Total seco** | **2200 kg** | **1750 kg** | — |
| Combustible | 80 L | 76 L | mismo XML |
| CoG Y | -0.15 | **-0.20** | mismo XML |

El CK1500 **no tiene slots de carga en la caja** en el XML base; transporta mercancía con **remolque scout** o addons de utilidad (no carga de misión en el techo).

### Addons con masa (tuning)

| Addon | Masa XML | Notas |
|-------|----------|-------|
| `rooftop_trunk` | 200 kg | Portaequipajes + combustible/repuestos extra |
| `rooftop_trunk_2` | 100 kg | Variante ligera |
| `trunk_stuff` | 60 kg | Decoración maletero |
| `trunk_stuff_2` | 150 kg | Decoración maletero |
| `snorkel_1` / `snorkel_2` | ~20 kg | Snorkel |

Escenario típico sim: **220 kg** (portaequipajes 200 + snorkel 20).

### Remolques scout compatibles

| Remolque | Masa chasis | Uso |
|----------|-------------|-----|
| `scout_trailer_offroad_cargo` | **800 kg** | Caja offroad (misiones) |
| `scout_trailer_flatbed_1/2` | 800 kg | Plataforma |
| `scout_trailer_offroad` / `tent` | 600 kg | Sin carga |
| `scout_trailer_oiltank` | 2500 kg | Cisterna (pesado) |

La masa de la **mercancía** no está en el XML del remolque: cada unidad es un `TruckAddon` en `[media]/classes/trucks/cargo/cargo_*.xml` con `<Body Mass="…">` y `CargoLength` (slots).

---

## Catálogo de carga Scout (extraído de `initial.pak.bak`)

| Carga | Slots | Masa | kg/slot |
|-------|-------|------|---------|
| Tablones madera | 1 | 500 kg | 500 |
| Ladrillos | 1 | 1000 kg | 1000 |
| Rollo metal | 1 | 1000 kg | 1000 |
| Repuestos | 1 | 1200 kg | 1200 |
| Bloques hormigón | 1 | 3000 kg | 3000 |
| Vigas metal | 2 | 2500 kg | 1250 |
| Tuberías medianas | 2 | 2250 kg | 1125 |
| Contenedor pequeño | 2 | 1500 kg | 750 |
| Losas hormigón | 2 | 3000 kg | 1500 |

Ejemplo misión habitual: remolque 800 kg + vigas metal 2500 kg → **5050 kg** remolque+carga, más **1750 kg** camión = **~6800 kg** total (con addons ~7020 kg).

---

## Referencia real — Chevrolet K10 4×4 ~1971

| Aspecto | Real | Juego (mod I6) |
|---------|------|----------------|
| Peso en vacío | ~1750–1860 kg (3850–4100 lb) | **1750 kg** ✓ |
| Payload útil (caja) | ~750–1000 kg (1650–2200 lb) | 1 slot ≈ 1000–1200 kg en remolque |
| Remolque ligero época | 500–1500 kg + carga moderada | Remolque 800 kg + hasta 2500 kg carga |
| Comportamiento cargado | Más lento, más hundimiento en barro, más inercia al soltar gas | Igual en sim (masa total en física) |

**Conclusión:** el chasis vacío del mod es realista. Las **misiones con remolque lleno** exceden con creces el payload histórico del K10 — es diseño de juego (Scout como furgoneta de contratos), no error del mod.

---

## Simulador Fase 3

### Nuevos campos en `VehicleConfig`

| Campo | Descripción |
|-------|-------------|
| `mass_kg` | Chasis seco (1750 mod) |
| `addon_mass_kg` | Portaequipajes, snorkel, etc. |
| `cargo_mass_kg` | Carga sobre el camión (0 en CK1500 típico) |
| `trailer_mass_kg` | Chasis remolque vacío |
| `trailer_cargo_mass_kg` | Mercancía en remolque |

`total_mass_kg()` suma todo. La función `step()` usa esa masa en:

- Fuerza normal → límite de tracción
- Resistencia a la rodadura y pendiente
- Hundimiento en barro (`sink`, `MUD_RESIST_COEF`)
- Aceleración `F = ma`

Remolque sin tracción: coeficientes extra `TRAILER_ROLL_COEF` y `TRAILER_HITCH_DRAG` (arrastre del enganche).

### Escenarios precargados (`LOAD_SCENARIOS`)

| ID | Descripción | Masa total aprox. |
|----|-------------|-------------------|
| `vacio` | Solo chasis mod | 1750 kg |
| `addons` | + portaequipajes y snorkel | 1970 kg |
| `trailer_vacio` | + remolque scout vacío | 2550 kg |
| `trailer_bricks` | + ladrillos 1 slot | 3550 kg |
| `trailer_spare_parts` | + repuestos 1 slot | 3750 kg |
| `trailer_metal_planks` | + vigas 2 slots | 5050 kg |
| `mision_pesada` | addons + remolque + vigas | 5270 kg |

### Comandos

```powershell
python -m unittest test_simulacion_carga -v
python simular_carga.py
```

Salida JSON: `simulacion_carga.json`

---

## Decisión Fase 3

### No parchear masas de carga en `.pak`

| Opción | Veredicto |
|--------|-----------|
| Bajar `Mass` en `cargo_*.xml` | **No** — afecta todos los contratos del juego, no solo CK1500 |
| Subir masa remolque / bajar carga | **No** — cambio global de balance de misiones |
| Mantener chasis 1750 kg (Fase 1) | **Sí** — ya alineado con K10 real |
| Simular vacío vs cargado | **Sí** — orienta expectativas en barro y cuestas |

Si en juego el CK1500 con remolque lleno resulta **demasiado capaz** en barro, el ajuste fino iría en motor (Fase 1) o neumáticos (Fase 2), no en multiplicar cientos de XML de carga.

**Fase 8** amplía esto: distribución longitudinal, tipo de acople (drawbar vs saddle) y masas reales de semi — ver **`FASE-8.md`**.

---

## Qué mirar en juego

1. **Vacío vs remolque + 2 slots** en barro medio (misma ruta Fase 2).
2. **Cuesta 12–15 %** con `mision_pesada` — ¿requiere marcha baja + diff lock?
3. **Aceleración en asfalto** cargado — ¿sensible pero jugable?
4. Comparar con **stock 2200 kg** desactivando mod (opcional) para sentir solo el efecto de carga.

---

## Archivos del proyecto

| Archivo | Rol |
|---------|-----|
| `simulador_ck1500.py` | `total_mass_kg`, `LOAD_SCENARIOS`, `run_cargo_matrix()` |
| `test_simulacion_carga.py` | Tests unittest Fase 3 |
| `simular_carga.py` | Informe consola + JSON |
| `simulacion_carga.json` | Resultados exportados |
| `FASE-3.md` | Este documento |

---

## Validación con telemetría (Fases 5–6)

| | |
|--|--|
| **Protocolos** | `f3_carga_barro`, `mh_f3_semi`, `fs_f3_carga` (auto si `payload_kg` &gt; 300) |
| **Parámetros diseño (XML/sim)** | `LOAD_SCENARIOS`, `total_mass_kg()` |
| **CE runtime** | `payload_kg` = masa Havok − vacío XML; `load_hint`, `trailer_id` |
| **Estado CE** | Calibrar con `scan_cargo.py`; re-grabar vacío vs cargado |
| **Criterio** | Delta velocidad cargado/vacío: sim y juego misma dirección |

```powershell
grabar_telemetria.bat
python cheat_engine/scan_cargo.py --diff vacio cargado
python importar_ce_csv.py --auto --compare
```

Ver **`docs/FASE-8.md`** y **`docs/FASE-6.md`**.

---

## Siguiente paso sugerido

**CK1500:** mod I6, offroad + diff lock, remolque `scout_trailer_offroad_cargo` con **vigas metal (2 slots)** en barro de Michigan / Alaska.

**MH9500:** semirremolque highway. Ver **`camiones/mh9500/FASES.md`** § Fase 3.

---

## MH9500 — carga (semirremolque)

| Escenario sim | Masa remolque | Carga útil | Uso |
|---------------|---------------|------------|-----|
| `semi_vacio` | 2500 kg | 0 | Baseline |
| `semi_cargado` | 2500 kg | **12000 kg** | Contrato pesado típico |

El MH9500 **no es un scout**: con ~19 t totales en barro el sim predice **inmovilidad** incluso con offroad + AWD — coherente con un camión de carretera sobrecargado.

```powershell
python simulador_mh9500.py
python -m unittest test_mh9500 -v
```
