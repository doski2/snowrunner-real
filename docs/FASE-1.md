# SnowRunner — Modificacion de parametros (vehiculos realistas)

Proyecto para ajustar la fisica vehiculo a vehiculo en SnowRunner con criterio de **realismo historico**. Prioridad: comportamiento creible, no vmax.

---

## Vehiculos del proyecto

| ID          | Vehiculo                       | Doc fases                      | Simulador                         | Estado mod |
|-------------|--------------------------------|--------------------------------|-----------------------------------|------------|
| `ck1500`    | Chevrolet CK1500 (K10 ~1971)   | `docs/FASE-1.md` … `FASE-8.md` | `sim/core.py`                     | Aplicado   |
| `mh9500`    | GMC MH9500 (Class 8 diesel)    | `camiones/mh9500/FASES.md`     | `camiones/mh9500/simulador.py`    | Aplicado   |
| `fleetstar` | International Fleetstar F2070A | `camiones/fleetstar/FASES.md`  | `camiones/fleetstar/simulador.py` | Aplicado   |
| `marshall`  | KHAN 39 Marshall               | `camiones/marshall/FASES.md`   | `camiones/marshall/simulador.py`  | Aplicado   |

Registro: `camiones/registry.py` · CLI: `apply_mod.py` · `.pak` por defecto incluye los tres.

---

## Estado del proyecto (junio 2026)

| Fase                 | CK1500                      | MH9500                         |
|----------------------|-----------------------------|--------------------------------|
| 1 Motor + chasis     | Hecho                       | Hecho                          |
| 2 Neumáticos         | Hecho (`wheels_scout1`)     | Hecho (`wheels_medium_double`) |
| 3 Carga              | Hecho (remolque scout)      | Hecho (semirremolque)          |
| 4 Terreno            | Doc + sim                   | Doc + sim                      |
| 5 Telemetría HUD     | Protocolos `f*`             | Protocolos `mh_*`              |
| 6 Cheat Engine Havok | **Operativo** — `FASE-6.md` | Mismo kit — **sin sesión CE**  |
| 7 Clima / tiempo     | Doc `FASE-7.md`             | Igual                          |
| 8 Remolques          | Doc `FASE-8.md`             | Semi ~4,3 t                    |
| Validación vs sim    | F2 offroad CE (MAE 16,8)    | Pendiente                      |

### Dos fuentes de datos (todas las fases)

| Fuente             | Qué define                       | Herramienta                                           |
|--------------------|----------------------------------|-------------------------------------------------------|
| **Diseño**         | Peso, motor, ruedas, carga (XML) | `simulador_*.py`, `verify_pak.py`                     |
| **Comportamiento** | Velocidad real en mapa           | Fase 5 HUD o **Fase 6 CE** → `comparar_telemetria.py` |

Cada `FASE-N.md` incluye § *Validación con telemetría* (protocolos, datos CE actuales y futuros).

**Archivos del proyecto**

| Archivo                                       | Funcion                                                       |
|-----------------------------------------------|---------------------------------------------------------------|
| `initial.pak`                                 | `.pak` modificado listo para instalar                         |
| `initial.pak.bak`                             | Copia del original Steam                                      |
| `vehiculos.py`                                | Parches XML por vehiculo (`CK1500_PATCHES`, `MH9500_PATCHES`) |
| `apply_mod.py`                                | CLI multi-vehiculo (default: todos)                           |
| `apply_ck1500_mod.py` / `apply_mh9500_mod.py` | Solo un vehiculo                                              |
| `repack_pak.py`                               | Parches XML + reempaquetado quirurgico del `.pak`             |
| `verify_pak.py`                               | Comprueba valores del mod dentro del `.pak`                   |
| `simulador_ck1500.py`                         | Simulacion base (4x4, 6 ruedas, RWD)                          |
| `simulador_mh9500.py`                         | Sim GMC MH9500                                                |
| `simulacion_resultados.json`                  | Salida del simulador CK1500                                   |
| `importar_ce_csv.py`                          | CSV Havok → sesión JSON                                       |
| `comparar_telemetria.py`                      | Juego vs sim (MAE)                                            |

---

# CK1500 — Fase 1 (detalle)

Proyecto original: **Chevrolet CK1500** (K10 4x4 ~1971).

## Estado Fase 1 CK1500

| Tarea                          | Estado                        |
|--------------------------------|-------------------------------|
| Analisis XML + comparativa K10 | Hecho                         |
| Simulador Python v3            | Hecho (`simulador_ck1500.py`) |
| Mod I6 en XML + `.pak`         | **Aplicado**                  |
| Prueba en juego                | Parcial                       |

---

## Metodo: donde viven los parametros

Las reglas fisicas estan en **`.xml`** dentro de **`initial.pak`**:

| Ubicacion | Ruta                                                                                       |
|-----------|--------------------------------------------------------------------------------------------|
| Steam     | `C:\Program Files (x86)\Steam\steamapps\common\SnowRunner\preload\paks\client\initial.pak` |
| Proyecto  | `c:\Users\doski\snowrunner real\initial.pak`                                               |

