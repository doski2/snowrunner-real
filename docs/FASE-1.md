# SnowRunner — Modificación de parámetros (vehículos realistas)

> **Enfoque (jul 2026):** solo modificamos **archivos XML dentro de `initial.pak`**. Simulador
> orienta; prueba final **en juego**. CE archivado: **`CE-ARCHIVADO.md`**.

Proyecto para ajustar la física vehículo a vehículo con criterio de **realismo histórico**.
Prioridad: comportamiento creíble, no vmax.

---

## Vehículos del proyecto

| ID          | Vehículo         | Parches                         | Simulador                         | Doc                           |
| ----------- | ---------------- | ------------------------------- | --------------------------------- | ----------------------------- |
| `ck1500`    | Chevrolet CK1500 | `camiones/ck1500/patches.py`    | `sim/core.py`                     | `camiones/ck1500/FASES.md`    |
| `mh9500`    | GMC MH9500       | `camiones/mh9500/patches.py`    | `camiones/mh9500/simulador.py`    | `camiones/mh9500/FASES.md`    |
| `fleetstar` | Fleetstar F2070A | `camiones/fleetstar/patches.py` | `camiones/fleetstar/simulador.py` | `camiones/fleetstar/FASES.md` |
| `marshall`  | KHAN 39 Marshall | `camiones/marshall/patches.py`  | `camiones/marshall/simulador.py`  | `camiones/marshall/FASES.md`  |
| `kodiak`    | Kodiak C70       | `camiones/kodiak/patches.py`    | `camiones/kodiak/simulador.py`    | `camiones/kodiak/FASES.md`    |
| `scout800`  | Scout 800        | `camiones/scout800/patches.py`  | `camiones/scout800/simulador.py`  | `camiones/scout800/FASES.md`  |
| `t813`      | Tatra T813       | `camiones/t813/patches.py`      | `camiones/t813/simulador.py`      | `camiones/t813/FASES.md`      |
| `bandit`    | KRS 58 Bandit    | `camiones/bandit/patches.py`    | `camiones/bandit/simulador.py`    | `camiones/bandit/FASES.md`    |

`python apply_mod.py --list` · Registro: `camiones/registry.py`

---

## Estado por fase (qué toca el `.pak`)

| Fase   | Archivos XML                           | Rol                               |
| ------ | -------------------------------------- | --------------------------------- |
| 1      | Motor, chasis, suspensión              | **Mod**                           |
| 2      | `wheels_*.xml`                         | **Mod**                           |
| 3      | Masa chasis (Fase 1); no `cargo_*.xml` | Doc + sim                         |
| 4      | Neumático (Fase 2); terreno = mapa     | Doc + sim                         |
| 5–6    | —                                      | **Archivado** (`CE-ARCHIVADO.md`) |
| 7      | —                                      | No editable en camión             |
| 8      | Enganche camión; remolques globales    | Doc                               |

### Diseño (XML) vs validación

| Fuente               | Herramienta                                                |
| -------------------- | ---------------------------------------------------------- |
| **Producto: `.pak`** | `camiones/*/patches.py` → `apply_mod.py` → `verify_pak.py` |
| **Orientación**      | `camiones/*/simulador.py`                                  |
| **Prueba final**     | Instalar en Steam + conducir (km/h HUD, sensación)         |

**Archivos clave:** `initial.pak`, `initial.pak.bak`, `repack_pak.py`, `camiones/registry.py`

---

## CK1500 — Fase 1 (detalle)

Proyecto original: **Chevrolet CK1500** (K10 4x4 ~1971).

## Estado Fase 1 CK1500

| Tarea                            | Estado                                          |
| -------------------------------- | ----------------------------------------------- |
| Analisis XML + comparativa K10   | Hecho                                           |
| Simulador Python v3              | Hecho (`sim/core.py`, tests `camiones/ck1500/`) |
| Mod I6 en XML + `.pak`           | **Aplicado**                                    |
| Prueba en juego                  | Parcial                                         |

---

## Metodo: donde viven los parametros

Las reglas fisicas estan en **`.xml`** dentro de **`initial.pak`**:

| Ubicacion   | Ruta                                                                                         |
| ----------- | -------------------------------------------------------------------------------------------- |
| Steam       | `C:\Program Files (x86)\Steam\steamapps\common\SnowRunner\preload\paks\client\initial.pak`   |
| Proyecto    | `c:\Users\doski\snowrunner real\initial.pak`                                                 |

### Formato del `.pak` (importante)

- Es un **ZIP** seguido de un **tail de 1 768 bytes** (metadata Saber).
- Las rutas internas usan **backslash**: `[media]\classes\trucks\chevrolet_ck1500.xml`.
- Al **extraer** con 7-Zip salen archivos **planos** (`[media]?classes?trucks?...`), sin carpetas —

  igual en original y modificado.

- **No usar `7z u`** sobre el `.pak`: falla por el tail y puede corromper la estructura.

### Flujo de trabajo correcto

```powershell
```

`repack_pak.py` solo modifica las entradas listadas en `PATCHES`, copia el resto del ZIP y preserva
tail + orden de archivos.

---

## Caso de estudio: Chevrolet CK1500

Vehiculo **Scout** (`TruckType="SCOUT"`). Motor de serie: `us_scout_old_engine_0` (no modificado).
Mejora de taller: `us_scout_old_engine_ck1500` (**modificado**).

### Archivos tocados por el mod (CK1500)

Definidos en `camiones/ck1500/patches.py`:

| Ruta en `.pak`                                       | Qué cambia                                                         |
| ---------------------------------------------------- | ------------------------------------------------------------------ |
| `[media]/classes/trucks/chevrolet_ck1500.xml`        | Masa, depósito, CoG                                                |
| `[media]/classes/suspensions/s_chevrolet_ck1500.xml` | Strength delantera default                                         |
| `[media]/classes/engines/e_us_scout_old_ck1500.xml`  | Par, MaxDeltaAngVel, consumo — **solo con motor CK1500 en taller** |
| `[media]/classes/wheels/wheels_scout1.xml`           | Fase 2 — `highway_1` substance                                     |

> Los motores genericos (`e_us_scout_old.xml`: engine_0/1/2) **no** estan modificados. El camion de
> serie se nota mas ligero; la calibracion I6 fuerte requiere instalar el motor CK1500 en el taller.

### Valores: fabrica vs mod aplicado

#### Chasis — `chevrolet_ck1500.xml`

| Parametro                 | Fabrica          | Mod I6          | Efecto                                               |
| ------------------------- | ---------------- | --------------- | ---------------------------------------------------- |
| `Mass` chasis / trasero   | 1150 / 1050 kg   | **900 / 850**   | Total 1750 kg (cerca del K10 real)                   |
| `FuelCapacity`            | 80 L             | **76 L**        | 20 gal US                                            |
| `CenterOfMassOffset Y`    | -0.15            | **-0.20**       | Centro de gravedad algo mas bajo                     |
| `DefaultTire`             | `highway_1`      | sin cambio      | Stock malo en barro (`SubstanceFriction=0.2`)        |
| `DiffLockType`            | `Uninstalled`    | sin cambio      | Bloqueo es mejora de taller; ver nota DiffLock abajo |

> **No parchear** `Responsiveness` ni `SteerSpeed` en `<Truck>`: Saber los define como
> **volante** [0–1], no motor ni tracción (`Integration of Trucks and Addons` §8, guía local
> `docs/saber_guides/v1.9.21/`).

#### Suspension default — `s_chevrolet_ck1500.xml`

| Parametro              | Delantera fabrica   | Delantera mod   |
| ---------------------- | ------------------- | --------------- |
| `Strength`             | 0.035               | **0.045**       |
| `Damping` / `Height`   | 0.2 / 0.065         | sin cambio      |

#### Motor exclusivo — `e_us_scout_old_ck1500.xml`

