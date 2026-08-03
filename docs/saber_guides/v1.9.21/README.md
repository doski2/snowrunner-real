# Integration of Trucks and Addons (Saber)

Copia local del material de [Google Drive
v1.9.21](https://drive.google.com/drive/u/0/folders/1IOWypnFu2uvij7jQG5xQ-hWDK4ZS0B3N).

| Archivo                                   | Origen                            | Páginas | Texto extraído                            |
| ----------------------------------------- | --------------------------------- | ------- | ----------------------------------------- |
| `Integration_of_Trucks_and_Addons.pdf`    | Steam `Sources/BinEditor/Guides/` | 167     | `Integration_of_Trucks_and_Addons.txt`    |
| `Integration_of_Trucks_and_Addons_RU.pdf` | Idem                              | 180     | `Integration_of_Trucks_and_Addons_RU.txt` |

**Versión en PDF:** 1.9.20 (11 Aug 2025). La carpeta Drive se llama v1.9.21; contenido alineado con
guía Saber actual.

## Índice de capítulos (EN)

| Capítulos | Tema                                                                            |
| --------- | ------------------------------------------------------------------------------- |
| 1–4       | Organización archivos, FBX, ejes, huesos Havok                                  |
| 5–6       | Estructura XML, templates, `_parent`                                            |
| 7–8       | Meshes, `<Truck>`, `<PhysicsModel>`, `<Body>`                                   |
| 9         | Suspensiones (`Strength`, `Height`, `SuspensionMin`)                            |
| 10        | Motores (`Torque`, `FuelConsumption`, `EngineResponsiveness`, `MaxDeltaAngVel`) |
| 11        | Cajas (`Gear`, `AngVel`, consumo AWD)                                           |
| 12–13     | Ruedas (`WheelFriction`, `SubstanceFriction`, tracks)                           |
| 14        | Addons                                                                          |
| 15        | Skins / colorización                                                            |
| 16        | DLC trucks                                                                      |
| 17–20     | Addons avanzados, farming trailers, agua, powered constraints                   |

## Parámetros que toca nuestro mod (`patches.py`)

Detalle Truck vs Engine y `<Body>` Havok: **`docs/FASE-1.md`** (§ Física modelada).

| XML               | Atributo               | Doc (sección)     | Notas Saber                                        |
| ----------------- | ---------------------- | ----------------- | -------------------------------------------------- |
| `<Body>`          | `Mass`                 | 8.4.2             | [0; 1 000 000] kg por body Havok                   |
| `<Body>`          | `CenterOfMassOffset`   | 8.4.2             | Desplaza CoG respecto al calculado por Havok       |
| `<Body>`          | `ForceBodyParams`      | 8.4.2             | Fuerza interacción barro/agua en bodies “pequeños” |
| `<Truck>`         | `FuelCapacity`         | 8. `<Truck>`      | Capacidad depósito                                 |
| `<Truck>`         | `Responsiveness`       | 8. `<Truck>`      | **Volante**, no motor [0; 1]                       |
| `<Engine>`        | `Torque`               | 10.1              | [0; 1 000 000] — no es cv                          |
| `<Engine>`        | `EngineResponsiveness` | 10.1              | Subida de rpm motor [0.01; 1]                      |
| `<Engine>`        | `MaxDeltaAngVel`       | 10.1              | Límite aceleración angular ruedas                  |
| `<Engine>`        | `FuelConsumption`      | 10.1              | [0; 100]                                           |
| `<Suspension>`    | `Strength` / `Height`  | 9. `<Suspension>` | Rigidez y altura por `WheelType`                   |
| `<WheelFriction>` | `BodyFriction`         | 12.3              | Tierra firme [0.1; 10]                             |
| `<WheelFriction>` | `BodyFrictionAsphalt`  | 12.3              | Asfalto                                            |
| `<WheelFriction>` | `SubstanceFriction`    | 12.3              | **Barro/sustancias** [0; 10]                       |

## Qué **no** cubre esta guía

- Menú TOOLS / dev en campaña (`tools_menu` es doc de mapas).
- `initial.cache_block`, telemetría, km/h en runtime.
- Terreno de mapa (viscosidad, wetness) — está en `.pak` de nivel.
- Curva de par del motor (un solo `Torque`).

## Logs

`LegacyLog.txt` en `Documents\My Games\SnowRunner\base\logs\` — errores al cargar/packing mods
(§1.4).

## RU vs EN

Mismo contenido técnico; RU tiene más páginas por maquetación. Usar EN para búsqueda en `.txt`.