### Formato del `.pak` (importante)

- Es un **ZIP** seguido de un **tail de 1 768 bytes** (metadata Saber).
- Las rutas internas usan **backslash**: `[media]\classes\trucks\chevrolet_ck1500.xml`.
- Al **extraer** con 7-Zip salen archivos **planos** (`[media]?classes?trucks?...`), sin carpetas — igual en original y modificado.
- **No usar `7z u`** sobre el `.pak`: falla por el tail y puede corromper la estructura.

### Flujo de trabajo correcto

```powershell
# 1. Aplicar mod (lee parches del .bak de Steam y reempaqueta)
python "c:\Users\doski\snowrunner real\apply_ck1500_mod.py"

# 2. Verificar contenido XML dentro del .pak
python "c:\Users\doski\snowrunner real\verify_pak.py"

# 3. Instalar (renombrar original en Steam antes)
# Copiar initial.pak -> ...\SnowRunner\preload\paks\client\initial.pak
```

`repack_pak.py` solo modifica **3 entradas** del ZIP, copia cabeceras del original y preserva tail + orden de 10 969 archivos.

---

## Caso de estudio: Chevrolet CK1500

Vehiculo **Scout** (`TruckType="SCOUT"`). Motor de serie: `us_scout_old_engine_0` (no modificado). Mejora de taller: `us_scout_old_engine_ck1500` (**modificado**).

### Archivos tocados por el mod

| Ruta logica en `.pak`                        | Que cambia                                                         |
|----------------------------------------------|--------------------------------------------------------------------|
| `classes/trucks/chevrolet_ck1500.xml`        | Masa, deposito, CoG — **siempre activo**                           |
| `classes/suspensions/s_chevrolet_ck1500.xml` | Strength delantera default — **siempre activo**                    |
| `classes/engines/e_us_scout_old_ck1500.xml`  | Par, MaxDeltaAngVel, consumo — **solo con motor CK1500 instalado** |

> Los motores genericos (`e_us_scout_old.xml`: engine_0/1/2) **no** estan modificados. El camion de serie se nota mas ligero; la calibracion I6 fuerte requiere instalar el motor CK1500 en el taller.

### Valores: fabrica vs mod aplicado

#### Chasis — `chevrolet_ck1500.xml`

| Parametro               | Fabrica        | Mod I6        | Efecto                                        |
|-------------------------|----------------|---------------|-----------------------------------------------|
| `Mass` chasis / trasero | 1150 / 1050 kg | **900 / 850** | Total 1750 kg (cerca del K10 real)            |
| `FuelCapacity`          | 80 L           | **76 L**      | 20 gal US                                     |
| `CenterOfMassOffset Y`  | -0.15          | **-0.20**     | Centro de gravedad algo mas bajo              |
| `DefaultTire`           | `highway_1`    | sin cambio    | Stock malo en barro (`SubstanceFriction=0.2`) |
| `DiffLockType`          | `Uninstalled`  | sin cambio    | Bloqueo es mejora de taller                   |

#### Suspension default — `s_chevrolet_ck1500.xml`

| Parametro            | Delantera fabrica | Delantera mod |
|----------------------|-------------------|---------------|
| `Strength`           | 0.035             | **0.045**     |
| `Damping` / `Height` | 0.2 / 0.065       | sin cambio    |

#### Motor exclusivo — `e_us_scout_old_ck1500.xml`

| Parametro              | Fabrica | Mod I6    | Notas                           |
|------------------------|---------|-----------|---------------------------------|
| `Torque`               | 62000   | **40000** | I6, no V8                       |
| `MaxDeltaAngVel`       | **10**  | **0.015** | Fix critico (arcade → realista) |
| `FuelConsumption`      | 3.3     | **1.5**   |
| `EngineResponsiveness` | 0.4     | **0.28**  | 

---

## Comparativa real K10 (~1971) vs juego