| Parametro                | Fabrica   | Mod I6      | Notas                                                                        |
| ------------------------ | --------- | ----------- | ---------------------------------------------------------------------------- |
| `Torque`                 | 62000     | **40000**   | I6, no V8                                                                    |
| `MaxDeltaAngVel`         | **10**    | **0.015**   | Límite aceleración **angular de ruedas** (Saber); stock 10 = casi sin límite |
| `FuelConsumption`        | 3.3       | **1.5**     |                                                                              |
| `EngineResponsiveness`   | 0.4       | **0.28**    | Subida de rpm del motor                                                      |

---

## Comparativa real K10 (~1971) vs juego

Fuentes: [GM Heritage 1971 Truck
PDF](https://www.gm.com/content/dam/company/no_search/heritage-archive-docs/vehicle-information-kits/chevrolet-trucks/1971-Chevrolet-Truck.pdf),
[Wikipedia C/K 2nd gen](https://en.wikipedia.org/wiki/Chevrolet_C/K_(second_generation)).

| Parametro         | Real K10            | Juego fabrica                          | Mod I6              |
| ----------------- | ------------------- | -------------------------------------- | ------------------- |
| Peso vacio        | 1750–1860 kg        | 2200 kg                                | **1750 kg**         |
| Deposito          | ~76 L               | 80 L                                   | **76 L**            |
| Motor serie       | 250 I6 ~185 lb-ft   | engine_0, Torque 35000                 | sin cambio          |
| Motor mejora      | —                   | CK1500 62000 / MaxDeltaAngVel **10**   | **40000 / 0.015**   |
| 0-97 km/h (sim)   | 13–18 s             | ~1 s (motor CK1500 stock)              | **~18.5 s**         |

### Motores Scout en juego (referencia)

| Motor                               | Torque              | Modificado   |
| ----------------------------------- | ------------------- | ------------ |
| `us_scout_old_engine_0` (defecto)   | 35000               | No           |
| `us_scout_old_engine_1`             | 42000               | No           |
| `us_scout_old_engine_2`             | 50000               | No           |
| `us_scout_old_engine_ck1500`        | 62000 → **40000**   | **Si**       |

---

## Fisica modelada

### Atributos `<Truck>` vs `<Engine>` (Saber)

| Atributo XML                    | Archivo                 | Qué controla                                                                        |
| ------------------------------- | ----------------------- | ----------------------------------------------------------------------------------- |
| `Responsiveness`                | `classes/trucks/*.xml`  | **Volante** (respuesta dirección), no motor                                         |
| `SteerSpeed` / `BackSteerSpeed` | truck                   | Velocidad de giro / retorno del volante                                             |
| `EngineResponsiveness`          | `classes/engines/*.xml` | Subida de rpm del motor [0.01–1]                                                    |
| `MaxDeltaAngVel`                | motor                   | **Límite de aceleración angular de las ruedas**; menor = menos agresivo al acelerar |
| `Torque`                        | motor                   | Par motor (Ncm Saber; no es cv)                                                     |

`MaxDeltaAngVel` en juego: el motor no entrega par al instante; cada paso limita cuánto puede
subir la velocidad angular de las ruedas. El CK1500 con motor taller en stock usa **10** (casi sin
tope → aceleración arcade). El mod I6 usa **0.015** alineado con motores pesados vanilla (~0.01).

En `sim/core.py`, `max_delta_ang_vel` modela ese tope (`max_change = max_delta_ang_vel * ANGVEL_RAMP

 dt`).

### `<Body>` en `<PhysicsModel>` (Havok) — referencia

Fuente: `Integration of Trucks and Addons` §8.4.2 (`docs/saber_guides/v1.9.21/`). Parámetros que el
mod **no parchea hoy** pero útiles para masa/CoG (Fase 8):

| Atributo             | Default aprox. | Efecto                                                                                       |
| -------------------- | -------------- | -------------------------------------------------------------------------------------------- |
| `Mass`               | 0              | Masa del body [0; 1 000 000] kg — **sí parcheamos**                                          |
| `CenterOfMassOffset` | —              | Desplaza CoG respecto al calculado por Havok desde la colisión                               |
| `GravityFactor`      | 1              | Multiplicador de gravedad en el body                                                         |
| `AngularDamping`     | 0.05           | “Viscosidad” en rotación                                                                     |
| `LinearDamping`      | 0              | “Viscosidad” en traslación                                                                   |
| `Friction`           | 0.5            | Fricción body↔body (no es `WheelFriction`)                                                   |
| `ForceBodyParams`    | false          | Si `true`, fuerza interacción barro/agua en bodies “pequeños” (por defecto solo los grandes) |
| `Collisions`         | Default        | Quién colisiona con quién (None, All, Internal, …)                                           |
| `NetSync="pv"`       | —              | Sincronización multijugador de posición/velocidad del body                                   |

`DiffLockType` en truck (`Installed` / `Uninstalled`): Saber indica que solo el valor funcional
real es el bloqueo **Always** vía addon; el atributo del truck es etiqueta para modders.

### Cadena Saber (documentacion + XML)

```text
```

Fuente motor: [Saber Interactive —
Engine](https://expeditions-guides.saber.games/truck_modding/tags_and_attributes_of_trucks/enginevariants/engine/)

### Neumaticos Scout (`_templates/trucks.xml`)

| Tipo              | Substance (barro)   | Uso                           |
| ----------------- | ------------------- | ----------------------------- |
| highway (stock)   | **0.2**             | Casi sin traccion en barro    |
| offroad           | 1.2                 | Cambio en taller              |
| mudtires          | 1.6                 | Mejor en barro                |
| chains            | 1.1                 | Hielo/nieve (`IsIgnoreIce`)   |

### Simulador v3 (`simulador_ck1500.py`)

Aproxima: wheel slip, barro deformable, diff lock, agua/snorkel, dano motor, 9 terrenos.

#### Matriz I6 (km/h a 30 s)

| Neumatico   | Asfalto   | Barro   | Nieve   | Hielo   | Agua poco   |
| ----------- | --------- | ------- | ------- | ------- | ----------- |
| highway     | 150       | 0       | 107     | 2.3     | 0           |
| offroad     | 150       | 16      | 112     | 2.3     | 22          |
| mudtires    | 150       | 36      | 112     | 2.3     | 38          |
| chains      | 150       | 15      | 112     | 24.5    | 21          |

#### Escenarios clave (60 s, marcha baja)

| Escenario                 | v30   | Notas                           |
| ------------------------- | ----- | ------------------------------- |
| Barro highway stock       | 0     | Correcto — cambiar neumaticos   |
| Barro offroad sin diff    | 23    | Diff abierto desperdicia par    |
| Barro offroad con diff    | 40    |                                 |
| Agua profunda + snorkel   | 25    | Sin snorkel: 0                  |

#### Metricas objetivo (no vmax)

| Metrica           | Real K10     | Sim I6       |
| ----------------- | ------------ | ------------ |
| 0-97 km/h         | 13–18 s      | **18.5 s**   |
| Barro (highway)   | 5–15 km/h    | 0            |
| Barro (offroad)   | 25–40 km/h   | 16–40        |

**Limites del simulador:** no replica Havok completo, deformacion 3D del barro ni particulas. Sirve
para comparar tendencias antes/después del mod.

```powershell
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

## Validación en juego (Fases 1–4)

| Qué comprobar        | Cómo                                              |
| -------------------- | ------------------------------------------------- |
| XML aplicado         | `verify_pak.py --vehicle <id>`                    |
| Tendencia esperada   | `python -m camiones.<id>.simulador`               |
| Comportamiento real  | Misma ruta F1/F2/F3 en mapa; anotar km/h HUD      |
| Ajuste               | Si no cuadra → `patches.py` → `apply_mod.py`      |

Fases 5–6 (telemetría CE): **archivadas** — ver `CE-ARCHIVADO.md`.

### Pendiente opcional

- Cambiar motor por defecto a `us_scout_old_engine_ck1500` en XML del camion
- Calibrar tambien `us_scout_old_engine_0` para I6 sin pasar por taller
- Afinar torque a ~38000 si en juego sigue algo rapido
- Actualizar canvas `ck1500-simulacion.canvas.tsx`

---

*Documento del proyecto SnowRunner CK1500 — Fase 1.*