Fuentes: [GM Heritage 1971 Truck PDF](https://www.gm.com/content/dam/company/no_search/heritage-archive-docs/vehicle-information-kits/chevrolet-trucks/1971-Chevrolet-Truck.pdf), [Wikipedia C/K 2nd gen](https://en.wikipedia.org/wiki/Chevrolet_C/K_(second_generation)).

| Parametro       | Real K10          | Juego fabrica                        | Mod I6            |
|-----------------|-------------------|--------------------------------------|-------------------|
| Peso vacio      | 1750–1860 kg      | 2200 kg                              | **1750 kg**       |
| Deposito        | ~76 L             | 80 L                                 | **76 L**          |
| Motor serie     | 250 I6 ~185 lb-ft | engine_0, Torque 35000               | sin cambio        |
| Motor mejora    | —                 | CK1500 62000 / MaxDeltaAngVel **10** | **40000 / 0.015** |
| 0-97 km/h (sim) | 13–18 s           | ~1 s (motor CK1500 stock)            | **~18.5 s**       |

### Motores Scout en juego (referencia)

| Motor                             | Torque            | Modificado |
|-----------------------------------|-------------------|------------|
| `us_scout_old_engine_0` (defecto) | 35000             | No         |
| `us_scout_old_engine_1`           | 42000             | No         |
| `us_scout_old_engine_2`           | 50000             | No         |
| `us_scout_old_engine_ck1500`      | 62000 → **40000** | **Si**     |

---

## Fisica modelada

### Cadena Saber (documentacion + XML)

```
Acelerador → EngineResponsiveness → MaxDeltaAngVel → Torque
  → Caja g_scout_default → Friccion neumatico → Traccion
  → Consumo (FuelConsumption × caja × marcha × AWD)
```

Fuente motor: [Saber Interactive — Engine](https://expeditions-guides.saber.games/truck_modding/tags_and_attributes_of_trucks/enginevariants/engine/)

### Neumaticos Scout (`_templates/trucks.xml`)

| Tipo            | Substance (barro) | Uso                         |
|-----------------|-------------------|-----------------------------|
| highway (stock) | **0.2**           | Casi sin traccion en barro  |
| offroad         | 1.2               | Cambio en taller            |
| mudtires        | 1.6               | Mejor en barro              |
| chains          | 1.1               | Hielo/nieve (`IsIgnoreIce`) |

### Simulador v3 (`simulador_ck1500.py`)

Aproxima: wheel slip, barro deformable, diff lock, agua/snorkel, dano motor, 9 terrenos.

**Matriz I6 (km/h a 30 s):**

| Neumatico | Asfalto | Barro | Nieve | Hielo | Agua poco |
|-----------|---------|-------|-------|-------|-----------|
| highway   | 150     | 0     | 107   | 2.3   | 0         |
| offroad   | 150     | 16    | 112   | 2.3   | 22        |
| mudtires  | 150     | 36    | 112   | 2.3   | 38        |
| chains    | 150     | 15    | 112   | 24.5  | 21        |

**Escenarios clave (60 s, marcha baja):**

| Escenario               | v30 | Notas                         |
|-------------------------|-----|-------------------------------|
| Barro highway stock     | 0   | Correcto — cambiar neumaticos |
| Barro offroad sin diff  | 23  | Diff abierto desperdicia par  |
| Barro offroad con diff  | 40  |                               |
| Agua profunda + snorkel | 25  | Sin snorkel: 0                |

**Metricas objetivo (no vmax):**

| Metrica         | Real K10   | Sim I6     |
|-----------------|------------|------------|
| 0-97 km/h       | 13–18 s    | **18.5 s** |
| Barro (highway) | 5–15 km/h  | 0          |
| Barro (offroad) | 25–40 km/h | 16–40      |

**Limites del simulador:** no replica Havok completo, deformacion 3D del barro ni particulas. Sirve para comparar tendencias antes/después del mod.

```powershell
python "c:\Users\doski\snowrunner real\simulador_ck1500.py"
```

---

## Instalacion en juego

1. Backup en Steam: renombrar `initial.pak` → `initial.pak.original`.
2. Copiar `c:\Users\doski\snowrunner real\initial.pak` a `...\preload\paks\client\`.
3. En taller del CK1500: instalar **motor CK1500** para notar MaxDeltaAngVel y torque I6.
4. Para barro: cambiar a neumaticos **offroad** o **mudtires**.

---

## Checklist

- [x] Rutas, herramientas, extraccion del `.pak`
- [x] XML CK1500 localizado y documentado
- [x] Comparativa K10 real vs juego
- [x] Simulador Python v3 + metricas
- [x] Mod I6 aplicado en 3 XML
- [x] Reempaquetado estructuralmente identico al original (`repack_pak.py`)
- [x] Script de verificacion (`verify_pak.py`)
- [ ] Prueba en juego y ajuste fino si hace falta

---

## Validación con telemetría (Fases 5–6)

| | |
|--|--|
| **Protocolos**                  | `f1_asfalto_i6`, `mh_f1_asfalto` |
| **Parámetros diseño (XML/sim)** | Torque, `MaxDeltaAngVel`, `Responsiveness`, masa chasis — `ENGINE_I6`, `simulador_*.py` |
| **CE / HUD mide**               | Curva `speed_kmh` vs tiempo en asfalto; `fuel_pct` (consumo relativo) |
| **Estado CE**                   | **Pendiente** `f1_asfalto_i6` |
| **Futuro CE**                   | Daño motor (`veh+0x148` → damage stat, re-validar offsets); RPM/par en vivo si se mapea `DRIVE_LOGIC` |
| **Criterio**                    | v30 juego vs sim: si juego >> sim → motor demasiado fuerte; si << → demasiado débil |

```powershell
python importar_ce_csv.py --protocol f1_asfalto_i6 --compare
```

Ver **`FASE-6.md`**.

### Pendiente opcional

- Cambiar motor por defecto a `us_scout_old_engine_ck1500` en XML del camion
- Calibrar tambien `us_scout_old_engine_0` para I6 sin pasar por taller
- Afinar torque a ~38000 si en juego sigue algo rapido
- Actualizar canvas `ck1500-simulacion.canvas.tsx`

---

*Documento del proyecto SnowRunner CK1500 — Fase 1.*
